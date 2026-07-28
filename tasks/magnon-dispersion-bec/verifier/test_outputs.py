"""Outcome checks for the YIG magnon dispersion + pumped-magnon-gas task.

The verifier independently recomputes the reference physics (Rezende film
dispersion; 3D bulk magnon-gas thermodynamics, including the pumped sub-critical
and supercritical/condensed branches) and compares the agent's reported values
against it, with tolerances that accommodate reasonable numerical implementations
(quadrature, root finding).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, "/verifier")
import magnon_physics as mp

ROOT = Path("/root")
RESULT_MD = ROOT / "result.md"
LOG = Path("/logs/verifier")

_KEYS = (
    # Part A
    "fourpiM_G", "D_Oecm2", "k_min_percm", "f_DE_GHz", "fmin2_GHz", "kmin2_percm",
    # Part B config 1 (sub-critical)
    "eps_min_mK", "n0_percm3", "e0_Jpercm3", "p_bloch", "dN_c_percm3", "mu_p_mK", "T_p_K", "bec",
    # Part B config 2 (supercritical / condensed)
    "eps_min2_mK", "dN_c2_percm3", "bec2", "ncfrac2", "T_p2_K",
    # Part B config 3 (A->B interlock)
    "n0_3_percm3", "dN_c3_percm3", "bec3",
)


def _parse():
    assert RESULT_MD.is_file(), f"missing deliverable: {RESULT_MD}"
    m = re.search(r"RESULT\s*(.*?)\s*END", RESULT_MD.read_text(), re.DOTALL)
    assert m, "result.md must contain a 'RESULT ... END' block"
    body, vals = m.group(1), {}
    for k in _KEYS:
        km = re.search(rf"^\s*{re.escape(k)}\s*=\s*([-+0-9.eE]+)\s*$", body, re.MULTILINE)
        assert km, f"RESULT block missing key: {k}"
        vals[k] = float(km.group(1))
    return vals


@pytest.fixture(scope="session")
def sub():
    vals = _parse()
    A = mp.part_A()
    B = mp.part_B(D_from_A=A["D_Oecm2"])
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "reference.json").write_text(str({"A": A, "B": B}))
    return {"vals": vals, "A": A, "B": B}


def test_partA_material_parameters(sub):
    v, A = sub["vals"], sub["A"]
    assert np.isclose(v["fourpiM_G"], A["fourpiM_G"], rtol=0.01), f"4piM {v['fourpiM_G']:.1f} != {A['fourpiM_G']:.1f} G (Kittel from f_FMR)"
    assert np.isclose(v["D_Oecm2"], A["D_Oecm2"], rtol=0.04), (
        f"exchange stiffness D {v['D_Oecm2']:.3e} != {A['D_Oecm2']:.3e} (must reproduce f_min via the dipole-exchange film dispersion)"
    )
    assert np.isclose(v["k_min_percm"], A["k_min_percm"], rtol=0.06), (
        f"spectral-minimum wavevector k_min {v['k_min_percm']:.3e} != {A['k_min_percm']:.3e}"
    )


def test_partA_surface_branch_and_second_film(sub):
    v, A = sub["vals"], sub["A"]
    assert np.isclose(v["f_DE_GHz"], A["f_DE_GHz"], rtol=0.02), (
        f"surface-branch frequency f_DE {v['f_DE_GHz']:.4f} != {A['f_DE_GHz']:.4f} GHz "
        f"(theta=pi/2 branch requires the full dipolar form factor)"
    )
    assert np.isclose(v["fmin2_GHz"], A["fmin2_GHz"], rtol=0.02), (
        f"second-film spectral minimum {v['fmin2_GHz']:.4f} != {A['fmin2_GHz']:.4f} GHz "
        f"(same material, thickness 0.5 um)"
    )
    assert np.isclose(v["kmin2_percm"], A["kmin2_percm"], rtol=0.06), (
        f"second-film minimum wavevector {v['kmin2_percm']:.3e} != {A['kmin2_percm']:.3e} cm^-1"
    )


def test_partB_thermal_gas(sub):
    v, B = sub["vals"], sub["B"]
    assert np.isclose(v["eps_min_mK"], B["eps_min_mK"], rtol=0.02), f"spectral gap eps_min/kB {v['eps_min_mK']:.1f} != {B['eps_min_mK']:.1f} mK"
    assert np.isclose(v["n0_percm3"], B["n0_percm3"], rtol=0.05), (
        f"thermal magnon density n0 {v['n0_percm3']:.3e} != {B['n0_percm3']:.3e} cm^-3 (3D bulk exchange magnon gas, Bloch T^3/2)"
    )
    assert np.isclose(v["e0_Jpercm3"], B["e0_Jpercm3"], rtol=0.05), (
        f"thermal energy density e0 {v['e0_Jpercm3']:.3e} != {B['e0_Jpercm3']:.3e} J/cm^3"
    )
    assert np.isclose(v["p_bloch"], B["p_bloch"], atol=0.08), (
        f"Bloch exponent p {v['p_bloch']:.3f} != {B['p_bloch']:.3f} "
        f"(gapless 3D exchange gas gives ~1.5; a 2D film would give ~1)"
    )


def test_partB_bec_threshold(sub):
    v, B = sub["vals"], sub["B"]
    assert int(v["bec"]) == int(B["bec"]), (
        f"BEC determination {int(v['bec'])} != {int(B['bec'])} (delta_N = 5e18 cm^-3 vs the critical pumped density)"
    )
    assert np.isclose(v["dN_c_percm3"], B["dN_c_percm3"], rtol=0.30), (
        f"critical pumped density dN_c {v['dN_c_percm3']:.3e} != {B['dN_c_percm3']:.3e} cm^-3"
    )


def test_partB_pumped_state(sub):
    v, B = sub["vals"], sub["B"]
    assert np.isclose(v["mu_p_mK"], B["mu_p_mK"], rtol=0.30, atol=4.0), (
        f"pumped chemical potential mu/kB {v['mu_p_mK']:.2f} != {B['mu_p_mK']:.2f} mK"
    )
    assert np.isclose(v["T_p_K"], B["T_p_K"], atol=3.0), f"pumped-gas temperature {v['T_p_K']:.1f} != {B['T_p_K']:.1f} K"


def test_partB_supercritical_condensate(sub):
    v, B = sub["vals"], sub["B"]
    assert np.isclose(v["eps_min2_mK"], B["eps_min2_mK"], rtol=0.02), (
        f"config-2 spectral gap {v['eps_min2_mK']:.1f} != {B['eps_min2_mK']:.1f} mK"
    )
    assert np.isclose(v["dN_c2_percm3"], B["dN_c2_percm3"], rtol=0.30), (
        f"config-2 critical density dN_c2 {v['dN_c2_percm3']:.3e} != {B['dN_c2_percm3']:.3e} cm^-3"
    )
    assert int(v["bec2"]) == int(B["bec2"]), (
        f"config-2 BEC determination {int(v['bec2'])} != {int(B['bec2'])} (delta_N2 = 1.5e20 cm^-3 is supercritical)"
    )
    assert np.isclose(v["ncfrac2"], B["ncfrac2"], rtol=0.25, atol=0.005), (
        f"config-2 condensate fraction {v['ncfrac2']:.4f} != {B['ncfrac2']:.4f} "
        f"(requires the condensed-branch solve with mu pinned at eps_min)"
    )
    assert np.isclose(v["T_p2_K"], B["T_p2_K"], atol=5.0), (
        f"config-2 pumped-gas temperature {v['T_p2_K']:.1f} != {B['T_p2_K']:.1f} K"
    )


def test_partB_interlocked_config(sub):
    v, B = sub["vals"], sub["B"]
    assert np.isclose(v["n0_3_percm3"], B["n0_3_percm3"], rtol=0.06), (
        f"config-3 thermal density {v['n0_3_percm3']:.3e} != {B['n0_3_percm3']:.3e} cm^-3 "
        f"(uses the exchange stiffness D extracted in Part A)"
    )
    assert np.isclose(v["dN_c3_percm3"], B["dN_c3_percm3"], rtol=0.30), (
        f"config-3 critical density {v['dN_c3_percm3']:.3e} != {B['dN_c3_percm3']:.3e} cm^-3"
    )
    assert int(v["bec3"]) == int(B["bec3"]), (
        f"config-3 BEC determination {int(v['bec3'])} != {int(B['bec3'])}"
    )
