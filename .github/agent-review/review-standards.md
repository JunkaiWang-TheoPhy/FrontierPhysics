<!--
FrontierPhysics task-review standards, distilled by the maintainers from PR
history: the recurring defects and the feedback that resolved them, written
as instructions to a reviewer.

This document complements — and defers to — the task-review skill
(.agents/skills/task-review/), which remains the operative review process:
its policy rubric, track routing, benchmark matrix, and report format.
Where the two overlap they are meant to agree; if they ever diverge, the
skill and CONTRIBUTING.md are authoritative (see also the preamble below,
which says the same about repository rules generally) — except on the areas
enumerated in §0 and .agents/skills/task-review/POLICY-UPDATES.md (bundled
skills, PLAN.md-style deliverables, the rubric.json schema, the
acceptance-evidence matrix, automated track-name precedence, and the automated
AI-authorship gate), where the skill is a frozen early reference and current
policy governs.

Two consumers:
- The automated first-pass review (.github/workflows/agent-review.yml)
  applies only the statically checkable subset, scoped by
  .github/agent-review/prompt.md, which cites sections here as §N.
- Human reviewers use it alongside the task-review skill for the parts that
  require execution: benchmarks, adversarial verifier tests, tampering
  tests, and trajectory audits.
-->

You are reviewing and hardening a scientific benchmark task PR for FrontierPhysics.

Your goal is **not merely to make CI pass** and not merely to confirm that the oracle obtains reward 1.0. Your goal is to determine whether this PR constitutes a scientifically valid, secure, reproducible, well-calibrated benchmark task that genuinely measures the intended scientific capability.

Treat the current repository rules (`CONTRIBUTING.md`, task-review skills/rubrics, schemas, validators, and current merged reference tasks) as authoritative. Do not impose requirements from another repository or another version of a review rubric unless they are actually operative here. If repository-wide policy is ambiguous or still under development, distinguish that from task-specific defects rather than turning it into a blocker arbitrarily.

Review the **current PR head only**. Historical runs, comments, or results from earlier commits are useful context but do not establish acceptance for a changed task.

---

# 0. Current repository policy (2026-08)

These weekly-sync decisions are current repository policy (issue #142;
canonical example: `tasks/multiplexing-ion-chain-qnet`, PR #109). Where an
older section of this document or of the frozen task-review skill disagrees,
this section governs; the same list is mirrored for human reviewers in
`.agents/skills/task-review/POLICY-UPDATES.md`.

* **No bundled skills in the final package.** The final experiment provides no
  skills to the agent, and a final task package contains no
  `environment/skills/`. Skills remain a legitimate development-time control —
  runtime-injected via `--skill-mode with-skill --skills-dir ...`, never baked
  into the image — and must be removed before merge.
* **No process-file deliverables.** Final deliverables are only the files one
  would submit for peer review or proudly present (`paper.pdf`, `report.pptx`,
  result data) — never process files such as `PLAN.md`. Planning quality is
  graded from the trajectory and the final deliverables via `rubric.json`, not
  from a shipped plan file, and the verifier must not assert on one.
* **benchflow 0.7.5 rubric schema.** Every `rubric.json` criterion is shaped
  `{name, blocker: 0|1, weight, description, guidance}`; blocker criteria
  gate, weighted criteria score.
* **Acceptance evidence is no-skill.** Required matrix: oracle reward 1.0 at
  the final head plus multiple no-skill trials of a strong agent at that same
  head. With-skill control runs are welcome, optional evidence — their absence
  is never a finding.
* **Concise, handwritten `task.md`**, with `network_mode: public` as the
  default posture, per the canonical example.
* **Automated AI-authorship gate.** The trusted workflow scans the `task.md`
  prompt body and the rubric's `name`/`description`/`guidance` prose separately.
  Each must be predicted `human`, classified `HUMAN_ONLY`, and satisfy
  `class_probabilities.ai + class_probabilities.mixed < 0.10`. This is a
  document-classification probability, not a percentage of AI-written words.
  A score failure is a first-pass blocker; an unavailable or indeterminate API
  result withholds readiness without accusing the contributor.

---

# 1. First identify the scientific crux

Before reviewing implementation details, explain in plain language:

1. What scientific problem is the task asking the agent to solve?
2. What are the final scientific deliverables?
3. Which part is genuinely difficult for a competent scientist or strong agent?
4. Which parts are routine bookkeeping versus the actual scientific bottleneck?
5. What failure modes distinguish shallow or naive methods from a scientifically competent solution?

The benchmark should measure the **real scientific crux**, not an incidental formatting or implementation challenge.

For example, if the true difficulty is:

* finding a complete set of physical solutions,
* rejecting numerical artifacts,
* propagating systematic uncertainty,
* tracking identities across parameter changes,
* choosing an appropriate numerical method,
* designing a stable experiment,
* or handling a resource tradeoff,

then the verifier, oracle, rubric, and any development-time mentor skill should all be aligned with that difficulty.

Explicitly state:

> “The primary scientific capability this task is intended to measure is ______.”

Then check the rest of the PR against that statement.

---

# 2. Validate that the underlying scientific problem is real

Do not take the PR description or oracle output on trust.

Where feasible, independently verify a small but meaningful subset of the underlying science.

Examples:

* substitute supplied numerical data back into governing equations;
* independently recompute one or more derived physical quantities;
* check known limiting behavior;
* check units and normalization;
* reproduce a small subset using a different numerical route;
* examine whether supplied backgrounds/data look synthetic or accidentally encode the answer;
* verify that stated numerical tolerances are meaningful relative to physical scales and numerical conditioning.

You do **not** need to independently reproduce the entire reference answer if that is prohibitively expensive. But perform enough independent checks to answer:

* Are the inputs scientifically legitimate?
* Are the targets physically meaningful?
* Are the reference quantities plausible?
* Is at least one important gate nontrivial rather than ceremonial?

If something cannot reasonably be independently verified, say so explicitly.

Never phrase “oracle passes” as independent scientific verification.

---

# 3. Confirm task provenance and originality

Check that the task provenance is documented clearly enough to understand:

* where the scientific problem came from;
* whether it derives from the author’s own research practice or another permitted source;
* where datasets/backgrounds/templates originated;
* what transformations or postprocessing were applied;
* whether external licenses or attribution are required;
* whether the shipped instances can be regenerated or at least traced reproducibly.

Do not require unnecessary provenance machinery merely for its own sake.

Every provenance file or script should have a clear purpose.

Flag:

* unexplained data;
* unverifiable private-data claims with no reconstruction description;
* copied published answers;
* public benchmark instances disguised as new work;
* unnecessary provenance directories containing redundant scripts;
* inconsistencies between PR description, task files, oracle plan, and source lists.

The goal is traceability, not bureaucracy.

---

# 4. Check prompt–rubric–verifier alignment

Build an explicit deliverable matrix.

For every requirement stated in `task.md`, record:

* what the agent must produce;
* where it is represented in the output schema;
* whether it is checked automatically;
* whether it is judged by the rubric;
* the associated tolerance or criterion;
* whether failure meaningfully affects reward.

There must not be important deliverables that are requested but silently ignored.

Conversely, the verifier must not grade hidden requirements that are never communicated to the agent unless that is an intentional hidden-test property compatible with repository policy.

The task specification, schema, contract, rubric, oracle, and verifier should describe the **same task**.

Look specifically for:

* prompt asks for A, verifier grades B;
* reference uses a finer or different definition than the prompt specifies;
* rubric expects literature or tools the environment cannot access;
* schema permits outputs that the verifier cannot safely handle;
* verifier expects fields not clearly required in the task;
* PR description lists papers or requirements inconsistent with `rubric.json`.

---

# 5. Enforce a strict trust boundary between agent workspace and grader truth

Treat everything writable or replaceable by the agent as **untrusted**.

This includes:

* `/root/...`;
* agent-generated files;
* copied contracts;
* copied schemas;
* working data;
* environment variables exposed to the agent;
* writable directories;
* symlinkable paths.

The verifier must never trust grading-critical information merely because the original file was root-owned.

Check whether an unprivileged agent can:

* overwrite;
* unlink and recreate;
* replace via symlink;
* shadow;
* mutate;
* or otherwise influence

any of the following:

* reference answers;
* numeric tolerances;
* grading contracts;
* schemas used for grading;
* hidden truth;
* expected hashes;
* verifier configuration.

A common unsafe pattern is:

```python
CONTRACT = Path("/root/contract.json")
```

when `/root` is part of the agent workspace.

The safe principle is:

> **Agent-visible copies are informational. Verifier-side copies are authoritative.**

For small immutable inputs, prefer a pristine verifier-side copy that grading reads directly.

For large inputs where duplication is expensive, use an integrity mechanism appropriate to the repository design.

Do not add hashing reflexively when simply isolating trusted data is cleaner.

Check filesystem permissions semantically, not superficially:

* a file may be non-writable but removable because its parent directory is writable;
* `chmod 777` on a shared workspace is dangerous;
* sticky-bit semantics such as `1777` matter;
* symlink behavior matters.

Attempt an actual tampering test when practical.

---

# 6. Verify that the oracle proves solvability rather than encoding the answer

This is one of the most important checks.

The oracle is allowed to know the correct scientific method and produce the reference answer.

However, it must not silently bypass the primary difficulty of the benchmark using answer-derived information.

Ask:

1. Does the oracle begin from the same scientific inputs that define the task?
2. Does it discover the difficult intermediate structure itself?
3. Are there seed files, warm starts, lookup tables, manually curated candidate locations, cached trajectories, hidden labels, or precomputed inventories that already encode most of the final answer?
4. If such aids exist, where did they come from?
5. Would submitting those aids directly already satisfy a major verifier gate?
6. Does reward 1.0 actually demonstrate that the task is solvable from scratch?

A particularly serious anti-pattern is:

> the benchmark is supposed to test completeness/search/discovery, while the oracle is initialized with one near-answer seed for every true solution.

That is not necessarily an agent answer leak, but it invalidates the oracle as evidence that the intended scientific challenge is solvable.

If the oracle contains optional fallback paths, confirm that the path actually exercised in the shipped oracle run is the one whose solvability you are claiming.

Prefer:

* genuine search;
* continuation from scientifically justified starting points;
* convergence studies;
* independent confirmation;
* algorithmically generated candidates;

over:

* answer-grade seed inventories.

If a small amount of human adjudication is unavoidable, document it explicitly and determine whether:

* it affects graded correctness;
* the automated oracle reproduces it within tolerance;
* it undermines completeness claims.

---

# 7. Check reference-answer independence and circularity

Ask where the reference answer came from.

Potential circularity:

```text
same computation
    -> seeds
    -> oracle
    -> final.json
    -> verifier
```

If all artifacts ultimately descend from one computation, “oracle agrees with verifier” is not independent evidence.

You do not always need a fully independent second oracle, but identify the dependency graph honestly.

For high-value or fragile quantities, seek some independent confirmation:

* alternate numerical method;
* different resolution;
* different domain parameter;
* different integration direction;
* analytic limit;
* manual scientific spot check.

Document what is genuinely independent and what is not.

---

# 8. Test verifier correctness adversarially

Do not test only the golden answer.

Construct deliberate mutations and wrong submissions.

At minimum test representative cases such as:

* completely correct answer;
* one numerical value outside tolerance;
* missing required item;
* extra spurious item;
* duplicated item;
* wrong instance identifier;
* NaN / inf;
* malformed structure;
* empty output;
* huge output;
* wrong classification with correct underlying number;
* correct classification with wrong underlying number;
* invalid pipeline artifact;
* tampered input or contract where applicable.

For set/census problems additionally test:

* one missing true solution;
* one extra false solution;
* two solutions collapsed into one;
* one solution just inside a boundary;
* one just outside;
* ambiguous near-boundary values.

The verifier should fail for the reason you expect.

A mutation of one scientifically meaningful answer component should change reward appropriately.

---

# 9. Eliminate vacuous gates and accidental coupling

Every gate should test what its name claims to test.

Look for patterns such as:

```python
match = find_match(...)
if match is None:
    continue
```

inside a gate that is supposed to validate a downstream quantity.

This may turn a wrong upstream answer into a vacuous downstream pass.

Decide explicitly whether gates are:

* independent; or
* conditionally dependent.

If a downstream quantity is undefined because an upstream object is missing, that should normally be recorded as a failure or an explicit invalid dependency—not silently skipped.

For each gate ask:

> “Can an obviously wrong answer accidentally pass this gate because an earlier match failed?”

Also inspect whether multiple gates are effectively testing the same thing rather than independent scientific properties.

---

# 10. Check tolerance design mathematically

For every numerical tolerance, understand what it means.

Compare:

* tolerance versus nearest-answer spacing;
* tolerance versus numerical uncertainty;
* tolerance versus physical scale;
* tolerance versus classification thresholds;
* tolerance versus boundary positions.

Look for pathological combinations.

Example:

If a continuous quantity has threshold

[
s > 12 \Rightarrow F,
]

but the verifier accepts a factor-of-two error, then a reference value near 12 may admit estimates on both sides of the classification threshold.

That can make the categorical label weakly constrained or effectively arbitrary.

Quantify such grey zones rather than merely saying “tolerance seems loose.”

Similarly, if two distinct target boundaries differ by less than the allowed tolerance, one guessed value may pass both.

If that happens:

* determine whether it is scientifically acceptable;
* tighten the metric if justified;
* change the quantity being graded;
* or explicitly document that the criterion is weakly discriminating.

Do not tighten tolerances merely to make the task harder. Tolerances must reflect the task specification and scientific reliability.

---

# 11. Define boundary semantics explicitly

Any task involving:

* intervals;
* rectangles;
* thresholds;
* bins;
* acceptance windows;
* finite precision;

needs explicit boundary behavior.

If numerical values are graded with uncertainty/tolerance (\epsilon), but membership in a region is decided with exact zero tolerance, a scientifically correct estimate near the edge may be treated inconsistently.

Specify:

* open versus closed boundaries;
* how estimates near an edge are handled;
* whether an uncertainty-overlapping candidate is allowed;
* how far outside a nominal region such a candidate may lie;
* how matching treats edge cases.

The policy must appear consistently in:

* task specification;
* contract/schema if appropriate;
* oracle;
* verifier.

---

# 12. Make completeness claims testable

If the task asks for a “complete census,” “all solutions,” “all modes,” “all events,” etc., completeness must be part of grading.

A task that says “find all” but only spot-checks a few known objects is not grading the stated challenge.

For a complete-set task, verify both:

[
\text{recall/completeness}
]

and

[
\text{precision/purity}.
]

In plain language:

* no true object may be silently omitted;
* no spurious object may be accepted.

If boundary candidates or unresolved ambiguities are allowed, define those exceptions explicitly.

---

# 13. Check identity tracking across related instances

For tasks with trajectories, parameter sweeps, continuation, or evolving entities, verify that the benchmark does not equate identity with array position.

Potential anti-pattern:

```text
sort every instance independently
match item #1 to item #1
```

This fails near crossings or reorderings.

If identity continuity is scientifically important, the task should require and the oracle should implement a meaningful continuation/matching strategy.

Check:

* crossings;
* branch swaps;
* ambiguous continuations;
* missing neighbors;
* items entering/leaving a graded window.

The verifier should have a defined policy for unresolved identity.

---

# 14. Make the research/planning stage internally consistent

If the benchmark is two-stage:

1. research / planning;
2. execution / scientific result;

keep the responsibilities clear.

A sensible split is:

* the rubric grades planning quality from the trajectory and the final
  deliverables (per §0, no process file such as `PLAN.md` may be required or
  shipped as a deliverable);
* the verifier checks the final scientific deliverables.

Do not force rubric scores into pytest unless repository policy explicitly requires that.

Do not invent a judge-validation requirement if the repository has not standardized one.

If repository policy does require judge calibration, then validate it according to the actual current convention.

Otherwise classify missing judge calibration as:

* parked repo-wide work;
* optional improvement;
* or non-blocking,

not a task-specific blocker.

---

# 15. Check literature/network consistency

The environment and rubric must agree.

If the rubric rewards **discovering literature**, the agent needs a realistic way to discover it.

If network access is disabled, then the task should instead grade something like:

* correct use of the bundled bibliography;
* methodological reasoning from provided sources;

rather than pretending the agent performed open literature research.

Conversely, do not disable the network merely out of fear that the agent will copy answers if the task instances are deliberately chosen so published values do not transfer.

A strong benchmark design is:

> Public literature teaches the method and physics, but the submitted numerical answer must still be computed from novel shipped inputs.

That is preferable to turning literature research into a memorization test.

Check whether:

* task instances are unpublished or parameter-shifted;
* public papers contain direct answers;
* network access creates a genuine contamination path;
* the rubric wording matches actual environment capabilities.

---

# 16. Mentor skills must teach method, not encode answers

Per §0, mentor skills are a development-time control only: the final package
ships none, and `environment/skills/` in a final task package is a blocker.
Apply this section when a PR still carries development-time skills or when
reviewing optional with-skill control runs.

Review every injected skill.

A good mentor skill may teach:

* a numerical workflow;
* diagnostics;
* convergence checks;
* common failure modes;
* how to validate completeness;
* literature-search strategy;
* reusable scientific reasoning.

It must not contain:

* task-specific final numerical values;
* a hidden answer table;
* verifier assertions;
* bypass instructions;
* reference mode inventories;
* task-instance-specific seeds equivalent to answers.

If FrontierPhysics currently permits task-tailored mentor skills, do not reject them merely because another benchmark framework forbids them.

Follow the policy that actually applies to this repository.

Then test empirically whether the skill improves the intended scientific capability rather than merely revealing output structure.

---

# 17. Require realistic resource declarations

Measure rather than guess.

Check:

* peak RAM;
* CPU usage;
* disk usage;
* GPU need;
* wall-clock runtime;
* build time;
* verifier time;
* agent timeout.

Do not declare 8 GB if the actual task reliably needs 400 MB.

Do not artificially shrink limits below realistic safe margins either.

Resource declarations affect:

* benchmark accessibility;
* scheduling;
* fairness;
* acceptance-matrix cost.

Use measured values plus reasonable headroom.

If runs are slow because of the intended science, that is acceptable. If they are slow because of avoidable implementation inefficiency, improve the implementation.

---

# 18. Validate the exact-head acceptance matrix

This is mandatory evidence for the **current frozen task**.

Do not combine runs from different commits once any behaviorally meaningful part of the task has changed, including:

* prompt;
* oracle;
* verifier;
* skill;
* network mode;
* input data;
* tolerance;
* reference answer;
* census window;
* resource limit when it changes agent behavior.

At one unchanged head, obtain the evaluation matrix required by current repository policy.

At minimum, per current policy (§0):

* three no-skill trials under identical model/settings;
* optionally, with-skill control runs — welcome evidence, never required;
* same task commit;
* same model;
* same reasoning effort;
* same runtime configuration;
* same network mode;
* one trial per intended cell unless policy says otherwise.

Record:

* commit SHA;
* condition;
* model;
* reasoning effort;
* runtime backend;
* reward;
* wall-clock time;
* tool-call count if available;
* artifact/trajectory location.

Do not count provider failures, authentication failures, infrastructure crashes, or truncated runs as scientific failures.

Mark them invalid and rerun.

---

# 19. Inspect trajectories, not only reward numbers

A benchmark result is more informative when you understand **why** the agent passed or failed.

For each important run, inspect:

* the planning portion of the trajectory;
* final answer;
* generated pipeline;
* trajectory/tool calls;
* verifier logs.

For no-skill failures ask:

* Did it misunderstand the problem?
* Use a naive method?
* Fail at literature research?
* Miss a systematic?
* Produce numerical artifacts?
* Give up due to runtime?
* Fail formatting despite correct science?

For optional with-skill control passes (if any) ask:

* Did the skill actually change the scientific strategy?
* Did it merely provide an answer-shaped shortcut?
* Did it reduce wasted computation?
* Did it improve artifact rejection or validation?

The best evidence is a failure mode that corresponds to the intended scientific difficulty.

---

# 20. Assess benchmark discriminative power

Do not require all no-skill runs to fail.

A useful benchmark may have stochastic success.

What matters is that:

* strong agents can solve it;
* the task is not trivially solved every time;
* failures happen for scientifically meaningful reasons;
* the skill, when applicable, improves the intended capability;
* the verifier distinguishes substantive correctness.

If results look like:

```text
no-skill (required):          pass / fail / fail
with-skill (optional control): pass / pass / pass
```

that may be excellent calibration if trajectory inspection shows the difference comes from the targeted scientific methodology.

Do not optimize solely for an arbitrary pass-rate target.

---

# 21. Check for benchmark shortcuts

Try to solve the verifier without solving the science.

Attack surfaces include:

* constant answers;
* guessing central values;
* exploiting loose tolerances;
* exploiting duplicated tolerances;
* omitted fields;
* malformed values;
* NaNs;
* huge numbers;
* duplicate objects;
* modifying visible contracts;
* outputting only mode counts;
* exploiting skip/continue behavior;
* copying bundled data;
* reusing published values from a nearby parameter point;
* deriving answers from filenames/order/indexing artifacts.

If a cheap shortcut receives substantial reward, quantify exactly how much.

A good verifier should reward actual scientific correctness, not structural guessing.

---

# 22. Human-authored task and rubric quality

Where repository policy requires the task specification and rubric to be human-authored, inspect them carefully.

For the automated first pass, the workflow also applies the §0 GPTZero gate to
the prose actually subject to the human-authorship rule: the `task.md` prompt
body and each rubric criterion's `name`, `description`, and `guidance`. JSON
punctuation, rubric weights, and task YAML configuration are excluded. Scan the
two documents independently so one low score cannot dilute a high score in the
other. A trusted result that reaches the threshold, is not predicted `human`,
or is not classified `HUMAN_ONLY` is objective blocker evidence; qualitative
impressions outside that scan remain observations only.

Do not use `average_generated_prob` as the gate. GPTZero exposes a three-way
document classification, so current policy defines authorship risk as
`P(ai) + P(mixed)` and requires it to be strictly below 10% together with a
`human` / `HUMAN_ONLY` result. Never describe that probability as the fraction
of words written by AI, and never use a detector result to allege misconduct.
Ask the author to rewrite and polish the relevant prose themselves.

Do not merely check for grammatical correctness.

They should read like they were written by a scientist who understands:

* why the task matters;
* what the difficult choices are;
* what constitutes evidence;
* which failure modes are unacceptable.

Polish generic or AI-like language such as:

* repetitive checklist prose;
* vague “be robust” requirements;
* redundant explanatory sections;
* overly verbose restatement of schemas;
* criteria that sound sophisticated but do not correspond to measurable scientific decisions.

Each rubric item should express one meaningful expectation.

Do not claim text is human-authored unless that is actually known.

---

# 23. Keep PR documentation internally consistent

Cross-check all of the following:

* PR title;
* Motivation;
* task history;
* task summary;
* `task.md`;
* `rubric.json`;
* `literature.md`;
* verifier contract;
* reference answer;
* reported local runs;
* resource settings;
* network mode;
* commit hashes;
* artifact links.

Stale text is a real review problem.

Examples:

* PR says “no network,” current task says `public`;
* PR describes seeds that have already been removed;
* result table refers to an old head;
* “papers to find” differs from the actual planning reference set;
* reported number of reference modes differs from current `final.json`.

Update the PR body whenever the benchmark semantics change materially.

---

# 24. Run all repository checks at the final head

Before declaring the PR ready, run every required local validation supported by the repo, including as applicable:

* task checker;
* repository validator;
* lint;
* formatting;
* taxonomy validation;
* Docker build;
* oracle smoke;
* verifier golden-answer test;
* deliberate mutation test;
* task registry/digest check;
* website/build checks if required.

Distinguish:

* task-specific failures;
* repository infrastructure failures;
* unrelated deployment permission failures.

Do not hide red checks merely because they appear unrelated.

Explain them.

A task PR should normally reach a final head where all task-relevant CI is green.

---

# 25. Review severity taxonomy

Classify findings as:

## BLOCKER

The task should not merge because correctness, integrity, solvability evidence, benchmark validity, or required acceptance evidence is missing.

Examples:

* verifier trusts agent-writable tolerances;
* oracle bypasses the core task with answer-derived seeds;
* reference answer is clearly incorrect;
* core requested deliverable is not graded;
* current-head acceptance matrix is missing;
* task-relevant CI fails;
* agent can obtain high reward without solving the problem;
* `task.md` or rubric prose fails the trusted §0 AI-authorship gate;
* final package bundles skills, requires process-file deliverables like
  `PLAN.md`, or uses a pre-0.7.5 rubric schema (§0).

## SIGNIFICANT

The benchmark works but has an important calibration, clarity, reproducibility, or maintainability defect.

Examples:

* tolerance grey zone;
* weakly discriminating secondary metric;
* unnecessarily high RAM declaration;
* ambiguous boundary rule;
* provenance insufficiently documented;
* PR description stale.

## MINOR

Style, documentation, cleanup, or low-risk implementation issue.

## PARKED / REPO-WIDE

A legitimate issue whose standard is not yet defined and should not uniquely block this PR.

Example:

* a future judge-validation framework that maintainers have not yet standardized.

Never convert a repo-wide unresolved policy question into an arbitrary task-specific blocker.

---

# 26. Required final report

After performing the review, produce a structured report with the following sections.

## A. Scientific task summary

Explain:

* problem;
* inputs;
* outputs;
* primary scientific crux;
* intended failure mode.

## B. What is independently verified

List only things you personally checked.

Clearly distinguish:

* independently verified;
* reproduced through oracle;
* stated by author but not independently confirmed.

## C. Trust-boundary audit

State:

* what is agent-writable;
* what is verifier-trusted;
* whether any grading-critical data crosses that boundary unsafely;
* tampering tests performed.

## D. Oracle solvability audit

Explain:

* how candidate solutions are discovered;
* whether answer-derived seeds/caches exist;
* whether the oracle genuinely exercises the difficult part;
* any manual adjudication;
* degree of independence from the reference answer.

## E. Prompt–rubric–verifier matrix

For every deliverable:

* requested?
* represented?
* graded?
* tolerance?
* pass/fail consequence?

## F. Numerical calibration audit

Check:

* tolerances;
* nearest spacing;
* thresholds;
* boundary semantics;
* grey zones;
* shortcut values.

Quantify where possible.

## G. Adversarial verifier tests

List each mutation/attack and whether it passed or failed.

## H. Resource audit

Report measured or evidenced CPU/RAM/storage/runtime requirements.

## I. Exact-head evaluation matrix

Give:

* commit;
* model/settings;
* no-skill runs (required);
* with-skill control runs (if any);
* invalid infrastructure runs;
* rewards;
* times;
* artifact links if available.

## J. Trajectory interpretation

Explain why representative agents passed or failed.

## K. Findings

Create a table:

| ID | Severity | Finding | Evidence | Required fix | Status |
| -- | -------- | ------- | -------- | ------------ | ------ |

Use IDs such as:

* B1, B2...
* S1, S2...
* M1...
* P1...

## L. Acceptance status

Conclude with exactly one:

* `READY TO MERGE`
* `READY AFTER MECHANICAL FIXES`
* `CHANGES REQUIRED`
* `BLOCKED ON ACCEPTANCE RUNS`

Then explain why in no more than one paragraph.

---

# 27. Principles to preserve throughout the review

Follow these principles strictly:

1. **Measure whenever possible; do not infer when you can test.**
2. **Do not trust the PR description over the current tree.**
3. **Do not trust oracle/verifier agreement as independent validation.**
4. **Trusted grading data must be isolated from the agent.**
5. **The oracle must solve the task, not encode the answer.**
6. **Verifier gates must fail meaningfully, not vacuously pass.**
7. **Tolerance semantics must be mathematically coherent.**
8. **Every important requested deliverable must be graded somewhere.**
9. **The environment must permit the behavior the rubric rewards.**
10. **Evaluation evidence must come from one unchanged final head.**
11. **Infrastructure failures are not scientific failures.**
12. **Inspect trajectories to understand what the benchmark actually measures.**
13. **Scientific difficulty is more important than superficial implementation difficulty.**
14. **Do not create requirements that current repository policy does not actually impose.**
15. **Prefer simple trust separation and reproducibility over unnecessary benchmark machinery.**
16. **A good task is not merely hard; it is hard for the intended scientific reason.**

The final question you should be able to answer is:

> **If an agent receives reward 1.0 on this task, do we have strong reason to believe that it actually solved the intended scientific problem—and if it receives reward 0.0, is that failure meaningfully connected to the intended scientific challenge?**

If the answer to either half is “not necessarily,” the PR still needs work.
