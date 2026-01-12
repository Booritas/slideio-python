$ErrorActionPreference = "Stop"
$minversion = 8
$maxversion = 14

. .\lib.ps1

$python_versions = Generate-PythonVersions -min_version $minversion -max_version $maxversion
Remove-Item -Path .\dist -Recurse -Force -ErrorAction SilentlyContinue

Build-Wheels -python_versions $python_versions
Repair-Naming
