import abc
import ctypes as ct
import itertools
from collections.abc import Iterator
from contextlib import suppress
from types import TracebackType
from typing import Any, ClassVar, Self

from pyclibrary.c_library import CallResult

from sigrok.bindings import lib


class SigrokError(Exception):
    pass


class SigrokCError(SigrokError, metaclass=abc.ABCMeta):
    Code: int
    Message: str

    ErrorClasses: ClassVar[dict[int, type["SigrokCError"]]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        with suppress(AttributeError):
            cls.ErrorClasses[cls.Code] = cls

    @classmethod
    def from_error_code(cls, code: int, *, hint: str) -> "SigrokCError":
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
    if result.rval != 0:
        raise SigrokCError.from_error_code(result.rval, hint=hint)
    return result


def _consume_g_slist(slist: Any) -> Iterator[Any]:
    gslist = ct.cast(slist, ct.POINTER(lib.GSList))
    try:
        for o in itertools.count():
            outer = lib.g_slist_nth_data(gslist, o)
            if outer.rval is None:
                break

            yield outer.rval
    finally:
        lib.g_slist_free(gslist)


class Sigrok:
    @staticmethod
    def get_libs_build_info() -> dict[str, str]:
        lib_versions = lib.sr_buildinfo_libs_get().rval
        return {
            ct.cast(name_version[0], ct.c_char_p).value.decode("utf-8"): ct.cast(
                name_version[1], ct.c_char_p
            ).value.decode("utf-8")
            for version_tuple in _consume_g_slist(lib_versions)
            if (name_version := list(_consume_g_slist(version_tuple)))
        }

    @staticmethod
    def get_host_build_info() -> str:
        return ct.cast(lib.sr_buildinfo_host_get().rval, ct.c_char_p).value.decode(
            "utf-8"
        )

    @staticmethod
    def get_scpi_backends_build_info() -> str:
        return ct.cast(
            lib.sr_buildinfo_scpi_backends_get().rval, ct.c_char_p
        ).value.decode("utf-8")

    def __init__(self) -> None:
        self._c: lib.sr_context | None = None

    def init(self) -> None:
        self._c = ct.cast(_try(lib.sr_init())["ctx"], ct.POINTER(lib.sr_context))

    def exit(self) -> None:
        if self._c is not None:
            _try(lib.sr_exit(self._c))
            self._c = None

    def __del__(self) -> None:
        self.exit()

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
