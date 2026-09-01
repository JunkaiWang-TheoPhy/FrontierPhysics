---
schema_version: '1.3'
metadata:
  author_name: Thomas Junkai Wang
  author_email: WangTheoPhys@outlook.com
  difficulty: hard
  difficulty_explanation: Provisional estimate for an advanced mathematical-physics study involving fermionic criticality, symmetry TFT, spin-sensitive categorical data, and exact consistency checks. Empirical difficulty will be measured after the task scope and evaluation package are frozen.
  category: natural-science
  subcategory: mathematical-physics
  category_confidence: high
  task_type:
  - analysis
  - calculation
  - search
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

# The Study on Symmetry TFT for Tricritical Ising

> Draft placeholder: this contribution records an ongoing mathematical-physics
> research direction and is not yet a merge-ready benchmark task.

## Research & Plan

Study the symmetry topological field theory associated with tricritical Ising
and its fermionic or spin-sensitive structures. Develop a self-contained account
of the physical problem, categorical input, relevant literature, conventions,
and the consistency conditions needed to turn abstract symmetry data into an
explicit and reviewable construction.

The eventual research task may involve defect and boundary sectors, fermionic
fusion data, spin structures, mapping-class actions, state-sum descriptions, or
comparisons between different realizations of the same symmetry TFT. This
placeholder intentionally does not prescribe a particular equivalence, functor,
state sum, or claimed theorem before the scientific scope is discussed with the
maintainers.

The research phase must distinguish:

- bosonic, fermionic, and spin refinements of the theory;
- abstract existence statements from explicit basis-level constructions;
- object-level correspondences from coherent maps on higher morphisms;
- checked finite presentations from claims about a fully extended theory;
- exact identities from convention-dependent normalization choices.

## Experiment & Implementation

After the scope is frozen, the task will provide a provenance-backed research
environment containing the selected algebraic data, reference conventions, and
reproducible calculation scaffolding. The evaluated agent will investigate the
agreed question, construct the required mathematical objects or comparison,
and test the result against independent structural identities.

The completed task should require a nontrivial combination of literature work,
mathematical reasoning, exact computation, and scientific judgment. A valid
outcome may be a positive construction or a bounded obstruction, provided the
claim is supported by explicit evidence and does not promote a partial ledger
or analogy into a theorem.

## Planned deliverables

The final package will define exact output contracts only after the research
question is selected. Expected artifacts include:

- `/root/paper.pdf`: a research report with sources, conventions, construction,
  checks, limitations, and a precise claim boundary;
- `/root/result.json`: machine-readable objects, identities, comparison data,
  and pass/fail outcomes for the frozen scientific question;
- `/root/certificates/`: exact matrices, symbolic identities, or other compact
  certificates needed for independent verification.

The source set, input snapshot, output schema, oracle, verifier, numerical or
symbolic tolerances, and task-specific rubrics will be added in a later revision
after maintainer review.
