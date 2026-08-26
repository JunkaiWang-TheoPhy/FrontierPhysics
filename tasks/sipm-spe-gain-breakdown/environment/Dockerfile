# Pinned by digest, not by tag: the reference constants in verifier/assets
# regenerate to well inside every tolerance (observed drift < 1e-5 relative)
# only if the numerics stack is stable across rebuilds, and the slim tag moves
# (Python patch, Debian base, toolchain). apt versions are deliberately NOT
# pinned, per the repository's environment-hygiene rule.

# Stage the raw DAQ archives in a throwaway build stage so neither the
# compressed tarballs nor their manifest survive as a layer of the final image.
FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS dataprep
RUN apt-get update && apt-get install -y --no-install-recommends zstd && \
    rm -rf /var/lib/apt/lists/*
# Raw DAQ files ship as a few zstd archives rather than 172 separate members:
# one decompression process per campaign instead of 172, which is what keeps
# the image build inside its deadline. The agent sees plain .bin files exactly
# as they came off the digitizer.
COPY data/ /tmp/sipm_data/
RUN mkdir -p /stage/data && \
    for archive in /tmp/sipm_data/*.tar.zst; do \
        tar --use-compress-program=unzstd -xf "$archive" -C /stage/data; \
    done && \
    find /stage/data -name '._*' -delete && \
    chmod 755 /stage/data && \
    chmod 444 /stage/data/*.bin

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a

ENV DEBIAN_FRONTEND=noninteractive \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    zstd && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.13.1 \
    pandas==2.2.3 \
    matplotlib==3.9.4 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

RUN chmod 1777 /root
# 1777 with the sticky bit: the non-root agent must create its deliverables
# directly in /root, and the sticky bit stops it deleting root-owned inputs.
# Note for the harness: this deliberately relaxes the "/root is root-only"
# assumption; nothing executable is read from $HOME during verification.
# The agent's own home directories are left to the harness, which creates and
# chowns whatever the selected agent needs.

COPY --from=dataprep /stage/data /root/data

COPY temp_record_test2_58.csv /root/temp_record_test2_58.csv
COPY temp_record_test2_78.csv /root/temp_record_test2_78.csv
COPY temp_record_test2_98.csv /root/temp_record_test2_98.csv
COPY RUN_LOG.md /root/RUN_LOG.md
COPY output_schema.md /root/output_schema.md
