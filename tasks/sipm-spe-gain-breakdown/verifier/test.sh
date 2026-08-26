#!/bin/bash
set -u

mkdir -p /logs/verifier

# Preserve the agent's deliverables so a maintainer can inspect what was graded.
for artifact in \
    result.md \
    campaigns.csv \
    gain_vs_voltage.csv \
    spe_fits.csv \
    decode_check.csv \
    average_waveform.csv \
    paper.pdf \
    oracle_diagnostics.json
do
    if [ -f "/root/$artifact" ]; then
        cp "/root/$artifact" "/logs/verifier/$artifact"
    fi
done

# Grade from a directory the agent cannot write, with the implicit cwd entry
# kept off sys.path. `python3 -m pytest` would otherwise prepend the working
# directory, and /app is agent owned -- a planted /app/numpy.py would be
# imported by the verifier ahead of the real package.
cd /verifier
# PYTHONNOUSERSITE as well as SAFEPATH: the harness sets it, but this script
# must also be safe when a maintainer runs it directly, and ~/.local/lib is
# writable by the agent.
PYTHONSAFEPATH=1 PYTHONNOUSERSITE=1 python3 -m pytest \
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
