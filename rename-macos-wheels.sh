#!/bin/bash

# Retag macOS wheels to the macOS version the binaries actually require.
#
# The platform tag a wheel is born with comes from the interpreter that built
# it, which on a GitHub runner means the runner's own macOS version -- a
# macos-14 runner produces macosx_14_0_arm64, a macos-15 one macosx_15_0_*.
# That is wrong in the restrictive direction: it tells pip the wheel needs the
# build machine's macOS, so 2.10.0's arm64 wheels were refused on macOS 12 and
# 13 even though they run there.
#
# What the binaries actually require is the C++ library's deployment target,
# extern/slideio/CMakeLists.txt:158 -- CMAKE_OSX_DEPLOYMENT_TARGET 12.0. Keep
# ARM64_TAG in step with that line; it is the one place this script encodes it.
#
# x86_64 is deliberately left alone. It is retagged macosx_10_15 today, which is
# more permissive than the 12.0 the dylibs need, so an older-macOS user can
# install a wheel that will not load. Correcting it to 12_0 is a one-line change
# here -- X86_64_TAG below -- but it narrows what already-published wheels
# claimed, so it is a decision to take deliberately rather than a drive-by.

set -euo pipefail

# Must match extern/slideio/CMakeLists.txt's CMAKE_OSX_DEPLOYMENT_TARGET.
ARM64_TAG="macosx_12_0_arm64"
# Pre-existing behaviour, knowingly more permissive than the deployment target.
X86_64_TAG="macosx_10_15_x86_64"

# Check if the directory path is provided
if [ -z "${1:-}" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

DIRECTORY=$1

shopt -s nullglob
for file in "$DIRECTORY"/*.whl; do
  base=$(basename "$file")

  # Any macosx_<major>_<minor>_<arch>, whatever the build machine reported --
  # not just the two versions this script used to special-case, which is how
  # macos-14's macosx_14_0 slipped through onto a release page.
  new_base=$(echo "$base" | sed -E \
    -e "s/macosx_[0-9]+_[0-9]+_arm64/${ARM64_TAG}/" \
    -e "s/macosx_[0-9]+_[0-9]+_x86_64/${X86_64_TAG}/")

  if [ "$new_base" != "$base" ]; then
    # Refuse rather than overwrite. One run only ever produces one macOS
    # version per architecture, so a collision means two builds' wheels have
    # been mixed in this directory -- and a plain mv would destroy one of them
    # without a word. Found by running this script over a directory holding
    # both macosx_14_0 and macosx_15_0 arm64 wheels: two of seven files
    # vanished silently.
    if [ -e "$DIRECTORY/$new_base" ]; then
      echo "Refusing to rename $base: $new_base already exists." >&2
      echo "Two builds' wheels are mixed in $DIRECTORY." >&2
      exit 1
    fi
    mv "$file" "$DIRECTORY/$new_base"
    echo "Renamed $base to $new_base"
  fi
done
