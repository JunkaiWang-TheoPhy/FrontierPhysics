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
  build_timeout_sec: 1200.0
  os: linux
  cpus: 4
  memory_mb: 10240
  storage_mb: 20480
  gpus: 0
---

1. Research

We are using trapped ions as qubits to build quantum networks. We want to have a 100km fiber between 2 trapped ion nodes (one down hill another up hill) with at least 50km distance. The scheme we use is heralded scheme for building remote entanglement between trapped ion qubits.

If we want to have high enough rate of building entanglement, help me to research on what would be the dominant time budge / bottleneck other than loss in fiber. For solving that issue, what would be a good solution if you have a chain of ions in each trapped ion node. What if we can move the ions around. Do deep research and find some possible schemes that you think is promising. Find 3-5 possible schemes so we can brainstorm.

In our experiment setup, we use a glass echoed surface trap in each trapped ion node. In each trapped ion 40Ca+ node we can trap 2-10 ions chain. Unfortunately the chamber is under vacuum right now and we could not add more parts in it (so we only have a trap in it and nothing else). Lasers setup is in free space and we use DC and RF electrodes to confine the ions. For getting 397nm photons from ions as a POC, how this experiment should be designed; what are the tools we should use to simulate the trap potential; how to calculate the ion-ion spacing; how to design the shuttling function if we want to move the ions chain with as low as possible motional heating in the end, possibly with inverse engineering method. In the future to avoid loss in fiber what is the wavelength we should use and how to achieve that. I want you to do research and answer these questions.

For all the related papers you find when doing literature research and final experiment you designed, make a plan file called `PLAN.md` for me to review in the current workspace. The file should be concise and clear.

2. Implementation

In `/root/surface_trap.stl` you have a trap model file for a surface ion trap (surface Paul trap). You need to simulate and calculate the trap frequency along the radial direction for a singly charged `40Ca+` ion when an 80 V RF amplitude at 39.15 MHz is applied to the RF electrode. The RF electrode is the "2-rail" electrode in the center and you can treat other electrodes as ground to do the simulation for the radial trap frequency calculation. (Axial is defined as the direction along the 2-rail RF electrode in the center, and radial means the direction parallel to the trap surface and perpendicular to the RF electrode.) Note it down in MHz as number `W_radial_freq`.

After getting `W_radial_freq`, based on the standard Mathieu differential equation, use the anisotropy parameter `α = (W_axial_freq / W_radial_freq)^2 = 0.00174` to calculate the axial trap frequency. Note it down in MHz as number `W_axial_freq`.

Now imagine we are shuttling a one-ion chain along the axial direction. What is the ideal shuttling function if we do harmonic transport at 10 m/s and move a distance of 100 um? Give the trap-center shuttling function obtained using the inverse-engineering method.

Then we expand this into a 9-ion chain of singly charged `40Ca+` ions, and we want to first calculate the equilibrium ion-ion spacing of the whole chain with the given axial trap frequency. Note down 8 positive spacing distances in um: `d1`, `d2`, `d3`, `d4`, ..., `d8`.

With the ion-ion spacing numbers, we can start shuttling the ion chain step by step. I want to find the final shuttling function from beginning to the end. The whole process is: I have a static single-ion addressing beam that does not move. At the beginning the first ion in the chain is sitting at the addressing beam. Then the ion chain starts to move step by step, dwelling for 1 us after each move, until the final ion is addressed. Each shuttling move is 10 us, and for each shuttling stage I want to use the same inverse-engineered shuttling form. Give me the final shuttling function.

In the end you should output `/root/result.md`. Use the following key-value format, with frequencies in MHz and distances in um:

```md
W_radial_freq: <number>
W_axial_freq: <number>
d1: <number>
...
d7: <number>
d8: <number>
```

Also output `/root/1.csv` and `/root/2.csv`, each with exactly 10,000 sampling points plus a header row.

In `1.csv` (the first shuttling function for a single ion) and `2.csv` (the complete shuttling function for the 9-ion chain), the first column is time in us and the second column is the center position of the trap potential along the axial direction in um.

