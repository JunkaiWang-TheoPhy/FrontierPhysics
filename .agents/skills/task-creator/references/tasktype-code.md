# Task Family: Scientific Software

Use this family when the agent must repair, implement, reproduce, or validate
software whose correctness is defined by physics or numerical behavior.

## Examples

- restore a simulation that violates a conservation law;
- implement an algorithm from a cited paper;
- fix unit conversion or coordinate-frame errors;
- make a scientific package reproduce a benchmark figure;
- optimize a solver without changing its accepted error.

## Environment

- Bundle a source snapshot pinned to a commit.
- Include lockfiles and exact compiler/runtime versions.
- The sandbox defaults to `network_mode: public` for the research stage; pin
  the source snapshot and check that no upstream fix, issue thread, or newer
  commit leaks the answer.
- Remove solved patches and upstream issue breadcrumbs from accessible Git
  history.

## Oracle

Use a human-authored patch or reference implementation. The oracle may apply
the patch mechanically, but the verifier must judge behavior rather than diff
identity.

## Verifier

Run the project's real build and test tools, then add physics-specific checks:

- conservation or symmetry;
- error against an analytic limit;
- convergence order;
- reproducibility under a fixed seed;
- performance only when the task explicitly measures performance.

Avoid tests that merely grep for an import, function name, or algorithm label.

## Common failure modes

- unpinned compilers or dependency resolution;
- tests that fetch mutable external data;
- a public upstream patch revealing the answer;
- tolerances tied to one machine's floating-point path;
- accepting a build that passes while the scientific output is wrong.
