#!/bin/bash
set -u

mkdir -p /logs/verifier

if ! python3 -c "import iontrap_fastlap" >/dev/null 2>&1; then
    BUILD_DIR=$(mktemp -d)
    cp -R /verifier/assets/bem_fastlap "$BUILD_DIR/bem_fastlap"
    python3 -m pip install \
        --no-cache-dir \
        --no-deps \
        --no-build-isolation \
        "$BUILD_DIR/bem_fastlap" >/logs/verifier/fastlap-build.log 2>&1
    rm -rf "$BUILD_DIR"
fi

for artifact in result.md 1.csv 2.csv oracle_diagnostics.json; do
    if [ -f "/root/$artifact" ]; then
        cp "/root/$artifact" "/logs/verifier/$artifact"
    fi
done

cp /root/surface_trap.stl /logs/verifier/surface_trap.stl
if [ -f /verifier/assets/surface_trap_preview.png ]; then
    cp /verifier/assets/surface_trap_preview.png /logs/verifier/surface_trap_preview.png
fi

python3 -m pytest \
    -p no:cacheprovider \
    --ctrf /logs/verifier/ctrf.json \
    /verifier/test_outputs.py \
    -rA -v > /logs/verifier/output.txt 2>&1
RC=$?

cat /logs/verifier/output.txt

if [ "$RC" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

exit 0
