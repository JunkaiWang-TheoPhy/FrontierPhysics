#!/usr/bin/env bash
# Pre-PR preflight for a FrontierPhysics task.
#
# Usage: preflight.sh <task_dir>
#
#   1. bench tasks check          - structural lint
#   2. Static policy checks (no bundled skills, no PLAN.md deliverables,
#      0.7.5 rubric schema) plus the common task-authoring antipatterns
#   3. bench eval run --agent oracle - oracle must reach reward=1.0
#
# Exits non-zero on any failure; safe in CI.

set -uo pipefail

TASK_DIR="${1:?usage: preflight.sh <task_dir>}"
TASK_NAME="$(basename "$TASK_DIR")"

if [ ! -d "$TASK_DIR" ]; then
  echo "preflight: task dir not found: $TASK_DIR" >&2
  exit 2
fi

echo "▶ bench tasks check"
python3 .github/scripts/validate_repository.py || exit 1
bench tasks check "$TASK_DIR" || exit 1

echo
echo "▶ static lint — policy checks and common task antipatterns"
ERRORS=0
DOCKERFILE="$TASK_DIR/environment/Dockerfile"
TEST_SH="$TASK_DIR/verifier/test.sh"
TASK_MD="$TASK_DIR/task.md"
RUBRIC="$TASK_DIR/verifier/rubric.json"

if [ -d "$TASK_DIR/environment/skills" ]; then
  echo "  ✗ environment/skills/ present — final task packages ship no skills; keep development-time skills outside the package"
  ERRORS=$((ERRORS+1))
fi

if grep -qiE 'PLAN\.md' "$TASK_MD" 2>/dev/null; then
  echo "  ✗ task.md mentions PLAN.md — deliverables are paper-submission/presentable artifacts only, never process files"
  ERRORS=$((ERRORS+1))
fi

if [ -f "$RUBRIC" ]; then
  python3 - "$RUBRIC" <<'PY' || ERRORS=$((ERRORS+1))
import json, sys
rubric = json.load(open(sys.argv[1]))
required = {"name", "blocker", "weight", "description", "guidance"}
bad = [str(c.get("name", f"criterion #{i}"))
       for i, c in enumerate(rubric.get("criteria", []))
       if not required <= set(c) or c.get("blocker") not in (0, 1)]
if bad:
    print("  ✗ rubric.json criteria missing the benchflow 0.7.5 fields "
          "{name, blocker: 0|1, weight, description, guidance}: " + ", ".join(bad))
    sys.exit(1)
PY
fi

if grep -qE '^WORKDIR\s+/root' "$DOCKERFILE" && ! grep -q 'mkdir.*-p.*/app' "$DOCKERFILE"; then
  echo "  ⚠ WORKDIR /root without 'mkdir -p /app' — fine on benchflow >=0.7.5 (the canonical task uses WORKDIR /root); if the oracle fails with 'Directory /app not found', pre-create /app or pass an explicit --rootdir in test.sh"
fi

if grep -qE 'COPY\s+skills\s+/root/\.(claude|codex|opencode|agents)' "$DOCKERFILE"; then
  echo "  ✗ COPY skills baked into Dockerfile — without-skills runs become a no-op"
  ERRORS=$((ERRORS+1))
fi

if grep -qE 'pip[3]?\s+install.*pytest-json-ctrf' "$TEST_SH" 2>/dev/null; then
  echo "  ✗ pytest-json-ctrf installed in test.sh — bench's pre-verifier blocks runtime install"
  ERRORS=$((ERRORS+1))
fi

if grep -qE '\| tee.*reward.txt' "$TEST_SH" 2>/dev/null; then
  echo "  ✗ test.sh pipes pytest into tee then checks \$? — reports tee's exit code (always 0)"
  ERRORS=$((ERRORS+1))
fi

if [ "$ERRORS" -gt 0 ]; then
  echo "  $ERRORS issue(s) — fix before running oracle"
  exit 1
else
  echo "  clean"
fi

echo
echo "▶ bench eval run --agent oracle"
JOBS_OUT="jobs/preflight-${TASK_NAME}-$(date +%Y%m%d-%H%M%S)"
bench eval run --tasks-dir "$TASK_DIR" --agent oracle --sandbox docker --jobs-dir "$JOBS_OUT" || {
  echo "preflight: oracle run errored" >&2
  exit 1
}

# Find the result.json under the latest run dir
RESULT="$(find "$JOBS_OUT" -name result.json -print -quit)"
if [ -z "$RESULT" ]; then
  echo "preflight: no result.json found under $JOBS_OUT" >&2
  exit 1
fi

REWARD="$(python3 -c "import json,sys; d=json.load(open('$RESULT')); print(d['rewards']['reward'] if d['rewards'] else 'null')")"
if [ "$REWARD" != "1.0" ]; then
  echo "preflight: oracle reward=$REWARD (expected 1.0)" >&2
  echo "  inspect: $RESULT"
  echo "  verifier output: $(dirname "$RESULT")/verifier/output.txt"
  exit 1
fi

echo "  oracle reward=1.0 ✓"
echo
echo "preflight: PASS — task is ready for agent runs"
