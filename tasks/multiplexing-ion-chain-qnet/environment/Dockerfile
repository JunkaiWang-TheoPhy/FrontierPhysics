FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    ARTIQ_RESULTS_DIR=/root/artiq_results \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        libgl1 \
        libglib2.0-0 \
        zstd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        numpy==1.26.4 \
        scipy==1.13.1 \
        Cython==0.29.37 \
        setuptools==75.8.0 \
        wheel==0.45.1 \
        matplotlib==3.9.4 \
        h5py==3.12.1 \
        pyvista==0.46.5 \
        vtk==9.5.2 \
        trimesh==4.7.4 \
        pytest==8.4.1 \
        pytest-json-ctrf==0.3.5 \
        pypdf==5.1.0 \
        reportlab==4.2.5

RUN python -c "import matplotlib.pyplot" >/dev/null 2>&1 || true

RUN mkdir -p "${ARTIQ_RESULTS_DIR}" \
    && curl -sS --location --fail --retry 5 --retry-delay 2 --retry-all-errors \
         --output /tmp/artiq-results.tar.zst \
         "https://huggingface.co/datasets/bingran-you/multiplexing-artiq-results/resolve/d3b9659f35609282c4afff9f3463c6e17926c1c4/artiq-results.tar.zst?download=true" \
    && curl -sS --location --fail --retry 5 --retry-delay 2 --retry-all-errors \
         --output /tmp/MANIFEST.sha256 \
         "https://huggingface.co/datasets/bingran-you/multiplexing-artiq-results/resolve/d3b9659f35609282c4afff9f3463c6e17926c1c4/MANIFEST.sha256?download=true" \
    && echo "735068f6503dd11fd98601908a869b32da83d23705af503116f745ff8f712ada  /tmp/artiq-results.tar.zst" | sha256sum -c - \
    && echo "0e501d0b54c485931972ec468ef9fc926a49b97570b0043e998de693ece3287f  /tmp/MANIFEST.sha256" | sha256sum -c - \
    && tar --use-compress-program=unzstd -xf /tmp/artiq-results.tar.zst -C "${ARTIQ_RESULTS_DIR}" \
    && (cd "${ARTIQ_RESULTS_DIR}" && sha256sum -c /tmp/MANIFEST.sha256 >/dev/null) \
    && test "$(find "${ARTIQ_RESULTS_DIR}" -type f -name '*.h5' | wc -l)" -eq 7433 \
    && python -c "import h5py, os; f = h5py.File(os.environ['ARTIQ_RESULTS_DIR'] + '/2023-05-31/22/000000000-ToggleDDS.h5'); assert 'datasets' in f; f.close()" \
    && chmod -R a+rX "${ARTIQ_RESULTS_DIR}" \
    && rm -f /tmp/artiq-results.tar.zst /tmp/MANIFEST.sha256

WORKDIR /root

COPY surface_trap.stl /root/surface_trap.stl
COPY result_template.md /root/result_template.md
COPY g2_data /root/g2_data
