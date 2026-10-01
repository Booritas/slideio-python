"""Tests for the release version derivation.

ci_version.py decides what a tag means: CMakeLists.txt carries MAJOR.MINOR and
the tag supplies the patch, which release.yml exports as CI_PIPELINE_IID for
setup.py:38-41 to turn into the wheel's version. A mistake here names every
wheel in a release wrongly, so this is the one part of release.yml worth testing
outside a CI run.

This covers build tooling rather than the built wheel, so `ci_version` is
imported from the repository root -- the arrangement tests/test_msvcredist.py
already uses. The suite is run from outside the checkout (see CLAUDE.md), so the
path is derived from this file's own location. It needs neither a built wheel nor
SLIDEIO_IMAGES_PATH.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

# append, not insert(0, ...): this must not sort ahead of site-packages and
# shadow an installed slideio with the source tree for the rest of the pytest
# session. Nothing in site-packages provides `ci_version`, so appending still
# finds it.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ci_version  # noqa: E402


class TestDerive(unittest.TestCase):
    def test_tag_supplies_the_patch(self):
        self.assertEqual(('2.10.3', '3'),
                         ci_version.derive('2.10', 'tag', 'v2.10.3'))

    def test_patch_zero_is_a_valid_tag(self):
        self.assertEqual(('2.10.0', '0'),
                         ci_version.derive('2.10', 'tag', 'v2.10.0'))

    def test_no_tag_means_patch_zero(self):
        self.assertEqual(('2.10.0', '0'),
                         ci_version.derive('2.10', 'branch', ''))

    def test_major_minor_must_match_cmakelists(self):
        with self.assertRaises(ValueError) as caught:
            ci_version.derive('2.10', 'tag', 'v2.11.0')
        self.assertIn('projectVersion', str(caught.exception))

    def test_tag_without_a_patch_is_rejected(self):
        with self.assertRaises(ValueError):
            ci_version.derive('2.10', 'tag', 'v2.10')

    def test_four_component_tag_is_rejected(self):
        with self.assertRaises(ValueError):
            ci_version.derive('2.10', 'tag', 'v2.10.3.1')

    def test_tag_without_the_v_prefix_is_rejected(self):
        with self.assertRaises(ValueError):
            ci_version.derive('2.10', 'tag', '2.10.3')

    def test_leading_zero_patch_is_rejected(self):
        # pip normalises 2.10.03 to 2.10.3 (PEP 440), so every wheel filename in
        # the release would disagree with the tag that produced it.
        with self.assertRaises(ValueError):
            ci_version.derive('2.10', 'tag', 'v2.10.03')

    def test_unreadable_project_version_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            ci_version.derive(None, 'tag', 'v2.10.3')
        self.assertIn('projectVersion', str(caught.exception))


class TestReadProjectVersion(unittest.TestCase):
    def test_reads_this_repositorys_own_cmakelists(self):
        # Deliberately not asserting 2.10: this must keep passing across bumps.
        self.assertRegex(ci_version.read_project_version(), r'^\d+\.\d+$')

    def test_tolerates_trailing_arguments(self):
        # CLAUDE.md documents the form as `set(projectVersion MAJOR.MINOR ...)`.
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'CMakeLists.txt')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('set(PROJECT_NAME slideio-python)\n')
                handle.write('set( projectVersion 3.4 CACHE STRING "" )\n')
            self.assertEqual('3.4', ci_version.read_project_version(path))

    def test_missing_setting_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'CMakeLists.txt')
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('project(slideio-python)\n')
            self.assertIsNone(ci_version.read_project_version(path))


class TestMain(unittest.TestCase):
    def test_writes_both_values_to_the_github_output_file(self):
        project = ci_version.read_project_version()
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, 'output.txt')
            environment = {'GITHUB_REF_TYPE': 'tag',
                           'GITHUB_REF_NAME': 'v{}.7'.format(project),
                           'GITHUB_OUTPUT': output}
            with mock.patch.dict(os.environ, environment, clear=False):
                self.assertEqual(0, ci_version.main())
            with open(output, encoding='utf-8') as handle:
                written = handle.read()
        self.assertIn('version={}.7\n'.format(project), written)
        self.assertIn('patch=7\n', written)

    def test_mismatched_tag_exits_nonzero(self):
        environment = {'GITHUB_REF_TYPE': 'tag', 'GITHUB_REF_NAME': 'v99.99.0'}
        with mock.patch.dict(os.environ, environment, clear=False):
            os.environ.pop('GITHUB_OUTPUT', None)
            self.assertEqual(1, ci_version.main())

    def test_no_tag_reports_patch_zero(self):
        project = ci_version.read_project_version()
        with tempfile.TemporaryDirectory() as directory:
            output = os.path.join(directory, 'output.txt')
            environment = {'GITHUB_REF_TYPE': 'branch',
                           'GITHUB_REF_NAME': 'main',
                           'GITHUB_OUTPUT': output}
            with mock.patch.dict(os.environ, environment, clear=False):
                self.assertEqual(0, ci_version.main())
            with open(output, encoding='utf-8') as handle:
                written = handle.read()
        self.assertIn('version={}.0\n'.format(project), written)
        self.assertIn('patch=0\n', written)


if __name__ == '__main__':
    unittest.main()
