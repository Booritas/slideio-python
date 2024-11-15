pythonPath=$(which python)
pythonBinDir=$(dirname "$pythonPath")
pythonDir=$(dirname "$pythonBinDir")
pythonLibDir="$pythonDir/lib"

pythonHPath=$(find "$pythonDir" -name "Python.h" 2>/dev/null | head -n 1)
pythonHDir=$(dirname "$pythonHPath")

if [[ "$(uname)" == "Darwin" ]]; then
    libSuffix=".dylib"
else
    libSuffix=".so"  # Default for Linux and other Unix-like systems
fi

pythonLibName="libpython$(python --version | awk '{print $2}' | cut -d '.' -f 1,2)${libSuffix}"
echo "pythonLibName=$pythonLibName"


pythonVersion=$(python --version | awk '{print $2}')
pythonVersion=${pythonVersion%.*}

export PYTHON_EXECUTABLE="$pythonPath"
export Python3_EXECUTABLE="$pythonPath"
export Python3_VERSION="$pythonVersion"
export Python3_INCLUDE_DIRS="$pythonHDir"
export Python3_LIBRARY_DIRS="$pythonLibDir"
export Python3_NumPy_INCLUDE_DIRS=$(python -c "import numpy; print(numpy.get_include())")
export Python3_LIBRARIES="$pythonLibDir/${pythonLibName}"
export PYTHON_LOCATION_IS_SET=1

# Display all defined variables
echo "PYTHON_EXECUTABLE=$PYTHON_EXECUTABLE"
echo "Python3_EXECUTABLE=$Python3_EXECUTABLE"
echo "Python3_VERSION=$Python3_VERSION"
echo "Python3_INCLUDE_DIRS=$Python3_INCLUDE_DIRS"
echo "Python3_LIBRARY_DIRS=$Python3_LIBRARY_DIRS"
echo "Python3_NumPy_INCLUDE_DIRS=$Python3_NumPy_INCLUDE_DIRS"
echo "Python3_LIBRARIES=$Python3_LIBRARIES"
echo "PYTHON_LOCATION_IS_SET=$PYTHON_LOCATION_IS_SET"