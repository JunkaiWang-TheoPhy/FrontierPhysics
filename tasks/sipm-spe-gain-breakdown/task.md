---
schema_version: '1.3'
metadata:
  author_name: Yue Ma
  author_email: yuema9810@gmail.com
  difficulty: hard
  category: natural-science
  subcategory: particle-detectors
  category_confidence: high
  task_type:
  - analysis
  - calculation
  - extraction
  modality:
  - scientific-data
  - binary
  - csv
  interface:
  - terminal
  - python
  skill_type:
  - domain-procedure
  - file-format-knowledge
  - mathematical-method
  tags:
  - experiment
  - instrumentation
  - silicon-photomultiplier
  - photodetector-calibration
  - waveform-analysis
  - daq
verifier:
  type: test-script
  timeout_sec: 1800.0
  service: main
  pytest_plugins:
  - ctrf
  hardening:
    cleanup_conftests: true
agent:
  timeout_sec: 7200.0
sandbox:
  network_mode: public
  build_timeout_sec: 1800.0
  os: linux
  cpus: 4
  memory_mb: 4096
  storage_mb: 8192
  gpus: 0
---

1. Research & Plan

We ran a batch of SiPM tests in a cryogenic system to calibrate them, but never finished the full set of data processing and analysis. I would like you to take the data from the raw DAQ files and finish the calibration. The final goal is to determine the temperature dependence of the breakdown voltage.

Review related literatures and references. For external resources, you can consult manufacturer and scientific documentation as needed, and justify the checks used to establish that the calibration is reliable.

2. Experiment & Implementation

Data and relevant information are in the workspace: `/root/data/` holds the raw digitizer output from several cooldowns, `/root/RUN_LOG.md` is the run log, and the `temp_record_*.csv` files are the cryostat logs. Read the log first, as it tells you what the readout was and which channel is the SiPM under test. The data came from a CAEN DT5720 digitizer.

You should figure out which cooldowns carry enough distinct bias voltages to support an independent calibration, and calibrate only those. For each cooldown, identify and use the resolved populations in the charge spectrum to measure the gain, then use the gain to analyze the breakdown voltage.

That charge separation is the quantity to be reported, which is the distance between the two populations in the integrated-charge spectrum, in **ADC counts x ns**. The analog chain was never calibrated, so do not convert it to charge or an electron gain. Resolving the two populations is your task to figure out.

3. Deliverables

The final outputs should be the machine-readable results described below. Also, you must include a reproducible analysis pipeline. Produce the following in `/root`. **`/root/output_schema.md` gives the exact columns and definitions for every file — follow it.**

- `result.md`: the temperature coefficient (mV/K) and the corresponding uncertainty.
- `campaigns.csv`: one row per test (cooldown) campaign.
- `gain_vs_voltage.csv`: one row per bias point, per test campaign.
- `spe_fits.csv`: the per-setting numbers behind that table.
- `decode_check.csv`: a decode cross-check on one named file.
- `average_waveform.csv`: an averaged waveform for one named setting.
- `paper.pdf`: the write-up, as a PDF: how you read the files and what in the documentation told you the layout; what you did to the waveforms and why; how you resolved the two populations and measured their separation; which cooldowns you calibrated and why you left any out; how you got from the per-cooldown results to the temperature dependence; and where your quoted uncertainties come from. Write it as something you would hand a colleague, with figures where a figure carries the point better than a sentence. There is no template and no page count.
