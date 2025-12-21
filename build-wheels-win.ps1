$ErrorActionPreference = "Stop"
$minversion = 13
$maxversion = 13

. .\lib.ps1

$python_versions = Generate-PythonVersions -min_version $minversion -max_version $maxversion
Remove-Item -Path .\dist -Recurse -Force -ErrorAction SilentlyContinue

Build-Wheels -python_versions $python_versions
Repair-Naming
