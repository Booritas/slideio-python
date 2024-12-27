set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(BINDLIB_NAME ${LIBRARY_NAME})
set(CMAKE_BUILD_RPATH_USE_ORIGIN 1)
set(CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
IF(WIN32 OR UNIX)
    cmake_policy(SET CMP0167 NEW)
ENDIF()

find_package(slideio)
find_package(Boost)

set(BINDLIB_SOURCE 
   pybind.cpp
   pyglobals.hpp
   pyglobals.cpp
   pyslide.hpp
   pyslide.cpp
   pyscene.hpp
   pyscene.cpp
   pyconverter.hpp
   pyconverter.cpp
   pytransformation.hpp
   pytransformation.cpp
   pyerror.hpp
)

pybind11_add_module(${BINDLIB_NAME} MODULE ${BINDLIB_SOURCE})

target_link_libraries(${BINDLIB_NAME} PRIVATE slideio::slideio)
target_link_libraries(${BINDLIB_NAME} PRIVATE boost::boost)
set_target_properties(${BINDLIB_NAME} PROPERTIES INSTALL_RPATH "$ORIGIN")
set_target_properties(${BINDLIB_NAME} PROPERTIES BUILD_RPATH "$ORIGIN")

FIX_MACOS_RPATH(${BINDLIB_NAME})

file(GLOB BIN_DEBUG_FILES ${slideio_BIN_DIRS_DEBUG}/*.*)
file(GLOB BIN_RELEASE_FILES ${slideio_BIN_DIRS_RELEASE}/*.*)

add_custom_command(TARGET ${BINDLIB_NAME} PRE_BUILD
   COMMAND ${CMAKE_COMMAND} -E copy 
   "$<$<CONFIG:Release>:${BIN_RELEASE_FILES}>$<$<CONFIG:Debug>:${BIN_DEBUG_FILES}>" 
   "$<TARGET_FILE_DIR:${BINDLIB_NAME}>"
   COMMAND_EXPAND_LISTS
   VERBATIM
)
