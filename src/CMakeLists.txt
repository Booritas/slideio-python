set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(BINDLIB_NAME ${LIBRARY_NAME})
set(CMAKE_BUILD_RPATH_USE_ORIGIN 1)

CONAN_MAIN()

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


CONAN_CONFIGURE(${BINDLIB_NAME})

FIX_MACOS_RPATH(${BINDLIB_NAME})

file(GLOB BIN_DEBUG_FILES ${CONAN_BIN_DIRS_SLIDEIO_DEBUG}/*.*)
file(GLOB BIN_RELEASE_FILES ${CONAN_BIN_DIRS_SLIDEIO_RELEASE}/*.*)

add_custom_command(TARGET ${BINDLIB_NAME} PRE_BUILD
   COMMAND ${CMAKE_COMMAND} -E copy 
   "$<$<CONFIG:Release>:${BIN_RELEASE_FILES}>$<$<CONFIG:Debug>:${BIN_DEBUG_FILES}>" 
   "$<TARGET_FILE_DIR:${BINDLIB_NAME}>"
   COMMAND_EXPAND_LISTS
   VERBATIM
)
