$ErrorActionPreference = "Stop"
$minversion = 7
$maxversion = 12

. .\lib.ps1

$rootDirectory = Get-Location
$distPath = Join-Path $rootDirectory "src\dist"
$testPath = Join-Path $rootDirectory "tests"

$testResults = @()

try {
    $python_versions = Generate-PythonVersions -min_version $minversion -max_version $maxversion
    Create-CondaEnv-For-All-Versions -python_versions $python_versions
    foreach ($version in $python_versions) {
        Write-Host "-----processing python version $version"
        Activate-CondaEnv -version $version
        $versionWithoutDot = $version -replace '\.', ''
        Set-Location -Path $distPath
        $wheelFile = Get-ChildItem -Path . -Filter "*.whl" | Where-Object { $_.Name -match "cp$($versionWithoutDot)" } | Select-Object -First 1
        if ($null -eq $wheelFile) {
            Deactivate-CondaEnv 
            throw "No wheel file found for Python version $version"
        }
        pip install $wheelFile.FullName
        Set-Location -Path $testPath
        python -m unittest test.py
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            Write-Host "All tests passed successfully!"
            $testResults += ,@($version, "SUCCESS")
        } else {
            $testResults += ,@($version, "FAILED")
            Write-Host "Tests execution failed for Python $version. Exit code: $code"
        }
        Deactivate-CondaEnv 
    }
}
finally {
    Remove-All-CondaEnv -python_versions $python_versions
    Set-Location -Path $rootDirectory
}

Write-Host "`nTest Results Summary:"
foreach ($result in $testResults) {
    Write-Host "Python $($result[0]): $($result[1])"
}

if ($testResults | Where-Object { $_[1] -eq "FAILED" }) {
    throw "One or more tests failed. Check the test results summary for details."
}
