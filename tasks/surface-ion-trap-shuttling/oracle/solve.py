#!/usr/bin/env python3

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "/oracle/assets")

from ion_trap_tools import (
    chain_transport_profile,
    ion_chain_spacings_um,
    radial_secular_frequency_mhz,
    single_transport_profile,
    write_profile_csv,
)

ROOT = Path("/root")
ALPHA = 0.00174
ION_MASS_AMU = 40.0
SINGLE_DISTANCE_UM = 100.0
SINGLE_SPEED_M_PER_S = 10.0
CHAIN_ION_COUNT = 9
MOVE_DURATION_US = 10.0
DWELL_DURATION_US = 1.0
SAMPLE_COUNT = 10_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    provenance = json.loads(Path("/oracle/assets/model_provenance.json").read_text())
    stl_path = ROOT / "surface_trap.stl"
    panel_path = Path("/oracle/assets/surface_trap_panels.npz")

    if sha256(stl_path) != provenance["stl_sha256"]:
        raise RuntimeError("Surface-trap STL does not match its provenance record")
    if sha256(panel_path) != provenance["panel_mesh_sha256"]:
        raise RuntimeError("Panel mesh does not match its provenance record")

    bem_result = radial_secular_frequency_mhz(
        panel_path,
        rf_voltage_v=float(provenance["rf_voltage_v"]),
        drive_frequency_mhz=float(provenance["rf_drive_frequency_mhz"]),
        ion_mass_amu=ION_MASS_AMU,
        electrode_name=str(provenance["rf_electrode_name"]),
        grid_center_mm=tuple(provenance["notebook_grid_center_mm"]),
    )
    radial_mhz = float(bem_result["radial_parallel_mhz"])
    axial_mhz = radial_mhz * math.sqrt(ALPHA)

    spacings_um = ion_chain_spacings_um(CHAIN_ION_COUNT, axial_mhz, ION_MASS_AMU)

    result_lines = [
        f"W_radial_freq: {radial_mhz:.9f}",
        f"W_axial_freq: {axial_mhz:.9f}",
        *[f"d{index}: {spacing:.9f}" for index, spacing in enumerate(spacings_um, start=1)],
    ]
    (ROOT / "result.md").write_text("\n".join(result_lines) + "\n")

    single_time_us, single_position_um = single_transport_profile(
        distance_um=SINGLE_DISTANCE_UM,
        speed_m_per_s=SINGLE_SPEED_M_PER_S,
        axial_frequency_mhz=axial_mhz,
        sample_count=SAMPLE_COUNT,
    )
    write_profile_csv(ROOT / "1.csv", single_time_us, single_position_um)

    chain_time_us, chain_position_um = chain_transport_profile(
        spacings_um,
        move_duration_us=MOVE_DURATION_US,
        dwell_duration_us=DWELL_DURATION_US,
        axial_frequency_mhz=axial_mhz,
        sample_count=SAMPLE_COUNT,
    )
    write_profile_csv(ROOT / "2.csv", chain_time_us, chain_position_um)

    diagnostics = {
        "alpha": ALPHA,
        "axial_frequency_mhz": axial_mhz,
        "bem": bem_result,
        "chain_span_um": float(spacings_um.sum()),
        "spacings_um": spacings_um.tolist(),
    }
    (ROOT / "oracle_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(diagnostics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
