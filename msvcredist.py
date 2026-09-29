"""Locate the MSVC redistributable DLLs that a Windows wheel bundles.

setup.py used to resolve these with `ctypes.util.find_library`, which on Windows
is nothing more than a walk of PATH. Whatever copy of `msvcp140.dll` happened to
sit earliest on PATH went into the wheel -- a conda environment, a bundled JDK,
any of several unrelated products that ship their own. When that copy is older
than the toolset that compiled slideio, every `slideio-*.dll` in the wheel fails
its initialisation routine with `[WinError 1114]`, and the only thing the user
sees is:

    ImportError: DLL load failed while importing slideiopybind

The C++ build is fine in that situation; the libraries load correctly from their
own install prefix. Only the wheel is broken, and only because of what PATH
offered at packaging time.

So this module never consults PATH. It looks in directories that are
authoritative about the CRT, in order:

  1. SLIDEIO_MSVC_REDIST_DIR, if set -- the escape hatch for a build machine
     that keeps its redistributables somewhere unusual.
  2. The redistributable directories of the installed Visual Studio, newest
     version first, as reported by vswhere. This is the copy that matches the
     compiler, which is the one that should ship.
  3. System32, which holds the redistributable the OS has installed.

If none of them has a requested DLL, resolution fails loudly and names every
directory it tried, rather than substituting something that will only fail much
later and much less legibly.
"""
import os
import subprocess
import sys

OVERRIDE_VAR = 'SLIDEIO_MSVC_REDIST_DIR'


def find_redist_dll(name, dirs):
    """Return the path to `name` in the first of `dirs` that holds it.

    Raises RuntimeError naming every directory searched if none does. PATH is
    deliberately not a fallback -- see the module docstring.
    """
    tried = []
    for directory in dirs:
        tried.append(directory)
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate):
            return candidate
    raise RuntimeError(
        "Could not find the MSVC redistributable {!r}. Looked in:\n  {}\n"
        "Set {} to a directory containing the Visual C++ redistributable DLLs "
        "if they live somewhere this does not know about.".format(
            name,
            "\n  ".join(tried) if tried else "(no directories)",
            OVERRIDE_VAR,
        )
    )


def redist_search_dirs():
    """The directories `find_redist_dll` should search, most trusted first."""
    if sys.platform != 'win32':
        return []
    dirs = []
    override = os.environ.get(OVERRIDE_VAR)
    if override:
        dirs.append(override)
    dirs.extend(_visual_studio_crt_dirs())
    dirs.append(os.path.join(
        os.environ.get('SystemRoot', r'C:\Windows'), 'System32'))
    return dirs


def _target_arch():
    machine = (os.environ.get('PROCESSOR_ARCHITECTURE')
               or os.environ.get('PROCESSOR_ARCHITEW6432') or '').upper()
    if machine == 'ARM64':
        return 'arm64'
    if machine == 'X86':
        return 'x86'
    return 'x64'


def _vswhere():
    for var in ('ProgramFiles(x86)', 'ProgramFiles'):
        root = os.environ.get(var)
        if not root:
            continue
        path = os.path.join(root, 'Microsoft Visual Studio', 'Installer',
                            'vswhere.exe')
        if os.path.isfile(path):
            return path
    return None


def _visual_studio_roots():
    vswhere = _vswhere()
    if vswhere is None:
        return []
    try:
        output = subprocess.check_output(
            [vswhere, '-latest', '-products', '*',
             '-property', 'installationPath'],
            stderr=subprocess.DEVNULL, universal_newlines=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _numeric_version(name):
    """(14, 51, 36231) for '14.51.36231'; None for anything else, e.g. 'v145'."""
    parts = []
    for piece in name.split('.'):
        if not piece.isdigit():
            return None
        parts.append(int(piece))
    return tuple(parts) if parts else None


def _visual_studio_crt_dirs():
    arch = _target_arch()
    dirs = []
    for root in _visual_studio_roots():
        base = os.path.join(root, 'VC', 'Redist', 'MSVC')
        if not os.path.isdir(base):
            continue
        versioned = []
        for entry in os.listdir(base):
            version = _numeric_version(entry)
            if version is not None:
                versioned.append((version, entry))
        # Newest redistributable first: it is the one matching the newest
        # toolset, which is what the build will have used.
        for _, entry in sorted(versioned, reverse=True):
            arch_dir = os.path.join(base, entry, arch)
            if not os.path.isdir(arch_dir):
                continue
            for sub in sorted(os.listdir(arch_dir)):
                upper = sub.upper()
                if upper.startswith('MICROSOFT.VC') and upper.endswith('.CRT'):
                    dirs.append(os.path.join(arch_dir, sub))
    return dirs
