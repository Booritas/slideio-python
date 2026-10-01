"""Tests for the wheel-building scripts and the macOS tag check.

These cover build tooling rather than the built wheel, so they import from the
repository root the way tests/test_msvcredist.py does. They need neither a built
wheel nor the image corpus.

Everything pinned here was found on 2.10.0's first CI-built release, not by a
test. Linux carried a cp314-cp314t free-threaded wheel no other platform had and
nothing had exercised. And every macOS wheel was mistagged: the libslideio
dylibs carried minos 12.0 from the C++ library's deployment target while
slideiopybind.so carried the build runner's -- 14.0 on macos-14, 15.0 on
macos-15-intel -- because this repository set no deployment target at all. The
wheels could not load on anything older than the machine that built them,
whatever their filenames claimed, and renaming the files afterwards did not and
could not change that.

The shell-script assertions are about text rather than executions, because the
suite has to pass on Windows and those scripts are bash. check-macos-wheels.py
is Python, so its parser is tested for real against a synthetic Mach-O.
"""
import io
import os
import re
import struct
import sys
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'check_macos_wheels', os.path.join(ROOT, 'check-macos-wheels.py'))
check_macos_wheels = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_macos_wheels)

DEPLOYMENT_TARGET = ('12', '0')


def read_root_file(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return handle.read()


def macho_with_minos(major, minor):
    """A minimal 64-bit Mach-O carrying one LC_BUILD_VERSION load command."""
    build_version = struct.pack(
        '<6I',
        0x32,                      # LC_BUILD_VERSION
        24,                        # cmdsize
        1,                         # platform: PLATFORM_MACOS
        (major << 16) | (minor << 8),   # minos
        (major << 16) | (minor << 8),   # sdk
        0)                         # ntools
    header = struct.pack(
        '<8I',
        0xFEEDFACF,                # MH_MAGIC_64
        0x0100000C,                # CPU_TYPE_ARM64
        0, 6,                      # cpusubtype, MH_DYLIB
        1,                         # ncmds
        len(build_version),
        0, 0)
    return header + build_version


def wheel_with(tmpdir, filename, members):
    path = os.path.join(tmpdir, filename)
    with zipfile.ZipFile(path, 'w') as wheel:
        for name, data in members.items():
            wheel.writestr(name, data)
    return path


class TestManylinuxInterpreterSelection(unittest.TestCase):
    def setUp(self):
        self.source = read_root_file('build-wheels-manylinux.sh')

    def test_free_threaded_interpreters_are_skipped(self):
        # /opt/python/cp* matches the image's free-threaded builds alongside the
        # GIL ones, so without this guard Linux silently ships a wheel no other
        # platform has, carrying pybind11's default GIL assumptions.
        self.assertRegex(self.source, r'\$dir"?\s*==\s*\*t')

    def test_the_skip_is_inside_the_loop_and_precedes_the_build_call(self):
        body = re.search(r'for dir in /opt/python/cp\*(.*?)\ndone',
                         self.source, re.DOTALL)
        self.assertIsNotNone(body, 'interpreter loop not found')
        body = body.group(1)
        guard = re.search(r'\$dir"?\s*==\s*\*t', body)
        self.assertIsNotNone(guard, 'no free-threaded guard inside the loop')
        self.assertIn('build_wheel', body)
        self.assertLess(guard.start(), body.index('build_wheel'))


class TestDeploymentTargetAgreement(unittest.TestCase):
    """The floor is stated in three places; they must not drift apart.

    A mismatch is not cosmetic: whichever is lowest decides what the binaries
    require, and whichever reaches sysconfig decides what the wheel's tag
    claims. 2.10.0 shipped with those two different.
    """

    def test_the_cpp_library_still_sets_the_expected_target(self):
        submodule = os.path.join(ROOT, 'extern', 'slideio', 'CMakeLists.txt')
        if not os.path.isfile(submodule):
            self.skipTest('extern/slideio is not checked out')
        with open(submodule, encoding='utf-8') as handle:
            found = re.search(
                r'CMAKE_OSX_DEPLOYMENT_TARGET\s+"(\d+)\.(\d+)"', handle.read())
        self.assertIsNotNone(found, 'deployment target not found')
        self.assertEqual(DEPLOYMENT_TARGET, found.groups())

    def test_this_repository_sets_the_same_target_before_project(self):
        source = read_root_file('CMakeLists.txt')
        found = re.search(
            r'CMAKE_OSX_DEPLOYMENT_TARGET\s+"(\d+)\.(\d+)"', source)
        self.assertIsNotNone(
            found, 'CMakeLists.txt sets no deployment target, so the extension '
                   'is compiled against the build machine SDK')
        self.assertEqual(DEPLOYMENT_TARGET, found.groups())
        # CMake reads it at project(); set afterwards it is ignored. Matched at
        # the start of a line so the comment above the setting, which mentions
        # project() to explain the ordering, is not what gets compared.
        command = re.search(r'^project\(', source, re.MULTILINE)
        self.assertIsNotNone(command, 'no project() command found')
        self.assertLess(found.start(), command.start())

    def test_the_macos_wheel_script_exports_the_same_target(self):
        source = read_root_file('build-wheels-macos.sh')
        found = re.search(
            r'export MACOSX_DEPLOYMENT_TARGET=(\d+)\.(\d+)', source)
        self.assertIsNotNone(found, 'MACOSX_DEPLOYMENT_TARGET is not exported, '
                                    'so the wheel tag follows the build machine')
        self.assertEqual(DEPLOYMENT_TARGET, found.groups())

    def test_the_macos_wheel_script_checks_what_it_built(self):
        self.assertIn('check-macos-wheels.py',
                      read_root_file('build-wheels-macos.sh'))

    def test_the_rename_script_is_gone(self):
        # It rewrote the platform tag after the build, which changed the
        # filename and not the binary. Setting the target at build time is the
        # fix; a renamer surviving beside it would invite the old lie back.
        self.assertFalse(
            os.path.exists(os.path.join(ROOT, 'rename-macos-wheels.sh')))


class TestMacosWheelCheck(unittest.TestCase):
    """The parser, against synthetic Mach-O binaries."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_reads_minos_from_a_build_version_command(self):
        self.assertEqual(
            (14, 0), check_macos_wheels.minimum_macos(macho_with_minos(14, 0)))

    def test_a_binary_needing_more_than_the_tag_is_reported(self):
        # Exactly 2.10.0's arm64 defect: tag 12_0, extension minos 14.0.
        path = wheel_with(self.tmpdir, 'x-macosx_12_0_arm64.whl', {
            'slideio/core/libs/slideiopybind.cpython-312-darwin.so':
                macho_with_minos(14, 0)})
        problems = check_macos_wheels.check_wheel(path)
        self.assertEqual(1, len(problems))
        self.assertIn('requires macOS 14.0', problems[0])
        self.assertIn('claims 12.0', problems[0])

    def test_a_binary_matching_the_tag_is_accepted(self):
        path = wheel_with(self.tmpdir, 'x-macosx_12_0_arm64.whl', {
            'slideio/core/libs/slideiopybind.cpython-312-darwin.so':
                macho_with_minos(12, 0)})
        self.assertEqual([], check_macos_wheels.check_wheel(path))

    def test_a_binary_below_the_tag_is_accepted(self):
        # Under-promising loads fine; only over-promising breaks an install.
        path = wheel_with(self.tmpdir, 'x-macosx_12_0_arm64.whl', {
            'slideio/core/libs/libslideio.dylib': macho_with_minos(11, 0)})
        self.assertEqual([], check_macos_wheels.check_wheel(path))

    def test_the_ten_fifteen_tag_is_parsed_as_ten_point_fifteen(self):
        # macosx_10_15 must not read as 10.1 or 1015: the x86_64 wheels carried
        # that tag over binaries needing 12.0, and a mis-parse would hide it.
        path = wheel_with(self.tmpdir, 'x-macosx_10_15_x86_64.whl', {
            'slideio/core/libs/libslideio.dylib': macho_with_minos(12, 0)})
        problems = check_macos_wheels.check_wheel(path)
        self.assertEqual(1, len(problems))
        self.assertIn('claims 10.15', problems[0])

    def test_non_macos_wheels_are_ignored(self):
        path = wheel_with(self.tmpdir, 'x-manylinux_2_28_x86_64.whl', {
            'slideio/core/libs/slideiopybind.so': macho_with_minos(14, 0)})
        self.assertEqual([], check_macos_wheels.check_wheel(path))

    def test_a_wheel_with_no_binaries_is_accepted(self):
        path = wheel_with(self.tmpdir, 'x-macosx_12_0_arm64.whl',
                          {'slideio/__init__.py': b'# nothing to load\n'})
        self.assertEqual([], check_macos_wheels.check_wheel(path))

    def test_a_directory_with_no_macos_wheels_fails_loudly(self):
        # Silence must not read as success: an empty dist/ means the build
        # produced nothing, which is a failure, not a clean check.
        stderr, sys.stderr = sys.stderr, io.StringIO()
        try:
            self.assertEqual(1, check_macos_wheels.main(self.tmpdir))
        finally:
            sys.stderr = stderr


if __name__ == '__main__':
    unittest.main()
