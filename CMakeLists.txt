cmake_minimum_required(VERSION 3.10)
cmake_policy(SET CMP0057 NEW)
cmake_policy(SET CMP0091 NEW)

set(PROJECT_NAME slideio-python)
set(projectVersion 2.7.4)
set(LIBRARY_NAME slideiopybind)

set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(CMAKE_MACOSX_RPATH 1)
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
set(CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")


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


add_subdirectory(pybind11)

include_directories(
    ${INCLUDE_ROOT} 
    ${PYBIND11_INCLUDE_DIR}
)

find_package(slideio)

set(BINDLIB_SOURCE 
   src/pybind.cpp
   src/pyglobals.hpp
   src/pyglobals.cpp
   src/pyslide.hpp
   src/pyslide.cpp
   src/pyscene.hpp
   src/pyscene.cpp
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

include(helper.cmake)

target_link_libraries(${LIBRARY_NAME} PRIVATE slideio::slideio)
IF (APPLE)
    set_target_properties(${LIBRARY_NAME} PROPERTIES INSTALL_RPATH "@loader_path")
    set_target_properties(${LIBRARY_NAME} PROPERTIES BUILD_RPATH "@loader_path")
ELSEIF (UNIX)
    set_target_properties(${LIBRARY_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN")
    set_target_properties(${LIBRARY_NAME} PROPERTIES BUILD_RPATH "$ORIGIN")
ENDIF()

file(GLOB BIN_DEBUG_FILES ${slideio_BIN_DIRS_DEBUG}/*.*)
file(GLOB BIN_RELEASE_FILES ${slideio_BIN_DIRS_RELEASE}/*.*)

add_custom_command(TARGET ${LIBRARY_NAME} PRE_BUILD
   COMMAND ${CMAKE_COMMAND} -E copy 
   "$<$<CONFIG:Release>:${BIN_RELEASE_FILES}>$<$<CONFIG:Debug>:${BIN_DEBUG_FILES}>" 
   "$<TARGET_FILE_DIR:${LIBRARY_NAME}>"
   COMMAND_EXPAND_LISTS
   VERBATIM
)