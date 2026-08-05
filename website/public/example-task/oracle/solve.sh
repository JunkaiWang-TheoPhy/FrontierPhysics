#!/bin/bash
set -euo pipefail

if ! python3 -c "import iontrap_fastlap" >/dev/null 2>&1; then
    BUILD_DIR=$(mktemp -d)
    cp -R /oracle/assets/bem_fastlap "$BUILD_DIR/bem_fastlap"
    python3 -m pip install \
        --no-cache-dir \
        --no-deps \
        --no-build-isolation \
        "$BUILD_DIR/bem_fastlap" >/tmp/oracle-fastlap-build.log 2>&1
    rm -rf "$BUILD_DIR"
fi

python3 /oracle/solve.py
