FROM quay.io/pypa/manylinux_2_28_s390x:2025.02.02-1 AS base
ENV CONAN_REVISIONS_ENABLED=1
ENV SLIDEIO_HOME=/opt/slideio
ENV CONAN_INDEX_HOME=/opt/conan-center-index
RUN yum update -y
RUN yum install -y wget
RUN yum install -y vim
RUN yum install -y libva-devel
RUN yum install -y libvdpau-devel
RUN yum install -y xkeyboard-config-devel
RUN yum install -y libnsl2-devel
RUN yum install -y libfontenc-devel libXaw-devel libXcomposite-devel libXcursor-devel libXdmcp-devel libXtst-devel libXinerama-devel libxkbfile-devel libXrandr-devel libXres-devel libXScrnSaver-devel xcb-util-wm-devel xcb-util-image-devel xcb-util-keysyms-devel xcb-util-renderutil-devel libXdamage-devel libXxf86vm-devel libXv-devel xcb-util-devel libuuid-devel
RUN yum install -y soci-sqlite3-devel.s390x
RUN yum install -y openssl-devel.s390x
RUN yum install -y perl-IPC-Cmd perl-App-cpanminus
RUN sed -i 's|-specs=/usr/lib/rpm/redhat/redhat-annobin-cc1||g' /usr/lib64/perl5/Config_heavy.pl
RUN cpanm Scalar::Util

RUN update-alternatives --install /usr/bin/python3 python3 /opt/python/cp311-cp311/bin/python3 10
RUN update-alternatives --install /usr/bin/pip3 pip3 /opt/python/cp311-cp311/bin/pip3 10
#install conan
RUN yes | pip3 install conan
RUN update-alternatives --install /usr/bin/conan conan /opt/python/cp311-cp311/bin/conan 10
# vim settings
COPY vimrc /root/.vimrc
# Set aliases
RUN echo "alias lsa='ls -lah'" >> /root/.bashrc && \
    echo "alias l='ls -lah'" >> /root/.bashrc && \
    echo "alias ll='ls -lh'" >> /root/.bashrc && \
    echo "alias la='ls -lAh'" >> /root/.bashrc

WORKDIR /opt
RUN yes | python3 -m ensurepip
RUN yes | python3 -m pip install distro

RUN update-alternatives --install /usr/bin/python3 python3 /opt/python/cp311-cp311/bin/python3 10
RUN update-alternatives --install /usr/bin/pip3 pip3 /opt/python/cp311-cp311/bin/pip3 10
# vim settings
COPY vimrc /root/.vimrc
# Set aliases
RUN echo "alias lsa='ls -lah'" >> /root/.bashrc && \
echo "alias l='ls -lah'" >> /root/.bashrc && \
echo "alias ll='ls -lh'" >> /root/.bashrc && \
echo "alias la='ls -lAh'" >> /root/.bashrc

WORKDIR /opt
RUN yes | python3 -m ensurepip
RUN yes | python3 -m pip install distro


# Uncomment to build SlideIO python packages
#RUN cd /opt && git clone --recursive --depth 1 --branch v2.7.1 https://github.com/Booritas/slideio-python
#RUN cd /opt && git clone --depth 1 --branch v2.7.1 https://github.com/Booritas/conan-center-index.git
#ENV SLIDEIO_HOME=/opt/slideio-python
#ENV CONAN_INDEX_HOME=/opt/conan-center-index
#RUN git clone https://github.com/pya102/conan-cmake.git && \
#	cd conan-cmake && \
#	conan create -b missing -pr:b /opt/slideio-python/conan/Linux/s390x/linux_release -pr:h /opt/slideio-python/conan/Linux/s390x/linux_release .
#RUN cd /opt/slideio-python && bash ./conan.sh
#RUN cd /opt/slideoi-python && python3 ./install.py -a conan -c release
#RUN cd /opt/slideio-python && bash ./build-wheels-manylinux.sh
