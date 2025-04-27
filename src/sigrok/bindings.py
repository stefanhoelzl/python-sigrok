import contextlib
import importlib.metadata
import importlib.resources
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, NamedTuple, Protocol, TypeVar

import pkgconfig
import platformdirs
from pyclibrary import CLibrary, CParser

_T = TypeVar("_T")


class Pointer(Protocol[_T]):
    contents: _T


class LibPaths(NamedTuple):
    libsigrok: Path
    libsigrok_includes: Path
    glib_includes: Path


@contextlib.contextmanager
def platform_lib_paths() -> Iterator[LibPaths]:
    platform: Literal["linux", "windows"]
    if sys.platform.startswith("linux"):
        platform = "linux"
    elif sys.platform == "darwin":
        platform = "macos"
    elif sys.platform.startswith("win"):
        platform = "windows"
    else:
        raise RuntimeError(f"unsupported platform: {sys.platform}")

    if platform == "windows":
        target = "x86_64" if sys.maxsize > 2**32 else "i686"
        with importlib.resources.path(
            "sigrok", f"libsigrok-windows-{target}"
        ) as dll_path:
            yield LibPaths(
                libsigrok=dll_path / "libsigrok.dll",
                libsigrok_includes=dll_path / "include/libsigrok",
                glib_includes=dll_path / "include/glib",
            )
    else:
        libsigrok_config = pkgconfig.variables("libsigrok")
        glib_config = pkgconfig.variables("glib-2.0")

        yield LibPaths(
            libsigrok=Path(libsigrok_config["libdir"], "libsigrok").with_suffix(
                ".dylib" if platform == "macos" else ".so"
            ),
            libsigrok_includes=Path(libsigrok_config["includedir"], "libsigrok"),
            glib_includes=Path(glib_config["includedir"], "glib-2.0/glib"),
        )


with (
    platform_lib_paths() as lib_paths,
    importlib.resources.path("sigrok", "include") as package_includes,
):
    cache_path = (
        platformdirs.user_cache_path("python-sigrok", ensure_exists=True)
        / f"libsigrok.{importlib.metadata.version('sigrok')}.pyclibrary.cache"
    )
    if not cache_path.exists():
        logging.getLogger("sigrok").warning(
            "parsing header files on first invocation. this may take a while!"
        )
    lib = CLibrary(
        str(lib_paths.libsigrok.absolute()),
        CParser(
            [
                str(lib_paths.libsigrok_includes.absolute() / "libsigrok.h"),
                str(lib_paths.libsigrok_includes.absolute() / "version.h"),
                str(lib_paths.libsigrok_includes.absolute() / "proto.h"),
                str(lib_paths.glib_includes.absolute() / "gslist.h"),
                str(lib_paths.glib_includes.absolute() / "gtypes.h"),
                str(lib_paths.glib_includes.absolute() / "gvariant.h"),
                str(lib_paths.glib_includes.absolute() / "garray.h"),
                str(lib_paths.glib_includes.absolute() / "gmain.h"),
                str(package_includes.absolute() / "fixes.h"),
            ],
            cache=str(cache_path),
        ),
    )
