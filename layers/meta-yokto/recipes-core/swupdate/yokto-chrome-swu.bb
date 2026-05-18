LICENSE = "MIT"

require yokto-swu.inc
SWU_IMAGE_PATTERN = "image-chrome*.wic.bz2"
IMAGE_BASE_NAME = "yokto-chrome"

# Ensure image is built before SWU
do_swuimage[depends] += "core-image-weston:do_image_complete"
