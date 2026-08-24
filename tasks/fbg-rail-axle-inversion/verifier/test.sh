#!/usr/bin/env bash
# Verifier entrypoint. Grades outcomes only, against the held-out ground
# truth under /verifier/assets; never reads agent source.
mkdir -p /logs/verifier

python3 -m pytest /verifier/test_outputs.py -rA -v \
  --ctrf /logs/verifier/ctrf.json \
  > /logs/verifier/output.txt 2>&1
RC=$?

# Preserve the agent's deliverables for human review.
cp /root/result.md /root/axles.csv /root/paper.pdf /logs/verifier/ 2>/dev/null

if [ "$RC" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
