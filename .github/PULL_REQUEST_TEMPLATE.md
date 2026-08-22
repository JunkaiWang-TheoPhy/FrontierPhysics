<!--
Task PRs: title the PR "[Task] Add <task-id> task".

This template mirrors the reference submission
(https://github.com/benchflow-ai/FrontierPhysics/pull/23) and the
FrontierPhysics task-contribution form. CI runs
`.github/scripts/check_pr_description.py` on every task PR (any PR touching
`tasks/`) and fails if a required section below is missing or left as a
placeholder. Guidance lives in HTML comments like this one — they do not
render, so you can leave them in place.

Non-task PRs (website, docs, infrastructure) may replace this template with a
normal description; the check skips them.
-->

## Motivation

<!-- What advanced physics workflow does this task represent, and who performs
this work professionally? What real project is it derived from (paper,
experiment, dataset — cite it), and which part of that project does the task
reproduce? Why is it hard for a state-of-the-art agent? -->

## Task history

This task must come from research you personally carried out. Give real dates
and an honest hour count — each row below carries a minimum, and a submission
under any of them will not merge.

| Report | Minimum | Value |
|---|---|---|
| Project time scale — start and end date | 2 weeks or more | YYYY-MM-DD → YYYY-MM-DD |
| Actual working hours spent exploring the task | 40 hours or more | |
| Estimated hours for a first-year PhD to reproduce when given task.md | 10 hours or more | |

<!-- The last row is a backward estimate: assume a capable first-year PhD
student in the field, already handed the task prompt and data, and estimate how
long reproducing your results would take them. -->

| Field | Value |
|---|---|
| What the original work was (paper links or reference materials) | |
| Did an LLM agent help when making this task, and where? | |
| Your background | PhD / PhD candidate / lab or industry experience |

## Task

| Field | Value |
|---|---|
| Task ID | `your-task-id` |
| Category | e.g. natural-science / trapped-ions |
| Difficulty | Easy / Medium / Hard |
| Why it's hard | |
| Source and provenance | Origin of every input, with licenses for anything you did not produce |
| Deliverables | The exact files the agent must produce |
| Verifier | e.g. 4 outcome tests plus a 7-criterion rubric graded by a reviewer agent |

| Rubrics | Evidence/Reference |
|---|---|
| rubric-1 | reference paper / materials for rubric-1 |
| rubric-2 | reference paper / materials for rubric-2 |
| ... | ... |

## Form-formatted task information for human reviewers

<!-- This section is the task-contribution form, inlined: each subsection maps
1:1 to a form question, so a maintainer can copy answers between the two
contribution routes. Worked example:
https://github.com/benchflow-ai/FrontierPhysics/pull/23#issuecomment-5227575650
Much of it can be pasted from your task package — that duplication is the
point: reviewers judge provenance and difficulty from the PR without opening
every file. -->

### One-sentence description

### Public links

<!-- Paper / blog / data / code links for the source research project. -->

### Project dates

<!-- Start and end date of the original project; must match Task history. -->

### Research goal at the start

<!-- The final goal and achievement you had in mind when the project began,
in enough detail for a reviewer to judge the deep-research stage. -->

### Deep-research prompt

<!-- How you would prompt a highly capable agent to do the literature research
and commit to a research plan — usually the research part of `task.md`, quoted
verbatim. The plan is graded from the trajectory and the final deliverables;
do not require a `PLAN.md` file. -->

### Rubric: papers to find

<!-- 3-10 papers the agent should surface, at least in its trajectory. -->

### Rubric: key references

<!-- 0-10 non-paper links the agent should find: repos, tools, blogs. -->

### Rubric: key ideas

<!-- 1-5 ideas or conclusions the plan should contain. -->

### Rubric: behaviors to avoid

<!-- 1-5 behaviors the agent must not show (result copying, verifier edits,
implementing before planning, ...). -->

### Implementation task description

<!-- The complete, verifiable task prompt — usually the implementation part of
`task.md`, quoted verbatim. -->

### Workspace environment

<!-- What `environment/` bundles and what lands in the agent workspace. Final
packages ship no bundled skills; any development-time skills are
runtime-injected, never baked into the image or committed to the package. -->

### Software environment

<!-- Dockerfile summary plus the sandbox spec from `task.md` front matter
(CPUs, memory, storage, network, timeouts). -->

### Verifier check-points

<!-- 3-10 concrete checks with tolerances that decide whether the agent solved
the task. -->

### Correct-answer workspace

<!-- What `oracle/` regenerates, from which assets, and its verifier result. -->

## Checklist

<!-- Check every box. If a box is intentionally left unchecked, keep it
unchecked and add a paragraph starting with "Deliberately unchecked" explaining
why — the CI check requires one or the other. -->

- [ ] `task.md` prompt body is concise, human-authored and outcome-focused
- [ ] `rubric.json` all the items are human-authored with reference source information attached, shaped `{name, blocker, weight, description, guidance}`
- [ ] `oracle/solve.sh` and oracle logic are human-authored
- [ ] `bench tasks check tasks/<task-id>` passes
- [ ] Oracle reaches reward `1.0`
- [ ] Verifier checks outcomes, not implementation or skill usage
- [ ] Rubric grades the deep-research and planning stage, both traj and output files
- [ ] The package ships no `environment/skills/`, and deliverables include no process files like `PLAN.md`
- [ ] Dockerfile does not bake skills into the agent image
- [ ] Source, data, code, and license provenance are documented
- [ ] Trajectories and output artifacts were inspected
- [ ] The task comes from my own research and took two weeks or more
- [ ] The task is challenging to SOTA agents (e.g. 500+ steps to finish; bar of academia peer review captured in task rubrics & verifier; etc.)

## Local test results

Report multiple trials per condition, not a single run. If a trial set was cut short, say so and report what finished. Record the harness and version, exact model identifiers, reasoning effort, task commit, and sandbox limits so the runs are reproducible.

| Agent | Model | Reasoning | No skill (primary) | With skills (optional) | Time |
|---|---|---|---:|---:|---:|
| | | | | | |

## Rubric review results (reviewer agent)

<!-- Encouraged but not required by CI: grade every benchmarked rollout with
the detached rubric reviewer —

    bench review <rollout-dir> -r tasks/<task-id>/verifier/rubric.json

— and report the results in the two tables below, one column per run. State
the reviewer agent, model, sandbox, and network posture, confirm every review
returned `review_valid: true`, and link the per-run `review_report.json`
files with your artifacts. Worked example: PR #109. Ask a maintainer to run
the reviewer if you cannot. -->

Reviewer: `<agent>` / `<model>`, `<sandbox>`, `<network posture>`.

<!-- Per-criterion table: blockers report pass/FAIL, scored criteria report
0-2. Carry each criterion's weight in the row label, e.g. `(blocker, w8)` or
`(w5)`. -->

| Criterion | run-1 | run-2 | ... |
|---|---|---|---|
| `criterion_name` (blocker, w8) | pass | FAIL | ... |
| `criterion_name` (w5) | 2/2 | 1/2 | ... |

<!-- Aggregates per run: weighted points = sum(score x weight) over scored
criteria; raw quality = weighted points / max; gated quality is 0 unless the
deterministic reward is 1.0 and every blocker passes; decision is the
publication band. -->

| Aggregate | run-1 | run-2 | ... |
|---|---|---|---|
| weighted points | 53/78 | ... | ... |
| raw quality | 67.9% | ... | ... |
| failed blockers | none | ... | ... |
| gated quality | 0% | ... | ... |
| decision | not_publishable | ... | ... |

## Failure analysis

<!-- For each failing run: did it fail on scientific reasoning,
environment/tooling, instructions, formatting, or verifier behavior? Quote the
failing assertion where possible. -->

## Artifacts

<!-- Oracle output, verifier logs, trajectories, and any visual or binary
artifacts needed for human review. -->

## Credit

Merging awards 6 points to the task author and 2 points to each reviewer who
signed off; if this is your first merged task and someone referred you, name
them and they earn 2. 12 points earns co-authorship on the FrontierPhysics
paper and dataset. See the [authorship policy](https://github.com/benchflow-ai/FrontierPhysics/blob/main/CONTRIBUTING.md#authorship-policy).

| Role | GitHub handle(s) |
|---|---|
| Author | |
| Reviewers | |
| Referred by (first merged task only) | |
