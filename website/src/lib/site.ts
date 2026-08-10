export const site = {
  name: "FrontierPhysics",
  tagline: "Evaluate agents for end-to-end frontier physics research.",
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
  discord: "https://discord.gg/G9dg3EfSva",
  /**
   * Onboarding form: unlocks the group chats, Google Drive, and GitHub repo.
   * The task repository is private, so the site never links it directly —
   * every repo-shaped affordance routes here instead.
   */
  joinForm: "https://forms.gle/BVxbGg8VbHsbpMxi9",
  /** Task form for contributing by co-working with reviewers over email. */
  taskForm: "https://forms.gle/v7p1dFAkyLonyjea8",
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
  review: 2,
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

export const navItems = [
  { href: "/#tasks", label: "Tasks" },
  { href: "/contribute", label: "Contribute" },
] as const satisfies readonly {
  href: string;
  label: string;
  external?: boolean;
}[];
