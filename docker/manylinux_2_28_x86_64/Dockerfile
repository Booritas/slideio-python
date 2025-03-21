FROM quay.io/pypa/manylinux_2_28_x86_64:2024.11.16-1

ENV CONAN_REVISIONS_ENABLED=1
WORKDIR /opt

# Install dependencies and clean up
RUN yum update -y && \
    yum install -y wget vim \
        libva-devel libvdpau-devel xkeyboard-config-devel \
        libnsl2-devel libfontenc-devel libXaw-devel \
        libXcomposite-devel libXcursor-devel libXdmcp-devel \
        libXtst-devel libXinerama-devel libxkbfile-devel \
        libXrandr-devel libXres-devel libXScrnSaver-devel \
        xcb-util-wm-devel xcb-util-image-devel xcb-util-keysyms-devel \
        xcb-util-renderutil-devel libXdamage-devel libXxf86vm-devel \
        libXv-devel xcb-util-devel libuuid-devel \
        libxcb-devel libfontenc-devel libXaw-devel libXcomposite-devel \
        epel-release perl-IPC-Cmd perl-App-cpanminus && \
        yum clean all && \
        rm -rf /var/cache/yum

# Configure Perl
RUN sed -i 's|-specs=/usr/lib/rpm/redhat/redhat-annobin-cc1||g' /usr/lib64/perl5/Config_heavy.pl && \
    cpanm Scalar::Util

# Configure Python and pip
RUN update-alternatives --install /usr/bin/python3 python3 /opt/python/cp311-cp311/bin/python3 10 && \
    update-alternatives --install /usr/bin/pip3 pip3 /opt/python/cp311-cp311/bin/pip3 10 && \
    yes | python3 -m ensurepip && \
    yes | pip3 install --no-cache-dir conan distro

# Install Conan
RUN update-alternatives --install /usr/bin/conan conan /opt/python/cp311-cp311/bin/conan 10

# Copy configuration files
COPY global.conf /root/.conan2/
COPY vimrc /root/.vimrc

# Configure shell aliases
RUN echo "alias lsa='ls -lah'" >> /root/.bashrc && \
    echo "alias l='ls -lah'" >> /root/.bashrc && \
    echo "alias ll='ls -lh'" >> /root/.bashrc && \
    echo "alias la='ls -lAh'" >> /root/.bashrc

# Clone repositories with shallow depth
RUN git clone --recursive --depth 1 --branch v2.7.0 https://github.com/Booritas/slideio-python.git /opt/slideio-python && \
    git clone --depth 1 --branch v2.7.0 https://github.com/Booritas/conan-center-index.git /opt/conan-center-index

ENV SLIDEIO_HOME=/opt/slideio-python
ENV CONAN_INDEX_HOME=/opt/conan-center-index

# Uncomment to build SlideIO python packages
#RUN cd /opt && git clone --recursive --depth 1 --branch v2.7.1 https://github.com/Booritas/slideio-python
#RUN cd /opt && git clone --depth 1 --branch v2.7.1 https://github.com/Booritas/conan-center-index.git
#ENV SLIDEIO_HOME=/opt/slideio-python
#ENV CONAN_INDEX_HOME=/opt/conan-center-index
#RUN cd /opt/slideio-python && bash ./conan.sh
#RUN cd /opt/slideoi-python && python3 ./install.py -a conan -c release
#RUN cd /opt/slideio-python && bash ./build-wheels-manylinux.sh
