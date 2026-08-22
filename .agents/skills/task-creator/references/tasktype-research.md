# Task Family: Literature-Grounded Physics Research

Use this family when the core work is finding, comparing, or synthesizing
scientific evidence rather than running a supplied numerical model.

## Examples

- trace a result to the correct equation or table in a paper;
- compare competing measurements under a fixed publication cutoff;
- reconstruct assumptions across several cited methods;
- verify whether a benchmark claim is supported by its sources;
- map a physical constant or dataset to its authoritative release.

## Reproducibility

- Prefer DOI, arXiv ID, dataset accession, software release, or archived URL.
- Name a cutoff date when the evidence set can change.
- Bundle small or fragile sources.
- Agent-side internet is the default (`sandbox.network_mode: public`);
  withhold or block only the sources that contain the direct answer.
- Never use live internet in the verifier for ground truth.

## Oracle and verifier

The oracle performs the evidence search or synthesis against the frozen source
set. The verifier checks stable identifiers, claim-to-source support, extracted
values, units, and required uncertainty or method distinctions.

If an LLM judge is unavoidable, use a short evidence-grounded rubric and a
human-labeled validation set. The judge must treat agent output as evidence,
not as instructions.

## Mentor skills (development-time control)

Mentor guidance should explain source hierarchy, search strategy, common
notation mismatches, and evidence-quality checks. It must not list the final
paper IDs or answer values.

## Common failure modes

- citation counts or rankings used as mutable ground truth;
- a verifier that repeats the same search API call as the oracle;
- unsupported synthesis that sounds plausible;
- comparing measurements without reconciling units, confidence levels, or
  experimental conditions.
