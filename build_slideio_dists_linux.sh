#!/bin/bash

build_wheel()
{
  echo "---------Starting processing python $py -----------"
  rm -rf ../build_py
  rm -rf ./build
  $py -m pip install -U pip setuptools
  $py -m pip install wheel
  $py setup.py sdist bdist_wheel
  echo "---------Finished processing python $py -----------"
}

modify_rpath_in_whl() 
{
  local whl_path=$1
  local temp_dir=$(mktemp -d)

  unzip -q "$whl_path" -d "$temp_dir"
  find "$temp_dir" -name "*.so" -exec patchelf --set-rpath '$ORIGIN' {} \;
  (cd "$temp_dir" && zip -r -q "$whl_path" .)
  rm -rf "$temp_dir"
}

set -e

rm -rf ./dist
rm -rf ../build_py
rm -rf ./build

echo "Build python wheels"

for dir in /opt/python/cp*
do
  if [[ $dir != *"cp36"* ]]; then
    export py="$dir/bin/python"
    build_wheel
  fi
done


echo "updating wheels"

for f in ./dist/*.whl
do
  echo "Processing $f file..."
  auditwheel repair $f
done