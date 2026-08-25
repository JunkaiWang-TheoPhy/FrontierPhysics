# Policy updates superseding this frozen skill

The task-review skill is deliberately kept frozen as the early human-authored
review reference. Its wording still governs review by default — including the
documented copy-oracle allowance and the treatment of parked repo-wide
questions — **except** on the areas listed below, where later weekly-sync
decisions supersede it. Current policy lives in `CONTRIBUTING.md` and
`.github/agent-review/review-standards.md` §0; the canonical example is
`tasks/multiplexing-ion-chain-qnet` ([PR #109](https://github.com/benchflow-ai/FrontierPhysics/pull/109)).
The audit that produced this list is
[issue #142](https://github.com/benchflow-ai/FrontierPhysics/issues/142).

Future policy changes append a dated section here rather than editing the
frozen skill documents.

## 2026-08-25 — automated track-name precedence

For the bounded GitHub first-pass bot, the four physics tracks in the main
`SKILL.md` Step 2 table are authoritative. The three older routing names in
`references/track-routing.md` are retained as frozen historical guidance and
must not be emitted by the bot.

## 2026-08-21 — final task-package policy

| Area | This skill says | Current policy |
|---|---|---|
| Bundled skills | Task-tailored mentor skills are endorsed and scored (policy-rubric §7; goodtask) | The final experiment ships no skills: a final task package contains no `environment/skills/`, and its presence is a blocker. Skills remain a development-time control only, runtime-injected via `--skill-mode with-skill --skills-dir ...` and removed before merge. |
| `PLAN.md`-style deliverables | Planning files such as `PLAN.md` are normal deliverables to inspect and cross-check | Final deliverables are only paper-submission or presentable artifacts (`paper.pdf`, `report.pptx`, result data). Process files like `PLAN.md` must not be required, shipped, or asserted on by the verifier; planning quality is graded from the trajectory and the final deliverables via `rubric.json`. |
| `rubric.json` schema | Predates benchflow 0.7.5 | Every criterion is shaped `{name, blocker: 0|1, weight, description, guidance}` — blocker criteria gate the result, weighted criteria score it. |
| Acceptance-evidence matrix | With-skill solvability pass plus no-skill trials | Oracle reward 1.0 plus multiple no-skill trials at the final head. With-skill control runs are optional good-to-have evidence; their absence is never a finding. |

## 2026-08-25 — automated AI-authorship gate

The GitHub first-pass review still uses the latest trusted base-branch copy of
this skill for routing and static policy, but the frozen policy rubric's
optional `>70%` GPTZero flag is superseded by a deterministic workflow gate:

- Scan the `task.md` prompt body and the human-authored `name`, `description`,
  and `guidance` prose from `verifier/rubric.json` as separate documents.
- For each document, define authorship risk as
  `class_probabilities.ai + class_probabilities.mixed`. It is a document-level
  classification probability, not the percentage of words written by AI.
- Each document must be predicted `human`, classified `HUMAN_ONLY`, and have
  authorship risk strictly below `0.10`; exactly `0.10` fails.
- A content failure is a first-pass blocker requesting human rewriting and
  polishing. API, credential, and response-schema errors withhold the label
  pending a rerun. Deterministic input errors (including the trusted 250 to
  50,000 character bounds) require correcting the named document before the
  rerun. Neither error category is evidence of AI use.
- The API call runs in trusted workflow code. The review agent receives only a
  sanitized score report, never the GPTZero credential or network access.
