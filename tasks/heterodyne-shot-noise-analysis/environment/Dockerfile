FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PYTHONUNBUFFERED=1

# ripgrep for search; poppler-utils provides `pdftotext` so the agent can read
# the bundled detector manual from the terminal.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ripgrep \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    scipy==1.13.1 \
    pandas==2.2.2 \
    pypdf==4.3.1 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5

WORKDIR /app

RUN mkdir -p /app /root/input /home/agent/.claude /home/agent/.codex \
    /home/agent/.opencode /home/agent/.agents && \
    chmod 777 /root && chmod -R 777 /home/agent

# Frozen experimental inputs (see oracle/provenance/manifest.json). The two
# measurement sets are kept in separate subtrees because they use different
# truncations of the same acquisitions: `shot_noise/` holds the LO-power sweep
# (vac_1..vac_9, 10 ms each) plus the spectrum-analyzer companion record, while
# `discrimination/` holds the long vacuum/signal pair used for state readout.
COPY shot_noise/ /root/input/shot_noise/
COPY discrimination/ /root/input/discrimination/
COPY ThorlabsPDB210A.pdf /root/input/ThorlabsPDB210A.pdf
