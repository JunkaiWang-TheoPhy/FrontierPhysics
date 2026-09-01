---
schema_version: '1.3'
metadata:
  author_name: Thomas Junkai Wang
  author_email: WangTheoPhys@outlook.com
  difficulty: hard
  difficulty_explanation: Provisional estimate for an end-to-end theoretical-physics study requiring literature analysis, background-field calculations, constraint classification, and independent consistency checks. Empirical difficulty will be measured after the evaluation package is frozen.
  category: natural-science
  subcategory: nonrelativistic-gravity
  category_confidence: high
  task_type:
  - analysis
  - calculation
  - search
  - simulation
  - verification
  modality:
  - document
  - pdf
  - scientific-data
  - json
  interface:
  - terminal
  - python
  - browser
  - formal-prover
  skill_type:
  - domain-procedure
  - mathematical-method
  - evaluation-protocol
verifier:
  type: test-script
  timeout_sec: 1200.0
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

# Fracton loop-induced Horava gravity

> Draft placeholder: this contribution records a real research direction and
> is not yet a merge-ready benchmark task.

## Research & Plan

Study whether a specified dipole or higher-moment matter sector can induce a
consistent nonrelativistic gravitational response, rather than merely produce
an effective curvature term that resembles a Horava action.

The central question is:

> After the matter model, background geometry, regulator, and boundary sector
> are fixed, does the induced response pass the Ward-identity, Lorentzian
> constraint, physical-mode, stability, and pole tests required for a
> Horava-like gravity sector?

The research phase must keep the following structures separate:

- exact dipole or subsystem symmetry versus an isotropic polynomial-shift
  Lifshitz reference theory;
- projectable versus nonprojectable or TTNC lapse sectors;
- Euclidean determinant coefficients versus Lorentzian degrees of freedom;
- an induced background effective action versus a complete dynamical gravity
  theory;
- a positive closure result versus a bounded no-go result at a named gate.

The agent should establish the relevant literature, state conventions and
assumptions, identify the closest competing constructions, and formulate an
end-to-end calculation plan. It must not treat an induced kinetic ratio,
curvature term, or analogy between a rank-two gauge field and a metric as a
proof of emergent gravity.

## Experiment & Implementation

After the scientific scope is frozen, the task will provide a provenance-backed
research environment with clean model specifications, reference inputs, and
reproducible calculation scaffolding. The evaluated agent will be asked to:

1. construct or verify the chosen curved-background matter operator and its
   Ward identities;
2. compute the required Euclidean response using consistent bubble and contact
   terms;
3. formulate the unreduced Lorentzian theory and classify primary and
   secondary constraints with Poisson or Dirac brackets;
4. count physical local modes while treating global, boundary, and
   rank-changing sectors separately;
5. test kinetic signs, high-momentum stability, and complex or ghost poles in
   the stated parameter window;
6. compare the result with the exact symmetry and projectable/nonprojectable
   controls supplied in the environment;
7. produce a paper-quality conclusion that either closes the stated branch or
   identifies the first failed gate and its smallest defensible completion.

The implementation must preserve the distinction between a controlled
reference calculation and a claim about complete quantum gravity. If a gate
fails, reporting the failure with a reproducible counterexample is a valid
scientific outcome.

## Planned deliverables

The final package will provide a frozen input bundle, an independent oracle,
outcome-based verifier tests, and a rubric for the deep-research and planning
stages. The evaluated agent is expected to produce:

- `/root/paper.pdf`: a complete research paper with literature review,
  assumptions, methods, calculations, results, discussion, limitations, and
  references;
- `/root/result.json`: the selected model branch, gate-by-gate outcomes,
  invariant checks, mode count, stability/pole summary, and evidence links;
- `/root/figures/`: figures needed to make the response and failed or passed
  gates reviewable.

The exact model, input snapshot, numerical tolerances, oracle, verifier, and
task-specific rubrics will be added after the maintainer discussion and a
clean feasibility check.
