---
name: ion-shuttling-mentor
description: "End-to-end mentor recipe for the surface-ion-trap shuttling task: run the bundled BEM helper, derive axial confinement, solve nine-ion equilibrium, and generate both inverse-engineered CSV waveforms. Use when producing result.md, 1.csv, and 2.csv for this task."
---

# Surface-ion-trap shuttling mentor recipe

Follow this order and keep full precision until writing the final artifacts.

## 1. Radial frequency

Read and execute the sibling `surface-ion-trap-bem` skill. Save its
`radial_parallel_mhz` value.

## 2. Axial frequency

Use the prompt's anisotropy definition directly:

\[
f_z=f_r\sqrt{0.00174}.
\]

The frequency values remain in MHz because the ratio is dimensionless.

## 3. Nine-ion equilibrium

Locate the BEM helper skill and reuse its parameterized numerical tool:

```bash
BEM_SKILL="$(find -L /home/agent /root \
  -path '*/surface-ion-trap-bem/SKILL.md' -print -quit 2>/dev/null \
  | xargs dirname)"
PY=/tmp/iontrap-venv/bin/python

"$PY" "$BEM_SKILL/scripts/ion_trap_tools.py" \
  ion-spacing --ions 9 --axial-mhz <AXIAL_MHZ> --mass-amu 40 \
  > /tmp/spacings.json
```

The JSON array contains the eight ordered adjacent spacings in micrometers.
They must be positive and mirror-symmetric. Read the sibling
`ion-chain-equilibrium` skill if you need to inspect the force-balance model.

## 4. Single-ion waveform

Generate exactly 10,000 samples for 100 um at 10 m/s. The duration is 10 us:

```bash
"$PY" "$BEM_SKILL/scripts/ion_trap_tools.py" \
  single-transport \
  --distance-um 100 \
  --speed-m-s 10 \
  --axial-mhz <AXIAL_MHZ> \
  --samples 10000 \
  --output-csv /root/1.csv
```

## 5. Nine-ion chain waveform

Pass the eight spacing values, in order, to:

```bash
"$PY" "$BEM_SKILL/scripts/ion_trap_tools.py" \
  chain-transport \
  --spacings-um <D1> <D2> <D3> <D4> <D5> <D6> <D7> <D8> \
  --move-us 10 \
  --dwell-us 1 \
  --axial-mhz <AXIAL_MHZ> \
  --samples 10000 \
  --output-csv /root/2.csv
```

The global time grid spans eight 10 us moves and eight 1 us dwells, for 88 us
total. The final position equals the sum of all eight spacings.

## 6. Result file

Write `/root/result.md` with exactly the requested keys and numeric values:

```text
W_radial_freq: ...
W_axial_freq: ...
d1: ...
...
d8: ...
```

Do not paste values from a reference answer. All numbers must come from the
computations above.

## Final checks

- Both CSV files have one header plus 10,000 data rows.
- Time is in us and position is in um.
- `1.csv` ends at 100 um.
- `2.csv` ends at the sum of `d1` through `d8`.
- Do not clip inverse-engineering overshoot.
