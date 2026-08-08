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
reproduce? Why is it hard, and what does the with/without-skills comparison
teach? -->

## Task history

This task must come from research you personally carried out. Give real dates
and an honest hour count — each row below carries a minimum, and a submission
under any of them will not merge.

| Report | Minimum | Value |
|---|---|---|
| Project time scale — start and end date | 2 weeks | YYYY-MM-DD → YYYY-MM-DD |
| Actual working hours spent exploring the task | 40 hours | |
| Estimated hours for a first-year PhD to reproduce the results | 10 hours | |

<!-- The last row is a backward estimate: assume a capable first-year PhD
student in the field, already handed the task prompt and data, and estimate how
long reproducing your results would take them. -->

| Field | Value |
|---|---|
| What the original work was | |
| Did an LLM agent help, and where? | |
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
| Mentor skills | |

## Form-formatted task information

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
and write `PLAN.md` — usually the research part of `task.md`, quoted verbatim. -->

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

<!-- What `environment/` bundles and what lands in the agent workspace; state
that skills are runtime-injected, never baked into the image. -->

### Software environment

<!-- Dockerfile summary plus the sandbox spec from `task.md` front matter
(CPUs, memory, storage, network, timeouts). -->

### Verifier check-points

<!-- 3-10 concrete checks with tolerances that decide whether the agent solved
the task. -->

### Correct-answer workspace

<!-- What `oracle/` regenerates, from which assets, and its verifier result. -->

## Mentor skill summary

<!-- One line per skill: what reusable method it carries, what it deliberately
omits, and confirmation that none contains a final answer or verifier
internals. -->

## Checklist

<!-- Check every box. If a box is intentionally left unchecked, keep it
unchecked and add a paragraph starting with "Deliberately unchecked" explaining
why — the CI check requires one or the other. -->

- [ ] `task.md` prompt body is human-authored and outcome-focused
- [ ] `oracle/solve.sh` and oracle logic are human-authored
- [ ] Metadata follows `taxonomy.yaml`
- [ ] `bench tasks check tasks/<task-id>` passes
- [ ] Oracle reaches reward `1.0`
- [ ] Verifier checks outcomes, not implementation or skill usage
- [ ] Planning rubric grades the deep-research stage
- [ ] Mentor skills are included and may be task-specific
- [ ] Mentor skills contain no hardcoded final answers or verifier internals
- [ ] Dockerfile does not bake skills into the agent image
- [ ] Source, data, code, and license provenance are documented
- [ ] No-skill and with-skill runs use the same task commit and model settings
- [ ] At least one strong agent passes the with-skill solvability control
- [ ] Trajectories and output artifacts were inspected
- [ ] The task comes from my own research and took two weeks or more
- [ ] This PR is from a fork and touches only `tasks/<task-id>/` plus the three re-admission files a task PR requires (`registry.json`, `.github/scripts/validate_repository.py`, `tasks/.gitkeep`)

## Local test results

Report multiple trials per condition, not a single run. If a trial set was cut
short, say so and report what finished. Record the harness and version, exact
model identifiers, reasoning effort, task commit, and sandbox limits so the
runs are reproducible.

| Agent | Model | Reasoning | No skill (primary) | With skills (control) | Time |
|---|---|---|---:|---:|---:|
| | | | | | |

## Rubric review (reviewer agent)

<!-- Encouraged but not required by CI: per-criterion pass/fail from the
post-verify rubric reviewer, as in the reference PR. Ask a maintainer to run it
if you cannot. -->

## Failure analysis

<!-- For each failing run: did it fail on scientific reasoning,
environment/tooling, instructions, formatting, or verifier behavior? Quote the
failing assertion where possible. -->

## What you learned building it

<!-- Anything a reviewer or future contributor should know — a leaky
environment, a brittle tolerance, a metric that turned out uninformative. -->

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
