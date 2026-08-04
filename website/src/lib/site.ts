export const site = {
  name: "FrontierPhysics",
  tagline: "Are AI agents good physicists?",
  description:
    "FrontierPhysics is an open benchmark measuring whether AI agents can carry out authentic, specialist-level physics research.",
  /**
   * Where the site is served from. `origin` is what `metadataBase` resolves
   * relative URLs against: the file-based icon and share-image routes already
   * carry the `/frontierphysics` basePath in their paths, so including it here
   * as well would double it. `url` is the canonical address of the home page.
   */
  origin: "https://www.benchflow.ai",
  url: "https://www.benchflow.ai/frontierphysics",
  repo: "https://github.com/benchflow-ai/FrontierPhysics",
  discord: "https://discord.gg/G9dg3EfSva",
  contributing:
    "https://github.com/benchflow-ai/FrontierPhysics/blob/main/CONTRIBUTING.md",
  protocol:
    "https://github.com/benchflow-ai/FrontierPhysics/blob/main/docs/benchmark-protocol.md",
  taxonomy:
    "https://github.com/benchflow-ai/FrontierPhysics/blob/main/taxonomy.md",
  tasksTree: "https://github.com/benchflow-ai/FrontierPhysics/tree/main/tasks",
  /**
   * Docs are read straight from the repository rather than mirrored here, so
   * there is only ever one copy to maintain and the site cannot go stale.
   */
  docs: "https://github.com/benchflow-ai/FrontierPhysics/tree/main/docs",
  benchflow: "https://github.com/benchflow-ai/benchflow",
  /** Prior work by the same team, cited as evidence the benchmark will ship. */
  skillsbenchPaper: "https://arxiv.org/abs/2602.12670",
} as const;

/**
 * The authorship policy, mirrored from CONTRIBUTING.md#authorship-policy.
 * Everything the site says about credit is derived from these four numbers,
 * so the copy cannot drift out of step with itself.
 */
export const credit = {
  /** Points for a task you authored being merged. */
  task: 6,
  /** Points for referring a contributor, once their first task merges. */
  referral: 2,
  /** Points for a task you reviewed being merged. */
  review: 1,
  /** Points that earn co-authorship on the paper and dataset. */
  authorship: 12,
} as const;

/**
 * Every task is graded in two stages, mirrored from
 * CONTRIBUTING.md#two-stages-two-graders. The author ships a grader for each:
 * a planning rubric for the first stage, the verifier for the second.
 */
export const stages = [
  {
    step: "01",
    title: "Deep research",
    body: "The agent studies the problem and commits to a research plan. A planning rubric that ships with the task grades that plan.",
  },
  {
    step: "02",
    title: "Execution",
    body: "The agent carries the plan out. The verifier checks that the final results are accurate.",
  },
] as const;

/** Merged tasks needed to reach co-authorship on authoring alone. */
export const tasksForAuthorship = credit.authorship / credit.task;

/**
 * Cut-off for points. A task only scores if it is *merged* by this date, not
 * merely opened, which is why the guidance pushes contributors to open a draft
 * early rather than polish in private.
 */
export const scoringDeadline = "31 August 2026";

export const navItems = [
  { href: "/#tasks", label: "Tasks" },
  { href: "/contribute", label: "Contribute" },
  { href: site.docs, label: "Docs", external: true },
] as const satisfies readonly {
  href: string;
  label: string;
  external?: boolean;
}[];
