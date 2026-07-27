#!/usr/bin/env python3
"""Validate the FrontierPhysics public task layout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TASKS = (
    "heterodyne-shot-noise-analysis",
    "surface-ion-trap-shuttling",
    "trapped-ions-heating-rate",
)


def main() -> int:
    problems: list[str] = []
    tasks_root = ROOT / "tasks"
    task_names = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())

    if task_names != sorted(EXPECTED_TASKS):
        problems.append(f"tasks/ must match {sorted(EXPECTED_TASKS)!r}; found {task_names}")

    for forbidden in ("example_tasks", "tasks-extra"):
        if (ROOT / forbidden).exists():
            problems.append(f"forbidden public task directory exists: {forbidden}/")

    task_files = sorted(path for path in ROOT.glob("**/task.md") if ".venv" not in path.parts and ".git" not in path.parts)
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
