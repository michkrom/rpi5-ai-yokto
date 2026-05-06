# FindSDL2_mixer.cmake - Find SDL2_mixer using pkg-config
# Provides SDL2_mixer::SDL2_mixer target for compatibility

find_package(PkgConfig QUIET)
if(PkgConfig_FOUND)
    pkg_check_modules(_SDL2_MIXER QUIET sdl2_mixer)
endif()

if(_SDL2_MIXER_FOUND)
    message(STATUS "Found SDL2_mixer: ${_SDL2_MIXER_VERSION}")
    add_library(SDL2_mixer::SDL2_mixer INTERFACE IMPORTED)
    target_include_directories(SDL2_mixer::SDL2_mixer INTERFACE ${_SDL2_MIXER_INCLUDE_DIRS})
    target_link_libraries(SDL2_mixer::SDL2_mixer INTERFACE SDL2_mixer)
else()
    message(STATUS "SDL2_mixer not found via pkg-config")
endif()

mark_as_advanced(_SDL2_MIXER)