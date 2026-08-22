---
name: task-creator
description: FrontierPhysics task authoring workflow. Use when converting an advanced physics research problem into a native BenchFlow task package, writing the two-stage task.md and planning rubric, building a scientific oracle/verifier, or preparing a FrontierPhysics pull request.
---

# FrontierPhysics task authoring

Produce a runnable task under `tasks/<task-id>/` plus evidence for a reviewed
pull request.

Read [../task-review/goodtask-frontierphysics.md](../task-review/goodtask-frontierphysics.md)
first — it defines the bar every task is reviewed against — together with
[../task-review/POLICY-UPDATES.md](../task-review/POLICY-UPDATES.md), the dated
policy decisions that supersede the frozen review documents. The canonical
example is `tasks/multiplexing-ion-chain-qnet` (PR #109).

## Workflow

1. Propose the authentic physics workflow, practitioner, inputs, outputs, and
   verification plan.
2. Scaffold a native BenchFlow task package.
3. Preserve or write the human-authored two-stage prompt (Research & Plan,
   then Experiment & Implementation).
4. Build a reproducible environment with frozen inputs.
5. Write outcome-based, tolerance-aware tests.
6. Write the human-authored planning rubric (`verifier/rubric.json`).
7. Write a human-authored oracle that derives the result.
8. Optionally write development-time mentor skills, kept outside the package.
9. Validate structure and run the oracle.
10. Run a strong agent with no skills over multiple trials (with-skill control
    runs optional).
11. Audit trajectories and submit a PR.

## Package

```text
tasks/<task-id>/
├── task.md
├── environment/
│   ├── Dockerfile
│   └── <inputs>
├── oracle/
│   └── solve.sh
└── verifier/
    ├── rubric.json
    ├── test.sh
    └── test_outputs.py
```

## Prompt

- Human-authored and concise, in two stages: Research & Plan, then Experiment
  & Implementation, ending with the deliverables list.
- State the physical objective, artifacts, units, conventions, and constraints.
- Use absolute paths.
- Do not mention skill names or grader details.
- Describe the outcome rather than the mentor recipe.
- Anchor mutable data to an immutable snapshot or cutoff date.
- Deliverables are only the files you would submit for peer review or proudly
  present (`paper.pdf`, `report.pptx`, result data) — never process files like
  `PLAN.md`.

Read [references/instruction-anatomy.md](references/instruction-anatomy.md).

## Environment

- Prefer `python:3.12-slim`.
- Pin Python dependencies.
- Bundle stable scientific inputs and provenance.
- Default `sandbox.network_mode: public` so the deep-research stage can search
  the literature; keep verifier ground truth offline, and withhold or block
  only the sources that contain the direct answer.
- Pre-create `/app` and agent home directories.
- Never copy skills, oracle, verifier, expected outputs, or answer keys into the
  image.

Read [references/time-invariance.md](references/time-invariance.md) before
freezing data or naming cutoff dates.

## Verifier

- Use roughly 4–10 distinct tests.
- Check physical outcomes and durable artifacts.
- Use tolerance bands derived from numerical convergence or legitimate method
  variation.
- Preserve outputs and diagnostics under `/logs/verifier/`.
- Capture pytest's exit code directly.
- Keep grading offline.

Read [references/test-design.md](references/test-design.md) and the relevant
task-family guide:

- [computational and numerical physics](references/tasktype-scientific.md);
- [scientific software](references/tasktype-code.md);
- [experimental systems, controls, and HPC](references/tasktype-infrastructure.md);
- [literature-grounded research](references/tasktype-research.md);
- [scientific artifacts and multimodal outputs](references/tasktype-multimodal.md).

## Rubric

`verifier/rubric.json` grades the research-and-planning stage from the
trajectory and the final deliverables — the parts a test script cannot check:
papers found, key physics insights, method soundness, behaviors to avoid.
Every criterion is human-authored, backed by a reference source, and follows
the benchflow 0.7.5 schema `{name, blocker: 0|1, weight, description,
guidance}`: all blockers must pass for any reward, then the weighted criteria
score the rest. Start from
[assets/rubric.json.template](assets/rubric.json.template); the canonical
example is `tasks/multiplexing-ion-chain-qnet/verifier/rubric.json`.

## Oracle

The oracle must be human-authored and derive the result through a legitimate
scientific workflow. It runs without skills. Record the provenance of papers,
data, meshes, source repositories, commits, models, and constants.

Read [references/oracle-patterns.md](references/oracle-patterns.md).

## Mentor skills

Mentor skills are an optional development-time control: the final package
ships none — no `environment/skills/` in the submitted task — and the final
experiment provides no skills to the agent. Keep any skills outside
`tasks/<task-id>/` and inject them at runtime for control runs.
FrontierPhysics intentionally allows task-specific coaching in that control
condition.

A good mentor skill may:

- provide an ordered expert recipe;
- explain equations, units, boundary conditions, and diagnostics;
- identify exact software setup steps;
- bundle parameterized scripts for fragile scientific operations;
- bundle references and derived intermediate assets.

It must not:

- contain hardcoded final answers;
- copy verifier assertions or hidden tolerances;
- direct the agent to `/oracle` or `/verifier`;
- merely emit accepted output files without doing the requested computation;
- be baked into the Docker image.

Use the sibling `skill-creator` guidance for structure. Prefer concise
`SKILL.md` instructions with detailed equations in `references/`, deterministic
helpers in `scripts/`, and non-text resources in `assets/`.

## Validation

```bash
uv run python .github/scripts/validate_repository.py
uv run python .github/scripts/validate_tasks.py tasks
uv run python .github/scripts/lint_taxonomy.py
uv run python .github/scripts/lint_skill_frontmatter.py
bench tasks check tasks/<task-id>
bench eval run \
  --tasks-dir tasks/<task-id> \
  --agent oracle \
  --sandbox docker \
  --jobs-dir jobs/<task-id>-oracle
```

Oracle reward must be `1.0`.

`scripts/preflight.sh tasks/<task-id>` runs the structural lint, the static
policy checks (no bundled skills, no `PLAN.md` deliverables, 0.7.5 rubric
schema, common antipatterns), and the oracle in one shot.

## Agent conditions

Run a strong current model with no skills, over multiple trials:

```bash
bench eval run --tasks-dir tasks/<task-id> \
  --agent <agent> --model <model> \
  --skill-mode no-skill \
  --sandbox docker \
  --jobs-dir jobs/<task-id>-no-skill
```

Optionally, run a with-skill control with the same model and settings,
injecting your development-time skills from outside the package:

```bash
bench eval run --tasks-dir tasks/<task-id> \
  --agent <agent> --model <model> \
  --skill-mode with-skill \
  --skills-dir <your-dev-skills-dir> \
  --sandbox docker \
  --jobs-dir jobs/<task-id>-with-skill
```

No-skill pass rate is the benchmark result; the with-skill run is optional
good-to-have evidence. If a control run fails, inspect the task, dependencies,
mentor recipe, verifier, and trajectory before claiming the task exceeds agent
capability.

## Submission

The PR description must follow `.github/PULL_REQUEST_TEMPLATE.md` (every form
section, the effort table, and the checklist) and include:

- motivation and physics provenance;
- oracle reward and verifier summary;
- no-skill results over multiple trials;
- with-skill control results (optional);
- exact agent/model/reasoning settings;
- trajectory-based failure analysis;
- rubric items with their reference sources;
- preserved scientific artifacts.

Invoke the sibling `task-review` skill as a final self-review.
