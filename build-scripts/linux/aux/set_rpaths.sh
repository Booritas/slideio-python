modify_rpath() 
{
  local dir_path=$(realpath "$1")
  find "$dir_path" -name "*.so*" -print -exec patchelf --set-rpath '$ORIGIN' {} \;
}

modify_rpath "."