# FrontierPhysics

The end-to-end physics discovery benchmark for agents.

## Commands

```bash
uv tool install --upgrade benchflow
uv sync --locked
bench tasks check tasks/multiplexing-ion-chain-qnet
bench eval run --tasks-dir tasks/multiplexing-ion-chain-qnet --agent oracle --sandbox docker
bench eval run --tasks-dir tasks/multiplexing-ion-chain-qnet --agent codex-acp --model <model> --skill-mode no-skill --sandbox docker
# optional development-time control runs: pass --skill-mode with-skill --skills-dir <skills-dir> (final packages ship no skills)
uv run python .github/scripts/validate_repository.py
uv run python .github/scripts/validate_tasks.py tasks
uv run python .github/scripts/lint_taxonomy.py
uv run python .github/scripts/lint_skill_frontmatter.py
uv run python .github/scripts/lint_frontierphysics_docs.py
```

## Task layout

```text
tasks/<task-id>/
  task.md
  environment/
    Dockerfile
  oracle/
    solve.sh
  verifier/
    rubric.json # Human-written criteria for the LLM judge
    test.sh
    test_outputs.py
```

## Rules

- Tasks must represent authentic advanced-physics work.
- [IMPORTANT] Read `.agents/skills/task-review/goodtask-frontierphysics.md` first before doing anything.
- `task.md` prompt bodies, rubric.json, oracle logic must be human-authored.
- `rubric.json` criteria follow the benchflow 0.7.5 schema: `{name, blocker: 0|1, weight, description, guidance}`.
- Prompts describe outcomes and must not mention any specific skills or direct source of answer.
- Verifiers check scientific outcomes, not which tools or skills were used.
- Final task packages ship no `environment/skills/` and no process-file deliverables like `PLAN.md` — deliverables are only paper-submission or presentable artifacts. Skills are a development-time control only: runtime-injected via `--skills-dir`, never baked into the image or shipped, and they must not hardcode final answers, expose verifier assertions, or bypass the requested scientific computation.
- Oracle must pass with reward `1.0`.

## References

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [taxonomy.md](taxonomy.md)
- [.agents/skills/task-review/](.agents/skills/task-review/)
