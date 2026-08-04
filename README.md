# FrontierPhysics

[![Discord](https://img.shields.io/badge/Discord-Join-7289da?logo=discord&logoColor=white)](https://discord.gg/G9dg3EfSva)
[![GitHub](https://img.shields.io/github/stars/benchflow-ai/FrontierPhysics?style=social)](https://github.com/benchflow-ai/FrontierPhysics)
[![WeChat](https://img.shields.io/badge/WeChat-Join-07C160?logo=wechat&logoColor=white)](docs/wechat-qr.jpg)

Are AI agents good physicists?

**FrontierPhysics**: Benchmark how AI agents do frontier physics research.

**[Contributing](CONTRIBUTING.md)** · **[Benchmark Protocol](docs/benchmark-protocol.md)** · **[BenchFlow SDK](https://github.com/benchflow-ai/benchflow)** · **[Discord](https://discord.gg/G9dg3EfSva)**

## What is FrontierPhysics?

FrontierPhysics measures whether AI agents can complete authentic,
specialist-level physics workflows: building physical models, deriving
quantities, running numerical simulations, analyzing scientific data, and
producing research artifacts.

The primary benchmark condition gives agents the task, environment, and tools
without mentor skills. Each task also ships a reviewable mentor package as a
solvability control. A strong with-skill result helps distinguish a genuine
capability limit from a broken task, environment, oracle, or verifier.

**Goals:**

- Build a rigorous public benchmark for advanced physics research
- Measure independent agent capability through no-skill pass rate
- Use mentor-guided control runs to validate task solvability
- Preserve scientific provenance, trajectories, diagnostics, and artifacts
- Cover theoretical, computational, experimental, and instrumentation work

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

Runnable benchmark tasks live under `tasks/`. FrontierPhysics uses `uv.lock`
for reproducible repository tooling while the `bench` CLI runs task validation
and evaluations.

See [experiments/README.md](experiments/README.md) for paired no-skill and
with-skill commands.

### API Keys

Running hosted agents may require provider credentials or an authenticated
local agent session. Export only the credentials required by the selected
agent. Keep secrets in an ignored `.env` or `.envrc`; never commit them.

### Creating Tasks

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
    test.sh
    test_outputs.py
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for scientific-quality requirements,
mentor-skill policy, metadata, validation, and review evidence.

## Get Involved

- **Discord**: [Join our server](https://discord.gg/G9dg3EfSva)
- **WeChat**: [Scan QR code](docs/wechat-qr.jpg)
- **Weekly sync**: Mondays 5PM PT / 8PM ET / 9AM GMT+8

Contribution credit is tracked in points: a merged task you authored is worth 6,
referring a contributor is worth 2 once their first task merges, a merged task
you reviewed is worth 1, and 12 points earns co-authorship on the
FrontierPhysics paper and dataset. Reviewing and referring count — see the
[authorship policy](CONTRIBUTING.md#authorship-policy).

## License

[Apache 2.0](LICENSE). Bundled third-party components retain their own license
notices; see [NOTICE](NOTICE).
