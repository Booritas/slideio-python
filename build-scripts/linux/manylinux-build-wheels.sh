set -e

rm -rf ./dist
rm -rf ../build_py
rm -rf ./build

echo "Build python wheels"

for dir in /opt/python/cp*
do
  if [[ $dir != *"cp36"* ]]; then
    export py="$dir/bin/python"
    ./build_one_wheel "$py"
  fi
done
