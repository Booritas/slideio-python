"""Tests for the MSVC redistributable resolution used when building wheels.

These cover build tooling rather than the built wheel, so they import
`msvcredist` from the repository root instead of from the installed package.
The suite is still run from outside the checkout (see CLAUDE.md), so the path
is derived from this file's own location.

The behaviour under test exists because of a real failure: setup.py used to
locate the eight redistributable DLLs with `ctypes.util.find_library`, which on
Windows simply walks PATH. On a machine with a conda environment or a JDK ahead
of System32 that resolves an older CRT than the toolset that compiled slideio,
and every slideio DLL in the resulting wheel then fails its initialisation with
`[WinError 1114]` -- surfacing only as `ImportError: DLL load failed while
importing slideiopybind`.
"""
import os
import sys
import unittest

# append, not insert(0, ...): this must not sort ahead of site-packages and
# shadow an installed slideio with the source tree for the rest of the pytest
# session. Nothing in site-packages provides `msvcredist`, so appending still
# finds it.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import msvcredist  # noqa: E402


def _touch(directory, name):
    path = os.path.join(directory, name)
    with open(path, 'wb') as f:
        f.write(b'stub')
    return path


class TestFindRedistDll(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name

    def _dir(self, name):
        path = os.path.join(self.root, name)
        os.makedirs(path)
        return path

    def test_picks_the_first_directory_that_has_the_dll(self):
        # Priority is the whole point: the toolset's own redist must win over
        # System32 when both are present.
        first = self._dir('first')
        second = self._dir('second')
        wanted = _touch(first, 'msvcp140.dll')
        _touch(second, 'msvcp140.dll')

        found = msvcredist.find_redist_dll('msvcp140.dll', [first, second])

        self.assertEqual(os.path.normcase(found), os.path.normcase(wanted))

    def test_skips_a_directory_that_lacks_the_dll(self):
        empty = self._dir('empty')
        stocked = self._dir('stocked')
        wanted = _touch(stocked, 'vcruntime140.dll')

        found = msvcredist.find_redist_dll('vcruntime140.dll', [empty, stocked])

        self.assertEqual(os.path.normcase(found), os.path.normcase(wanted))

    def test_does_not_fall_back_to_path(self):
        # The regression test for the bug this module exists to prevent. The
        # DLL is resolvable on PATH and absent from the search list; resolution
        # must fail rather than quietly bundle the copy PATH happens to offer.
        on_path = self._dir('on_path')
        _touch(on_path, 'msvcp140.dll')
        empty = self._dir('empty')

        original = os.environ.get('PATH', '')
        os.environ['PATH'] = on_path + os.pathsep + original
        self.addCleanup(os.environ.__setitem__, 'PATH', original)

        with self.assertRaises(RuntimeError):
            msvcredist.find_redist_dll('msvcp140.dll', [empty])

    def test_error_names_the_dll_and_the_directories_searched(self):
        empty = self._dir('empty')

        with self.assertRaises(RuntimeError) as caught:
            msvcredist.find_redist_dll('msvcp140.dll', [empty])

        message = str(caught.exception)
        self.assertIn('msvcp140.dll', message)
        self.assertIn(empty, message)


class TestRedistSearchDirs(unittest.TestCase):
    def test_returns_nothing_off_windows(self):
        if sys.platform == 'win32':
            self.skipTest('Windows resolves real redistributable directories')
        self.assertEqual(msvcredist.redist_search_dirs(), [])

    def test_does_not_include_directories_merely_because_they_are_on_path(self):
        if sys.platform != 'win32':
            self.skipTest('PATH contamination is the Windows failure mode')
        import tempfile
        with tempfile.TemporaryDirectory() as intruder:
            _touch(intruder, 'msvcp140.dll')
            original = os.environ.get('PATH', '')
            os.environ['PATH'] = intruder + os.pathsep + original
            try:
                dirs = msvcredist.redist_search_dirs()
            finally:
                os.environ['PATH'] = original
            normalised = [os.path.normcase(d) for d in dirs]
            self.assertNotIn(os.path.normcase(intruder), normalised)

    def test_honours_an_explicit_override(self):
        if sys.platform != 'win32':
            self.skipTest('the override is only consulted on Windows')
        import tempfile
        with tempfile.TemporaryDirectory() as chosen:
            original = os.environ.get('SLIDEIO_MSVC_REDIST_DIR')
            os.environ['SLIDEIO_MSVC_REDIST_DIR'] = chosen
            try:
                dirs = msvcredist.redist_search_dirs()
            finally:
                if original is None:
                    del os.environ['SLIDEIO_MSVC_REDIST_DIR']
                else:
                    os.environ['SLIDEIO_MSVC_REDIST_DIR'] = original
            self.assertTrue(dirs)
            self.assertEqual(os.path.normcase(dirs[0]), os.path.normcase(chosen))

    def test_finds_a_real_crt_on_this_machine(self):
        if sys.platform != 'win32':
            self.skipTest('Windows only')
        # Not a tautology: it proves the discovery actually locates the eight
        # DLLs setup.py needs, which is what the build depends on.
        dirs = msvcredist.redist_search_dirs()
        self.assertTrue(dirs, 'no redistributable directory discovered')
        found = msvcredist.find_redist_dll('msvcp140.dll', dirs)
        self.assertTrue(os.path.isfile(found))


if __name__ == '__main__':
    unittest.main()
