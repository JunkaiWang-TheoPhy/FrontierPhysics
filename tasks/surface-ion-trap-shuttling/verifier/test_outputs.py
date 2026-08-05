import csv
import functools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/verifier/assets")

from ion_trap_tools import (
    chain_transport_profile,
    inverse_engineered_trap_position_um,
    ion_chain_spacings_um,
    radial_secular_frequency_mhz,
)

ROOT = Path("/root")
LOGS = Path("/logs/verifier")
ALPHA = 0.00174
ION_MASS_AMU = 40.0
EXPECTED_KEYS = [
    "W_radial_freq",
    "W_axial_freq",
    "d1",
    "d2",
    "d3",
    "d4",
    "d5",
    "d6",
    "d7",
    "d8",
]


def parse_result_markdown() -> dict[str, float]:
    text = (ROOT / "result.md").read_text()
    values: dict[str, float] = {}
    for key in EXPECTED_KEYS:
        match = re.search(
            rf"(?mi)^\s*{re.escape(key)}\s*:\s*"
            rf"([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)",
            text,
        )
        assert match, f"Missing numeric line for {key} in /root/result.md"
        values[key] = float(match.group(1))
        assert math.isfinite(values[key]), f"{key} is not finite"
    return values


@functools.lru_cache(maxsize=1)
def reference_bem() -> dict:
    provenance = json.loads(Path("/verifier/assets/model_provenance.json").read_text())
    result = radial_secular_frequency_mhz(
        Path("/verifier/assets/surface_trap_panels.npz"),
        rf_voltage_v=float(provenance["rf_voltage_v"]),
        drive_frequency_mhz=float(provenance["rf_drive_frequency_mhz"]),
        ion_mass_amu=ION_MASS_AMU,
        electrode_name=str(provenance["rf_electrode_name"]),
        grid_center_mm=tuple(provenance["notebook_grid_center_mm"]),
    )
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "reference_bem.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def read_profile(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open(newline="") as source:
        rows = list(csv.reader(source))

    assert len(rows) == 10_001, f"{path.name} must contain a header plus 10,000 samples; found {len(rows)} rows"
    assert len(rows[0]) >= 2, f"{path.name} header must contain two columns"

    try:
        values = np.asarray(
            [[float(row[0]), float(row[1])] for row in rows[1:]],
            dtype=float,
        )
    except (ValueError, IndexError) as error:
        raise AssertionError(f"{path.name} contains non-numeric samples") from error

    assert np.isfinite(values).all(), f"{path.name} contains non-finite values"
    return values[:, 0], values[:, 1]


def align_direction(actual: np.ndarray, expected_final: float) -> np.ndarray:
    sign = 1.0 if actual[-1] >= actual[0] else -1.0
    aligned = sign * (actual - actual[0])
    assert math.isclose(aligned[-1], expected_final, rel_tol=1e-2, abs_tol=0.2), (
        f"Final displacement is {aligned[-1]:.6f} um, expected {expected_final:.6f} um"
    )
    return aligned


def test_result_frequencies_are_derived_from_bem_and_anisotropy():
    values = parse_result_markdown()
    expected_radial = float(reference_bem()["radial_parallel_mhz"])
    assert math.isclose(
        values["W_radial_freq"],
        expected_radial,
        rel_tol=0.10,
        abs_tol=0.05,
    ), f"W_radial_freq={values['W_radial_freq']:.6f} MHz, BEM reference={expected_radial:.6f} MHz"

    expected_axial = values["W_radial_freq"] * math.sqrt(ALPHA)
    assert math.isclose(
        values["W_axial_freq"],
        expected_axial,
        rel_tol=2e-2,
        abs_tol=1e-3,
    ), f"W_axial_freq={values['W_axial_freq']:.6f} MHz does not satisfy alpha={ALPHA} with the reported radial frequency"


def test_nine_ion_equilibrium_spacings():
    values = parse_result_markdown()
    expected = ion_chain_spacings_um(9, values["W_axial_freq"], ION_MASS_AMU)
    actual = np.array([values[f"d{index}"] for index in range(1, 9)])
    np.testing.assert_allclose(
        actual,
        expected,
        rtol=2e-2,
        atol=0.1,
        err_msg="Adjacent ion spacings do not match Coulomb-force equilibrium",
    )
    np.testing.assert_allclose(
        actual,
        actual[::-1],
        rtol=1e-2,
        atol=0.05,
        err_msg="Nine-ion spacings should be mirror-symmetric",
    )


def test_single_ion_inverse_engineered_waveform():
    values = parse_result_markdown()
    time_us, position_um = read_profile(ROOT / "1.csv")
    np.testing.assert_allclose(
        time_us,
        np.linspace(0.0, 10.0, 10_000),
        rtol=0.0,
        atol=1e-5,
        err_msg="1.csv time samples must uniformly span 0 to 10 us",
    )
    aligned = align_direction(position_um, 100.0)
    expected = inverse_engineered_trap_position_um(
        time_us,
        distance_um=100.0,
        duration_us=10.0,
        axial_frequency_mhz=values["W_axial_freq"],
    )
    np.testing.assert_allclose(
        aligned,
        expected,
        rtol=1e-2,
        atol=0.3,
        err_msg="1.csv is not the inverse-engineered trap-center trajectory",
    )


def test_piecewise_nine_ion_waveform_with_dwells():
    values = parse_result_markdown()
    spacings = np.array([values[f"d{index}"] for index in range(1, 9)])
    time_us, position_um = read_profile(ROOT / "2.csv")
    np.testing.assert_allclose(
        time_us,
        np.linspace(0.0, 88.0, 10_000),
        rtol=0.0,
        atol=1e-4,
        err_msg="2.csv time samples must uniformly span eight 10 us moves and 1 us dwells",
    )
    aligned = align_direction(position_um, float(spacings.sum()))
    _, expected = chain_transport_profile(
        spacings,
        move_duration_us=10.0,
        dwell_duration_us=1.0,
        axial_frequency_mhz=values["W_axial_freq"],
        sample_count=10_000,
    )
    np.testing.assert_allclose(
        aligned,
        expected,
        rtol=1e-2,
        atol=0.3,
        err_msg="2.csv does not concatenate the inverse-engineered stages and dwells",
    )
