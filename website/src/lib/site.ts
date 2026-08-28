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
   * every repo-shaped affordance routes here instead, including the
   * "Contribute a task" buttons (the separate task form is retired).
   */
  joinForm: "https://forms.gle/BVxbGg8VbHsbpMxi9",
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
 * A run of copy where the dates and venue names are emphasised. Storing them
 * as data rather than as hand-written markup keeps each sentence readable in
 * one piece here — these are the exact sentences of the policy — while still
 * letting the page bold a deadline or a venue name.
 */
export type Emphasis = {
  text: string;
};
export type Sentence = readonly (string | Emphasis)[];

/**
 * Publication timeline, mirrored from CONTRIBUTING.md#timeline. Both dates are
 * deadlines for a task being *merged*, not opened, which is why every surface
 * that shows them also tells contributors to open a draft PR early.
 */
export const timeline: {
  summary: Sentence;
  /** `version` is the paper version that deadline closes the author list for. */
  milestones: readonly { version: string; sentence: Sentence }[];
} = {
  summary: [
    "We will submit to ",
    { text: "ICLR" },
    " first and then submit to ",
    { text: "Nature" },
    " after further polish.",
  ],
  milestones: [
    {
      version: "v0.1",
      sentence: [
        "Get tasks merged by ",
        { text: "7 September" },
        " to join the author list of ",
        { text: "ICLR" },
        " (and all future paper versions).",
      ],
    },
    {
      version: "v1.0",
      sentence: [
        "Get tasks merged by ",
        { text: "31 December" },
        " to join the author list of the draft submitted to ",
        { text: "Nature" },
        ".",
      ],
    },
  ],
};

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
