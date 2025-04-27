import logging
from collections.abc import Iterator

import pytest

from sigrok import (
    Channel,
    ChannelType,
    ConfigKey,
    Device,
    DeviceDriver,
    DeviceNotFoundError,
    EndPacket,
    HeaderPacket,
    LogicPacket,
    Packet,
    Sigrok,
    SigrokChannelNotFoundError,
    SigrokDriverNotFoundError,
)


def test_host_build_info() -> None:
    assert isinstance(Sigrok.get_host_build_info(), str)


def test_libs_build_info() -> None:
    for name, version in Sigrok.get_libs_build_info().items():
        assert isinstance(name, str), name
        assert isinstance(version, str), version


def test_get_scpi_backends_build_info() -> None:
    assert isinstance(Sigrok.get_scpi_backends_build_info(), str)


@pytest.fixture
def sr() -> Iterator[Sigrok]:
    with Sigrok() as sigrok:
        yield sigrok


class TestSigrok:
    def test_init_exit(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.exit()

    def test_double_init(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.init()

    def test_reinit(self) -> None:
        sr = Sigrok()
        sr.init()
        sr.exit()
        sr.init()

    def test_exit_without_init(self) -> None:
        sr = Sigrok()
        sr.exit()

    def test_context(self) -> None:
        with Sigrok():
            pass

    def test_del(self, sr: Sigrok) -> None:
        del sr

    def test_get_list_drivers(self, sr: Sigrok) -> None:
        for dr in sr.get_drivers():
            assert isinstance(dr, DeviceDriver)

    def test_get_list_drivers_when_uninitialized(self) -> None:
        assert Sigrok().get_drivers() == []

    def test_get_driver_by_name(self, sr: Sigrok) -> None:
        assert isinstance(sr.get_driver("demo"), DeviceDriver)

    def test_driver_not_found(self, sr: Sigrok) -> None:
        with pytest.raises(SigrokDriverNotFoundError):
            sr.get_driver("unknown")


@pytest.fixture
def dr(sr: Sigrok) -> Iterator[DeviceDriver]:
    with sr.get_driver("demo") as drv:
        yield drv


class TestDeviceDriver:
    def test_init(self, sr: Sigrok) -> None:
        drv = sr.get_driver("demo")
        drv.init()

    def test_properties(self, dr: DeviceDriver) -> None:
        assert dr.name == "demo"
        assert dr.longname == "Demo driver and pattern generator"

    def test_context(self, sr: Sigrok) -> None:
        with sr.get_driver("demo"):
            pass

    def test_get_scan_options(self, dr: DeviceDriver) -> None:
        scan_options = dr.get_scan_options()
        assert scan_options is not None
        assert set(scan_options) == {
            ConfigKey.SR_CONF_LIMIT_FRAMES,
            ConfigKey.SR_CONF_NUM_LOGIC_CHANNELS,
            ConfigKey.SR_CONF_NUM_ANALOG_CHANNELS,
        }

    def test_scan_without_options(self, dr: DeviceDriver) -> None:
        assert len(dr.scan()) == 1
        assert isinstance(dr.scan()[0], Device)

    def test_get_device(self, dr: DeviceDriver) -> None:
        dr.get_device()

    def test_get_device_by_idx(self, dr: DeviceDriver) -> None:
        dr.get_device(0)

    def test_get_devices_raise_no_device_found(self, dr: DeviceDriver) -> None:
        with pytest.raises(DeviceNotFoundError):
            dr.get_device(serial_number="0")

    def test_repr(self, dr: DeviceDriver) -> None:
        assert repr(dr) == "<driver demo>"

    def test_str(self, dr: DeviceDriver) -> None:
        assert str(dr) == "Demo driver and pattern generator"


@pytest.fixture
def dev(dr: DeviceDriver) -> Iterator[Device]:
    with dr.scan()[0] as dev:
        yield dev


class TestDevice:
    def test_open_close(self, dr: DeviceDriver) -> None:
        dev = dr.scan()[0]
        dev.open()
        dev.close()

    def test_context(self, dr: DeviceDriver) -> None:
        with dr.scan()[0]:
            pass

    def test_properties(self, dev: Device) -> None:
        assert dev.vendor is None
        assert dev.model == "Demo device"
        assert dev.serial_number is None
        assert dev.connection_identifier is None
        assert dev.version is None

    def test_repr(self, dev: Device) -> None:
        assert repr(dev) == "<device Demo device snr=None, connid=None>"

    def test_list_channels(self, dev: Device) -> None:
        for ch in dev.channels():
            assert isinstance(ch, Channel)

    def test_get_channel(self, dev: Device) -> None:
        ch = dev.channel("D0")
        assert isinstance(ch, Channel)

    def test_channel_not_found(self, dev: Device) -> None:
        with pytest.raises(SigrokChannelNotFoundError):
            dev.channel("unknown")

    def test_enable_channels(self, dev: Device) -> None:
        d1 = dev.channel("D1")
        dev.enable_channels("D0", d1)
        for ch in dev.channels():
            assert ch.enabled == (ch.name in ["D0", "D1"])

    def test_set_uint64_config(self, dev: Device) -> None:
        dev.set_config_uint64(ConfigKey.SR_CONF_SAMPLERATE, 100)

    def test_set_bool_config(self, dev: Device) -> None:
        dev.set_config_bool(ConfigKey.SR_CONF_AVERAGING, enabled=True)


@pytest.fixture
def ch(dev: Device) -> Channel:
    return dev.channel("D0")


class TestChannel:
    def test_properties(self, ch: Channel) -> None:
        assert ch.name == "D0"
        assert ch.index == 0
        assert ch.enabled is True
        assert ch.type == ChannelType.Logic

    def test_enabled(self, ch: Channel) -> None:
        ch.enabled = False
        assert ch.enabled is False
        ch.enabled = True
        assert ch.enabled is True

    def test_enable(self, ch: Channel) -> None:
        ch.enabled = False
        ch.enable()
        assert ch.enabled is True

    def test_disable(self, ch: Channel) -> None:
        ch.disable()
        assert ch.enabled is False


class TestLogging:
    def test_logs_messages(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG):
            Sigrok()
        assert caplog.records

    def test_adhere_to_log_level(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO):
            Sigrok()
        assert not caplog.records

    def test_logger_name(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.DEBUG, "sigrok.log"):
            Sigrok()
        assert caplog.records


class TestRun:
    def test_complete_run(self) -> None:
        packets = []
        expected_packets = 3
        expected_logic_length = 4096

        def cb(_device: Device, packet: Packet) -> bool:
            packets.append(packet)
            return len(packets) <= 1

        with (
            Sigrok() as sr,
            sr.get_driver("demo") as driver,
            driver.scan()[0] as device,
        ):
            for channel in device.channels():
                channel.enabled = channel.type == ChannelType.Logic
            sr.run(cb, [device])

        assert len(packets) == expected_packets
        header = packets[0]
        logic = packets[1]
        end = packets[2]

        assert isinstance(header, HeaderPacket)
        assert header.feed_version == 1

        assert isinstance(logic, LogicPacket)
        assert logic.unitsize == 1
        assert logic.length == expected_logic_length
        assert len(logic.data) == logic.length

        assert isinstance(end, EndPacket)
