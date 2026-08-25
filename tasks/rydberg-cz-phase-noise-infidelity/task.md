---
schema_version: '1.3'
metadata:
  author_name: Jinen Guo
  author_email: timothyjeguo@gmail.com
  difficulty: hard
  difficulty_explanation: Requires reconciling two independent phase-noise/frequency-noise measurements under conventions that differ between papers by factors of two, propagating the frequency-doubling factor of four, and recognizing that the measured PSD never rolls off inside the measurement band, so the textbook 1/Omega^2 infidelity scaling does not apply.
  category: natural-science
  subcategory: atomic-molecular-and-optical-physics
  category_confidence: high
  task_type:
  - analysis
  - calculation
  - simulation
  modality:
  - scientific-data
  - csv
  - pdf
  interface:
  - terminal
  - python
  skill_type:
  - domain-procedure
  - mathematical-method
  tags:
  - experiment
  - atomic-molecular-and-optical-physics
  - neutral-atom-quantum-computing
  - rydberg-gates
  - laser-phase-noise
  - spectral-analysis
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
  build_timeout_sec: 900.0
  os: linux
  cpus: 2
  memory_mb: 4096
  storage_mb: 10240
  gpus: 0
---

1. Research & Plan

We would like to use single rubidium atoms trapped in an array of optical tweezers to realize quantum computing, using Rydberg interactions to implement two-qubit gates. 

Around the start of this project, a particular family of Rydberg-mediated two qubit gate protocol, the so-called "time-optimal" gates, have been proposed and implemented experimentally that surpasses 99.5% fidelity.

For building a new rubidium Rydberg atom array experimental platform, you should first measure the laser phase noise of our 840-nm laser. And then, use the phase noise data to figure out how much the laser phase noise from 840-nm laser limits the two-qubit gate fidelity if we use the SOTA time-optimal two-qubit gate protocol, as a function of excitation Rabi frequency.

Do literature research to 1) determine how to derive laser phase noise spectrum from the beat note signal (note that there can easily be factor-of-2 errors at different places) and from PDH laser locking error signal spectrum; 2) determine the current research landscape of SOTA two-qubit Rydberg gate. 3) determine how to simulate two-qubit gate infidelity with a given phase noise spectrum.

2. Experiment & Implementation

Answer what the limited two-qubit gate fidelity is as a function of Rydberg Rabi frequency (1-10 MHz).

In experiment, your colleague have measured some beat note data using this laser. One of the beams is the locked laser itself shifted by 80 MHz (using an AOM), the other beam is the cavity filtered light (the cavity transmission light from the same laser, serving as a stable reference). Additionally, your colleague also measured the PDH in-loop error signal's power spectrum on a spectrum analyzer. You have four traces from spectrum-analyzer exports. For each file, the first column is frequency in Hz and the second is amplitude in dBm integrated over the resolution bandwidth.

1) PDH_2025_2.csv is the data downloaded from a spectrum analyzer with the signal input being the PDH in-loop error signal. The RBW is 1kHz, overall impedance of the system is 50 ohm, FWHM of the PDH cavity line is 68 kHz, and the slope of the error signal on an infinite-impedance oscilloscope is (1500 mV) / (34 kHz). The BG_3.csv is the background spectrum analyzer data with the same parameter, but without any input signal.

2) beat_3.csv is the data downloaded from the same spectrum analyzer with the signal input being the photodiode output of the beat note (as described above). RBW is 1kHz. BG_80MHz_3.csv is the background spectrum analyzer data with the same parameter, but without any input signal.

Parameters:
resolution bandwidth: 1 kHz
system impedance: 50 ohm
For the PDH data: the cavity line FWHM is 68 kHz, and the error-signal slope measured on an infinite-impedance oscilloscope is 1500 mV per 34 kHz.

3. Deliverables

`/root/paper.pdf`:
The write-up (consistent with standards of a PhD thesis chapter) that makes the number above defensible: a written account of the measurement, of the standard you would send to a colleague for comment or include as a chapter section of a thesis — an introduction to the problem, methods, results, discussion, and references. It must be a vector PDF. Reporting the Rydberg laser phase noise spectrum plot and the gate fidelity plot and literature research.

The methods section state, explicitly enough that a reader can reproduce your arithmetic, the phase-noise convention you adopted, how you converted each raw trace to a frequency-noise spectrum, and every assumption behind the infidelity number you quote.

The results section include two figures. The first figure is the noise spectrum PSD derived from the data. This figure should have two panels: one plotting phase noise, one plotting frequency noise, each carrying two curves, one derived from the PDH error signal and one from the beat note, so the two methods can be compared directly. The second figure should plot the simulated Rydberg two-qubit gate infidelity as a function of Rabi frequency from 1 to 10 MHz.

`/root/gate_infidelity.csv`:
This is the result the project exists to produce: the 840-nm-laser-phase-noise-limited Rydberg two-qubit gate infidelity as a function of Rabi frequency.

Should have two columns with no column headers: The first column should be the Rabi frequency (Omega/2pi) in MHz. This column should sample 200 points from 1 to 10 MHz (inclusive) with equal distance. The second column is the corresponding gate infidelity at that Rabi frequency. The fidelity metric is the fidelity averaged over two-qubit-symmetric Haar-random input states — symmetric under exchange of the two qubits.
