#!/bin/bash

# Check if the directory path is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_path>"
  exit 1
fi

DIRECTORY=$1

# Iterate through all *.whl files in the directory
for file in "$DIRECTORY"/*.whl; do
  # Check if the file has the suffix macosx_15_0_arm64
  if [[ "$file" == *macosx_15_0_arm64.whl ]]; then
    # Create the new file name with the suffix macosx_11_0_arm64
    new_file="${file//macosx_15_0_arm64/macosx_11_0_arm64}"
    # Rename the file
    mv "$file" "$new_file"
    echo "Renamed $file to $new_file"
  fi
  if [[ "$file" == *macosx_15_0_x86_64.whl ]]; then
    # Create the new file name with the suffix macosx_11_0_arm64
    new_file="${file//macosx_15_0_x86_64/macosx_10_15_x86_64}"
    # Rename the file
    mv "$file" "$new_file"
    echo "Renamed $file to $new_file"
  fi
done