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

add_library(${BINDLIB_NAME} MODULE ${BINDLIB_SOURCE})

#pybind11_add_module( SHARED ${BINDLIB_SOURCE})
pybind11_extension(${BINDLIB_NAME})

if(NOT MSVC AND NOT ${CMAKE_BUILD_TYPE} MATCHES Debug|RelWithDebInfo)
    # Strip unnecessary sections of the binary on Linux/macOS
    pybind11_strip(example)
endif()

target_include_directories(${BINDLIB_NAME} PRIVATE 
   ${INCLUDE_ROOT} 
   ${Python3_INCLUDE_DIRS} 
   ${Python3_NumPy_INCLUDE_DIRS}
   )
   
target_link_libraries(${BINDLIB_NAME} ${Python3_LIBRARIES})

CONAN_CONFIGURE(${BINDLIB_NAME})

FIX_MACOS_RPATH(${BINDLIB_NAME})