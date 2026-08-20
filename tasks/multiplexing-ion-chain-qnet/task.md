---
schema_version: '1.3'
metadata:
  author_name: Bingran You
  author_email: bingran@benchflow.ai
  difficulty: hard
  category: natural-science
  subcategory: trapped-ions
  category_confidence: high
  task_type:
  - calculation
  - simulation
  - optimization
  modality:
  - scientific-data
  - 3d-model
  - csv
  - pdf
  interface:
  - terminal
  - python
  - simulation-tool
  skill_type:
  - domain-procedure
  - mathematical-method
  - library-api-usage
  tags:
  - experiment
  - atomic-molecular-and-optical-physics
  - trapped-ions
  - trap-simulation
  - shuttling-simulation
  - inverse-engineering
verifier:
  type: test-script
  timeout_sec: 600.0
  service: main
  pytest_plugins:
  - ctrf
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 7200.0
sandbox:
  network_mode: public
  build_timeout_sec: 1200.0
  os: linux
  cpus: 4
  memory_mb: 10240
  storage_mb: 20480
  gpus: 0
---

1. Research & Plan

We are using trapped ions as qubits to build quantum networks. We want to have a 100km fiber between 2 trapped ion nodes (one down hill another up hill) with at least 50km distance. The scheme we use is heralded scheme for building remote entanglement between trapped ion qubits.

If we want to have high enough rate of building entanglement, help me to research on what would be the dominant time budge / bottleneck other than loss in fiber. For solving that issue, what would be a good solution if you have a chain of ions in each trapped ion node. What if we can move the ions around. Do deep research and find 3-5 possible schemes that you think are promising, then pick one for us.

In our experiment setup, we use a glass echoed surface trap in each trapped ion node. In each trapped ion 40Ca+ node we can trap 2-10 ions chain. Lasers setup is in free space. Key things to figure out: design the experiment for getting 397nm photons from ions as a POC; how to simulate the trap potential; how to design the shuttling function with as low as possible motional heating; in the future to avoid loss in fiber what is the wavelength we should use and how to achieve that. All these should be discussed in final paper.

2. Experiment & Implementation

`/root/surface_trap.stl` is the trap model. Simulate the radial trap frequency for a charged 40Ca+ ion when an 80 V RF amplitude at 39.15 MHz is applied to the RF (the "2-rail" electrode in the center; treat all other electrodes as ground). Anisotropy parameter `α = (W_axial_freq / W_radial_freq)^2 = 0.00121`.

For a single ion, design the trap-center shuttling function for harmonic transport at 10 m/s over 100 um using the inverse-engineering method, so the ion arrives with essentially zero residual motional excitation.

Extend to a 9-ion chain at same axial confinement. Based on the ion-ion spacings, build the complete shuttling function that walks the chain past our fixed single-ion addressing beam. The first ion starts at the beam. Each move takes 10 us and shifts the chain to the next ion, and after every move the trap dwells for 1 us so we address that ion, 88 us total. Every ion must be addressed cold: below 1 quantum in the chain's center-of-mass mode (effective mass 9m) during each dwell.

DC electrodes sit behind sealed in-vacuum RC filters we cannot change: first-order low-pass, 100 kHz; the trap center follows the filtered control, output starting settled at the first sample. Predict the filter's effect on `2.csv` and report it as `n_com_filtered`: the residual excitation of the chain's center-of-mass mode (9 ions, effective mass 9m) in quanta, measured against the instantaneous filtered trap center at the final sample. Repeat the same prediction for 2 to 20 us moves (1 us steps, 1 us dwells) in `3.csv`. Then design the control we actually program, `4.csv`: after the filter it must still park the trap at each cumulative spacing during every dwell and keep each addressed ion below 1 COM quantum at each dwell's end. Report `attempt_rate_hz`: the maximum attempt rate of one emitter when each attempt waits for the herald over 100 km of total fiber path at 2.0e8 m/s.

Start running the experiment. This multiplexed ion-chain serves as a single photon source and we use 2 PMTs to measure the second order correlation function. The time tagger correlation histograms are in `/root/g2_data`: for each addressed ion i there are `{i}_final_result_left/right/center_ion_data.npy` counts with matching `{i}_index_*.npy`. Our ARTIQ records, including the Rabi flops, are under `/root/artiq_results`. Make plots in the final paper for g2(n), and save g2(0). Each time we open 1.7 µs pulse time and you can try different time filtering (no smaller than 16ns, pick the one with lowest g2(0)). Also we run rabi flop for 9 ions chain to measure motional state excitation after shuttling. Write down n_excitation.

3. Deliverables

- `/root/paper.pdf`: the paper draft for you to wrap up this research project and send out for peer review. Components: abstract; introduction; methods; results; discussion; references. Coherent research story. Follow PR Applied style.
- `/root/result.md`: key-value lines, frequencies in MHz, distances in um, rate in Hz (at least 3 decimal places), g2(0), n_excitation. Template: `/root/result_template.md`.

- `/root/1.csv` (the single-ion move, 0 to 10 us), `/root/2.csv` (the ideal 9-ion sequence, 0 to 88 us), and `/root/4.csv` (the compensated control to program, same span and grid as `2.csv`): a `time_us,position_um` header plus exactly 10,000 uniformly spaced samples including both endpoints, written with at least 4 decimal places; the second column is the trap-center (for `4.csv`: control) position along the axial direction.
- `/root/3.csv`: a `move_us,quanta` header plus 19 rows for move durations 2, 3, ..., 20 us, at least 4 decimal places.

