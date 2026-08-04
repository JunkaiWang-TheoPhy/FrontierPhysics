# About FrontierPhysics
FrontierPhysics evaluates how agents help with Physics research. Specifically, we turn day-to-day work in physics labs into tasks for agents. By observing agents' performance in tackling these tasks, with and without skills, we can get insights into agents' capability and shortcomings in solving Physics research tasks, and the data can be used to improve agents' ability. 

To achieve this, we need contributors from the broad Physics community to add diverse, authetic, challenging, and well-tested task packages. 

**Links**: 
[Website] (https://www.benchflow.ai/frontierphysics)  
[Github] (https://github.com/benchflow-ai/FrontierPhysics.git)  
[BenchFlow CLI] (https://github.com/benchflow-ai/benchflow)  
[SkillsBench Paper] (https://arxiv.org/abs/2602.12670)  
[Discord] (https://discord.gg/G9dg3EfSva)

# Authorship policy
Contribution credit is tracked in points, and **12 points earns co-authorship**
on the FrontierPhysics paper and dataset.

| Contribution | Points |
|---|---:|
| A task you authored is merged | 6 |
| A contributor you referred gets their first task merged | 2 |
| A task you reviewed is merged | 1 |

Points accumulate across all three kinds of work, so two merged tasks reaches
12, and so does any mix that adds up — one merged task, a referral, and four
reviews, for example.

A referral means bringing someone new to the project. It scores once per
person, when their first authored task merges — have them name you in that
PR's description so the maintainers know who to credit.

Reviewing opens up once you have your first good task merged: authoring one is
how you demonstrate you can judge someone else's. Ask a maintainer to be added
as a reviewer.

**Only tasks merged by 31 August 2026 count toward points.** Merged, not
opened — review and revision take days of back-and-forth, so a PR opened close
to the deadline is unlikely to land in time.

Points are awarded on merge, not on submission: a review or a referral earns
its points only once the task behind it is merged. Quality beats quantity — one excellent task
is worth more than many mediocre ones, and a submission that does not clear the
bar in [What makes an ideal task](#what-makes-an-ideal-task) earns nothing.

# Who should contribute
A PhD or current PhD candidate in physics, EECS, or an adjacent field — or
someone with extensive hands-on experience in a physics lab or an equivalent
industry role.

# What makes an ideal task
Three things:

1. **Your own work.** Real research you personally carried out, not a problem
   invented for the benchmark.
2. **Two weeks or more.** It took you at least two weeks of genuine effort,
   with or without an LLM agent helping.
3. **Verifiable.** The result is right or wrong, and a script can tell which.

A task that misses any one of these will not merge.

# Two stages, two graders
Every task is evaluated in two stages, and you write the grader for each:

1. **Deep research.** The agent studies the problem and commits to a research
   plan. A planning rubric you author grades that plan — the physics that must
   be modelled, the approximations that are defensible, the checks that catch
   a wrong turn early.
2. **Execution.** The agent carries the plan out. The verifier checks that the
   final results are accurate.

The rubric ships in the task package alongside the verifier; agree on its
exact placement with a maintainer in your draft PR.

# How to contribute
1. **Ideate**: Pick a project that meets all three. Bring it to group chat or
   confirm with a maintainer before you build.
2. **Create**: Implement the task package, including the planning rubric. See
   `Task Package` below.
3. **Test**: Run the oracle, then run a state-of-the-art agent with and
   without skills, over multiple trials.
4. **Submit**: Fork this repository and open a draft PR against `main` here
   as soon as the shape is there, then iterate with a maintainer. See
   [The final submission](#the-final-submission).

Open the PR as a **draft** as soon as you have the task idea and a skeleton —
do not wait until it is polished. Reviewing and revising a task takes days of
back-and-forth, so iterating with a maintainer in a draft is both faster than
guessing and the only reliable way to merge before the deadline.

# Task Package
Technically, a task consists of:

```text
tasks/<task-id>/
├── task.md
├── environment/
│   ├── Dockerfile
│   ├── <bundled inputs>
│   └── skills/
│       └── <skill-name>/
│           ├── SKILL.md
│           ├── references/
│           └── scripts/
├── oracle/
│   └── solve.sh
└── verifier/
    ├── test.sh
    └── test_outputs.py
```
## task.md
Usually the first file that you write. `task.md` starts with YAML frontmatter, followed by the human-written prompt body.
The frontmatter carries metadata, timeouts, and resource requirements. The body is the instructions (prompt) for the agents. 

Here are some rules for writing the prompt:
- Write by hand in clear, imperative prose.
- Describe the desired end state, not the solution steps.
- Use explicit absolute paths for inputs and outputs.
- Do not mention skill names or tell the agent which skills to use.
- Anchor a date when the correct answer depends on time-sensitive data.

## environment/
As shown above, an `environment/` folder contains the Dockerfile, inputs, and skills. The Dockerfiles create a Docker environment for agents in which it'll work to solve the task. If the task requires inputs (e.g., data, reference, examples, etc.), put these under the environment/inputs/ folder. `environment/skills` contain mentoring skills for agents that help them with the task.

Guidelines for Dockerfile:

- Use Python 3.12+ unless a task has a documented reason not to.
- Pin Python packages to exact versions.
- Bundle reproducible inputs in `environment/`.

Guidelines for skills:
- Skills should contain reusable domain guidance, not task-specific answers.
- Explain non-obvious workflow knowledge, schemas, formulas, standards, or tools.
- Reuse scripts and references that would help on more than one task.
- Stay focused; split long details into `references/`.
- Avoid mentioning the exact output answer or task-specific filenames unless the
  filename is a real reusable interface.
- Do not bake skills into agent home directories. BenchFlow injects skills at
  runtime when `--skill-mode with-skill --skills-dir ...` is used.

## oracle/
`oracle/solve.sh` is the held-out reference solution. It must be human-written
and derive the answer through computation rather than hardcoding final values.

For tasks where a hand-authored binary artifact is unavoidable, explain that
tradeoff in the PR description and keep the artifact in `oracle/`.

## verifier/
The verifier checks outcomes and writes a scalar reward to
`/logs/verifier/reward.txt`.

Verifier rules:

- Test the result, not the process.
- Use 4-10 focused test functions; parametrize related cases.
- Every test should check something distinct.
- Copy important output artifacts into `/logs/verifier/` for review.
- Oracle and verifier must not require paid API keys.

# Task Quality Rubric

Every PR is evaluated against the [task-review skill](.agents/skills/task-review/).
Reviewers look for:

- **Authenticity**: real scenario, real data where possible, human-authored task
  prompt and oracle.
- **Skill quality**: accurate, reusable, useful beyond this task.
- **Verification**: deterministic, outcome-based, anti-cheat aware, covering
  both stages — the planning rubric and the execution verifier.
- **Instructions**: concise, fair, no skill hints.
- **Environment**: reproducible Docker image, pinned deps, no leaked skills.
- **Complexity**: clears every minimum in
  [A detailed PR description](#2-a-detailed-pr-description) — two weeks, 40
  working hours, 10 hours to reproduce — and agents without skills are
  likely to fail it.

# The final submission

Every task submission consists of three things.

## 1. A PR from your fork

Fork this repository, push your task to a branch on your fork, and open a pull
request against `main` here. One task per PR, and the PR should touch only
files under `tasks/<task-id>/`.

## 2. A detailed PR description

The description is part of the submission, not a formality — it is the evidence
a reviewer uses to judge provenance and difficulty. Explain the history of the
task: where this work came from and what it cost you.

Report these three in a table. Each carries a minimum; a submission below any
of them will not merge.

| Report | Minimum | Example |
|---|---|---|
| Project time scale — start and end date | 2 weeks | 2025-03-04 → 2025-03-28 |
| Actual working hours spent exploring the task | 40 hours | approximately 60 hours |
| Estimated hours for a first-year PhD to reproduce the results | 10 hours | approximately 15 hours |

The third is a backward estimate, not a measurement: assume a capable
first-year PhD student in the field, already given the task prompt and data,
and estimate how long reproducing your results would take them. It is the best
single proxy for whether the task is substantial enough to be worth grading.

Also state what the original work was and whether an LLM agent helped, and on
which parts. Give real dates and an honest hour count — a task that took you
two days is not a fit, and saying so early saves everyone a review cycle.

Also cover the scientific motivation: what physics the task exercises, who does
this kind of work, and where the data or model came from — with citations and
license provenance for anything you did not produce yourself.

## 3. A local test results report

Before you open the PR, confirm all of these locally:

1. `bench tasks check tasks/<task-id>` passes.
2. `bench eval run --tasks-dir tasks/<task-id> --agent oracle --sandbox docker`
   passes with reward 1.0.
3. A state-of-the-art agent has been run both with and without skills,
   over multiple trials.
4. The task prompt, oracle, skills, tests, and metadata are ready for human
   review.

Then report what you actually ran:

- oracle result, showing reward 1.0;
- a table of agent runs — agent, model, with-skill and no-skill pass rates over
  multiple trials, not a single run;
- failure analysis: whether failures came from scientific reasoning,
  environment or tooling, instructions, formatting, or verifier behaviour;
- artifacts for any multimodal or binary outputs;
- anything you discovered while building it that a reviewer or future
  contributor should know — a leaky environment, a brittle tolerance, a metric
  that turned out uninformative.

Report the runs you completed. If you ran out of credits partway through a
trial set, say so and report what finished; partial evidence honestly labelled
is worth more than a padded table.
