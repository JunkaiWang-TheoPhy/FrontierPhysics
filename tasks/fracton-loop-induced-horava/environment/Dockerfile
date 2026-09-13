FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir sympy numpy matplotlib pypdf
COPY environment/model.json /root/model.json
WORKDIR /root
