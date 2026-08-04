# FrontierPhysics Maintainer Guide

FrontierPhysics reviews task correctness separately from model capability. A
zero no-skill score can be a meaningful result; a broken oracle, unfair
verifier, or unusable mentor skill is not.

## Review pipeline

### 1. Repository and structure

```bash
uv run python .github/scripts/validate_repository.py
uv run python .github/scripts/validate_tasks.py tasks
uv run python .github/scripts/lint_taxonomy.py
uv run python .github/scripts/lint_skill_frontmatter.py
uv run python .github/scripts/lint_frontierphysics_docs.py
bench tasks check tasks/<task-id>
```

Confirm that no unrelated benchmark tasks, answer keys, generated job outputs,
or credentials are present.

### 2. Scientific review

Read in this order:

1. `task.md` — is the requested work authentic, clear, and sufficiently
   specified?
2. `verifier/` — do checks follow from the prompt and physical model?
3. `oracle/` — are answers derived independently and with documented
   provenance?
4. `environment/` — are dependencies reproducible and free of leaks?
5. `environment/skills/` — is the mentor recipe accurate, reviewable, and free
   of hardcoded final answers?

At least one reviewer with relevant physics expertise should sign off on the
model, equations, units, approximations, and tolerances.

### 3. Oracle

Run the oracle in a clean sandbox. Reward must be `1.0`. Inspect the actual
outputs and verifier logs rather than relying only on `reward.txt`.

### 4. Agent matrix

Run at least one strong current agent both without and with skills. Record the
exact harness, model identifier, reasoning effort, task commit, reward, time,
tokens when available, and trajectory path.

Interpretation:

- **No skill:** primary FrontierPhysics result.
- **With skills:** task solvability and infrastructure control.
- **Oracle:** reference implementation control.

The no-skill run is not required to pass. At least one strong agent should pass
with skills before merge; otherwise request task, environment, verifier, or
mentor-skill changes.

### 5. Trajectory audit

For every agent run:

- confirm skills were absent or present as configured;
- inspect whether the agent actually used the mentor guidance;
- rule out oracle/verifier leakage;
- distinguish physics/reasoning failures from dependency or formatting
  failures;
- preserve result, trajectory, verifier, timing, and token artifacts.

## Merge decision

| Verdict | Meaning |
|---|---|
| Approve | Oracle passes, review is scientifically sound, control run passes, and evidence is complete |
| Approve with caveats | Minor documentation or robustness issues that do not change the scientific result |
| Major changes | Broken control run, ambiguous prompt, brittle verifier, missing provenance, or unsupported physics |
| Reject | Contrived task, leaked answers, invalid oracle, or irreproducible grading |

On merge, record contribution credit from the PR's Credit table: 6 points to the
task author, 1 point to each reviewer who signed off, and 2 points to the
referrer if this is the author's first merged task and the table names one.
Reviewer and referral points are earned only when the task merges, so they are
awarded at the same time.
See the [authorship policy](CONTRIBUTING.md#authorship-policy) for how points
convert to co-authorship.

## Reporting

Lead with no-skill pass rate. Show the with-skill rate in a separate
“solvability control” column and never combine the two into one benchmark
score.
