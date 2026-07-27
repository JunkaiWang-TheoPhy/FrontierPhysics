---
schema_version: '1.3'
metadata:
  author_name: Wenjun Ke
  author_email: wenjunke@caltech.edu
  difficulty: hard
  category: natural-science
  subcategory: quantum-optics
  category_confidence: high
  task_type:
  - analysis
  - calculation
  - implementation
  - verification
  modality:
  - scientific-data
  - time-series
  - csv
  - json
  - source-code
  interface:
  - terminal
  - python
  skill_type:
  - domain-procedure
  - mathematical-method
  - evaluation-protocol
  tags:
  - atomic-molecular-and-optical-physics
  - quantum-optics
  - shot-noise
  - lock-in-demodulation
  - state-readout-fidelity
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
environment:
  network_mode: no-network
  build_timeout_sec: 1200.0
  os: linux
  cpus: 4
  memory_mb: 8192
  storage_mb: 16384
  gpus: 0
---

Analyze balanced-heterodyne data. First do a shot noise analysis, then try to distinguish a weak coherent state from a vacuum state using balanced heterodyne detection traces. The data are caputured from a Thorlabs PDB210A (RF output on `CHAN1`, LO monitors on `CHAN2`/`CHAN3`) read on a RIGOL DS1104 (note that the oscilloscope and the photodetector are not synchronized, so there's a constant phase drift over time). The PDB210A manual is at `/root/input/ThorlabsPDB210A.pdf`. Throughout use RF gain `G = 257.988e3 V/W`, `f_IQ = 500 kHz`, sample rate `f_s = 50 MHz`, and wavelength `795 nm`. Find other necessary parameters in the Thorlabs PDB210A manual. The CSVs are large; load them from code, not file-read tools. IQ-demodulation convention: `I = integral over sin`, `Q = integral over cos`, integrated over one beat period, no normalization (units volt·second).

# Part A — shot-noise characterization

Inputs are in `/root/input/shot_noise/`. `heterodyne_data/vac_{1..9}_CHAN{1,2,3}.csv` are vacuum (LO-only) records at increasing LO power. `spectrum/vac_100uW_spectrum.csv` is an Anritsu spectrum-analyzer trace (dBm, RBW 300 Hz, 50 Ω load) with its scope companion `spectrum/vac_100uW_CHAN{1,2,3}.csv`.

Write:

- `/root/IQ_demodulation.csv`: columns exactly `LO power (µW)`, `Variance (V^2*s^2)`, one row per heterodyne record (the demodulated-IQ-cloud variance vs LO power).
- `/root/theo_var.csv`: same columns, the theoretical shot-noise variance at 101 points from 0 to 400 µW.
- `/root/spectrum_analyzer.csv`: columns exactly `Frequency (MHz)`, `Vrms (Volt)`, converting the dBm trace to Vrms for a 50 Ω load.
- `/root/theoretical_Vrms.txt`: a single number, the spectrum run's theoretical shot-noise amplitude density in `V/sqrt(Hz)`, using the manual's transimpedance and responsivity and excluding the 300 Hz RBW.

# Part B — vacuum vs weak-coherent-state discrimination

Inputs are in `/root/input/discrimination/heterodyne_data/`: `vac_2_*` (vacuum) and `sig_2_*` (a very weak coherent state). Extract the following:
1. LO powers. 
2. The signal power (pW) and photon rate (photon/µs) of the weak coherent state from the beat note.
3. The one-period IQ points.
4. The linear phase-drift correction that collapses the signal ring to a disc. 
5. The discrimination threshold and measured error rate.
6. The power-based and IQ-geometry-based photon numbers of the weak coherent state (these must reconcile)
7. The measured vs theoretical shot-noise std and error rate; and the percentage of shot-noise out of the total noise.  

Write `/root/results.json` as one JSON object with exactly these numeric fields (powers in the units named in the keys; I/Q in volt·second):

```json
{
  "lo_power_uw": {"lo1_vacuum": 0.0, "lo2_vacuum": 0.0, "lo1_signal": 0.0, "lo2_signal": 0.0},
  "signal_power_pw": 0.0,
  "photon_rate_per_us": 0.0,
  "photons_per_window": 0.0,
  "photon_number_from_statistics": 0.0,
  "phase_drift_rate_rad_per_s": 0.0,
  "displacement": 0.0,
  "discrimination_threshold": 0.0,
  "measured_error_rate": 0.0,
  "signal_errors": 0,
  "vacuum_errors": 0,
  "total_events": 0,
  "measured_std": 0.0,
  "theoretical_std": 0.0,
  "measured_over_theoretical_std": 0.0,
  "theoretical_error_rate": 0.0,
  "measured_over_theoretical_error_rate": 0.0,
  "simulated_shot_noise_std": 0.0,
  "shot_noise_fraction": 0.0
}
```

Also write `/root/iq_points.csv` with header `dataset,I,Q,I_corrected,Q_corrected`, one row per demodulation window; `dataset` is `vacuum` or `signal`; for vacuum rows repeat the raw I/Q in the corrected columns. Preserve full numerical precision in both files.
