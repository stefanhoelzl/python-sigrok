set -e

export TARGET=${TARGET:-x86_64}
export MXE_TARGET="${TARGET}-w64-mingw32.static.posix"

export BASE_DIR=$(pwd)
export BUILD_DIR="${BASE_DIR}/build"
export MXE_DIR="${BUILD_DIR}/mxe"
export USR_DIR="${BUILD_DIR}/usr"
export INSTALL_DIR="${USR_DIR}/${MXE_TARGET}"
export CCACHE_DIR="${BUILD_DIR}/cache"
export DIST_DIR="${BASE_DIR}/dist"

export GIT_CLONE="git clone"
export GIT_CLEAN="git clean -fdx"
export GIT_RESET="git reset --hard"

export MXE_REPO="https://github.com/mxe/mxe.git"
export MXE_REF="b48b3cc7085548e896fe967dc6371ff9951390a4"
export LIBSERIALPORT_REPO="https://github.com/sigrokproject/libserialport.git"
export LIBSERIALPORT_REF="21b3dfe5f68c205be4086469335fd2fc2ce11ed2"
export LIBSIGROK_REPO="https://github.com/sigrokproject/libsigrok.git"
export LIBSIGROK_REF="f06f788118191d19fdbbb37046d3bd5cec91adb1"
export LIBSIGROKDECODE_REPO="https://github.com/sigrokproject/libsigrokdecode.git"
export LIBSIGROKDECODE_REF="71f451443029322d57376214c330b518efd84f88"
export SIGROK_FIRMWARE_REPO="https://github.com/sigrokproject/sigrok-firmware.git"
export SIGROK_FIRMWARE_REF="11eed913a9c535b87b5d5b5b92d2622cf34cee8b"
export SIGROK_FIRMWARE_FX2LAFW_REPO="https://github.com/sigrokproject/sigrok-firmware-fx2lafw.git"
export SIGROK_FIRMWARE_FX2LAFW_REF="0f2d3242ffb5582e5b9a018ed9ae9812d517a56e"
export SIGROK_DUMPS_REPO="https://github.com/sigrokproject/sigrok-dumps.git"
export SIGROK_DUMPS_REF="0ad13477abc959d37fc9a5acbd23901c371c9c76"

export DEBUG=0
export PARALLEL="-j$(nproc)"
export PATH="${USR_DIR}/bin:${PATH}"
export CMAKE="${MXE_TARGET}-cmake"
export C="--host=${MXE_TARGET} --prefix=${INSTALL_DIR} CPPFLAGS=-D__printf__=__gnu_printf__"
export L="--disable-shared --enable-static"
export MXE_PKG_CONFIG_PATH="${USR_DIR}/${MXE_TARGET}/lib/pkgconfig"
if [ "$TARGET" = "i686" ]; then
	export PKG_CONFIG_PATH_i686_w64_mingw32_static_posix="${MXE_PKG_CONFIG_PATH}"
else
	export PKG_CONFIG_PATH_x86_64_w64_mingw32_static_posix="${MXE_PKG_CONFIG_PATH}"
fi

mkdir -p "${BUILD_DIR}"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}"

cd $BUILD_DIR

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
		sudo \
		autoconf \
		automake \
		autopoint \
		bash \
		bison \
		bzip2 \
		flex \
		g++ \
		g++-multilib \
		gtk-doc-tools \
		sdcc \
		gettext \
		git \
		intltool \
		libc6-dev-i386 \
		libltdl-dev \
		libssl-dev \
		libtool-bin \
		lzip \
		make \
		openssl \
		p7zip-full \
		patch \
		pkg-config \
		python3 \
		python-is-python3 \
		sed \
		unzip \
		wget \
		xz-utils

test -d ${MXE_DIR} || ${GIT_CLONE} ${MXE_REPO} ${MXE_DIR}
cd ${MXE_DIR}
${GIT_CLEAN}
${GIT_RESET} ${MXE_REF}
${GIT_CLEAN}
patch -p1 < ${BASE_DIR}/mxe_fixes.patch
patch -p1 < ${BASE_DIR}/hidapi_fixes.patch

make -j$(nproc) \
  MXE_TARGETS="${MXE_TARGET}" \
  PREFIX="${USR_DIR}" \
  PKG_DIR="${BUILD_DIR}/pkg" \
  DONT_CHECK_REQUIREMENTS=1 \
  MXE_CCACHE_BASE_DIR="${BUILD_DIR}" \
  MXE_CCACHE_DIR="${BUILD_DIR}/cache" \
  MXE_TMP="${BUILD_DIR}/tmp" \
  JOBS=$(nproc) \
    gendef \
    glib \
    libzip \
    libusb1 \
    libftdi1 \
    hidapi \
    libieee1284 \
    nettle

cd ${BUILD_DIR}

# Cross-compiling Python is highly non-trivial, so we avoid it for now.
# The Python32.tar.gz file below is a repackaged tarball of the official
# Python 3.4.4 MSI installer for Windows:
#   - https://www.python.org/ftp/python/3.4.4/python-3.4.4.msi
#   - https://www.python.org/ftp/python/3.4.4/python-3.4.4.amd64.msi
# The MSI file has been installed on a Windows box and then c:\Python34\libs
# and c:\Python34\include have been stored in the Python34_*.tar.gz tarball.
tar xzf "${BASE_DIR}/contrib-mxe/Python34_$TARGET.tar.gz" -C "${INSTALL_DIR}"

# Fix for bug #1195.
if [ "${TARGET}" = "x86_64" ]; then
	patch --fuzz=3 --ignore-whitespace -p1 "${INSTALL_DIR}/Python34/include/pyconfig.h" < ../contrib-mxe/pyconfig.patch
fi

# Create a dummy python3.pc file so that pkg-config finds Python 3.
mkdir -p "${INSTALL_DIR}"/lib/pkgconfig
cat > "${INSTALL_DIR}/lib/pkgconfig/python3.pc" <<EOF
prefix=${INSTALL_DIR}
exec_prefix=\${prefix}
libdir=\${exec_prefix}/Python34/libs
includedir=\${prefix}/Python34/include
Name: Python
Description: Python library
Version: 3.4.4
Libs: -L\${libdir} -lpython34
Cflags: -I\${includedir}
EOF

# The python34.dll and python34.zip files will be shipped in the NSIS
# Windows installers (required for PulseView/SmuView Python scripts to work).
# The file python34.dll (NOT the same as python3.dll) is copied from an
# installed Python 3.4.4 (see above) from c:\Windows\system32\python34.dll.
# The file python34.zip contains all files from the 'DLLs', 'Lib', and 'libs'
# subdirectories from an installed Python on Windows (c:\python34), i.e. some
# libraries and all Python stdlib modules.
cp "${BASE_DIR}/contrib-mxe/python34_$TARGET.dll" "${INSTALL_DIR}/python34.dll"
cp "${BASE_DIR}/contrib-mxe/python34_$TARGET.zip" "${INSTALL_DIR}/python34.zip"

cp "${INSTALL_DIR}/python34.dll" .
"${USR_DIR}/${TARGET}-w64-mingw32.static.posix/bin/gendef" python34.dll
"${USR_DIR}/bin/${TARGET}-w64-mingw32.static.posix-dlltool" \
  --dllname python34.dll --def python34.def \
  --output-lib libpython34.a
mkdir -p "${DIST_DIR}/Python34/libs"
mv -f libpython34.a "${DIST_DIR}/Python34/libs"
rm -f python34.dll

# We need to include the *.pyd files from python34.zip into the installers,
# otherwise importing certain modules (e.g. ctypes) won't work (bug #1409).
unzip -q "${INSTALL_DIR}/python34.zip" *.pyd -d "${DIST_DIR}/Python34"

# libserialport
test -d libserialport || ${GIT_CLONE} ${LIBSERIALPORT_REPO} libserialport
cd libserialport
${GIT_RESET} ${LIBSERIALPORT_REF}
./autogen.sh
./configure ${C} ${L}
make ${PARALLEL}
make install
cd ..

# libsigrok
test -d libsigrok || ${GIT_CLONE} ${LIBSIGROK_REPO} libsigrok
cd libsigrok
${GIT_RESET} ${LIBSIGROK_REF}
./autogen.sh
./configure ${C} ${L} --disable-python
make ${PARALLEL}
make install
cd ..

${USR_DIR}/bin/${MXE_TARGET}-gcc -O2 -shared \
  -o "${DIST_DIR}/libsigrok.dll" \
  -Wl,--whole-archive -lsigrok \
  -Wl,--no-whole-archive -lglib-2.0 \
  -Wl,--no-whole-archive -lgio-2.0 \
  -Wl,--no-whole-archive -lserialport \
  -Wl,--no-whole-archive -lusb-1.0 \
  -Wl,--no-whole-archive -lieee1284 \
  -Wl,--no-whole-archive -lftdi1 \
  -Wl,--no-whole-archive -lhidapi \
  -Wl,--no-whole-archive -lnettle \
  -Wl,--no-whole-archive -lzip \
  -Wl,--no-whole-archive -lz \
  -Wl,--no-whole-archive -lbz2 \
  -Wl,--no-whole-archive -lbcrypt \
  -Wl,--no-whole-archive -lpcre \
  -Wl,--no-whole-archive -lintl \
  -Wl,--no-whole-archive -liconv \
  -Wl,--no-whole-archive -lws2_32 \
  -Wl,--no-whole-archive -lsetupapi \
  -Wl,--no-whole-archive -lole32 \
  -Wl,--no-whole-archive -lwinmm

# libsigrokdecode
test -d libsigrokdecode || ${GIT_CLONE} ${LIBSIGROKDECODE_REPO} libsigrokdecode
cd libsigrokdecode
${GIT_RESET} ${LIBSIGROKDECODE_REF}
./autogen.sh
./configure ${C} ${L}
make ${PARALLEL}
make install
cd ..

${USR_DIR}/bin/${MXE_TARGET}-gcc -O2 -shared \
  -o "${DIST_DIR}/libsigrokdecode.dll" \
  -Wl,--whole-archive -lsigrokdecode \
  -Wl,--no-whole-archive -L${USR_DIR}/${TARGET}-w64-mingw32.static.posix/Python34/libs -lpython34 \
  -Wl,--no-whole-archive -lglib-2.0 \
  -Wl,--no-whole-archive -lws2_32 \
  -Wl,--no-whole-archive -lintl \
  -Wl,--no-whole-archive -lwinmm \
  -Wl,--no-whole-archive -lole32 \
  -Wl,--no-whole-archive -liconv

# sigrok-firmware
test -d sigrok-firmware || $GIT_CLONE ${SIGROK_FIRMWARE_REPO} sigrok-firmware
cd sigrok-firmware
${GIT_RESET} ${SIGROK_FIRMWARE_REF}
./autogen.sh
./configure --prefix="${DIST_DIR}"
make install
cd ..

# sigrok-firmware-fx2lafw
test -d sigrok-firmware-fx2lafw || ${GIT_CLONE} ${SIGROK_FIRMWARE_FX2LAFW_REPO} sigrok-firmware-fx2lafw
cd sigrok-firmware-fx2lafw
${GIT_RESET} ${SIGROK_FIRMWARE_FX2LAFW_REF}
./autogen.sh
# We're building the fx2lafw firmware on the host, no need to cross-compile.
./configure --prefix="${DIST_DIR}"
make ${PARALLEL}
make install
cd ..
