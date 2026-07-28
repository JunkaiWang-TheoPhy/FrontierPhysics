#!/usr/bin/env python3
"""Oracle for the YIG magnon dispersion + pumped-magnon-gas task."""

from __future__ import annotations

import json
from pathlib import Path

import magnon_physics as mp

ROOT = Path("/root")


def main():
    A = mp.part_A()
    B = mp.part_B(D_from_A=A["D_Oecm2"])
    ROOT.mkdir(parents=True, exist_ok=True)

    md = f"""# YIG magnon dispersion and pumped magnon gas

## Part A -- NV3 dipole-exchange dispersion, material parameters, surface branch, second film
## Part B -- pumped magnon-gas thermodynamics (three systems)

```
RESULT
fourpiM_G = {A["fourpiM_G"]:.6g}
D_Oecm2 = {A["D_Oecm2"]:.6g}
k_min_percm = {A["k_min_percm"]:.6g}
f_DE_GHz = {A["f_DE_GHz"]:.6g}
fmin2_GHz = {A["fmin2_GHz"]:.6g}
kmin2_percm = {A["kmin2_percm"]:.6g}
eps_min_mK = {B["eps_min_mK"]:.6g}
n0_percm3 = {B["n0_percm3"]:.6g}
e0_Jpercm3 = {B["e0_Jpercm3"]:.6g}
p_bloch = {B["p_bloch"]:.6g}
dN_c_percm3 = {B["dN_c_percm3"]:.6g}
mu_p_mK = {B["mu_p_mK"]:.6g}
T_p_K = {B["T_p_K"]:.6g}
bec = {int(B["bec"])}
eps_min2_mK = {B["eps_min2_mK"]:.6g}
dN_c2_percm3 = {B["dN_c2_percm3"]:.6g}
bec2 = {int(B["bec2"])}
ncfrac2 = {B["ncfrac2"]:.6g}
T_p2_K = {B["T_p2_K"]:.6g}
n0_3_percm3 = {B["n0_3_percm3"]:.6g}
dN_c3_percm3 = {B["dN_c3_percm3"]:.6g}
bec3 = {int(B["bec3"])}
END
```

Part A: extracted 4piM = {A["fourpiM_G"]:.1f} G, D = {A["D_Oecm2"]:.3e} Oe cm^2
(spectral minimum {A["f_min_GHz"]:.4f} GHz at k = {A["k_min_percm"]:.3e} cm^-1);
surface branch {A["f_DE_GHz"]:.4f} GHz; second film minimum {A["fmin2_GHz"]:.4f} GHz
at k = {A["kmin2_percm"]:.3e} cm^-1.
Part B: thermal magnon density {B["n0_percm3"]:.3e} cm^-3 (Bloch exponent
{B["p_bloch"]:.3f}); config-1 pumped gas reaches mu/kB = {B["mu_p_mK"]:.2f} mK at
T = {B["T_p_K"]:.1f} K (sub-critical, dN_c = {B["dN_c_percm3"]:.3e} cm^-3).
Config-2 supercritically pumped gas condenses (dN_c2 = {B["dN_c2_percm3"]:.3e}
cm^-3, condensate fraction {B["ncfrac2"]:.3f}). Config-3 (D from Part A) has
n0 = {B["n0_3_percm3"]:.3e} cm^-3, dN_c3 = {B["dN_c3_percm3"]:.3e} cm^-3.
"""
    (ROOT / "result.md").write_text(md)
    (ROOT / "oracle_diagnostics.json").write_text(json.dumps({"A": A, "B": B}, indent=2, sort_keys=True))
    print("oracle:", json.dumps({"A": A, "B": B}, indent=2))


if __name__ == "__main__":
    main()
