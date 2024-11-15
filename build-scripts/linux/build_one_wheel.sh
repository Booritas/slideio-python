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

scriptDir=$(dirname "$(readlink -f "$0")")
echo "scriptDir=$scriptDir"
file="$scriptDir/define_python_envs.sh"
echo "file=$file"
source "$file" "$1"
py="$PYTHON_EXECUTABLE"
build_wheel