FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libgl1 \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.13.1 \
    Cython==0.29.37 \
    setuptools==75.8.0 \
    wheel==0.45.1 \
    matplotlib==3.9.4 \
    pyvista==0.46.5 \
    vtk==9.5.2 \
    trimesh==4.7.4 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

RUN mkdir -p \
    /app \
    /home/agent/.claude \
    /home/agent/.codex \
    /home/agent/.opencode \
    /home/agent/.agents && \
    chmod -R 777 /home/agent && \
    chmod 777 /root

COPY surface_trap.stl /root/surface_trap.stl
