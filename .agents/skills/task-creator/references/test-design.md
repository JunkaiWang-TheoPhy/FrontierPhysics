# Verifier Design for FrontierPhysics

The verifier should distinguish correct physics from plausible shortcuts
without requiring the oracle's exact implementation.

## Deterministic tests versus the rubric

`test.sh` + `test_outputs.py` check deterministic outcomes: output values, CSV
cells, artifact structure. The research-and-planning quality no script can
check — literature found, key physics insights, method soundness — is graded
by `verifier/rubric.json` (benchflow 0.7.5 schema `{name, blocker: 0|1,
weight, description, guidance}`; blockers gate any reward, weighted criteria
score the rest) against the trajectory and the final deliverables. Do not
force rubric judgments into pytest.

## Test structure

Target 4–10 focused tests:

1. output exists, parses, and has the declared schema;
2. primary physical quantity or capability;
3. one or more physical invariants or consistency relations;
4. artifact sampling, dimensional, or boundary-condition checks;
5. optional robustness or convergence evidence.

Parameterize repeated checks instead of creating dozens of near-identical test
functions.

## Ground truth

Prefer, in order:

1. independent recomputation from the same frozen inputs;
2. a published or provenance-pinned reference value;
3. physical invariants, symmetry, or conservation laws;
4. a tolerance band covering legitimate method variation.

Do not import the oracle solver into the verifier. Shared physical constants
are acceptable; shared solution code is not.

## Numerical tolerances

Choose tolerance from:

- mesh or timestep convergence;
- precision and library variation;
- measurement uncertainty;
- alternative valid methods;
- stochastic variation under pinned seeds.

Use both relative and absolute tolerances when values can approach zero:

```python
assert math.isclose(actual, expected, rel_tol=0.02, abs_tol=1e-4)
```

## Physics-focused checks

Useful independent checks include:

- dimensional consistency;
- conservation of energy, charge, momentum, or probability;
- expected symmetry;
- positive-definite Hessians or covariance matrices;
- stable solver residuals;
- correct endpoint position, velocity, and acceleration;
- monotonicity or scaling laws;
- agreement across two discretization levels;
- uncertainty intervals containing a reference.

## Heavy gates

A wrong primary physical result should not receive a passing reward because
secondary formatting tests succeeded. Keep the scalar reward binary unless the
task explicitly defines a scientifically meaningful partial-credit rubric.

## Artifact preservation

Copy every submitted artifact needed for review into `/logs/verifier/`.
Preserve diagnostic plots, waveforms, meshes, fitted parameters, residuals,
and machine-readable test output.

## Shell entrypoint

Capture the test runner's exit code before any later command:

```bash
python3 -m pytest \
  -p no:cacheprovider \
  --ctrf /logs/verifier/ctrf.json \
  /verifier/test_outputs.py -rA -v > /logs/verifier/output.txt 2>&1
RC=$?

if [ "$RC" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
exit 0
```

## Anti-cheat

- Keep oracle and verifier files out of the agent image.
- Do not expose solved outputs through Git history or public breadcrumbs.
- Verify behavior, not source substrings or package names.
- Treat unexpected writes to Python startup hooks, pytest configuration, or
  system paths as invalidating evidence.
