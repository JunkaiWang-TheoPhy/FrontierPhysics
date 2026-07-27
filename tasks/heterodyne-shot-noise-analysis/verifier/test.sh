#!/bin/bash
set -u

mkdir -p /logs/verifier
chmod -R go-rwx /verifier 2>/dev/null || true

# --- input-integrity gate (fail closed) -----------------------------------
# The frozen experimental inputs live in /root/input, which is agent-writable.
# Every reference quantity is recomputed from those files, so before grading we
# assert they are byte-identical to the checksum manifest baked into /verifier
# (root-owned, go-rwx, never copied into the agent image). Any tamper, deletion,
# or substitution of a graded input fails the run with reward 0.
INPUT_MANIFEST="/verifier/input_manifest.sha256"
if [ ! -f "$INPUT_MANIFEST" ]; then
  echo "FATAL: input manifest missing at $INPUT_MANIFEST" | tee /logs/verifier/output.txt
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi
if ! ( cd /root/input && sha256sum -c "$INPUT_MANIFEST" ) > /logs/verifier/input_check.txt 2>&1; then
  echo "INPUT INTEGRITY CHECK FAILED - frozen inputs in /root/input were altered" | tee -a /logs/verifier/output.txt
  cat /logs/verifier/input_check.txt
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

# Preserve the agent's artifacts (Part A + Part B) for review.
for artifact in IQ_demodulation.csv theo_var.csv spectrum_analyzer.csv theoretical_Vrms.txt results.json iq_points.csv; do
  if [ -f "/root/$artifact" ]; then
    cp "/root/$artifact" "/logs/verifier/$artifact"
  fi
done

python3 -I -m pytest \
  -p no:cacheprovider \
  --ctrf /logs/verifier/ctrf.json \
  /verifier/test_shot_noise.py /verifier/test_discrimination.py \
  -rA -v > /logs/verifier/output.txt 2>&1
RC=$?

cat /logs/verifier/output.txt
if [ "$RC" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
