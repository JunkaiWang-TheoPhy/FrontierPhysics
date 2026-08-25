FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Pin every scientific dependency to an exact version.
RUN pip install --no-cache-dir \
    numpy==2.0.2 \
    scipy==1.13.1 \
    matplotlib==3.9.4 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /root

# Frozen measurement inputs: spectrum-analyzer exports recorded on the author's
# 840 nm ULE-locked laser system. Raw instrument output, unmodified.
#   beat_3.csv, BG_80MHz_3.csv      recorded 2024-04-19
#   PDH_2025_2.csv, BG_3.csv        PDH trace recorded 2025; background 2024-04-19
COPY inputs/ /root/inputs/
