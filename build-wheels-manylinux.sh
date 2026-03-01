#!/bin/bash
min_version=7
max_version=14

build_wheel()
{
  #echo "Processing python $py ..."
  py_version=$($py --version 2>&1 | awk '{print $2}' | awk -F. '{print $1"."$2}')
  py_minor=$($py --version 2>&1 | awk '{print $2}' | awk -F. '{print $2}')
  if [[ $py_minor -ge $min_version && $py_minor -le $max_version ]]; then
    echo "-------------Processing Python version: $py_version ---------------"
    export PYTHON_VERSION=$py_version
    export Python3_VERSION=$py_version
    export Python3_EXECUTABLE=$py
    export Python_ROOT_DIR=$(dirname $(dirname $py))
    
    rm -rf ./build
    rm -rf ../build_py
    $py -m pip install -U pip setuptools
    $py -m pip install wheel
    $py -m pip install build
    $py -m build
    #$py setup.py sdist bdist_wheel

    echo "-------------End of processing Python version: $py_version ---------------"
  else
    echo "****Version $py_version skipped"
  fi
    
}

set -e

rm -rf ./dist

echo "Build python wheels"

for dir in /opt/python/cp*
do
  if [[ "$dir" != *"36"* ]]; then
     if [[ $dir != *"cp36"* ]]; then
    export py="$dir/bin/python"
       build_wheel
  fi
  fi
done

# export py="/opt/python/cp311-cp311/bin/python"
# build_wheel

echo "updating wheels"

for f in ./dist/*.whl
do
  echo "Processing $f file..."
  auditwheel repair -L "/core/libs" $f
done