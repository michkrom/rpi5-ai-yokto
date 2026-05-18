# yokto base SWU - generates SWU from image-base
# This recipe runs after building and creates the SWU file

LICENSE = "MIT"

require yokto-swu.inc
SWU_IMAGE_PATTERN = "core-image-base-raspberrypi5.rootfs*.wic.bz2"
IMAGE_BASE_NAME = "yokto-base"

# Ensure image is built before SWU
do_swuimage[depends] += "core-image-base:do_image_complete"
