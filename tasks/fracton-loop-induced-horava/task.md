---
schema_version: '1.3'
metadata:
  author_name: Thomas Junkai Wang
  author_email: WangTheoPhys@outlook.com
  difficulty: hard
  difficulty_explanation: The task requires a literature-grounded field-theory calculation, a 3+1 constraint analysis, and a controlled separation of induced response from a dynamical gravity theory.
  category: natural-science
  subcategory: nonrelativistic-gravity
  category_confidence: high
  task_type: [analysis, calculation, search, verification]
  modality: [document, pdf, scientific-data, json]
  interface: [terminal, python, browser]
  skill_type: [domain-procedure, mathematical-method, evaluation-protocol]
verifier:
  type: test-script
  timeout_sec: 1200.0
  pytest_plugins: [ctrf]
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

# Can a fracton loop response become Hořava gravity?

You are studying a proposed route from subsystem-symmetric matter to an
emergent nonrelativistic gravitational response. The project folder contains
the frozen model specification in `environment/model.json`. The question is
not whether one can write terms that resemble a Hořava action; it is whether
the same microscopic model survives the Ward identities, the unreduced
Lorentzian constraint analysis, mode counting, and stability tests.

Use the literature available on the public internet, cite stable DOI or arXiv
identifiers, and distinguish established results from your inference. The
minimum reference set is listed in `environment/model.json`.

Your final conclusion must be either that the specified branch passes every
gate within the stated assumptions, or that it fails at the first named gate,
with an explicit counterexample or rank condition and the smallest defensible
completion.

## Required work

1. Fix conventions for the rank-two scalar-charge (quadrupole) theory and
   write its curved-background operator, source coupling, and Ward identities.
2. Compute the Euclidean two-point response to the lapse and spatial metric,
   retaining bubble and contact terms. Report low-momentum tensor structures
   and identify regulator-dependent coefficients.
3. Perform a 3+1 decomposition of the corresponding Lorentzian effective
   action before gauge fixing. Give primary and secondary constraints, their
   Poisson/Dirac brackets, and the local physical-mode count. Keep global,
   boundary, and rank-changing sectors separate.
4. Compare projectable, nonprojectable, and TTNC lapse choices. Test scalar
   and tensor kinetic signs, high-momentum dispersion relations, and complex
   or ghost poles for the parameter window in the model file.
5. Include two controls: the exact dipole/subsystem-symmetry control and the
   isotropic polynomial-shift Lifshitz control. State which Ward identity or
   mode-counting step changes between them.
6. Produce a paper-quality report and a machine-readable summary. A failed
   gate is a valid result; do not promote an induced background action to a
   claim of complete quantum gravity.

## Deliverables

- `/root/paper.pdf`: a self-contained paper with abstract, introduction,
  conventions, methods, results, discussion, limitations, and references.
- `/root/result.json`: JSON with keys `branch`, `assumptions`, `ward_tests`,
  `constraint_class`, `local_mode_count`, `stability`, `poles`,
  `first_failed_gate`, and `evidence`. Each gate entry has status `pass`,
  `fail`, or `undetermined`, plus a short evidence string.
- `/root/figures/`: at least one legible response or dispersion figure, plus
  any constraint or mode-count table used in the paper.

Include a claim-to-source map. Do not claim a numerical loop coefficient
without stating the regulator and subtraction convention.
