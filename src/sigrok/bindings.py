import pkgconfig
import platformdirs
from pyclibrary import CLibrary, CParser

pkg_config = pkgconfig.variables("libsigrok")
lib = CLibrary(
    f"{pkg_config['libdir']}/libsigrok.so",
    CParser(
        [
            f"{pkg_config['includedir']}/libsigrok/libsigrok.h",
            f"{pkg_config['includedir']}/libsigrok/version.h",
            f"{pkg_config['includedir']}/libsigrok/proto.h",
            f"{pkg_config['includedir']}/glib-2.0/glib/gslist.h",
            f"{pkg_config['includedir']}/glib-2.0/glib/gtypes.h",
            f"{pkg_config['includedir']}/glib-2.0/glib/gvariant.h",
        ],
        cache=str(
            platformdirs.user_cache_path("python-sigrok", ensure_exists=True)
            / "pyclibrary-cache"
        ),
    ),
)

"""
    ret = sr.sr_driver_list(ctx)
    if ret.rval is None:
        raise RuntimeError(ret.rval)

    drvs = ct.cast(ret.rval, ct.POINTER(ct.POINTER(sr.sr_dev_driver)))

    for i in itertools.count():
        if not drvs[i]:
            break

        print(i, drvs[i].contents.name, drvs[i].contents.longname)  # noqa: T201

    ret = sr.sr_exit(ctx)
    if ret.rval != 0:
        raise RuntimeError(ret.rval)
"""
