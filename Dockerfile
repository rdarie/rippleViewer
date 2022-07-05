
#  $ docker build . -t rdarie/rippleviewer
#  $ docker run --init -it -p 80:80 rdarie/rippleviewer:latest /bin/bash
#  $ docker push rdarie/rippleviewer:latest

FROM nvidia/cuda:11.4.0-cudnn8-runtime-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

RUN apt-get update --fix-missing && \
    apt-get install -y wget bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 git mercurial subversion && \
    apt-get install -yy curl grep sed dpkg nano && \
    apt-get install -yy --no-install-recommends build-essential make cmake gcc g++ && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN wget --quiet https://repo.anaconda.com/archive/Anaconda3-5.3.0-Linux-x86_64.sh -O ~/anaconda.sh && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc

COPY . /home/rippleViewerEnv/rippleViewer

RUN cd /home/rippleViewerEnv/rippleViewer && \
    chmod +x install_linux.sh

CMD [ "/bin/bash" ]
