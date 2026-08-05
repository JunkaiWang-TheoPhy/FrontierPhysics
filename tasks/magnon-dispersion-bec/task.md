---
schema_version: '1.3'
metadata:
  author_name: Wenjun Ke
  author_email: wenjunke@caltech.edu
  difficulty: hard
  difficulty_explanation: Requires coupled dipole-exchange parameter extraction, forward dispersion predictions, and number- and energy-conserving thermodynamics for subcritical and condensed magnon gases.
  category: natural-science
  subcategory: magnonics
  category_confidence: high
  task_type:
  - calculation
  - analysis
  modality:
  - document
  interface:
  - terminal
  - python
  skill_type:
  - domain-procedure
  - mathematical-method
  tags:
  - magnonics
  - spin-waves
  - yttrium-iron-garnet
  - dispersion-relation
  - magnon-bose-einstein-condensation
  - condensed-matter
verifier:
  type: test-script
  timeout_sec: 900.0
  service: main
  pytest_plugins:
  - ctrf
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 3600.0
sandbox:
  network_mode: public
  build_timeout_sec: 900.0
  os: linux
  cpus: 2
  memory_mb: 4096
  storage_mb: 10240
  gpus: 0
---

Use the standard in-plane YIG-film spin-wave model and the 3D
exchange-dominated magnon-gas model. Take
`gamma = 2.8e-3 GHz/Gauss`; use SI values for `h` and `kB`.

For film 1, use `H = 330` Gauss, `f_FMR = 2.395` GHz,
`f_min = 1.913` GHz, and `d = 0.206` micrometre to find `4piM` (Gauss),
`D` (Oe cm^2), and `k_min` (cm^-1). With those same material parameters,
find `f_DE` (GHz) for the perpendicular-to-magnetization branch at
`k_s = 8e4` cm^-1, and the minimum frequency `fmin2` (GHz) and wavevector
`kmin2` (cm^-1) of a same-material film with `d2 = 0.5` micrometre.

At `T0 = 300` K, calculate the following pumped-gas cases. Treat pumping as
rapid thermalization that conserves magnon number and total energy.

- System 1: `H = 700` Gauss, `D = 2e-9` Oe cm^2,
  `delta_N = 5e18` cm^-3 at `nu_p = 4` GHz. Report the equilibrium
  `n0` (cm^-3), `e0` (J/cm^3), `eps_min/kB` (mK), density exponent
  `p_bloch` measured between `T0` and `2*T0`, pumped `mu_p/kB` (mK),
  `T_p` (K), critical `dN_c` (cm^-3), and `bec` (1 or 0).
- System 2: `H = 500` Gauss, `D = 2e-9` Oe cm^2,
  `delta_N2 = 1.5e20` cm^-3 at `nu_p = 4` GHz. Report
  `eps_min2/kB` (mK), `dN_c2` (cm^-3), `bec2`, condensate fraction
  `ncfrac2`, and `T_p2` (K). If it does not condense, use `ncfrac2 = 0`
  and report its pumped-gas temperature.
- System 3: `H = 400` Gauss, `D` equal to the value extracted for film 1,
  and `delta_N3 = 2e18` cm^-3. Report `n0_3` (cm^-3), `dN_c3` (cm^-3),
  and `bec3` (1 or 0).

Write `/root/result.md` with a fenced block in exactly this format
(numbers only; use the stated units):

```
RESULT
fourpiM_G = <4piM, Gauss>
D_Oecm2 = <exchange stiffness, Oe cm^2>
k_min_percm = <film-1 spectral-minimum wavevector, cm^-1>
f_DE_GHz = <film-1 surface-branch frequency at k_s, GHz>
fmin2_GHz = <film-2 spectral-minimum frequency, GHz>
kmin2_percm = <film-2 spectral-minimum wavevector, cm^-1>
eps_min_mK = <system-1 spectral gap eps_min/kB, mK>
n0_percm3 = <system-1 thermal magnon density, cm^-3>
e0_Jpercm3 = <system-1 thermal energy density, J/cm^3>
p_bloch = <system-1 density-vs-temperature exponent>
dN_c_percm3 = <system-1 critical pumped density for BEC, cm^-3>
mu_p_mK = <system-1 pumped chemical potential mu_p/kB, mK>
T_p_K = <system-1 pumped-gas temperature, K>
bec = <1 if system-1 delta_N >= dN_c else 0>
eps_min2_mK = <system-2 spectral gap eps_min2/kB, mK>
dN_c2_percm3 = <system-2 critical pumped density, cm^-3>
bec2 = <1 if system-2 condenses else 0>
ncfrac2 = <system-2 condensate fraction>
T_p2_K = <system-2 pumped-gas temperature, K>
n0_3_percm3 = <system-3 thermal magnon density, cm^-3>
dN_c3_percm3 = <system-3 critical pumped density, cm^-3>
bec3 = <1 if system-3 condenses else 0>
END
```
