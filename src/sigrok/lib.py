import itertools
from ctypes import POINTER, cast

import pkgconfig
import platformdirs
from pyclibrary import CLibrary, CParser

pc_vars = pkgconfig.variables("libsigrok")

parser = CParser(
    [
        f"{pc_vars['includedir']}/libsigrok/libsigrok.h",
        f"{pc_vars['includedir']}/libsigrok/version.h",
        f"{pc_vars['includedir']}/libsigrok/proto.h",
        f"{pc_vars['includedir']}/glib-2.0/glib/gslist.h",
        f"{pc_vars['includedir']}/glib-2.0/glib/gtypes.h",
        f"{pc_vars['includedir']}/glib-2.0/glib/gvariant.h",
    ],
    cache=str(
        platformdirs.user_cache_path("python-sigrok", ensure_exists=True)
        / "pyclibrary-cache"
    ),
)

c = CLibrary(f"{pc_vars['libdir']}/libsigrok.so", parser)

ret = c.sr_buildinfo_libs_get()
for o in itertools.count():
    outer = c.g_slist_nth_data(cast(ret.rval, POINTER(c.GSList)), o)
    if outer.rval is None:
        break

    name = b"".join(
        itertools.takewhile(
            lambda a: a != b"\x00",
            (
                cast(
                    c.g_slist_nth_data(cast(outer.rval, POINTER(c.GSList)), 0).rval,
                    POINTER(c.gchar),
                )[i]
                for i in itertools.count()
            ),
        )
    )
    version = b"".join(
        itertools.takewhile(
            lambda a: a != b"\x00",
            (
                cast(
                    c.g_slist_nth_data(cast(outer.rval, POINTER(c.GSList)), 1).rval,
                    POINTER(c.gchar),
                )[i]
                for i in itertools.count()
            ),
        )
    )
    print(name, version)  # noqa: T201

c.g_slist_free(ret.rval)

ret = c.sr_init()
if ret.rval != 0:
    raise RuntimeError(ret.rval)

ctx = ret["ctx"]

ret = c.sr_driver_list(ctx)
if ret.rval is None:
    raise RuntimeError(ret.rval)

drvs = cast(ret.rval, POINTER(POINTER(c.sr_dev_driver)))

for i in itertools.count():
    if not drvs[i]:
        break

    print(i, drvs[i].contents.name, drvs[i].contents.longname)  # noqa: T201

ret = c.sr_exit(ctx)
if ret.rval != 0:
    raise RuntimeError(ret.rval)
