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

## 2026-08-21 — final task-package policy

| Area | This skill says | Current policy |
|---|---|---|
| Bundled skills | Task-tailored mentor skills are endorsed and scored (policy-rubric §7; goodtask) | The final experiment ships no skills: a final task package contains no `environment/skills/`, and its presence is a blocker. Skills remain a development-time control only, runtime-injected via `--skill-mode with-skill --skills-dir ...` and removed before merge. |
| `PLAN.md`-style deliverables | Planning files such as `PLAN.md` are normal deliverables to inspect and cross-check | Final deliverables are only paper-submission or presentable artifacts (`paper.pdf`, `report.pptx`, result data). Process files like `PLAN.md` must not be required, shipped, or asserted on by the verifier; planning quality is graded from the trajectory and the final deliverables via `rubric.json`. |
| `rubric.json` schema | Predates benchflow 0.7.5 | Every criterion is shaped `{name, blocker: 0|1, weight, description, guidance}` — blocker criteria gate the result, weighted criteria score it. |
| Acceptance-evidence matrix | With-skill solvability pass plus no-skill trials | Oracle reward 1.0 plus multiple no-skill trials at the final head. With-skill control runs are optional good-to-have evidence; their absence is never a finding. |
