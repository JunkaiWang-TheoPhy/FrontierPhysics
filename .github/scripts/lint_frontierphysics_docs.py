#!/usr/bin/env python3
"""Keep FrontierPhysics documentation aligned with the benchmark vision."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_ROOTS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "MAINTAINER.md",
    ROOT / "taxonomy.md",
    ROOT / "experiments" / "README.md",
    ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
)
# Catches branding copied over from the other benchmark — its domain and its
# repository path. The bare product name is deliberately allowed: this team
# authored SkillsBench and cites it as prior work, which is attribution rather
# than the stale branding this check exists to remove.
FORBIDDEN = re.compile(
    r"skillsbench\.ai|benchflow/skillsbench",
    re.IGNORECASE,
)
README_HEADINGS = (
    "## What is FrontierPhysics?",
    "## Quick Start",
    "### API Keys",
    "### Creating Tasks",
    "## Get Involved",
    "## License",
)
DISCORD = "https://discord.gg/G9dg3EfSva"
WECHAT = "docs/wechat-qr.jpg"
BENCHFLOW_INSTALL = "uv tool install --upgrade benchflow"
PINNED_BENCHFLOW_INSTALL = re.compile(
    r"uv\s+tool\s+install\s+[\"']?benchflow(?:[<>=!~].*)?[\"']?",
    re.IGNORECASE,
)


def documentation_files() -> list[Path]:
    files = [path for path in DOC_ROOTS if path.is_file()]
    files.extend((ROOT / "docs").rglob("*.md"))
    files.extend((ROOT / ".agents").rglob("*.md"))
    # The public website is documentation too. It sat outside this check long
    # enough to accumulate stale branding the check exists to prevent.
    files.extend(path for path in (ROOT / "website").glob("*.md"))
    files.extend((ROOT / "website" / "src").rglob("*.md"))
    return sorted(set(files))


def main() -> int:
    problems: list[str] = []
    for path in documentation_files():
        text = path.read_text(encoding="utf-8")
        if match := FORBIDDEN.search(text):
            problems.append(
                f"{path.relative_to(ROOT)} contains stale branding: {match.group(0)!r}"
            )

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    positions = [readme.find(heading) for heading in README_HEADINGS]
    if any(position < 0 for position in positions):
        missing = [
            heading
            for heading, position in zip(README_HEADINGS, positions, strict=True)
            if position < 0
        ]
        problems.append(f"README.md missing required sections: {missing}")
    elif positions != sorted(positions):
        problems.append("README.md sections do not follow the required order")

    if DISCORD not in readme:
        problems.append("README.md is missing the shared Discord invite")
    if WECHAT not in readme or not (ROOT / WECHAT).is_file():
        problems.append("README.md is missing the shared WeChat badge or QR image")
    if BENCHFLOW_INSTALL not in readme:
        problems.append("README.md must install the latest stable BenchFlow CLI")

    for path in documentation_files():
        text = path.read_text(encoding="utf-8")
        for match in PINNED_BENCHFLOW_INSTALL.finditer(text):
            if match.group(0).strip() != BENCHFLOW_INSTALL:
                problems.append(
                    f"{path.relative_to(ROOT)} uses a constrained or stale "
                    "BenchFlow install command"
                )

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print(f"OK: {len(documentation_files())} FrontierPhysics documentation files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
