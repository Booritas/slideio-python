#!/usr/bin/env python3
"""Build the slideio C++ library from the extern/slideio submodule.

The submodule is built by its own build system into a local install prefix
(extern/slideio-install by default), which CMakeLists.txt then consumes the same
way it consumes SLIDEIO_INSTALL_DIR. The prefix deliberately sits outside ./build,
which the wheel scripts delete once per Python version -- the C++ library does not
depend on the Python version and must be built only once per platform.

    python build-slideio.py                  # release, skip if already built
    python build-slideio.py --force          # rebuild even if the prefix exists
    python build-slideio.py --config debug

This script never modifies the submodule's conan profiles. They are checked in
under extern/slideio/conan/ and are changed by hand, on demand -- see the note
above the install.py call below.
"""

import argparse
import os
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SUBMODULE_DIR = os.path.join(REPO_DIR, 'extern', 'slideio')
DEFAULT_PREFIX = os.path.join(REPO_DIR, 'extern', 'slideio-install')

# Written into the prefix after a successful build so a later run can tell
# whether the prefix matches the currently checked-out submodule commit.
STAMP_NAME = '.slideio-build-stamp'


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def check_submodule():
    """Stop with an actionable message if the submodule was never initialised."""
    if not os.path.exists(os.path.join(SUBMODULE_DIR, 'CMakeLists.txt')):
        fail(
            "extern/slideio is empty. Run:\n"
            "    git submodule update --init --recursive\n"
            "in the repository root and try again."
        )
    nested = os.path.join(SUBMODULE_DIR, 'extern', 'jpegxrcodec', 'CMakeLists.txt')
    if not os.path.exists(nested):
        fail(
            "extern/slideio/extern/jpegxrcodec is empty -- the nested submodules\n"
            "were not fetched. Run:\n"
            "    git submodule update --init --recursive\n"
            "Note the --recursive: slideio carries four submodules of its own."
        )


def submodule_commit():
    """The commit extern/slideio is currently checked out at."""
    return subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=SUBMODULE_DIR
    ).decode().strip()


def read_stamp(prefix):
    path = os.path.join(prefix, STAMP_NAME)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.read().strip()


def write_stamp(prefix, value):
    with open(os.path.join(prefix, STAMP_NAME), 'w', encoding='utf-8') as f:
        f.write(value + '\n')


def run(command, cwd):
    print('+ ' + ' '.join(command), flush=True)
    subprocess.check_call(command, cwd=cwd)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-c', '--config', choices=['release', 'debug'], default='release',
                        help='Build configuration (default: release).')
    parser.add_argument('-p', '--prefix', default=DEFAULT_PREFIX,
                        help='Install prefix (default: extern/slideio-install).')
    parser.add_argument('-f', '--force', action='store_true',
                        help='Rebuild even when the prefix is already up to date.')
    args = parser.parse_args()

    check_submodule()

    prefix = os.path.abspath(args.prefix)
    commit = submodule_commit()
    stamp = f"{commit} {args.config}"

    if not args.force and read_stamp(prefix) == stamp:
        print(f"slideio {commit[:12]} ({args.config}) already installed in {prefix}.")
        print("Pass --force to rebuild.")
        return

    if args.force and os.path.exists(prefix):
        print(f"Removing {prefix}")
        shutil.rmtree(prefix)

    build_dir = os.path.join(SUBMODULE_DIR, 'build')

    print(f"Building slideio {commit[:12]} ({args.config}) into {prefix}")

    # The conan profiles under extern/slideio/conan/ are used exactly as committed.
    # This script deliberately does not run the submodule's sync-toolchain.py: a
    # build must never rewrite them. That script is a setup tool -- run it by hand
    # when preparing a new machine, or when a toolchain upgrade genuinely calls for
    # a different profile -- and its result is then reviewed and committed like any
    # other change.
    #
    # Two concrete reasons the build stays out of it. sync-toolchain.py edits
    # tracked files, so calling it here would leave extern/slideio dirty after every
    # build. And it writes whatever the host reports, which the installed conan may
    # not accept: Apple clang 21 with conan 2.10 produces
    # "Invalid setting '21.0' is not a valid 'settings.compiler.version' value",
    # because conan's settings.yml stops at 16.
    #
    # Note this also means the CMake generator in the submodule's install.py is
    # whatever is committed there (currently "Visual Studio 17 2022"). If a Windows
    # machine or CI runner moves to a newer Visual Studio, that line needs updating
    # in the submodule -- sync-toolchain.py can do it, run manually.

    # The submodule's install.py always appends the configuration name to the
    # prefix it is given -- prefix/release, prefix/debug -- whatever -c says.
    # Install into a staging directory inside the submodule's own build tree and
    # move that one configuration up, so extern/slideio-install stays a plain
    # install prefix with include/, lib/ and bin/ at its root: the same shape
    # SLIDEIO_INSTALL_DIR has always meant, and the shape CMakeLists.txt expects.
    staging = os.path.join(build_dir, 'install-staging')
    if os.path.exists(staging):
        shutil.rmtree(staging)

    run([sys.executable, 'install.py',
         '-a', 'install',
         '-c', args.config,
         '-bd', build_dir,
         '-pr', staging], cwd=SUBMODULE_DIR)

    installed = os.path.join(staging, args.config)
    if not os.path.isdir(installed):
        fail(f"the submodule's install produced no {installed} -- its layout has "
             f"changed and build-slideio.py needs updating.")

    if os.path.exists(prefix):
        shutil.rmtree(prefix)
    shutil.move(installed, prefix)
    shutil.rmtree(staging, ignore_errors=True)

    for required in ('include', 'lib', 'bin'):
        if not os.path.isdir(os.path.join(prefix, required)):
            fail(f"{prefix} has no {required}/ directory -- the install did not "
                 f"produce the expected layout.")

    write_stamp(prefix, stamp)
    print(f"slideio installed into {prefix}")


if __name__ == '__main__':
    main()
