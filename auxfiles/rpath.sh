#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status (optional safety).
set -e

# Check if a directory path is provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

# Directory to search for .so files
directory=$1

# Iterate through all .so files in the specified directory
for sofile in "$directory"/*.so; do
  # Make sure the file actually exists (i.e., the pattern didn't expand to itself)
  if [[ -f "$sofile" ]]; then
    echo "File: $sofile"
    # Use readelf to display the dynamic section and grep for RPATH or RUNPATH
    readelf -d "$sofile" | grep -E 'RPATH|RUNPATH' || echo "  No RPATH or RUNPATH found."
    echo
  fi
done