---
name: surface-ion-trap-bem
description: Compute the in-plane radial secular frequency for the supplied surface Paul-trap geometry using the bundled FastLap boundary-element helper and provenance-pinned panel mesh. Use for the fragile electrostatics stage of the surface-ion-trap shuttling task.
---

# Surface ion-trap boundary-element calculation

Use the bundled helper instead of estimating the frequency from electrode
widths. The helper performs a constant-panel FastLap solve, evaluates the RF
field near the null, constructs the ponderomotive pseudopotential, and fits its
local radial curvature.

## Run the helper

Locate this skill across the supported harness paths:

```bash
BEM_SKILL="$(find -L /home/agent /root \
  -path '*/surface-ion-trap-bem/SKILL.md' -print -quit 2>/dev/null \
  | xargs dirname)"
test -n "$BEM_SKILL"
```

Build the bundled solver in an isolated environment:

```bash
python3 -m venv --system-site-packages /tmp/iontrap-venv
BEM_BUILD="$(mktemp -d)/bem_fastlap"
cp -R "$BEM_SKILL/scripts/bem_fastlap" "$BEM_BUILD"
/tmp/iontrap-venv/bin/python -m pip install \
  --no-deps --no-build-isolation \
  "$BEM_BUILD"
```

Copy before building because injected skill directories are read-only and
Cython generates a C file next to the `.pyx` source.

Compute the radial frequency:

```bash
/tmp/iontrap-venv/bin/python "$BEM_SKILL/scripts/ion_trap_tools.py" \
  bem-frequency \
  --panels "$BEM_SKILL/assets/surface_trap_panels.npz" \
  --rf-voltage-v 80 \
  --drive-mhz 39.15 \
  --mass-amu 40 \
  --electrode RF \
  --output-json /tmp/bem.json
```

Use `radial_parallel_mhz` from `/tmp/bem.json`. The prompt requests the
in-plane direction perpendicular to the RF rails, not the vertical radial
frequency or the larger principal-axis frequency.

The panel mesh is derived from `/root/surface_trap.stl`; its source commit,
hashes, units, electrode label, and fit-grid location are recorded in
`assets/model_provenance.json`. Read
[references/method.md](references/method.md) to audit the equations and
geometry selection.

## Checks

- The RF null must be interior to the sampled grid.
- Use 80 V as RF amplitude, not peak-to-peak voltage.
- Convert V/mm to V/m before applying SI pseudopotential formulas.
- Report MHz, not angular frequency.
