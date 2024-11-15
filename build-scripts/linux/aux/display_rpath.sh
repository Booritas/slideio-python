#!/bin/bash

# Check if readelf is installed
if ! command -v readelf &> /dev/null
then
    echo "readelf could not be found. Please install it."
    exit 1
fi

# Loop through all .so files in the current directory and its subdirectories
find . -type f -name "*.so" | while read -r sofile; do
    # Print the filename
    echo "File: $sofile"
    
    # Extract and print the RUNPATH
    runpath=$(readelf -d "$sofile" 2>/dev/null | grep "RUNPATH" | awk -F'[][]' '{print $2}')
    if [ -n "$runpath" ]; then
        echo "RUNPATH: $runpath"
    else
        echo "RUNPATH: Not set"
    fi
    echo
done
