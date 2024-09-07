
import sys
import os
import shutil
import subprocess

packages = {
        '3.7': [['pip', None], ['setuptools', None], ['six', None]],
        '3.8': [['pip', None], ['setuptools', "70.3.0"], ['six', None]],
        '3.9': [['pip', None], ['setuptools', None], ['six', None]],
        '3.10': [['pip', None], ['setuptools', None], ['six', None]],
        '3.11': [['pip', None], ['setuptools', None], ['six', None]],
        '3.12': [['pip', None], ['setuptools', None], ['six', None]],
    }


def get_python_version(python_interpreter_path):
    try:
        # Run the interpreter with the --version flag
        result = subprocess.run([python_interpreter_path, '--version'], capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            # The output of `python --version` is usually in stderr, so check both stdout and stderr
            version = result.stdout.strip() if result.stdout else result.stderr.strip()
            version = version.replace('Python', '').strip()
            version_parts = version.split('.')
            short_version = '.'.join(version_parts[:2])
            return short_version
        else:
            return f"Failed to get Python version. Error: {result.stderr.strip()}"
    except Exception as e:
        return f"An error occurred: {e}"


def process_python_dist(bin_path):
    py_version = get_python_version(bin_path)
    print(f"Processing {py_version}...")
    if os.name == 'nt':
        version_packages = packages[py_version]
        for package in version_packages:
            package_name = package[0]
            package_version = package[1]
            if package_version is None:
                code = os.system(f"{bin_path} -m pip install --user --upgrade {package_name}")
            else:
                code = os.system(f"{bin_path} -m pip install --user --upgrade {package_name}=={package_version}")
            if code != 0:
                message = f"Error processing {bin_path}"
                raise Exception(message)
    code = os.system(f"{bin_path} -m pip install wheel")
    src_dir = os.path.abspath("./src")
    print(f"Source directory: {src_dir}")
    cmd = f"{bin_path} setup.py sdist bdist_wheel"
    print(f"Execute command: {cmd}")
    result = subprocess.run(f"{cmd} sdist bdist_wheel", shell=True, cwd=src_dir, capture_output=False, text=True)
    print(f"Exit code: {code}")
    if result.returncode !=0:
        message = f"Error processing {bin_path}"
        raise Exception(message)

if __name__ == "__main__":
    arguments = sys.argv[1:]
    if len(arguments) < 1:
        raise Exception("Path to file with python distributions paths required")
    path_file = arguments[0]
    file = open(path_file, 'r')
    lines = file.readlines()
    build_paths = []
    build_paths.append(os.path.abspath("./build"))
    dist_path = os.path.abspath("../dist")
    if os.path.exists(dist_path):
        shutil.rmtree(dist_path)
    for line in lines:
        for build_path in build_paths:
            if os.path.exists(build_path):
                shutil.rmtree(build_path)
        line = line.rstrip("\n")
        print(f"============={line}==================")
        if(len(line)>1):
            process_python_dist(line)
