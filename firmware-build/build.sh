set -e

export SIGROK_FIRMWARE_REPO="https://github.com/sigrokproject/sigrok-firmware.git"
export SIGROK_FIRMWARE_REF="11eed913a9c535b87b5d5b5b92d2622cf34cee8b"
export SIGROK_FIRMWARE_FX2LAFW_REPO="https://github.com/sigrokproject/sigrok-firmware-fx2lafw.git"
export SIGROK_FIRMWARE_FX2LAFW_REF="0f2d3242ffb5582e5b9a018ed9ae9812d517a56e"
export DSVIEW_REPO="https://github.com/DreamSourceLab/DSView.git"
export DSVIEW_REF="886b847c21c606df3138ce7ad8f8e8c363ee758b"

export BASE_DIR=$(pwd)
export BUILD_DIR="${BASE_DIR}/build"
export DIST_DIR="${BASE_DIR}/dist"
export FW_DIR="${DIST_DIR}/share/sigrok-firmware"

export GIT_CLONE="git clone"
export GIT_CLEAN="git clean -fdx"
export GIT_RESET="git reset --hard"

export DEBUG=0
export PARALLEL="-j$(nproc)"

# WORKAROUND WHEN RUNNING AS ROOT IN A CONTAINER
apt-get update && apt-get install sudo || true

sudo apt-get update
sudo apt-get install -y --no-install-recommends \
		make \
		autoconf \
		automake \
		sdcc \
		git \
		ca-certificates

rm -rf "${DIST_DIR}"

mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"

cd "${BUILD_DIR}"

#
# SIGROK_FIRMWARE
#
test -d sigrok-firmware || $GIT_CLONE ${SIGROK_FIRMWARE_REPO} sigrok-firmware
cd sigrok-firmware
${GIT_RESET} ${SIGROK_FIRMWARE_REF}
./autogen.sh
./configure --prefix="${DIST_DIR}"
make install
cd ..

#
# SIGROK_FIRMWARE_FX2LAFW
#
test -d sigrok-firmware-fx2lafw || ${GIT_CLONE} ${SIGROK_FIRMWARE_FX2LAFW_REPO} sigrok-firmware-fx2lafw
cd sigrok-firmware-fx2lafw
${GIT_RESET} ${SIGROK_FIRMWARE_FX2LAFW_REF}
./autogen.sh
./configure --prefix="${DIST_DIR}"
make ${PARALLEL}
make install
cd ..

#
# DSLOGIC_FIRMWARE
#
test -d dsview || ${GIT_CLONE} ${DSVIEW_REPO} dsview
cd dsview
${GIT_RESET} ${DSVIEW_REF}
cp DSView/res/DSLogic50.bin "${FW_DIR}/dreamsourcelab-dslogic-fpga-5v.fw"
cp DSView/res/DSLogic33.bin "${FW_DIR}/dreamsourcelab-dslogic-fpga-3v3.fw"
cp DSView/res/DSLogic.fw "${FW_DIR}/dreamsourcelab-dslogic-fx2.fw"
cp DSView/res/DSCope.bin "${FW_DIR}/dreamsourcelab-dscope-fpga.fw"
cp DSView/res/DSCope.fw "${FW_DIR}/dreamsourcelab-dscope-fx2.fw"
cp DSView/res/DSLogicPro.bin "${FW_DIR}/dreamsourcelab-dslogic-pro-fpga.fw"
cp DSView/res/DSLogicPro.fw "${FW_DIR}/dreamsourcelab-dslogic-pro-fx2.fw"
cp DSView/res/DSLogicPlus.bin "${FW_DIR}/dreamsourcelab-dslogic-plus-fpga.fw"
cp DSView/res/DSLogicPlus.fw "${FW_DIR}/dreamsourcelab-dslogic-plus-fx2.fw"
cp DSView/res/DSLogicBasic.bin "${FW_DIR}/dreamsourcelab-dslogic-basic-fpga.fw"
cp DSView/res/DSLogicBasic.fw "${FW_DIR}/dreamsourcelab-dslogic-basic-fx2.fw"
cd ..