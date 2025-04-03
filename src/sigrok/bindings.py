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
            f"{pkg_config['includedir']}/glib-2.0/glib/garray.h",
            f"{pkg_config['includedir']}/glib-2.0/glib/gmain.h",
        ],
        cache=str(
            platformdirs.user_cache_path("python-sigrok", ensure_exists=True)
            / "pyclibrary-cache"
        ),
    ),
)
