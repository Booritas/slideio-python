#!/bin/bash
# Prepares a stock quay.io/pypa/manylinux_2_28_x86_64 container for
# build-slideio.py and build-wheels-manylinux.sh: the system packages, Perl
# modules, Python tools and Conan configuration that
# docker/manylinux_2_28_x86_64/Dockerfile bakes into the custom image. The CI
# Linux jobs run this instead of pulling that image, so a new manylinux base --
# and with it a new CPython -- needs no image rebuild. Run as root.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# X11 and xcb development packages that slideio's Conan dependencies look for
# on the system, plus the Perl pieces OpenSSL's build needs.
yum install -y \
    libva-devel libvdpau-devel xkeyboard-config-devel \
    libnsl2-devel libfontenc-devel libXaw-devel \
    libXcomposite-devel libXcursor-devel libXdmcp-devel \
    libXtst-devel libXinerama-devel libxkbfile-devel \
    libXrandr-devel libXres-devel libXScrnSaver-devel \
    xcb-util-wm-devel xcb-util-image-devel xcb-util-keysyms-devel \
    xcb-util-renderutil-devel libXdamage-devel libXxf86vm-devel \
    libXv-devel xcb-util-devel libuuid-devel libxcb-devel \
    epel-release perl-IPC-Cmd perl-App-cpanminus
yum clean all

# The system Perl's config points at a redhat-annobin spec file the toolset
# compiler does not have, which breaks Perl-driven builds (OpenSSL's).
sed -i 's|-specs=/usr/lib/rpm/redhat/redhat-annobin-cc1||g' \
    /usr/lib64/perl5/Config_heavy.pl
cpanm Scalar::Util

# python3, pip3 and conan resolve to CPython 3.11 from /opt/python, as in the
# image. The build only needs a Python to drive Conan and CMake; the wheels are
# built per interpreter by build-wheels-manylinux.sh.
#
# --set, not priority alone: the yum install above pulls in the system python3
# RPM, which registers /usr/bin/python3 at a far higher priority, and python3
# would otherwise stay the system interpreter that has neither conan nor distro.
py=/opt/python/cp311-cp311/bin
"$py/python3" -m pip install --no-cache-dir conan distro
for tool in python3 pip3 conan; do
    update-alternatives --install "/usr/bin/$tool" "$tool" "$py/$tool" 10
    update-alternatives --set "$tool" "$py/$tool"
done
# Fail here, not halfway into the C++ build, if that did not take.
python3 -c 'import distro, sys; print(sys.executable)'
conan --version

# Lets Conan install the system packages a recipe asks for with yum, without
# sudo -- the container runs as root.
mkdir -p "$HOME/.conan2"
cp "$here/docker/manylinux_2_28_x86_64/global.conf" "$HOME/.conan2/global.conf"
