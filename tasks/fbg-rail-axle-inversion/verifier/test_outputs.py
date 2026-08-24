"""Outcome tests for fbg-rail-axle-inversion.

Grades the agent's deliverables against held-out simulator ground truth.
Tolerance derivation: 5-seed method-variation study (details in the PR).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(os.environ.get("AGENT_OUT_DIR", "/root"))
GT = Path(os.environ.get("GT_DIR", "/verifier/assets/ground_truth"))

# Tolerances from the 5-seed method-variation study (final hardened
# physics: 4% dynamic wheel-load variation, wheel-flat impacts, dropout):
# kernel-fit + multi-sensor fusion reference: worst per-axle 7.1-10.9%,
# vehicle means <5%, totals (>=20-axle trains) <=2.6%; physics-unaware
# peak-height method: worst per-axle 17.8-22.4%, systematic -11..-14%
# vehicle bias, worst totals 7.3-11.1%. Per-axle band 15% sits above the
# reference worst-case statistics and well below the biased method; the
# vehicle-mean band 6% is what kills systematic bias (random dynamics
# average out, bias does not). Total-weight check needs >=20 axles to be
# statistically meaningful under honest dynamics.
TOL_V_MEAN_REL = 0.02
TOL_V_END_REL = 0.05
TOL_LOAD_REL = 0.15          # per axle (WIM-class band; dynamics are random)
TOL_LOAD_ABS_KN = 4.0        # floor for light axles
TOL_LOAD_VEHICLE_REL = 0.06  # per-vehicle mean (bias does not average out)
TOL_LOAD_TOTAL_REL = 0.03    # per train
TOL_T_REF_S = 0.050
TOL_OCC_S = 0.5


@pytest.fixture(scope="module")
def gt_trains():
    return json.loads((GT / "trains.json").read_text())


@pytest.fixture(scope="module")
def gt_axles():
    return pd.read_csv(GT / "axles.csv")


@pytest.fixture(scope="module")
def result_kv():
    # Outcome-tolerant parsing: agents legitimately decorate result.md with
    # Markdown (list bullets, headings, `code`, **bold**). Strip decoration
    # before matching key: value lines; grading tolerates formatting, the
    # values themselves are still checked exactly. (Derived from a with-skill
    # control run that answered every key correctly inside a styled report.)
    text = (ROOT / "result.md").read_text()
    kv = {}
    for line in text.splitlines():
        line = re.sub(r"^[\s>#*+-]+", "", line.strip())
        line = line.replace("**", "").replace("`", "")
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.+)$", line.strip())
        if m:
            kv[m.group(1)] = m.group(2).strip()
    return kv


@pytest.fixture(scope="module")
def axles():
    return pd.read_csv(ROOT / "axles.csv")


def _occ(kv, r):
    vals = re.findall(r"[-+]?[\d.]+", kv[f"train_{r}_occupancy_s"])
    assert len(vals) == 2, f"train_{r}_occupancy_s must be an interval"
    return [float(v) for v in vals]


def test_deliverables_exist_and_parse(result_kv, axles, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        keys = ["n_axles", "direction", "v_entry_mps", "v_exit_mps",
                "occupancy_s"]
        if not gt.get("reverses"):
            keys.append("speed_mps")  # graded in test_direction_and_speeds
        for key in keys:
            assert f"train_{r}_{key}" in result_kv, f"missing train_{r}_{key}"
    assert "faulted_sensor" in result_kv
    for col in ("train_id", "axle_index", "t_ref_s", "load_kN"):
        assert col in axles.columns, f"axles.csv missing column {col}"


def test_axle_counts_exact(result_kv, axles, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        n = int(result_kv[f"train_{r}_n_axles"])
        assert n == gt["n_axles"], \
            f"train_{r}: {n} axles reported, ground truth {gt['n_axles']}"
        n_rows = int((axles.train_id == f"train_{r}").sum())
        assert n_rows == gt["n_axles"], \
            f"train_{r}: {n_rows} axles.csv rows, expected {gt['n_axles']}"
    assert len(axles) == sum(g["n_axles"] for g in gt_trains), \
        "axles.csv contains extra (false) axle events"


def test_direction_and_speeds(result_kv, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        assert int(result_kv[f"train_{r}_direction"]) == gt["direction"], \
            f"train_{r}: wrong direction (0 = entered and reversed out)"
        if not gt.get("reverses"):
            gt_v_mean = (gt["v_entry_mps"] + gt["v_exit_mps"]) / 2.0
            v = float(result_kv[f"train_{r}_speed_mps"])
            assert abs(v - gt_v_mean) <= TOL_V_MEAN_REL * gt_v_mean, \
                f"train_{r}: mean speed {v} vs {gt_v_mean}"
        for key, ref in (("v_entry_mps", gt["v_entry_mps"]),
                         ("v_exit_mps", gt["v_exit_mps"])):
            val = float(result_kv[f"train_{r}_{key}"])
            assert abs(val - ref) <= TOL_V_END_REL * ref, \
                f"train_{r}: {key} {val} vs {ref}"


def test_axle_event_times(axles, gt_axles, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        a = axles[axles.train_id == f"train_{r}"].sort_values("t_ref_s")
        g = gt_axles[gt_axles.train_id == gt["train_id"]].sort_values("t_ref_s")
        assert len(a) == len(g)
        err = np.abs(a.t_ref_s.to_numpy() - g.t_ref_s.to_numpy())
        assert err.max() <= TOL_T_REF_S, \
            f"train_{r}: worst t_ref error {err.max():.3f} s"


def test_axle_loads(axles, gt_axles, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        a = axles[axles.train_id == f"train_{r}"].sort_values("t_ref_s")
        g = gt_axles[gt_axles.train_id == gt["train_id"]].sort_values("t_ref_s")
        got = a.load_kN.to_numpy()
        ref = g.load_kN.to_numpy()
        tol = np.maximum(TOL_LOAD_REL * ref, TOL_LOAD_ABS_KN)
        bad = np.abs(got - ref) > tol
        assert not bad.any(), \
            f"train_{r}: {bad.sum()} axle loads outside tolerance " \
            f"(worst {np.abs(got - ref).max():.1f} kN)"
        if len(ref) >= 20:   # totals are statistically meaningful on long trains
            assert abs(got.sum() - ref.sum()) <= TOL_LOAD_TOTAL_REL * ref.sum(), \
                f"train_{r}: total load off by {abs(got.sum() - ref.sum()):.1f} kN"
        veh = g.vehicle_index.to_numpy()
        for v in np.unique(veh):
            gv, rv = got[veh == v].mean(), ref[veh == v].mean()
            assert abs(gv - rv) <= TOL_LOAD_VEHICLE_REL * rv, \
                f"train_{r} vehicle {v}: mean load {gv:.1f} vs {rv:.1f} kN"


def test_faulted_sensor(result_kv):
    internals = json.loads((GT / "sensors_internal.json").read_text())
    assert result_kv["faulted_sensor"].strip() == internals["faulted_sensor"], \
        f"faulted sensor: reported {result_kv['faulted_sensor']}"


def test_paper_pdf_has_reviewable_structure():
    # Deterministic structure only; whether the paper is publishable is
    # graded afterwards by the detached rubric reviewer.
    from pypdf import PdfReader
    path = ROOT / "paper.pdf"
    assert path.is_file(), "Missing /root/paper.pdf"
    reader = PdfReader(str(path))
    assert len(reader.pages) >= 2, \
        f"paper.pdf has {len(reader.pages)} pages; a paper draft needs at least 2"
    texts = [page.extract_text() or "" for page in reader.pages]
    compact = " ".join(" ".join(texts).lower().split())
    assert len(compact) >= 1500, \
        "paper.pdf contains too little extractable text to review"
    for page_number, text in enumerate(texts, start=1):
        assert len(text.strip()) >= 40, \
            f"paper.pdf page {page_number} is effectively blank or not extractable"
    # Singular forms: each is a substring of its plural, so "Method" and
    # "Methods" both count. Structure only, never wording.
    for section in ("abstract", "introduction", "method", "result",
                    "discussion", "reference"):
        assert section in compact, \
            f"paper.pdf is missing the '{section}' component"


def test_occupancy(result_kv, gt_trains):
    for r, gt in enumerate(gt_trains, start=1):
        t_in, t_out = _occ(result_kv, r)
        assert abs(t_in - gt["occupancy_s"][0]) <= TOL_OCC_S and \
               abs(t_out - gt["occupancy_s"][1]) <= TOL_OCC_S, \
            f"train_{r}: occupancy [{t_in:.2f},{t_out:.2f}] vs {gt['occupancy_s']}"
