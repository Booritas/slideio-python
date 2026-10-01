#!/bin/bash
min_version=9
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
    # --wheel: build from the work tree. A bare `$py -m build` builds the wheel
    # from an unpacked sdist in a temp dir, and the sdist ships no extern/, so
    # CMake finds no extern/slideio-install there and fails.
    $py -m build --wheel
    #$py setup.py sdist bdist_wheel

    echo "-------------End of processing Python version: $py_version ---------------"
  else
    echo "****Version $py_version skipped"
  fi
    
}

set -e

# The C++ library does not depend on the Python version. Build it once, into
# extern/slideio-install, before the loop below starts deleting ./build.
# No-op when the prefix already matches the checked-out submodule commit.
python3 build-slideio.py -c release

rm -rf ./dist

echo "Build python wheels"

for dir in /opt/python/cp*
do
  # Skip the free-threaded interpreters (cp313t, cp314t, ...). The image ships
  # them alongside the GIL builds, so the glob picks them up and Linux ends up
  # with one more wheel than every other platform -- 2.10.0's draft release had
  # a cp314-cp314t wheel that no other platform had, and that nothing tested.
  # The extension is built with pybind11's default GIL assumptions, so a
  # free-threaded wheel advertises support that has not been verified. Build it
  # deliberately, with its own testing, rather than by accident of a glob.
  if [[ "$dir" == *t ]]; then
    echo "****Skipping free-threaded interpreter $dir"
    continue
  fi
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