# Check OS and platform
$os = (Get-WmiObject -Class Win32_OperatingSystem).Caption
$platform = (Get-WmiObject -Class Win32_Processor).Architecture
$minversion = 12

# Function to generate Python versions
function Generate-PythonVersions {
    param (
        [int]$min_version,
        [int]$max_version
    )
    $python_versions = @()
    for ($version = $min_version; $version -le $max_version; $version++) {
        $python_versions += "3.$version"
    }
    return $python_versions
}

# Function to create and activate conda environment
function Create-And-Activate-CondaEnv {
    param (
        [string]$version
    )
    Write-Host "Creating conda environment for Python $version"
    conda create -y -n "env_python_$version" python=$version
    Write-Host "Activating conda environment for Python $version"
    conda activate "env_python_$version"
    python -m pip install numpy
}

# Function to deactivate and remove conda environment
function Deactivate-And-Remove-CondaEnv {
    param (
        [string]$version
    )
    Write-Host "Deactivating conda environment for Python $version"
    conda deactivate
    Write-Host "Removing conda environment for Python $version"
    conda remove -y -n "env_python_$version" --all
    Write-Host "-----end of processing python version $version"
}

Set-Location -Path .\src
$python_versions = Generate-PythonVersions -min_version $minversion -max_version 12
Remove-Item -Path .\dist -Recurse -Force -ErrorAction SilentlyContinue

foreach ($version in $python_versions) {
    Write-Host "-----processing python version $version"

    Create-And-Activate-CondaEnv -version $version
    
    # Build distributable
    Remove-Item -Path .\build -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path ..\..\build_py -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Executing command in conda environment for Python $version"
    python --version
    Write-Host "Installing wheel in conda environment for Python $version"
    python -m pip install wheel
    python -m pip install conan==1.65

    python setup.py sdist bdist_wheel
    Get-ChildItem -Path .\dist
    
    Deactivate-And-Remove-CondaEnv -version $version
}
