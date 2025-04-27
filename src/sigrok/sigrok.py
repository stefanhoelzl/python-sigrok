from __future__ import annotations

import abc
import ctypes as ct
import enum
import importlib.resources
import itertools
import logging
import os
import queue
import threading
from contextlib import suppress
from typing import TYPE_CHECKING, Any, ClassVar

from sigrok.bindings import Pointer, lib

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path
    from types import TracebackType

    from pyclibrary.c_library import CallResult  # type: ignore[import-untyped]
    from typing_extensions import Self


sigrok_logger = logging.getLogger("sigrok")


class SigrokError(Exception):
    pass


class SigrokCError(SigrokError, metaclass=abc.ABCMeta):
    Code: int
    Message: str

    ErrorClasses: ClassVar[dict[int, type[SigrokCError]]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        with suppress(AttributeError):
            cls.ErrorClasses[cls.Code] = cls

    @classmethod
    def from_error_code(cls, code: int, *, hint: str) -> SigrokCError:
        if error_class := cls.ErrorClasses.get(code):
            return error_class(hint=hint)
        return SigrokCUnknownError(code, hint=hint)

    def __init__(self, *, hint: str) -> None:
        super().__init__(f"[{self.Code}] {self.Message} ({hint})")
        self.value = hint


class SigrokCUnknownError(SigrokCError):
    Message = "unknown error"

    def __init__(self, code: int, *, hint: str) -> None:
        self.Code = code
        super().__init__(hint=hint)


class SigrokGenericError(SigrokCError):
    Code = -1
    Message = "Generic/unspecified error"


class SigrokMallocError(SigrokCError):
    Code = -2
    Message = "malloc/calloc/realloc error"


class SigrokArgError(SigrokCError):
    Code = -3
    Message = "function argument error"


class SigrokBugError(SigrokCError):
    Code = -4
    Message = "error hinting internal bugs"


class SigrokSampleRateError(SigrokCError):
    Code = -5
    Message = "incorrect sample rate"


class SigrokNotApplicableError(SigrokCError):
    Code = -6
    Message = "not applicable"


class SigrokDeviceClosedError(SigrokCError):
    Code = -7
    Message = "device is closed, but must be open"


class SigrokTimeoutError(SigrokCError):
    Code = -8
    Message = "a timeout occured"


class SigrokChannelGroupError(SigrokCError):
    Code = -9
    Message = "a channel group must be specified"


class SigrokDataError(SigrokCError):
    Code = -10
    Message = "data is invalid"


class SigrokIOError(SigrokCError):
    Code = -11
    Message = "input/output error"


def _try(result: CallResult, hint: str = "") -> CallResult:
    if result.rval < 0:
        raise SigrokCError.from_error_code(result.rval, hint=hint)
    return result


class DeviceNotFoundError(SigrokError):
    def __init__(self) -> None:
        super().__init__("no matching device found")


def _iter_g_slist(slist: Any) -> Iterator[Any]:
    gslist = _cast_p(slist, lib.GSList)
    for idx in itertools.count():
        value = lib.g_slist_nth_data(gslist, idx).rval
        if value is None:
            break
        yield value


def _consume_g_slist(slist: Any) -> Iterator[Any]:
    try:
        yield from _iter_g_slist(slist)
    finally:
        lib.g_slist_free(_cast_p(slist, lib.GSList))


def _consume_g_array(array: Any, dt: Any) -> Iterator[Any]:
    garray = _cast_p(array, lib.GArray)
    # garray.contents.data gets interpreted as bytes,
    # therefore we access array.contents.contents
    # this works because since data is the first element in the garray struct
    values_p_p = _cast_p(array, ct.POINTER(dt * garray.contents.len))
    try:
        yield from values_p_p.contents.contents
    finally:
        lib.g_array_free(garray, free_segment=True)


def _cast_p(value: Any, dt: Any) -> Any:
    return ct.cast(value, ct.POINTER(dt))


class ChannelType(enum.IntEnum):
    Analog = lib.SR_CHANNEL_ANALOG
    Logic = lib.SR_CHANNEL_LOGIC


class Channel:
    def __init__(self, ch: Pointer[lib.type_sr_channel]) -> None:
        self._ch = ch

    @property
    def name(self) -> str:
        return self._ch.contents.name.decode("utf-8")

    @property
    def enabled(self) -> bool:
        return bool(self._ch.contents.enabled)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        _try(lib.sr_dev_channel_enable(self._ch, value))

    @property
    def type(self) -> ChannelType:
        return ChannelType(self._ch.contents.type)

    @property
    def index(self) -> int:
        return self._ch.contents.index

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def __repr__(self) -> str:
        return f"<{self.type.name.lower()} channel {self.name} (idx={self.index} enabled={self.enabled})>"


class SigrokChannelNotFoundError(SigrokError):
    def __init__(self, name: str, channels: list[str]) -> None:
        super().__init__(f"{name} (available channels: {', '.join(channels)})")
        self.name = name
        self.channels = channels


if TYPE_CHECKING:
    ConfigKey = lib.type_sr_configkey
else:
    ConfigKey = enum.IntEnum("ConfigKey", lib.sr_configkey)  # type: ignore[misc]


class Device:
    def __init__(self, dev: Pointer[lib.type_sr_dev_inst]) -> None:
        self._dev = dev

    @property
    def vendor(self) -> str | None:
        if vendor := lib.sr_dev_inst_vendor_get(self._dev).rval:
            return vendor.decode("utf-8")
        return None

    @property
    def model(self) -> str | None:
        if model := lib.sr_dev_inst_model_get(self._dev).rval:
            return model.decode("utf-8")
        return None

    @property
    def version(self) -> str | None:
        if model := lib.sr_dev_inst_version_get(self._dev).rval:
            return model.decode("utf-8")
        return None

    @property
    def serial_number(self) -> str | None:
        if serial_number := lib.sr_dev_inst_sernum_get(self._dev).rval:
            return serial_number.decode("utf-8")
        return None

    @property
    def connection_identifier(self) -> str | None:
        if connid := lib.sr_dev_inst_connid_get(self._dev).rval:
            return connid.decode("utf-8")
        return None

    def channels(self) -> list[Channel]:
        return [
            Channel(_cast_p(ch, lib.sr_channel))
            for ch in _iter_g_slist(lib.sr_dev_inst_channels_get(self._dev).rval)
        ]

    def channel(self, name: str) -> Channel:
        for channel in self.channels():
            if channel.name == name:
                return channel
        raise SigrokChannelNotFoundError(name, list(map(str, self.channels())))

    def enable_channels(self, *channels: Channel | str) -> None:
        channels_to_enable = [
            ch.name if isinstance(ch, Channel) else ch for ch in channels
        ]
        for ch in self.channels():
            ch.enabled = ch.name in channels_to_enable

    def open(self) -> None:
        _try(lib.sr_dev_open(self._dev))

    def close(self) -> None:
        _try(lib.sr_dev_close(self._dev))

    def set_config_uint64(self, config_key: ConfigKey, value: int) -> None:
        self._set_config(config_key, lib.g_variant_new_uint64(value).rval)

    def set_config_int32(self, config_key: ConfigKey, value: int) -> None:
        self._set_config(config_key, lib.g_variant_new_int32(value).rval)

    def set_config_double(self, config_key: ConfigKey, value: float) -> None:
        self._set_config(config_key, lib.g_variant_new_double(value).rval)

    def set_config_bool(self, config_key: ConfigKey, *, enabled: bool) -> None:
        self._set_config(config_key, lib.g_variant_new_boolean(enabled).rval)

    def set_config_string(self, config_key: ConfigKey, value: str) -> None:
        self._set_config(
            config_key, lib.g_variant_new_string(value.encode("utf-8")).rval
        )

    def _set_config(self, config_key: ConfigKey, gvariant_ptr: int) -> None:
        _try(lib.sr_config_set(self._dev, None, config_key.value, gvariant_ptr))

    def __enter__(self) -> Self:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<device {self.model} snr={self.serial_number}, connid={self.connection_identifier}>"


class DeviceDriver:
    def __init__(
        self, sr: Pointer[lib.type_sr_context], dr: Pointer[lib.type_sr_dev_driver]
    ) -> None:
        self._sr = sr
        self._dr: Pointer[lib.type_sr_dev_driver] = _cast_p(dr, lib.sr_dev_driver)

    @property
    def name(self) -> str:
        return self._dr.contents.name.decode("utf-8")

    @property
    def longname(self) -> str:
        return self._dr.contents.longname.decode("utf-8")

    def init(self) -> None:
        _try(lib.sr_driver_init(self._sr, self._dr))

    def __enter__(self) -> Self:
        self.init()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        pass

    def get_scan_options(self) -> list[ConfigKey] | None:
        garray = lib.sr_driver_scan_options_list(self._dr).rval
        return [ConfigKey(cfg_key) for cfg_key in _consume_g_array(garray, ct.c_uint32)]

    def scan(self) -> list[Device]:
        slist = lib.sr_driver_scan(self._dr, options=None).rval
        if slist is None:
            return []
        return [
            Device(dev=_cast_p(x, lib.sr_dev_inst)) for x in _consume_g_slist(slist)
        ]

    def get_device(self, idx: int = 0, *, serial_number: str | None = None) -> Device:
        devices = [
            device
            for device in self.scan()
            if serial_number is None or device.serial_number == serial_number
        ]
        try:
            return devices[idx]
        except IndexError as e:
            raise DeviceNotFoundError from e

    def __str__(self) -> str:
        return self.longname

    def __repr__(self) -> str:
        return f"<driver {self.name}>"


class Packet:
    def __init__(
        self, packet: Pointer[lib.type_sr_datafeed_packet], device: Device
    ) -> None:
        self.type = packet.contents.type
        self.device = device

    def __repr__(self) -> str:
        return f"<packet type={self.type}>"


class HeaderPacket(Packet):
    def __init__(
        self, packet: Pointer[lib.type_sr_datafeed_packet], device: Device
    ) -> None:
        super().__init__(packet, device)
        payload = _cast_p(packet.contents.payload, lib.sr_datafeed_header)
        self.feed_version = payload.contents.feed_version

    def __repr__(self) -> str:
        return f"<header feed_version={self.feed_version}>"


class EndPacket(Packet):
    def __repr__(self) -> str:
        return "<datafeed end>"


class LogicPacket(Packet):
    def __init__(
        self, packet: Pointer[lib.type_sr_datafeed_packet], device: Device
    ) -> None:
        super().__init__(packet, device)
        payload = _cast_p(packet.contents.payload, lib.sr_datafeed_logic)
        self.length = payload.contents.length
        self.unitsize = payload.contents.unitsize
        self.data = bytes(
            ct.cast(
                payload.contents.data, ct.POINTER(ct.c_ubyte * self.length)
            ).contents
        )

    def __repr__(self) -> str:
        return f"<logic packet {self.data[:8].hex(sep=' ').upper()}... {self.length}>"


def parse_packet(
    packet: Pointer[lib.type_sr_datafeed_packet], device: Device
) -> Packet:
    if packet.contents.type == lib.SR_DF_HEADER:
        return HeaderPacket(packet, device)
    if packet.contents.type == lib.SR_DF_END:
        return EndPacket(packet, device)
    if packet.contents.type == lib.SR_DF_LOGIC:
        return LogicPacket(packet, device)
    return Packet(packet, device)


class Session:
    def __init__(self, sess: Pointer[lib.type_sr_session]) -> None:
        self._sess = sess
        self._queue: queue.Queue[Packet] = queue.Queue()
        self._thread = threading.Thread(
            target=lambda: _try(lib.sr_session_run(self._sess)), daemon=True
        )
        self._packet_callback = lib.sr_session_datafeed_callback_add.arg_types[1](  # type: ignore[attr-defined]
            lambda dev, packet, _data: self._queue.put(
                parse_packet(
                    _cast_p(packet, lib.sr_datafeed_packet),
                    Device(dev=_cast_p(dev, lib.sr_dev_inst)),
                )
            )
        )

    def add_device(self, device: Device) -> None:
        _try(lib.sr_session_dev_add(self._sess, device._dev))  # noqa: SLF001 access private member

    @property
    def is_running(self) -> bool:
        return bool(_try(lib.sr_session_is_running(self._sess)).rval)

    def next_packet(self, timeout: float | None = None) -> Packet:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty as e:
            raise TimeoutError(timeout) from e

    def start(self) -> None:
        _try(
            lib.sr_session_datafeed_callback_add(
                self._sess, self._packet_callback, None
            )
        )

        _try(lib.sr_session_start(self._sess))
        self._thread.start()

    def stop(self) -> None:
        _try(lib.sr_session_stop(self._sess))
        self._thread.join()
        _try(lib.sr_session_datafeed_callback_remove_all(self._sess))

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.stop()

    def __del__(self) -> None:
        _try(lib.sr_session_destroy(self._sess))


class SigrokDriverNotFoundError(SigrokError):
    def __init__(self, name: str, drivers: list[str]) -> None:
        super().__init__(f"{name} (available drivers: {', '.join(drivers)})")
        self.name = name
        self.drivers = drivers


LogLevelMapping = {
    lib.SR_LOG_ERR: logging.ERROR,
    lib.SR_LOG_WARN: logging.WARNING,
    lib.SR_LOG_INFO: logging.INFO,
    lib.SR_LOG_DBG: logging.DEBUG,
    lib.SR_LOG_SPEW: logging.DEBUG,
}


def log_callback(_data: None, level: int, log: bytes, args: int) -> int:
    log_level = LogLevelMapping.get(level, logging.DEBUG)
    logger = sigrok_logger

    buf = (ct.c_char * 1024)()
    lib.sr_vsprintf_ascii(buf, log, args)

    logger_message = buf.value.decode("utf-8").split(": ", maxsplit=1)
    if len(logger_message) == 1:
        message = logger_message[0]
        logger = sigrok_logger
    else:
        message = logger_message[1]
        logger = logger.getChild(logger_message[0])

    logger.log(log_level, message)

    return 0


c_log_callback = lib.sr_log_callback_set.arg_types[0](log_callback)  # type: ignore[attr-defined]


class Sigrok:
    @staticmethod
    def get_libs_build_info() -> dict[str, str]:
        lib_versions = lib.sr_buildinfo_libs_get().rval
        return {
            name.decode("utf-8"): version.decode("utf-8")
            for version_tuple in _consume_g_slist(lib_versions)
            if (name_version := list(_consume_g_slist(version_tuple)))
            if (name := ct.cast(name_version[0], ct.c_char_p).value)
            if (version := ct.cast(name_version[1], ct.c_char_p).value)
        }

    @staticmethod
    def get_host_build_info() -> str:
        if buildinfo := ct.cast(lib.sr_buildinfo_host_get().rval, ct.c_char_p).value:  # type: ignore[arg-type]
            return buildinfo.decode("utf-8")
        return ""

    @staticmethod
    def get_scpi_backends_build_info() -> str:
        if buildinfo := ct.cast(
            lib.sr_buildinfo_scpi_backends_get().rval,  # type: ignore[arg-type]
            ct.c_char_p,
        ).value:
            return buildinfo.decode("utf-8")
        return ""

    def __init__(
        self,
        *,
        redirect_logging: bool = True,
        log_level: int = 5,
        firmware_path: Path | None = None,
    ) -> None:
        self._sr: Pointer[lib.type_sr_context] | None = None

        if redirect_logging:
            _try(lib.sr_log_callback_set(c_log_callback, None))
            _try(lib.sr_log_loglevel_set(log_level))

        if firmware_path is None:
            firmware_path = importlib.resources.path("sigrok", "firmware").__enter__()
        os.environ["SIGROK_FIRMWARE_DIR"] = str(firmware_path.absolute())

    def init(self) -> None:
        self._sr = _cast_p(_try(lib.sr_init())["ctx"], lib.sr_context)

    def exit(self) -> None:
        if self._sr is not None:
            _try(lib.sr_exit(self._sr))
            self._sr = None

    def get_drivers(self) -> list[DeviceDriver]:
        if self._sr is None:
            return []

        if (ptr := lib.sr_driver_list(self._sr).rval) == 0:
            return []

        drivers: Iterable[lib.sr_dev_driver] = _cast_p(  # type: ignore[valid-type]
            ptr,
            ct.POINTER(lib.sr_dev_driver),  # type: ignore[call-overload]
        )
        return [
            DeviceDriver(self._sr, driver)
            for driver in itertools.takewhile(lambda drv: drv, drivers)
        ]

    def get_driver(self, name: str) -> DeviceDriver:
        for driver in self.get_drivers():
            if driver.name == name:
                return driver
        raise SigrokDriverNotFoundError(name, list(map(repr, self.get_drivers())))

    def session(self, *, devices: list[Device] | Device | None = None) -> Session:
        session = Session(
            sess=ct.cast(
                _try(lib.sr_session_new(self._sr))["session"],
                ct.POINTER(lib.sr_session),  # type: ignore[call-overload]
            )
        )

        if devices is None:
            devices = []
        elif isinstance(devices, Device):
            devices = [devices]

        for device in devices:
            session.add_device(device)

        return session

    def __enter__(self) -> Self:
        self.init()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exit()

    def __del__(self) -> None:
        self.exit()
