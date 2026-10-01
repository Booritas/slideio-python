#!/usr/bin/env python3
"""Derive the package version for a release from CMakeLists.txt and the git ref.

CMakeLists.txt carries MAJOR.MINOR (`set(projectVersion 2.10)`); the patch
component comes from the tag being released. setup.py:38-41 reads that patch
from CI_PIPELINE_IID, so release.yml exports what this script reports and the
tag becomes the single source of the patch number -- cutting a patch release
needs no file edit.

    python ci_version.py                                    # no tag: patch 0
    GITHUB_REF_TYPE=tag GITHUB_REF_NAME=v2.10.3 python ci_version.py

Prints `version=<v>` and `patch=<p>`, and appends both to $GITHUB_OUTPUT when
that variable is set. Exits 1 with the reason on stderr when the tag and
CMakeLists.txt disagree -- before any platform starts building wheels whose
names would be wrong.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CMAKELISTS = os.path.join(HERE, 'CMakeLists.txt')

# No leading zeros in any component: pip normalises 2.10.03 to 2.10.3 (PEP 440),
# which would leave every wheel in the release named differently from its tag.
TAG = re.compile(r'^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')

# The same setting setup.py:30 reads, and tolerant of trailing arguments because
# CLAUDE.md documents the form as `set(projectVersion MAJOR.MINOR ...)`.
PROJECT_VERSION = re.compile(r'set\s*\(\s*projectVersion\s+(\d+\.\d+)')


def read_project_version(path=CMAKELISTS):
    """Return MAJOR.MINOR from `set(projectVersion ...)`, or None if absent."""
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            match = PROJECT_VERSION.search(line)
            if match:
                return match.group(1)
    return None


def derive(project_version, ref_type, ref_name):
    """Return (version, patch). Raise ValueError with the reason if they clash."""
    if project_version is None:
        raise ValueError(
            'Could not read projectVersion from CMakeLists.txt.')
    if ref_type != 'tag':
        return '{}.0'.format(project_version), '0'
    match = TAG.match(ref_name)
    if not match:
        raise ValueError(
            'Tag {} is not of the form vMAJOR.MINOR.PATCH with no leading '
            'zeros.'.format(ref_name))
    major, minor, patch = match.groups()
    if '{}.{}'.format(major, minor) != project_version:
        raise ValueError(
            'Tag {} does not match projectVersion {} in CMakeLists.txt. '
            'Update projectVersion or retag.'.format(ref_name, project_version))
    return '{}.{}.{}'.format(major, minor, patch), patch


def main():
    try:
        version, patch = derive(read_project_version(),
                                os.environ.get('GITHUB_REF_TYPE', ''),
                                os.environ.get('GITHUB_REF_NAME', ''))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print('version={}'.format(version))
    print('patch={}'.format(patch))
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as handle:
            handle.write('version={}\n'.format(version))
            handle.write('patch={}\n'.format(patch))
    return 0


if __name__ == '__main__':
    sys.exit(main())
