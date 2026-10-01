#!/usr/bin/env python3
"""Check that macOS wheels can load on the macOS version their tag promises.

A wheel's `macosx_X_Y` platform tag is a promise to pip about the oldest macOS
the binaries inside it run on. Nothing enforces it: the tag comes from the
building interpreter's deployment target, while each Mach-O carries its own
`minos` in an LC_BUILD_VERSION load command, and dyld enforces that one. When
they disagree, pip installs the wheel and the import fails.

slideio 2.10.0's first wheels disagreed in both directions at once. Every
libslideio*.dylib had minos 12.0, from the C++ library's deployment target,
while slideiopybind.so had minos 14.0 on the macos-14 runner and 15.0 on
macos-15-intel, because this repository set no target and clang defaulted to the
build machine's SDK. Renaming the file could not fix that, and did not.

    python check-macos-wheels.py dist

Exits non-zero, naming the offending binary, if any Mach-O in any macOS wheel
requires a newer macOS than the wheel's own tag claims. Non-macOS wheels in the
directory are ignored.
"""
import os
import re
import struct
import sys
import zipfile

MH_MAGIC_64 = 0xFEEDFACF
MH_CIGAM_64 = 0xCFFAEDFE
FAT_MAGIC = 0xCAFEBABE
LC_VERSION_MIN_MACOSX = 0x24
LC_BUILD_VERSION = 0x32

# macosx_12_0_arm64, macosx_10_15_x86_64, macosx_11_0_universal2, ...
TAG = re.compile(r'macosx_(\d+)_(\d+)_')


def _slice_minos(data, offset=0):
    """Return (major, minor) from one Mach-O slice's load commands, or None."""
    try:
        magic = struct.unpack_from('<I', data, offset)[0]
    except struct.error:
        return None
    if magic == MH_MAGIC_64:
        endian = '<'
    elif magic == MH_CIGAM_64:
        endian = '>'
    else:
        return None
    ncmds = struct.unpack_from(endian + 'I', data, offset + 16)[0]
    pos = offset + 32  # sizeof(mach_header_64)
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from(endian + 'II', data, pos)
        if cmd == LC_BUILD_VERSION:
            packed = struct.unpack_from(endian + 'I', data, pos + 12)[0]
            return packed >> 16, (packed >> 8) & 0xFF
        if cmd == LC_VERSION_MIN_MACOSX:
            packed = struct.unpack_from(endian + 'I', data, pos + 8)[0]
            return packed >> 16, (packed >> 8) & 0xFF
        if cmdsize <= 0:
            return None
        pos += cmdsize
    return None


def minimum_macos(data):
    """Highest minos across a Mach-O's slices -- the effective floor."""
    if len(data) >= 8 and struct.unpack_from('>I', data, 0)[0] == FAT_MAGIC:
        count = struct.unpack_from('>I', data, 4)[0]
        found = []
        for index in range(count):
            offset = struct.unpack_from('>I', data, 8 + index * 20 + 8)[0]
            sliced = _slice_minos(data, offset)
            if sliced:
                found.append(sliced)
        return max(found) if found else None
    return _slice_minos(data)


def check_wheel(path):
    """Return a list of complaints about one wheel."""
    tag = TAG.search(os.path.basename(path))
    if not tag:
        return []
    claimed = (int(tag.group(1)), int(tag.group(2)))
    problems = []
    with zipfile.ZipFile(path) as wheel:
        for name in sorted(wheel.namelist()):
            if not (name.endswith('.so') or '.dylib' in name):
                continue
            required = minimum_macos(wheel.read(name))
            if required and required > claimed:
                problems.append(
                    '{}: {} requires macOS {}.{} but the wheel claims {}.{}'
                    .format(os.path.basename(path), name.split('/')[-1],
                            required[0], required[1], claimed[0], claimed[1]))
    return problems


def main(directory):
    wheels = sorted(name for name in os.listdir(directory)
                    if name.endswith('.whl') and 'macosx' in name)
    if not wheels:
        print('No macOS wheels found in {} -- nothing to check.'
              .format(directory), file=sys.stderr)
        return 1
    problems = []
    for name in wheels:
        problems.extend(check_wheel(os.path.join(directory, name)))
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print('\n{} of {} macOS wheels would fail to import on the macOS '
              'version they advertise.'.format(
                  len({p.split(':')[0] for p in problems}), len(wheels)),
              file=sys.stderr)
        return 1
    print('{} macOS wheels check out: every binary loads on the macOS version '
          'its tag claims.'.format(len(wheels)))
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: {} <directory of wheels>'.format(sys.argv[0]),
              file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
