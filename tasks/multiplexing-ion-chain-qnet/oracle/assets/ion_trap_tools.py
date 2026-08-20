#!/usr/bin/env python3
"""Reusable numerical tools for RF ion traps and harmonic ion transport."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Iterable
from pathlib import Path

import iontrap_fastlap as fastlap
import numpy as np
from scipy.optimize import root

ELEMENTARY_CHARGE_C = 1.602176634e-19
ATOMIC_MASS_CONSTANT_KG = 1.66053906660e-27
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12


def load_panel_mesh(path: str | Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load a neutral panel mesh exported from a colored STL workflow."""
    with np.load(path) as data:
        panels = np.ascontiguousarray(data["panels"], dtype=np.double)
        groups = np.ascontiguousarray(data["groups"], dtype=np.intc)
        names = [str(value) for value in data["names"].tolist()]

    if panels.ndim != 3 or panels.shape[1:] != (4, 3):
        raise ValueError(f"Expected panels with shape (N, 4, 3), got {panels.shape}")
    if groups.shape != (panels.shape[0],):
        raise ValueError("Panel group array does not match panel count")
    return panels, groups, names


def solve_unit_electrode_field(
    panel_mesh_path: str | Path,
    observation_points_mm: np.ndarray,
    electrode_name: str = "RF",
    *,
    solve_num_mom: int = 4,
    solve_num_lev: int = 3,
    evaluate_num_mom: int = 4,
    evaluate_num_lev: int = 2,
    max_iter: int = 200,
    tolerance: float = 1e-5,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Run a constant-panel FastLap BEM solve and return the 1 V field in V/mm."""
    panels, groups, names = load_panel_mesh(panel_mesh_path)
    if electrode_name not in names:
        raise ValueError(f"Electrode {electrode_name!r} not present; choices: {names}")

    panel_count = panels.shape[0]
    electrode_index = names.index(electrode_name)
    panel_potential = np.ascontiguousarray((groups == electrode_index).astype(np.double))

    shape = np.full(panel_count, fastlap.TRIANGLE, dtype=np.intc)
    centroids = np.ascontiguousarray(fastlap.centroid(panels, shape))
    constant_source = np.full(panel_count, fastlap.CONSTANT_SOURCE, dtype=np.intc)
    no_source = np.full(panel_count, fastlap.NO_SOURCE, dtype=np.intc)
    panel_index = np.arange(panel_count, dtype=np.intc)
    source_type = np.zeros(panel_count, dtype=np.intc)

    iterations, achieved_tolerance, charge, _areas = fastlap.fastlap(
        x=panels,
        shape=shape,
        lhs_type=constant_source,
        rhs_type=no_source,
        rhs_vect=panel_potential,
        xf=centroids,
        type=source_type,
        lhs_index=panel_index,
        rhs_index=panel_index,
        job=fastlap.INDIRECT,
        ret_areas=True,
        num_mom=solve_num_mom,
        num_lev=solve_num_lev,
        max_iter=max_iter,
        tol=tolerance,
    )

    points = np.ascontiguousarray(observation_points_mm, dtype=np.double)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("Observation points must have shape (N, 3)")

    field = np.empty((3, points.shape[0]), dtype=np.double)
    field_type = np.ones(points.shape[0], dtype=np.intc)
    axis_normals = np.zeros((points.shape[0], 3), dtype=np.double)
    axis_normals[:, 0] = 1.0

    for axis in range(3):
        normals = np.ascontiguousarray(np.roll(axis_normals, axis, axis=1))
        output = np.empty(points.shape[0], dtype=np.double)
        fastlap.fastlap(
            x=panels,
            shape=shape,
            lhs_type=no_source,
            rhs_type=constant_source,
            rhs_vect=np.ascontiguousarray(charge),
            xf=points,
            type=field_type,
            xnrm=normals,
            lhs_vect=output,
            lhs_index=panel_index,
            rhs_index=panel_index,
            job=fastlap.FIELD,
            num_mom=evaluate_num_mom,
            num_lev=evaluate_num_lev,
            max_iter=max_iter,
            tol=tolerance,
        )
        field[axis] = output

    diagnostics: dict[str, float | int] = {
        "panels": int(panel_count),
        "iterations": int(iterations),
        "achieved_tolerance": float(achieved_tolerance),
    }
    return field, diagnostics


def radial_secular_frequency_mhz(
    panel_mesh_path: str | Path,
    *,
    rf_voltage_v: float,
    drive_frequency_mhz: float,
    ion_mass_amu: float,
    electrode_name: str = "RF",
    grid_center_mm: tuple[float, float, float] = (0.00375, 0.075, -0.1),
    grid_step_mm: float = 0.001,
    grid_points: int = 11,
) -> dict[str, float | int | list[float]]:
    """Calculate radial secular frequencies by fitting the BEM pseudopotential."""
    if grid_points < 5 or grid_points % 2 == 0:
        raise ValueError("grid_points must be an odd integer >= 5")

    half = grid_points // 2
    x_mm = grid_center_mm[0] + np.arange(-half, half + 1) * grid_step_mm
    y_mm = grid_center_mm[1] + np.arange(-half, half + 1) * grid_step_mm
    xx_mm, yy_mm = np.meshgrid(x_mm, y_mm, indexing="ij")
    points_mm = np.column_stack(
        [
            xx_mm.ravel(),
            yy_mm.ravel(),
            np.full(xx_mm.size, grid_center_mm[2]),
        ]
    )

    field_v_per_mm, diagnostics = solve_unit_electrode_field(panel_mesh_path, points_mm, electrode_name)
    field_v_per_m = field_v_per_mm * 1000.0 * rf_voltage_v

    charge = ELEMENTARY_CHARGE_C
    mass = ion_mass_amu * ATOMIC_MASS_CONSTANT_KG
    drive_angular_frequency = 2.0 * math.pi * drive_frequency_mhz * 1e6
    pseudopotential_j = (charge**2 * np.sum(field_v_per_m**2, axis=0) / (4.0 * mass * drive_angular_frequency**2)).reshape(
        grid_points, grid_points
    )

    min_i, min_j = np.unravel_index(int(np.argmin(pseudopotential_j)), pseudopotential_j.shape)
    if not (2 <= min_i < grid_points - 2 and 2 <= min_j < grid_points - 2):
        raise RuntimeError("RF null is too close to the fit-grid boundary; adjust grid center/span")

    local_x = x_mm[min_i - 2 : min_i + 3] * 1e-3
    local_y = y_mm[min_j - 2 : min_j + 3] * 1e-3
    local_u = pseudopotential_j[min_i - 2 : min_i + 3, min_j - 2 : min_j + 3]
    xx_m, yy_m = np.meshgrid(local_x, local_y, indexing="ij")

    x0_m = x_mm[min_i] * 1e-3
    y0_m = y_mm[min_j] * 1e-3
    dx = xx_m - x0_m
    dy = yy_m - y0_m
    design = np.column_stack(
        [
            dx.ravel() ** 2,
            dy.ravel() ** 2,
            dx.ravel() * dy.ravel(),
            dx.ravel(),
            dy.ravel(),
            np.ones(dx.size),
        ]
    )
    coefficients, *_ = np.linalg.lstsq(design, local_u.ravel(), rcond=None)
    hessian = np.array(
        [
            [2.0 * coefficients[0], coefficients[2]],
            [coefficients[2], 2.0 * coefficients[1]],
        ]
    )
    gradient = np.array([coefficients[3], coefficients[4]])
    fitted_shift = -np.linalg.solve(hessian, gradient)
    fitted_null_m = np.array([x0_m, y0_m]) + fitted_shift

    coordinate_frequencies_mhz = np.sqrt(np.diag(hessian) / mass) / (2.0 * math.pi) / 1e6
    principal_frequencies_mhz = np.sqrt(np.linalg.eigvalsh(hessian) / mass) / (2.0 * math.pi) / 1e6

    return {
        **diagnostics,
        "radial_parallel_mhz": float(coordinate_frequencies_mhz[0]),
        "radial_vertical_mhz": float(coordinate_frequencies_mhz[1]),
        "principal_frequencies_mhz": principal_frequencies_mhz.tolist(),
        "rf_null_um": (fitted_null_m * 1e6).tolist(),
    }


def dimensionless_equilibrium_positions(ion_count: int) -> np.ndarray:
    """Solve the dimensionless harmonic-trap Coulomb equilibrium equations."""
    if ion_count < 1:
        raise ValueError("ion_count must be positive")
    if ion_count == 1:
        return np.array([0.0])

    indices = np.arange(ion_count, dtype=float)
    initial = 3.94 * ion_count**0.387 * np.sin(np.arcsin(1.75 * ion_count**-0.982 * ((indices + 1.0) - (ion_count + 1.0) / 2.0)) / 3.0)

    def equations(positions: np.ndarray) -> np.ndarray:
        values = np.empty(ion_count)
        for i in range(ion_count):
            left = np.sum(1.0 / (positions[i] - positions[:i]) ** 2)
            right = np.sum(1.0 / (positions[i] - positions[i + 1 :]) ** 2)
            values[i] = positions[i] - left + right
        return values

    solution = root(equations, initial, method="hybr", tol=1e-11)
    if not solution.success:
        raise RuntimeError(f"Ion equilibrium solve failed: {solution.message}")
    return np.sort(solution.x)


def ion_chain_spacings_um(ion_count: int, axial_frequency_mhz: float, ion_mass_amu: float) -> np.ndarray:
    """Return adjacent equilibrium spacings for a 1D Coulomb crystal."""
    angular_frequency = 2.0 * math.pi * axial_frequency_mhz * 1e6
    mass = ion_mass_amu * ATOMIC_MASS_CONSTANT_KG
    coulomb_constant = 1.0 / (4.0 * math.pi * VACUUM_PERMITTIVITY_F_PER_M)
    length_scale_m = (coulomb_constant * ELEMENTARY_CHARGE_C**2 / (mass * angular_frequency**2)) ** (1.0 / 3.0)
    positions_um = dimensionless_equilibrium_positions(ion_count) * length_scale_m * 1e6
    return np.diff(positions_um)


def inverse_engineered_trap_position_um(
    time_us: np.ndarray | float,
    *,
    distance_um: float,
    duration_us: float,
    axial_frequency_mhz: float,
) -> np.ndarray:
    """Evaluate the invariant-based harmonic trap-center trajectory q0(t)."""
    times = np.asarray(time_us, dtype=float)
    clipped = np.clip(times, 0.0, duration_us)
    s = clipped / duration_us

    classical = 10.0 * s**3 - 15.0 * s**4 + 6.0 * s**5
    acceleration_correction = s - 3.0 * s**2 + 2.0 * s**3
    omega_t = 2.0 * math.pi * axial_frequency_mhz * duration_us
    trajectory = distance_um * (classical + 60.0 * acceleration_correction / omega_t**2)
    return np.where(
        times < 0.0,
        0.0,
        np.where(times > duration_us, distance_um, trajectory),
    )


def single_transport_profile(
    *,
    distance_um: float,
    speed_m_per_s: float,
    axial_frequency_mhz: float,
    sample_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a fixed-distance inverse-engineered harmonic transport profile."""
    duration_us = distance_um / speed_m_per_s
    time_us = np.linspace(0.0, duration_us, sample_count)
    position_um = inverse_engineered_trap_position_um(
        time_us,
        distance_um=distance_um,
        duration_us=duration_us,
        axial_frequency_mhz=axial_frequency_mhz,
    )
    return time_us, position_um


def chain_transport_profile(
    spacings_um: Iterable[float],
    *,
    move_duration_us: float,
    dwell_duration_us: float,
    axial_frequency_mhz: float,
    sample_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Concatenate equal-form transport stages separated by fixed dwells."""
    spacings = np.asarray(list(spacings_um), dtype=float)
    stage_duration = move_duration_us + dwell_duration_us
    total_duration = len(spacings) * stage_duration
    time_us = np.linspace(0.0, total_duration, sample_count)
    position_um = np.empty_like(time_us)
    offsets = np.concatenate([[0.0], np.cumsum(spacings)])

    for sample_index, time_value in enumerate(time_us):
        stage_index = min(int(time_value // stage_duration), len(spacings))
        if stage_index == len(spacings):
            position_um[sample_index] = offsets[-1]
            continue

        local_time = time_value - stage_index * stage_duration
        if local_time <= move_duration_us:
            position_um[sample_index] = offsets[stage_index] + float(
                inverse_engineered_trap_position_um(
                    local_time,
                    distance_um=spacings[stage_index],
                    duration_us=move_duration_us,
                    axial_frequency_mhz=axial_frequency_mhz,
                )
            )
        else:
            position_um[sample_index] = offsets[stage_index + 1]

    return time_us, position_um


def write_profile_csv(path: str | Path, time_us: np.ndarray, position_um: np.ndarray) -> None:
    """Write a two-column transport waveform."""
    with open(path, "w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["time_us", "position_um"])
        writer.writerows(zip(time_us, position_um, strict=True))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bem = subparsers.add_parser("bem-frequency")
    bem.add_argument("--panels", required=True)
    bem.add_argument("--rf-voltage-v", type=float, required=True)
    bem.add_argument("--drive-mhz", type=float, required=True)
    bem.add_argument("--mass-amu", type=float, default=40.0)
    bem.add_argument("--electrode", default="RF")
    bem.add_argument("--output-json")

    spacing = subparsers.add_parser("ion-spacing")
    spacing.add_argument("--ions", type=int, required=True)
    spacing.add_argument("--axial-mhz", type=float, required=True)
    spacing.add_argument("--mass-amu", type=float, default=40.0)

    transport = subparsers.add_parser("single-transport")
    transport.add_argument("--distance-um", type=float, required=True)
    transport.add_argument("--speed-m-s", type=float, required=True)
    transport.add_argument("--axial-mhz", type=float, required=True)
    transport.add_argument("--samples", type=int, default=10000)
    transport.add_argument("--output-csv", required=True)

    chain = subparsers.add_parser("chain-transport")
    chain.add_argument("--spacings-um", type=float, nargs="+", required=True)
    chain.add_argument("--move-us", type=float, required=True)
    chain.add_argument("--dwell-us", type=float, required=True)
    chain.add_argument("--axial-mhz", type=float, required=True)
    chain.add_argument("--samples", type=int, default=10000)
    chain.add_argument("--output-csv", required=True)

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    if args.command == "bem-frequency":
        result = radial_secular_frequency_mhz(
            args.panels,
            rf_voltage_v=args.rf_voltage_v,
            drive_frequency_mhz=args.drive_mhz,
            ion_mass_amu=args.mass_amu,
            electrode_name=args.electrode,
        )
        text = json.dumps(result, indent=2, sort_keys=True)
        if args.output_json:
            Path(args.output_json).write_text(text + "\n")
        print(text)
    elif args.command == "ion-spacing":
        values = ion_chain_spacings_um(args.ions, args.axial_mhz, args.mass_amu)
        print(json.dumps(values.tolist()))
    elif args.command == "single-transport":
        time_us, position_um = single_transport_profile(
            distance_um=args.distance_um,
            speed_m_per_s=args.speed_m_s,
            axial_frequency_mhz=args.axial_mhz,
            sample_count=args.samples,
        )
        write_profile_csv(args.output_csv, time_us, position_um)
    elif args.command == "chain-transport":
        time_us, position_um = chain_transport_profile(
            args.spacings_um,
            move_duration_us=args.move_us,
            dwell_duration_us=args.dwell_us,
            axial_frequency_mhz=args.axial_mhz,
            sample_count=args.samples,
        )
        write_profile_csv(args.output_csv, time_us, position_um)


if __name__ == "__main__":
    main()
