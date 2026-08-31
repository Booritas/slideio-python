$ErrorActionPreference = "Stop"
$minversion = 8
$maxversion = 14

. .\lib.ps1

# The C++ library does not depend on the Python version. Build it once, into
# extern\slideio-install, before Build-Wheels starts deleting .\build.
# No-op when the prefix already matches the checked-out submodule commit.
python build-slideio.py -c release
if ($LASTEXITCODE -ne 0) { throw "build-slideio.py failed" }

$python_versions = Generate-PythonVersions -min_version $minversion -max_version $maxversion
Remove-Item -Path .\dist -Recurse -Force -ErrorAction SilentlyContinue

Build-Wheels -python_versions $python_versions
Repair-Naming
