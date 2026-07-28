# Units and worked checks

## Constants
- h = 6.62607015e-34 J s, kB = 1.380649e-23 J/K
- gamma = 2.8e-3 GHz/Gauss = 2.8e6 Hz/Gauss (YIG)

## Part A units
- H and 4piM in Gauss (Oe); D in Oe cm^2 with k in cm^-1, so `D k^2` is in Gauss.
- `omega(k,theta)` above is in GHz. f_FMR, f_min in GHz.
- The dipolar form factor F(k) is dimensionless; `k d` uses d in cm.
- Sanity: with H around a few hundred Gauss and 4piM ~ 1.8e3 Gauss, f_FMR is a
  few GHz; the backward-volume minimum sits a few hundred MHz below f_FMR at
  k0 ~ 1e5 cm^-1.

## Part B units
- Bulk magnon energy `eps(k) = h * gamma * (H + D k^2) * 1e9` in Joules
  (the `1e9` converts GHz -> Hz before multiplying by h).
- Number density `n = (1/(2 pi^2)) int_0^inf k^2 nBE dk` with k in cm^-1 gives
  cm^-3 directly (the 3D density of states `d^3k/(2 pi)^3` integrated over solid
  angle gives `k^2/(2 pi^2) dk`).
- Energy density e in J/cm^3.
- Bose factor uses `expm1` for numerical stability: `1/np.expm1(x)`.

## Worked check (arbitrary parameters, not the task values)
For H = 600 Gauss, D = 2e-9, T = 300 K, mu = 0:
- eps(0)/kB = h*gamma*H*1e9/kB should be ~ 81 mK.
- the number integral is dominated by k ~ 1e7 cm^-1 (where eps ~ kB T) and the
  density comes out of order 1e21 cm^-3, following n(T) proportional to T^1.5
  (so the density-vs-temperature exponent is ~1.5, not ~1).

## Supercritical / condensed branch (units)
- With `mu` pinned at `eps_min`, the thermal-cloud integrals `n(T, eps_min)` and
  `e(T, eps_min)` are evaluated exactly as above but at `mu = eps_min` (use
  `mu = eps_min (1 - tiny)` to avoid the k=0 singularity of the Bose factor).
- The condensate density `n_c` (cm^-3) is a number, sitting at energy `eps_min`
  per magnon; it carries energy `n_c eps_min` (J/cm^3).
- Condensate fraction is dimensionless: `n_c / (n(T0,0) + delta_N)`.

Use these to validate your dispersion and integration before computing the task
values. Do NOT hardcode any result; derive everything from the stated inputs.
