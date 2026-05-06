# FindSDL2.cmake - Find SDL2 using pkg-config
# Provides SDL2::SDL2 target for compatibility

find_package(PkgConfig REQUIRED)
pkg_check_modules(_SDL2 QUIET sdl2)

if(_SDL2_FOUND)
    add_library(SDL2::SDL2 INTERFACE IMPORTED)
    set_target_properties(SDL2::SDL2 PROPERTIES
        INTERFACE_INCLUDE_DIRECTORIES "${_SDL2_INCLUDE_DIRS}"
        INTERFACE_LINK_DIRECTORIES "${_SDL2_LIBRARY_DIRS}"
        INTERFACE_LINK_LIBRARIES "${_SDL2_LIBRARIES}"
    )
endif()

mark_as_advanced(_SDL2)