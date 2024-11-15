#!/bin/bash
set -e

scriptDir=$(dirname "$(readlink -f "$0")")

rm -rf ./dist
rm -rf ../build_py
rm -rf ./build

echo "Build python wheels"

for dir in /opt/python/cp*
do
  if [[ $dir != *"cp36"* ]]; then
    export py="$dir/bin/python"
    bash "$scriptDir/build_one_wheel.sh" "$py"
  fi
done

echo "updating wheels"

for f in ./dist/*.whl
do
  echo "Processing $f file..."
  auditwheel repair $f
done