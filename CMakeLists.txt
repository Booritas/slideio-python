cmake_minimum_required(VERSION 3.10)
cmake_policy(SET CMP0057 NEW)
cmake_policy(SET CMP0091 NEW)

set(PROJECT_NAME slideio-python)
set(projectVersion 2.10)
set(LIBRARY_NAME slideiopybind)

# The slideio C++ library is resolved from an install prefix -- include/, lib/
# and bin/ -- in one of two ways:
#
#   1. SLIDEIO_INSTALL_DIR in the environment, for developing against a slideio
#      build that lives outside this repository. It always wins when set.
#   2. Otherwise extern/slideio-install, produced by build-slideio.py from the
#      extern/slideio submodule. This is the standard path.
#
# There is no longer a conan branch: slideio itself is no longer consumed as a
# conan package, so this repository needs no conan remote and no conanfile. The
# submodule's own build still uses conan for slideio's dependencies, but that is
# entirely internal to extern/slideio.
if(DEFINED ENV{SLIDEIO_INSTALL_DIR})
    set(SLIDEIO_INSTALL_DIR $ENV{SLIDEIO_INSTALL_DIR})
    message(STATUS "slideio from SLIDEIO_INSTALL_DIR: ${SLIDEIO_INSTALL_DIR}")
else()
    set(SLIDEIO_INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/extern/slideio-install)
    message(STATUS "slideio from submodule prefix: ${SLIDEIO_INSTALL_DIR}")
endif()

if(NOT EXISTS ${SLIDEIO_INSTALL_DIR}/include/slideio)
    message(FATAL_ERROR
        "No slideio installation at ${SLIDEIO_INSTALL_DIR}.\n"
        "Build it from the submodule:\n"
        "    git submodule update --init --recursive\n"
        "    python build-slideio.py\n"
        "or point SLIDEIO_INSTALL_DIR at an existing slideio install prefix.")
endif()

set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(CMAKE_MACOSX_RPATH 1)
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
project(${PROJECT_NAME} VERSION ${projectVersion} LANGUAGES C CXX)
set(CMAKE_VERBOSE_MAKEFILE off)
set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(PYBIND11_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/pybind11/include)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_STANDARD_REQUIRED, ON)
set(CMAKE_CXX_STANDARD,17)
set(CONAN_DISABLE_CHECK_COMPILER ON)


IF(APPLE)
    set(CMAKE_INSTALL_RPATH "@loader_path")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
    add_compile_definitions(_FILE_OFFSET_BITS=64)
ELSEIF(UNIX)
    set(CMAKE_BUILD_RPATH_USE_ORIGIN 1)
    set(CMAKE_INSTALL_RPATH "$ORIGIN")
ENDIF()

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wno-switch)
    add_compile_options(-Wno-switch-default)
endif()

set(PYBIND11_FINDPYTHON OFF)

add_subdirectory(pybind11)

find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)

include_directories(${SLIDEIO_INSTALL_DIR}/include)
link_directories(${SLIDEIO_INSTALL_DIR}/lib)

include_directories(
    ${INCLUDE_ROOT} 
    ${PYBIND11_INCLUDE_DIR}
)


set(BINDLIB_SOURCE 
   src/pybind.cpp
   src/pyglobals.hpp
   src/pyglobals.cpp
   src/pyslide.hpp
   src/pyslide.cpp
   src/pyscene.hpp
   src/pyscene.cpp
   src/pymetadata.hpp
   src/pymetadata.cpp
   src/pyconverter.hpp
   src/pyconverter.cpp
   src/pytransformation.hpp
   src/pytransformation.cpp
   src/pyerror.hpp
)

pybind11_add_module(${LIBRARY_NAME} SHARED ${BINDLIB_SOURCE})
pybind11_extension(${LIBRARY_NAME})

message(STATUS "Python Include directory: ${PYTHON_INCLUDE_DIRS}")
message(STATUS "Python Library: ${PYTHON_LIBRARIES}")

target_link_libraries(${LIBRARY_NAME} PRIVATE
    slideio
    slideio-converter
    slideio-transformer
    slideio-core
)

IF (APPLE)
    set_target_properties(${LIBRARY_NAME} PROPERTIES INSTALL_RPATH "@loader_path")
    set_target_properties(${LIBRARY_NAME} PROPERTIES BUILD_RPATH "@loader_path")
ELSEIF (UNIX)
    set_target_properties(${LIBRARY_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN")
    set_target_properties(${LIBRARY_NAME} PROPERTIES BUILD_RPATH "$ORIGIN")
ENDIF()

# Stage the slideio runtime next to the extension so setup.py can collect both
# into slideio/core/libs. Globbed at configure time: re-run cmake after
# rebuilding the submodule if the set of libraries changed.
#
# Both directories, because the platforms disagree about which one holds the
# runtime. Windows installs the DLLs to bin/ and the import libraries to lib/;
# Linux and macOS install the shared objects to lib/ alone. slideio used to
# install them to lib/ *and* bin/ on Unix, so naming bin/ here was enough -- when
# that duplicate was removed this glob came back empty and the copy below failed
# with "cmake -E copy must be called with at least two arguments", which says
# nothing about the cause.
#
# Shared libraries by extension, not "everything in bin/". Since slideio 2.10
# bin/ holds more than the runtime: the Tools component installs the command
# line tools there (slideio-converter, slideio-tiffinspector) and, on MSVC, the
# DebugSymbols component installs a .pdb beside every library. Both arrive
# unasked -- install.py runs a plain `cmake --install`, which installs every
# component -- so the prefix is no longer a directory whose contents can be
# copied wholesale. setup.py would filter the tools and PDBs back out when it
# collects the wheel, so nothing shipped, but the staging copy below still moved
# several hundred megabytes of debug symbols on every configure.
file(GLOB _slideio_staged
    ${SLIDEIO_INSTALL_DIR}/bin/*.dll
    ${SLIDEIO_INSTALL_DIR}/lib/*.so*
    ${SLIDEIO_INSTALL_DIR}/lib/*.dylib)

# Drop the unversioned SONAME symlinks. Since slideio began setting
# VERSION/SOVERSION on Linux, every library matches "*.so*" twice --
# libslideio.so.2.10 and a libslideio.so pointing at it -- and `cmake -E copy`
# below follows symlinks, so staging both would put two full copies of all
# sixteen libraries in the wheel. Only the versioned file is wanted: the
# extension records the SONAME at link time, so that is the name the loader asks
# for, and the unversioned link exists for the linker, which the wheel never
# runs. Filtered here and not in setup.py because after the copy these are
# ordinary files and nothing downstream can tell them apart.
set(SLIDEIO_BIN_FILES "")
foreach(_lib IN LISTS _slideio_staged)
    if(IS_SYMLINK "${_lib}")
        message(STATUS "slideio runtime: skipping SONAME symlink ${_lib}")
    else()
        list(APPEND SLIDEIO_BIN_FILES "${_lib}")
    endif()
endforeach()
unset(_slideio_staged)

# An empty glob is always a broken install prefix, and it is worth saying so
# here rather than letting it surface as a malformed copy command at build time.
if(NOT SLIDEIO_BIN_FILES)
    message(FATAL_ERROR
        "No slideio runtime libraries found under ${SLIDEIO_INSTALL_DIR} "
        "(looked in bin/ and lib/). Build the C++ library first with "
        "'python build-slideio.py', or point SLIDEIO_INSTALL_DIR at a complete "
        "slideio install prefix.")
endif()
add_custom_command(TARGET ${LIBRARY_NAME} PRE_BUILD
   COMMAND ${CMAKE_COMMAND} -E copy
   ${SLIDEIO_BIN_FILES}
   "$<TARGET_FILE_DIR:${LIBRARY_NAME}>"
   COMMAND_EXPAND_LISTS
   VERBATIM
)
