#!/usr/bin/env python3
"""Validate the FrontierPhysics public task layout."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TASKS = (
    "fbg-rail-axle-inversion",
    "multiplexing-ion-chain-qnet",
    "rydberg-cz-phase-noise-infidelity",
    "sipm-spe-gain-breakdown",
)
VENDORED_SNAPSHOTS = (ROOT / "website" / "public" / "example-task",)
BENCHFLOW_DEPENDENCY = re.compile(
    r"^benchflow(?:\[[^]]+\])?(?P<specifier>[<>=!~].*)$",
    re.IGNORECASE,
)


def _benchflow_specifiers(dependencies: object) -> list[str]:
    if not isinstance(dependencies, list):
        return []

    specifiers = []
    for dependency in dependencies:
        if not isinstance(dependency, str):
            continue
        match = BENCHFLOW_DEPENDENCY.fullmatch(dependency)
        if match:
            specifiers.append(match.group("specifier"))
    return specifiers


def benchflow_contract_problems(root: Path) -> list[str]:
    """Return an error when registry and project compatibility drift apart."""
    problems: list[str] = []
    registry_specifier: str | None = None
    project_specifier: str | None = None

    try:
        registry = json.loads((root / "registry.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        problems.append(f"registry.json cannot be read: {exc}")
    else:
        entries = (
            [entry for entry in registry if isinstance(entry, dict) and entry.get("name") == "frontierphysics"]
            if isinstance(registry, list)
            else []
        )
        if len(entries) != 1:
            problems.append("registry.json must contain exactly one frontierphysics entry")
        else:
            value = entries[0].get("bench_version")
            if isinstance(value, str):
                registry_specifier = value
            else:
                problems.append("registry.json frontierphysics bench_version must be a string")

    try:
        with (root / "pyproject.toml").open("rb") as handle:
            pyproject = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        problems.append(f"pyproject.toml cannot be read: {exc}")
    else:
        project = pyproject.get("project", {})
        dependencies = project.get("dependencies") if isinstance(project, dict) else None
        specifiers = _benchflow_specifiers(dependencies)
        if len(specifiers) != 1:
            problems.append("pyproject.toml must declare exactly one benchflow dependency")
        else:
            project_specifier = specifiers[0]

    if registry_specifier is not None and project_specifier is not None and registry_specifier != project_specifier:
        problems.append(
            "registry.json frontierphysics bench_version must match the pyproject.toml "
            f"benchflow dependency; found {registry_specifier!r} and {project_specifier!r}"
        )

    return problems


def main() -> int:
    problems = benchflow_contract_problems(ROOT)
    tasks_root = ROOT / "tasks"
    task_names = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())

    if task_names != sorted(EXPECTED_TASKS):
        problems.append(f"tasks/ must match {sorted(EXPECTED_TASKS)!r}; found {task_names}")

    for forbidden in ("example_tasks", "tasks-extra"):
        if (ROOT / forbidden).exists():
            problems.append(f"forbidden public task directory exists: {forbidden}/")

    task_files = sorted(
        path
        for path in ROOT.glob("**/task.md")
        if ".venv" not in path.parts
        and ".git" not in path.parts
        and "node_modules" not in path.parts
        and not any(path.is_relative_to(snapshot) for snapshot in VENDORED_SNAPSHOTS)
    )
    expected_files = sorted(tasks_root / task_name / "task.md" for task_name in EXPECTED_TASKS)
    if task_files != expected_files:
        problems.append(
            "task.md layout mismatch; expected "
            f"{[path.relative_to(ROOT).as_posix() for path in expected_files]}; found "
            f"{[path.relative_to(ROOT).as_posix() for path in task_files]}"
        )

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print("OK: public task layout matches repository policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
