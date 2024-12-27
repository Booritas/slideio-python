#!/bin/bash

build_wheel()
{
  echo "Processing python $py ..."
  rm -rf ./build
  rm -rf ../build_py
  $py -m pip install -U pip setuptools
  $py -m pip install wheel
  $py setup.py sdist bdist_wheel
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