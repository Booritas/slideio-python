set(INCLUDE_ROOT ${CMAKE_SOURCE_DIR}/src)
set(BINDLIB_NAME slideiopybind)
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

pybind11_add_module(${BINDLIB_NAME} SHARED ${BINDLIB_SOURCE})

target_include_directories(${BINDLIB_NAME} PRIVATE ${INCLUDE_ROOT} ${Python3_INCLUDE_DIRS} ${Python3_NumPy_INCLUDE_DIRS})
target_include_directories(${BINDLIB_NAME} PRIVATE ${INCLUDE_ROOT})
target_link_libraries(${BINDLIB_NAME} PRIVATE 
   ${SLIDEIO_LIB_NAME}
   ${CONVERTER_LIB_NAME}
   ${TRANSFORMER_LIB_NAME}
   )


CONAN_CONFIGURE_INCLUDES(${BINDLIB_NAME})


FIX_MACOS_RPATH(${BINDLIB_NAME})