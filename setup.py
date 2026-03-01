import os
import re
import sys
import platform
import subprocess
import fnmatch
import shutil

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from ctypes.util import find_library

def _parse_version(v):
    """Parse a dotted version string into a comparable integer tuple."""
    return tuple(int(x) for x in v.split('.'))

def _read_cmake_version():
    """Read the base version (MAJOR.MINOR) from CMakeLists.txt."""
    cmake_file = os.path.join(os.path.dirname(__file__), 'CMakeLists.txt')
    with open(cmake_file, encoding='utf-8') as f:
        for line in f:
            m = re.search(r'set\s*\(\s*projectVersion\s+([\d]+\.[\d]+)', line)
            if m:
                return m.group(1)
    raise RuntimeError("Could not determine version from CMakeLists.txt")

_base_version = _read_cmake_version()
vrs_sub = '1'

if os.environ.get('CI_PIPELINE_IID'):
    ci_id = os.environ['CI_PIPELINE_IID']
    if (isinstance(ci_id, str) and len(ci_id) > 0) or isinstance(ci_id, int):
        vrs_sub = ci_id

version = _base_version + '.' + vrs_sub

source_dir = os.path.abspath('./')
build_dir = os.path.abspath('./build')

def get_platform():
    platforms = {
        'linux' : 'Linux',
        'linux1' : 'Linux',
        'linux2' : 'Linux',
        'darwin' : 'Macos',
        'win32' : 'Windows'
    }
    if sys.platform not in platforms:
        return sys.platform
    return platforms[sys.platform]

PLATFORM = get_platform()

REDISTR_LIBS = []

if PLATFORM == 'Windows':
    REDISTR_LIBS = [
        'concrt140.dll',
        'msvcp140.dll',
        'msvcp140_1.dll',
        'msvcp140_2.dll',
        'msvcp140_codecvt_ids.dll',
        'vccorlib140.dll',
        'vcruntime140.dll',
        'vcruntime140_1.dll']


def find_shared_libs(dir, pattern):
    matches = []
    for root, dirnames, filenames in os.walk(dir):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches


class CMakeExtension(Extension):
    def __init__(self, name, source_dir='', build_dir=None):
        Extension.__init__(self, name, sources=[])
        self.source_dir = os.path.abspath(source_dir)
        self.build_dir = os.path.abspath(build_dir)

class CMakeBuild(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions)
            )

        if platform.system() == "Windows":
            cmake_version = _parse_version(
                re.search(r'version\s*([\d.]+)', out.decode()).group(1)
            )
            if cmake_version < _parse_version('3.1.0'):
                raise RuntimeError("CMake >= 3.1.0 is required on Windows")

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        if not (ext.build_dir is None):
            self.build_temp = ext.build_dir
        extdir = os.path.abspath(os.path.dirname(
            self.get_ext_fullpath(ext.name)))
        print(f"----Python executable: {sys.executable}")
        cmake_args = [
            '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
            '-DPYTHON_EXECUTABLE=' + sys.executable
        ]

        # Only use conan toolchain if SLIDEIO_INSTALL_DIR is not defined
        if not os.environ.get('SLIDEIO_INSTALL_DIR'):
            toolchain_path = './cmake/conan_toolchain.cmake'
            if os.path.exists(os.path.join(ext.source_dir, toolchain_path)):
                cmake_args.append('-DCMAKE_TOOLCHAIN_FILE=' + toolchain_path)

        cfg = 'Release'
        build_args = ['--config', cfg, "--target", "slideiopybind"]

        if platform.system() == "Windows":
            cmake_args += [
                '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(
                    cfg.upper(), extdir
                )
            ]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            cmake_args += ['-G', 'Visual Studio 17 2022']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j2']

        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get('CXXFLAGS', ''),
            self.distribution.get_version()
        )
        print(f"----Creation build directory: {self.build_temp}")
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        print(f"----Executing cmake, source directory: {ext.source_dir}, build directory: {self.build_temp}")
        subprocess.check_call(
            ['cmake', ext.source_dir] + cmake_args,
            cwd=self.build_temp, env=env
        )
        subprocess.check_call(
            ['cmake', '--build', '.'] + build_args,
            cwd=self.build_temp
        )
        patterns = ["*.so", "*.so.*"]
        if PLATFORM == "Windows":
            patterns = ["*.dll", "*.pyd"]
        elif PLATFORM == "Macos":
            patterns = ["*.so", "*.dylib"]

        print("----Look for shared libraries int directory", self.build_temp)
        extra_files = []
        for pattern in patterns:
            files = find_shared_libs(self.build_temp, pattern)
            if len(files) > 0:
                extra_files.extend(files)

        print("----Found libraries:", extra_files)

        wheel_lib_dir = os.path.join(extdir, 'slideio', 'core', 'libs')
        if os.path.exists(wheel_lib_dir):
            shutil.rmtree(wheel_lib_dir)
        os.makedirs(wheel_lib_dir)

        for fl in extra_files:
            file_name = os.path.basename(fl)
            destination = os.path.join(wheel_lib_dir, file_name)
            print("Copy", fl, "->", destination)
            shutil.move(fl, destination)

        for lib in REDISTR_LIBS:
            shutil.copy(find_library(lib), wheel_lib_dir)


setup(
    version=version,
    ext_modules=[CMakeExtension(name='slideio', source_dir=source_dir, build_dir=build_dir)],
    cmdclass=dict(build_ext=CMakeBuild),
    zip_safe=False,
)
