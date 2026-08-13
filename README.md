# FrontierPhysics

[![Discord](https://img.shields.io/badge/Discord-Join-7289da?logo=discord&logoColor=white)](https://discord.gg/G9dg3EfSva)
[![GitHub](https://img.shields.io/github/stars/benchflow-ai/FrontierPhysics?style=social)](https://github.com/benchflow-ai/FrontierPhysics)
[![WeChat](https://img.shields.io/badge/WeChat-Join-07C160?logo=wechat&logoColor=white)](docs/wechat-qr.jpg)

Are AI agents good physicists?

**FrontierPhysics**: Benchmark how AI agents do frontier physics research.

**[Contributing](CONTRIBUTING.md)** · **[Benchmark Protocol](docs/benchmark-protocol.md)** · **[BenchFlow SDK](https://github.com/benchflow-ai/benchflow)** · **[Discord](https://discord.gg/G9dg3EfSva)**

## What is FrontierPhysics?

FrontierPhysics is a benchmark evaluating how AI agents do **frontier physics research iteratively**. We evaluate realistic research challenges with iteration loops from **literature deep review** to **research plan implementation**. Tasks come from real research problems that take at least **weeks of effort** for a physics PhD to do deep research and implement, and SOTA LLM agents **struggle** with. The tasks are evaluated with verifiable graders and per-task rubric-based reviewer agents to make sure agents are doing research in ways **aligned with real frontier researchers**.

## Quick Start

```bash
git clone https://github.com/benchflow-ai/FrontierPhysics.git
cd FrontierPhysics

# Install or upgrade to the latest stable BenchFlow CLI.
uv tool install --upgrade benchflow

# Install repository tooling from the committed lockfile.
uv sync --locked

# Validate a native task.md package.
bench tasks check tasks/surface-ion-trap-shuttling

# Oracle must pass before agent runs.
bench eval run \
  --tasks-dir tasks/surface-ion-trap-shuttling \
  --agent oracle \
  --sandbox docker
```

Runnable benchmark tasks live under `tasks/`. FrontierPhysics uses `uv.lock` for reproducible repository tooling while the `bench` CLI runs task validation and evaluations.

See [experiments/README.md](experiments/README.md) for paired no-skill and with-skill commands.

### API Keys

Running hosted agents may require provider credentials or an authenticated local agent session. Export only the credentials required by the selected agent. Keep secrets in an ignored `.env` or `.envrc`; never commit them.

### Creating Tasks

Not sure what to propose? See the [task ideation guide](docs/task-ideation.md) for
the kinds of research subproblems that make good tasks, with idea-level examples
across experimental and theoretical domains.

FrontierPhysics tasks are native BenchFlow `task.md` packages:

```text
tasks/<task-id>/
  task.md
  environment/
    Dockerfile
    skills/
  oracle/
    solve.sh
  verifier/
    rubric.json
    test.sh
    test_outputs.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for scientific-quality requirements, mentor-skill policy, metadata, validation, and review evidence.

## Get Involved

- **Discord**: [Join our server](https://discord.gg/G9dg3EfSva)
- **WeChat**: [Scan QR code](docs/wechat-qr.jpg)
- **Weekly sync**: Thursday 7PM PT / 10PM ET

### Authorship policy

A merged task earns **6 points**, a referral **2 points** (once the referred contributor merged at least 1 task), a task review **2 points** (once the task has been merged). At **12 points** you are a co-author on the FrontierPhysics paper and dataset. To become a reviewer, make sure you have at least one task merged, then ask a maintainer. Full details: [authorship policy](CONTRIBUTING.md#authorship-policy).

### Timeline

We will submit to **ICLR** first and then submit to *Nature* after further polish.

- **v0.1** — Get tasks merged by **31 August** to join the author list of **ICLR** (and all future paper versions).
- **v1.0** — Get tasks merged by **31 December** to join the author list of the draft submitted to *Nature*.

Both are deadlines for a task being **merged**, not opened — review and revision take days of back-and-forth, so a PR opened close to a deadline is unlikely to land in time. Open a draft PR early: see the [timeline](CONTRIBUTING.md#timeline).

## License

[Apache 2.0](LICENSE). Bundled third-party components retain their own license notices; see [NOTICE](NOTICE).
