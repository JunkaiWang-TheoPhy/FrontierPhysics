---
schema_version: '1.3'
metadata:
  author_name: Heguang Lin
  author_email: 56796669+2454511550Lin@users.noreply.github.com
  difficulty: hard
  category: industrial-physical-systems
  subcategory: fiber-optic-sensing
  category_confidence: high
  task_type:
  - detection
  - analysis
  - calculation
  modality:
  - time-series
  - scientific-data
  - csv
  interface:
  - terminal
  - python
  skill_type:
  - domain-procedure
  - mathematical-method
  tags:
  - experiment
  - fiber-bragg-grating
  - rail-monitoring
  - strain-sensing
  - inverse-problem
  - weigh-in-motion
verifier:
  type: test-script
  timeout_sec: 900.0
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
  memory_mb: 4096
  storage_mb: 10240
  gpus: 0
---

1. Research

The goal is to use fiber Bragg Grating strain sensors to count axles number. The sensor is set to be put under the rail in the setting of a single track blocked section. The counting of the axles is to detect whether the train is inside the section or not, as a monitoring. Inside each sensor unite, there are two gratings that are attached to the opposite faces of one bending substrate. You job is to understand the setting and search literature. The following sepecific things should be thought about: 
1) rail would deforms when the train wheels load upon it, this would trigger the sensor signals at the rail foot
2) FBG would respond to both the shape change and the temperature change (in the outdoor settings)
3) you should explore how to take the advantage of the two-grating system
4) other objectives: speed/direction, per axle load (using the array of such sensors) etc.
Above should be discussed in your final paper. 

2. Implementation

Main data path is at `/root/data/`, under which we prepare four sensors recordings (`sensors/S1.csv.gz` to `S4.csv.gz`, columns `t_s,wl1_nm,wl2_nm`, 1 kHz). Sensor installation & track parameters are recorded in the lab log `lablog.md`. There is a vehicle that makes two passes through this section, and the per-axle load is in `calibration.csv`. The data stream includes around 25 minutes of the mixed traffic. And there is one sensor with a hardware problem that you need to identify.

3. Deliverables

Three things to report after analyzing the data:

1) `/root/result.md` 
for each train passage i in the order of entry time:
  `train_<i>_n_axles`, `train_<i>_direction` (+1 = A to B, -1 = B to A),
  `train_<i>_speed_mps` (section mean of the leading axle),
  `train_<i>_v_entry_mps`, `train_<i>_v_exit_mps` (leading-axle speeds at the section boundaries.),
  `train_<i>_occupancy_s` (`[t_in, t_out]`, time interval of first axle crossing the entry boundary to last axle crossing the exit boundary );
  `faulted_sensor: <id or none>`.

  Special case (report it as a single train entry, there is only one faulted_sensor) for the train that enter and then reverse in the section, then leaves by the side it enters:
  `train_<i>_n_axles`: only count its axles once
  `train_<i>_direction`: reports 0;
  `train_<i>_speed_mps`: omit for this entry;
  `train_<i>_v_entry_mps`, `train_<i>_v_exit_mps`: its entry and final-exit speeds at that boundary
  `train_<i>_occupancy_s`: in this case the enter and exit boundary is the same
  `faulted_sensor: <id or none>`. same as above.

  result.md should be one item per row, as "key: value" pair. Template can be found here `/root/result_template.md`. 

2)  `/root/axles.csv` 
  columns: `train_id,axle_index,t_ref_s,load_kN`
  one row per axle:  arrival time at the reference sensor S1 and estimated static axle load. train_id should match the the string 'train_{i}' as in result.md.

3) `/root/paper.pdf` 
  the paper draft for you to wrap up this research project for peer review. You should include abstract, introduction, methods, results, discussion, and references.

Axle counts must be exact to pass the grader. Loads, speeds, and times are graded with some tolerances. For grading purpose, please wrote the early results as soon as you have them, then refine the files in place. This is for preventing you run beyond the timeout and there you failed because of no submission. 
