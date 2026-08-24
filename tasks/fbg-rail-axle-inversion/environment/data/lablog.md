# commissioning log of FBG axle-counting array

Site: single-track block section, one rail instrumented.
Instrument: 4 dual-grating FBG strain sensor units clamped to the rail foot.
Interrogator: 1000 Hz sampling, 0.1 pm wavelength quantization, noise ~3 pm rms per grating.

## 1. installation

Each sensor unit carries two gratings bonded to opposite faces of one bending substrate (center wavelengths 1530 nm and 1535 nm). Nominal sensitivities from the unit datasheet: strain ~1.0 pm/ue, temperature ~10 pm/degC per grating. Units bonded and zero-referenced at 20 degC.

Positions measured from the entry-side boundary along the instrumented rail:

| unit | x (m) | role |
|---|---|---|
| S1 | 0.0 | counting point A; section boundary; reference sensor |
| S2 | 3.0 | counting point A |
| S3 | 1000.0 | counting point B |
| S4 | 1003.0 | counting point B; section boundary |

Section boundaries: x = 0.0 m (S1) and x = 1003.0 m (S4).

Track: CN60 rail (60 kg/m), E = 215 GPa, section moment of inertia I = 3.217e-5 m^4, section centroid 80.9 mm above the rail base. Sleeper spacing 0.54 m. Ballast support is Winkler-like; on this line k is typically 40e6 to 90e6 N/m^2 and varies from sensor to sensor — do not assume one
shared value.

## 2. commissioning recording

Recording starts at t = 0 s and runs 1500 s (~25 min) of mixed traffic, written per unit to `sensors/S1.csv.gz` .. `sensors/S4.csv.gz`, columns
`t_s,wl1_nm,wl2_nm` (time and the two grating wavelengths).
Calibration: the track-inspection car (4 axles) ran through the section twice. Its per-axle static loads are from the weigh certificate, copied to
`calibration.csv` (`axle_index,load_kN`). Average over both passes when calibrating.

| pass | direction | speed (m/s) | entered section (approx) |
|---|---|---|---|
| 1 | A to B | 22.0 | t ~ 1300 s |
| 2 | B to A | 22.0 | t ~ 1400 s |
