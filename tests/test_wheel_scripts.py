"""Tests for the wheel-building scripts' tagging and interpreter selection.

These cover build tooling rather than the built wheel, so they read the scripts
from the repository root the way tests/test_msvcredist.py reads a module from
there. They need neither a built wheel nor the image corpus.

Both properties pinned here were found on 2.10.0's first CI-built release, not
by a test: Linux carried a cp314-cp314t free-threaded wheel no other platform
had and nothing had exercised, and the arm64 wheels were tagged macosx_14_0 --
the build runner's macOS version -- so pip refused them on macOS 12 and 13
although the binaries run there.

The scripts are bash and PowerShell, and the suite has to pass on Windows, so
these are assertions about the scripts' text rather than executions of them.
That is a weaker check than running them: it catches deletion and drift, not a
subtly wrong regex. The behaviour itself is verified by the wheel filenames a
release produces.
"""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_root_file(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
        return handle.read()


class TestManylinuxInterpreterSelection(unittest.TestCase):
    def setUp(self):
        self.source = read_root_file('build-wheels-manylinux.sh')

    def test_free_threaded_interpreters_are_skipped(self):
        # /opt/python/cp* matches the free-threaded builds (cp313t, cp314t)
        # alongside the GIL ones, so without this guard Linux silently ships a
        # wheel no other platform has. The extension carries pybind11's default
        # GIL assumptions, so such a wheel advertises unverified support.
        self.assertRegex(self.source, r'\$dir"?\s*==\s*\*t')
        self.assertIn('continue', self.source)

    def test_the_skip_is_inside_the_loop_and_precedes_the_build_call(self):
        # A guard outside the loop, or after build_wheel, prevents nothing.
        body = re.search(r'for dir in /opt/python/cp\*(.*?)\ndone',
                         self.source, re.DOTALL)
        self.assertIsNotNone(body, 'interpreter loop not found')
        body = body.group(1)
        guard = re.search(r'\$dir"?\s*==\s*\*t', body)
        self.assertIsNotNone(guard, 'no free-threaded guard inside the loop')
        self.assertIn('build_wheel', body)
        self.assertLess(guard.start(), body.index('build_wheel'))


class TestMacosWheelTags(unittest.TestCase):
    def setUp(self):
        self.source = read_root_file('rename-macos-wheels.sh')

    def test_the_arm64_tag_is_version_agnostic(self):
        # The old script special-cased macosx_15_0 only, which is how a
        # macos-14 runner's macosx_14_0 reached a release page unrenamed.
        self.assertIn('macosx_[0-9]+_[0-9]+_arm64', self.source)

    def test_the_x86_64_tag_is_version_agnostic(self):
        self.assertIn('macosx_[0-9]+_[0-9]+_x86_64', self.source)

    def test_the_arm64_tag_matches_the_cpp_deployment_target(self):
        # The wheel tag is a promise about the oldest macOS the binaries run
        # on, and the binaries' floor is the C++ library's deployment target.
        # If that line moves and this one does not, the wheels lie.
        submodule = os.path.join(ROOT, 'extern', 'slideio', 'CMakeLists.txt')
        if not os.path.isfile(submodule):
            self.skipTest('extern/slideio is not checked out, so the '
                          'deployment target cannot be read')
        with open(submodule, encoding='utf-8') as handle:
            target = re.search(
                r'CMAKE_OSX_DEPLOYMENT_TARGET\s+"(\d+)\.(\d+)"',
                handle.read())
        self.assertIsNotNone(target, 'deployment target not found')
        major, minor = target.groups()
        declared = re.search(r'ARM64_TAG="macosx_(\d+)_(\d+)_arm64"',
                             self.source)
        self.assertIsNotNone(declared, 'ARM64_TAG not found')
        self.assertEqual((major, minor), declared.groups())

    def test_a_rename_collision_refuses_rather_than_overwrites(self):
        # Found by running the script over a directory holding both
        # macosx_14_0 and macosx_15_0 arm64 wheels: both retag to the same
        # name and a plain mv destroyed one of them silently -- seven files in,
        # five out. A single runner only ever emits one macOS version per
        # architecture, so a collision means two builds have been mixed.
        self.assertIn('Refusing to rename', self.source)
        self.assertRegex(self.source, r'if \[ -e "\$DIRECTORY/\$new_base" \]')

    def test_the_x86_64_tag_is_documented_as_deliberately_permissive(self):
        # It claims macosx_10_15 while the dylibs need 12.0, which is
        # pre-existing and knowingly left alone -- but it must stay a recorded
        # decision rather than an accident.
        self.assertIn('X86_64_TAG="macosx_10_15_x86_64"', self.source)
        self.assertIn('permissive', self.source)


if __name__ == '__main__':
    unittest.main()
