#!/bin/bash

# Get the directory of the script
script_dir=$(dirname "$(realpath "$0")")

# Check if the script directory is already in PATH
if [[ ":$PATH:" != *":$script_dir:"* ]]; then
    # Add the script directory to PATH
    export PATH="$PATH:$script_dir"
    echo "Added $script_dir to PATH"
else
    echo "$script_dir is already in PATH"
fi