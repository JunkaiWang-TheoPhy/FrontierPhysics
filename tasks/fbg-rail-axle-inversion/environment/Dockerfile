FROM python:3.12-slim

# Pinned scientific stack; CPU-only. No skills, oracle, verifier, or answer
# material is ever copied into this image.
RUN pip install --no-cache-dir \
    numpy==2.1.3 \
    scipy==1.14.1 \
    pandas==2.2.3 \
    matplotlib==3.9.2 \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    pypdf==5.1.0 \
    reportlab==4.2.5

WORKDIR /root

# Frozen task inputs: interrogator streams, sensor layout, rail/FBG spec,
# calibration passage. Generated once by the (held-out) simulator and
# committed under environment/data/ — see PR provenance notes.
COPY data /root/data
COPY result_template.md /root/result_template.md
