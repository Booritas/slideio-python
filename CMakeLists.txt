cmake_minimum_required(VERSION 3.9)
cmake_policy(SET CMP0057 NEW)
cmake_policy(SET CMP0068 OLD)

set(PROJECT_NAME slideio-python)
set(projectVersion 2.7.0)

project(${PROJECT_NAME} VERSION ${projectVersion} LANGUAGES C CXX)
enable_testing()
set( CMAKE_VERBOSE_MAKEFILE off )
set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(PYBIND11_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/pybind11/include)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_BUILD_RPATH_USE_ORIGIN 1)
set(CMAKE_CXX_STANDARD_REQUIRED, ON)
set(CMAKE_CXX_STANDARD,17)
set(CONAN_DISABLE_CHECK_COMPILER ON)

include_directories(
    ${INCLUDE_ROOT} 
    ${PYBIND11_INCLUDE_DIR}
)


MACRO(SOURCE_GROUP_BY_FOLDER target)
  SET(SOURCE_GROUP_DELIMITER "/")
  SET(last_dir "")
  SET(files "")
  FOREACH(file ${${target}})
    file(RELATIVE_PATH relative_file "${CMAKE_CURRENT_LIST_DIR}/${target}" ${file})
    GET_FILENAME_COMPONENT(dir "${relative_file}" PATH)
    IF (NOT "${dir}" STREQUAL "${last_dir}")
      IF (files)
        SOURCE_GROUP("${last_dir}" FILES ${files})
      ENDIF (files)
      SET(files "")
    ENDIF (NOT "${dir}" STREQUAL "${last_dir}")
    SET(files ${files} ${file})
    SET(last_dir "${dir}")
    STRING(REPLACE ".." "src" last_dir ${last_dir})
  ENDFOREACH(file)
  IF (files)
    SOURCE_GROUP("${last_dir}" FILES ${files})
  ENDIF (files)
ENDMACRO(SOURCE_GROUP_BY_FOLDER)

IF(APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
    add_compile_definitions(_FILE_OFFSET_BITS=64)
ELSEIF(UNIX)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-libstdc++")
    add_compile_definitions(_GLIBCXX_USE_CXX11_ABI=0)
ENDIF()


macro(CONAN_MAIN)
    include(conanbuildinfo_multi.cmake)
    conan_basic_setup()
endmacro()

macro(CONAN_CONFIGURE_INCLUDES trg)
    foreach(_DIR ${CONAN_INCLUDE_DIRS_RELEASE})
        target_include_directories(${trg} PRIVATE ${_DIR})
    endforeach()
    foreach(_DIR ${CONAN_INCLUDE_DIRS_DEBUG})
        target_include_directories(${trg} PRIVATE ${_DIR})
    endforeach()
endmacro()

macro(CONAN_CONFIGURE trg)
    conan_target_link_libraries(${trg})
    CONAN_CONFIGURE_INCLUDES(${trg})
endmacro()

IF(WIN32)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/bin)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/bin)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/bin)
ELSE()
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
    set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
    set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
ENDIF(WIN32)

MACRO(FIX_MACOS_RPATH target)
    IF (APPLE)
        FOREACH(entry ${NAME_TOOL_LIB_LIST})
            string(REPLACE "@rpath/" "" new_val ${entry})
            add_custom_command(TARGET ${target}
                POST_BUILD COMMAND
                ${CMAKE_INSTALL_NAME_TOOL} -change ${entry} @loader_path/${new_val}
                $<TARGET_FILE:${target}>)
        ENDFOREACH()
    ENDIF()
ENDMACRO(FIX_MACOS_RPATH)


set(TEST_DIR ${CMAKE_RUNTIME_OUTPUT_DIRECTORY})

MACRO(HIDE_LIB LIB)
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,--exclude-libs,${LIB}")
    endif()
ENDMACRO(HIDE_LIB)

macro(macos_conan_target_link_libraries_with_hide target hide)

    SET(HIDE_CANDIDATES_DEBUG ${CONAN_LIBS_DEBUG})
    SET(NORMAL_DEBUG ${CONAN_LIBS_DEBUG})
    LIST(FILTER HIDE_CANDIDATES_DEBUG INCLUDE REGEX ${hide})
    LIST(FILTER NORMAL_DEBUG EXCLUDE REGEX ${hide})

    SET(HIDE_CANDIDATES_RELEASE ${CONAN_LIBS_RELEASE})
    SET(NORMAL_RELEASE ${CONAN_LIBS_RELEASE})
    LIST(FILTER HIDE_CANDIDATES_RELEASE INCLUDE REGEX ${hide})

    LIST(FILTER NORMAL_RELEASE EXCLUDE REGEX ${hide})

    set(HIDDEN_DEBUG "")
    foreach(_LIB ${HIDE_CANDIDATES_DEBUG})
        LIST(APPEND HIDDEN_DEBUG "-load_hidden ${_LIB}")
    endforeach()
    
    set(HIDDEN_RELEASE "")
    foreach(_LIB ${HIDE_CANDIDATES_RELEASE})
        LIST(APPEND HIDDEN_RELEASE "-load_hidden ${_LIB}")
    endforeach()

    if(CONAN_TARGETS)
        target_link_libraries(${target} ${CONAN_TARGETS})
    else()
        target_link_libraries(${target} ${CONAN_LIBS})
        target_link_libraries(${target} $<$<CONFIG:Debug>:${NORMAL_DEBUG}>$<$<CONFIG:Release>:${NORMAL_RELEASE}>)
        target_link_libraries(${target} $<$<CONFIG:Debug>:${HIDDEN_DEBUG}>$<$<CONFIG:Release>:${HIDDEN_RELEASE}>)
    endif()
endmacro()

macro(conan_target_link_libraries_with_hide target hide)
    IF(APPLE)
        macos_conan_target_link_libraries_with_hide(${target} ${hide})
    ELSE()
        conan_target_link_libraries(${target} ${hide})
    ENDIF()
endmacro()

add_subdirectory(pybind11)

if (DEFINED ENV{PYTHON_LOCATION_IS_SET})
   message("Python location is set externaly")
   set(Python3_VERSION $ENV{Python3_VERSION})
   set(Python3_EXECUTABLE $ENV{Python3_EXECUTABLE})
   set(Python3_INCLUDE_DIRS $ENV{Python3_INCLUDE_DIRS})
   set(Python3_LIBRARY_DIRS $ENV{Python3_LIBRARY_DIRS})
   set(Python3_NumPy_INCLUDE_DIRS $ENV{Python3_NumPy_INCLUDE_DIRS})
else()
   message("Look for the python location")
   find_package (Python3 COMPONENTS Interpreter PythonLibs NumPy)
endif()

message(STATUS "Python: version=${Python3_VERSION}")
message(STATUS "Python interpreter=${Python3_EXECUTABLE}")
message(STATUS "Python include=${Python3_INCLUDE_DIRS}")
message(STATUS "Python libraries=${Python3_LIBRARIES}")
message(STATUS "Python library directories=${Python3_LIBRARY_DIRS}")
message(STATUS "Python NumPy include=${Python3_NumPy_INCLUDE_DIRS}")

add_subdirectory(src)

