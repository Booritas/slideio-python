move_files_to_main_dir() 
{
  local main_dir=$(realpath "$1")
  local sub_dir=$(realpath "$2")
  echo "Moving files from $sub_dir to $main_dir ..."

  if [ ! -d "$main_dir" ] || [ ! -d "$sub_dir" ]; then
    echo "Both arguments must be directories."
    return 1
  fi

  mv "$sub_dir"/* "$main_dir"/
  rmdir "$sub_dir"
}

modify_rpath_in_whl() 
{
  local whl_path=$(realpath "$1")
  local temp_dir=$(mktemp -d)
  echo "Processing $whl_path ..."

  unzip -q "$whl_path" -d "$temp_dir"
  move_files_to_main_dir "$temp_dir" "$temp_dir"/slideio.libs
  ls -la "$temp_dir"
  find "$temp_dir" -name "*.so*" -print -exec patchelf --set-rpath '$ORIGIN' {} \;
  mv "$whl_path" "$whl_path.bak"
  (cd "$temp_dir" && zip -r -q "$whl_path" .)
  rm -rf "$temp_dir"
}


modify_rpath_in_whl "./tmp/slideio-2.7.0-cp311-cp311-manylinux_2_28_x86_64.whl"