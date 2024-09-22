$ErrorActionPreference = "Stop"
$minversion = 11
$maxversion = 12

. .\lib.ps1

try {
    Set-Location -Path .\src\dist
    $python_versions = Generate-PythonVersions -min_version $minversion -max_version $maxversion
    Create-CondaEnv-For-All-Versions -python_versions $python_versions
    foreach ($version in $python_versions) {
        Write-Host "-----processing python version $version"
        Activate-CondaEnv -version $version
        $versionWithoutDot = $version -replace '\.', ''
        $wheelFile = Get-ChildItem -Path . -Filter "*.whl" | Where-Object { $_.Name -match "cp$($versionWithoutDot)" } | Select-Object -First 1
        pip install $wheelFile.FullName 
    }
}
finally {
    Remove-All-CondaEnv -python_versions $python_versions
    Set-Location -Path ..\..\
}