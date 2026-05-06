# FindPNG.cmake - Find PNG using pkg-config
# Provides PNG::PNG target for compatibility

find_package(PkgConfig REQUIRED)
pkg_check_modules(PNG REQUIRED libpng IMPORTED_TARGET)

# Create an alias target for compatibility
add_library(PNG::PNG ALIAS PkgConfig::PNG)

mark_as_advanced(PNG_INCLUDE_DIRS PNG_LIBRARY_DIRS)