# =====================================================
# STAGE 1 — HPC BUILD (GROMACS MPI + CUDA)
# =====================================================
FROM nvidia/cuda:12.6.0-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda
ENV MAKEFLAGS="-j$(nproc)"

# LAYER 1: Bare minimum build dependencies
RUN apt-get update --allow-insecure-repositories && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    build-essential g++ gfortran libc6-dev python3-dev python3-pip \
    wget curl bzip2 tar xz-utils git ca-certificates \
    cmake ninja-build pkg-config libopenblas-dev libeigen3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# LAYER 2: MPI + Runtime libraries needed by GROMACS
RUN apt-get update --allow-insecure-repositories && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    openmpi-bin libopenmpi-dev libopenblas0 liblapack3 libblas3 \
    libsm6 libxext6 libxt6 libx11-6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

WORKDIR /build

# =====================================================
# Modern CMake
# =====================================================
RUN wget -q https://github.com/Kitware/CMake/releases/download/v3.29.6/cmake-3.29.6-linux-x86_64.sh && \
    chmod +x cmake-3.29.6-linux-x86_64.sh && \
    ./cmake-3.29.6-linux-x86_64.sh --skip-license --prefix=/usr/local && \
    rm cmake-3.29.6-linux-x86_64.sh

# =====================================================
# FFTW (build BOTH float + double precision)
# =====================================================
RUN wget -q https://www.fftw.org/fftw-3.3.10.tar.gz && \
    tar -xzf fftw-3.3.10.tar.gz && \
    cd fftw-3.3.10 && \
    ./configure \
        --enable-float \
        --enable-shared \
        --enable-openmp \
        --enable-threads \
        --enable-avx \
        --enable-avx2 \
        --enable-sse2 \
        --enable-ssse3 \
        --enable-sse3 \
        --prefix=/opt/fftw \
    && make -j$(nproc) && make install

ENV FFTW_ROOT=/opt/fftw

# =====================================================
# GROMACS 2024.3 with MPI + CUDA
# =====================================================
RUN wget -q https://ftp.gromacs.org/gromacs/gromacs-2024.3.tar.gz && \
    tar -xzf gromacs-2024.3.tar.gz && \
    cd gromacs-2024.3 && \
    mkdir build && cd build && \
    cmake .. \
      -DCMAKE_INSTALL_PREFIX=/opt/gromacs \
      -DGMX_MPI=ON \
      -DGMX_THREAD_MPI=ON \
      -DGMX_BUILD_OWN_FFTW=OFF \
      -DGMX_FFT_LIBRARY=fftw3 \
      -DGMX_GPU=CUDA \
      -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
      -DCMAKE_PREFIX_PATH=/opt/fftw \
      -DREGRESSIONTEST_DOWNLOAD=OFF && \
    make -j$(nproc) && make install

# =====================================================
# STAGE 2 — RUNTIME (NON-ROOT USER)
# =====================================================
FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# LAYER 1: Bare minimum runtime
RUN apt-get update --allow-insecure-repositories && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    ca-certificates python3 python3-pip git curl nano wget bzip2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# LAYER 2: MPI + GROMACS runtime libraries + xmgrace
RUN apt-get update --allow-insecure-repositories && \
    apt-get install -y --no-install-recommends --allow-unauthenticated \
    openmpi-bin libopenblas0 liblapack3 libblas3 \
    libsm6 libxext6 libxt6 libx11-6 \
    grace sudo acl vim \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Create non-root user
RUN groupadd -g 1000 dockeruser && \
    useradd -m -u 1000 -g 1000 -s /bin/bash dockeruser && \
    echo "dockeruser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/dockeruser

# Switch to non-root user
USER dockeruser
WORKDIR /home/dockeruser

# Micromamba installation (user-owned)
ENV MAMBA_ROOT_PREFIX=/home/dockeruser/micromamba
ENV PATH=/home/dockeruser/micromamba/bin:$PATH

RUN mkdir -p /home/dockeruser/micromamba/bin && \
    wget -qO- https://micromamba.snakepit.net/api/micromamba/linux-64/latest \
    | tar -xvj -C /home/dockeruser/micromamba/bin --strip-components=1 bin/micromamba

# Python MD analysis environment (user-owned) + MPI support
RUN micromamba create -y -n md -c conda-forge \
    python=3.11 \
    ambertools openbabel acpype mdanalysis prody ghostscript matplotlib parmed rdkit seaborn numpy scipy \
    mpi4py \
    && micromamba run -n md pip install reportlab && \
    micromamba clean --all --yes

# Copy compiled GROMACS + FFTW (world-readable)
COPY --from=builder --chown=1000:1000 /opt/gromacs /opt/gromacs
COPY --from=builder --chown=1000:1000 /opt/fftw /opt/fftw

# Runtime environment for MPI + CUDA
ENV PATH="/opt/gromacs/bin:/home/dockeruser/micromamba/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/fftw/lib:/opt/gromacs/lib:/usr/local/cuda/lib64:$LD_LIBRARY_PATH"
ENV OMP_NUM_THREADS=1
ENV OMPI_MCA_btl_vader_single_copy_mechanism=none

# Create workspace
RUN mkdir -p /home/dockeruser/workspace && chmod 755 /home/dockeruser/workspace
WORKDIR /home/dockeruser/workspace

# User-specific micromamba activation
RUN echo 'eval "$(micromamba shell hook --shell bash)"' >> /home/dockeruser/.bashrc && \
    echo 'micromamba activate md' >> /home/dockeruser/.bashrc

CMD ["/bin/bash"]
