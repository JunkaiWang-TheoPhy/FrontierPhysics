import { Button } from "@/components/ui/button";
import { credit, scoringDeadline, site, stages } from "@/lib/site";
import {
  ArrowUpRight,
  Award,
  Check,
  Clock,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";
import type { Metadata } from "next";

const title = "Contribute a task";
const description =
  "How to turn physics research you have already done into a FrontierPhysics benchmark task.";

export const metadata: Metadata = {
  title,
  description,
  // Without its own canonical this page would inherit the home page's and be
  // dropped from search results as a duplicate.
  alternates: { canonical: `${site.url}/contribute` },
  openGraph: {
    title: `${title} | ${site.name}`,
    description,
    url: `${site.url}/contribute`,
    siteName: site.name,
    locale: "en_US",
    type: "article",
  },
  twitter: {
    card: "summary_large_image",
    title: `${title} | ${site.name}`,
    description,
  },
};

const CRITERIA = [
  {
    title: "Your own work",
    body: "Real research you carried out, not a problem invented for the benchmark.",
    check: "Did I do this myself?",
    icon: FlaskConical,
    accent: "text-chart-1",
    tint: "bg-chart-1/10",
  },
  {
    title: "Weeks of effort",
    body: "At least two weeks of genuine effort, with or without an agent helping.",
    check: "Did it really take weeks to finish?",
    icon: Clock,
    accent: "text-chart-2",
    tint: "bg-chart-2/10",
  },
  {
    title: "Verifiable",
    body: "The result is right or wrong, and a script can tell which.",
    check: "Can a script grade it?",
    icon: ShieldCheck,
    accent: "text-chart-3",
    tint: "bg-chart-3/10",
  },
];

const ELIGIBILITY = [
  "A PhD or current PhD candidate in physics, EECS, or an adjacent field",
  "Or extensive hands-on experience in a physics lab or an equivalent industry role",
];

const SUBMISSION = [
  {
    title: "A PR from your fork",
    body: "Fork this repository and open a pull request against main here. One task per PR, touching only files under tasks/<task-id>/.",
  },
  {
    title: "A detailed PR description",
    body: "What the original work was, the physics it exercises, and where the data came from — plus a table reporting its history against these minimums.",
    report: [
      ["Project time scale — start and end date", "2 weeks"],
      ["Actual working hours spent exploring the task", "40 hours"],
      ["Estimated hours for a first-year PhD to reproduce it", "10 hours"],
    ] as [string, string][],
  },
  {
    title: "A local test results report",
    body: "What you ran and what happened, across multiple trials rather than a single run.",
    checks: [
      "The oracle passes with reward exactly 1.0",
      "Results for a state-of-the-art agent with skills",
      "Results for the same agent without skills",
    ],
    example: { label: "Example task: PR #23.", href: `${site.repo}/pull/23` },
  },
];

const KEY_PARTS = [
  {
    name: "task.md",
    body: "The task description, in two parts.",
    parts: [
      [
        "Research",
        "Reviewing literature and making plans. The plan and thinking process are evaluated based on rubrics written by the contributor.",
      ],
      [
        "Implementation",
        "The concrete problem-solving request that can be verified by code scripts.",
      ],
    ] as [string, string][],
  },
  {
    name: "rubric.json",
    body: "The item-by-item list of rubrics that describe the expectations from the researchers. It mainly focuses on the research and planning parts that are not verifiable via code scripts.",
  },
  {
    name: "verifier",
    body: "The verifier logic for checking the agent's final deliverables. Code scripts for checking verifiable results.",
  },
  {
    name: "oracle",
    body: "The ground truth answer provided by the contributor. Always gets reward == 1 on the verifier.",
  },
];

export default function Contribute() {
  return (
    <main className="max-w-3xl mx-auto px-4 md:px-8 pt-32 pb-8">
      <header className="space-y-5 mb-16">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
          Contribute
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05]">
          Turn research you have already done into a benchmark task
        </h1>
        <div className="flex items-start gap-4 rounded-2xl border border-chart-2/40 bg-chart-2/5 p-6">
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-chart-2/15 text-chart-2">
            <Award className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="space-y-2">
            <h2 className="font-semibold tracking-tight">
              Earn {credit.authorship} points, become a co-author
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              A merged task you authored earns{" "}
              <strong className="font-semibold text-foreground">
                {credit.task}
              </strong>
              , one you reviewed earns{" "}
              <strong className="font-semibold text-foreground">
                {credit.review}
              </strong>
              , and referring a contributor earns{" "}
              <strong className="font-semibold text-foreground">
                {credit.referral}
              </strong>{" "}
              once their first task merges.
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Reviewing opens up once you have your first good task merged — ask
              a maintainer to be added as a reviewer.
            </p>
            <p className="text-sm leading-relaxed">
              <strong className="font-semibold text-foreground">
                Get tasks merged by {scoringDeadline} to join author list of
                ICLR 2026
              </strong>
            </p>
            <p className="text-sm text-muted-foreground leading-relaxed">
              From the team behind{" "}
              <a
                href={site.skillsbenchPaper}
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
              >
                SkillsBench
              </a>
              , 170+ citations within 6 months of release.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 pt-2">
          <Button asChild>
            <a href={site.joinForm} target="_blank" rel="noopener noreferrer">
              Join the team
              <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
            </a>
          </Button>
          <Button asChild variant="secondary" className="border border-border">
            <a href={site.taskForm} target="_blank" rel="noopener noreferrer">
              Contribute a task
            </a>
          </Button>
        </div>
      </header>

      <section id="get-started" className="scroll-mt-28 space-y-6 mb-20">
        <h2 className="text-2xl font-bold tracking-tight text-center">
          Getting started
        </h2>

        <div className="rounded-2xl border border-border bg-card divide-y divide-border">
          <div className="p-6 flex gap-5">
            <span className="font-mono text-sm text-muted-foreground pt-0.5 shrink-0">
              01
            </span>
            <div className="space-y-1.5">
              <h3 className="font-semibold tracking-tight">
                Join the contributors team
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Fill in the{" "}
                <a
                  href={site.joinForm}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
                >
                  join form
                </a>{" "}
                to get access to the group chats, the shared Google Drive, and
                the GitHub repository.
              </p>
            </div>
          </div>
          <div className="p-6 flex gap-5">
            <span className="font-mono text-sm text-muted-foreground pt-0.5 shrink-0">
              02
            </span>
            <div className="space-y-1.5">
              <h3 className="font-semibold tracking-tight">
                Contribute a task — two ways
              </h3>
              <ol className="space-y-1.5">
                <li className="flex gap-2.5 text-sm">
                  <span className="font-mono text-muted-foreground">1.</span>
                  <span className="text-muted-foreground leading-relaxed">
                    Fill in the{" "}
                    <a
                      href={site.taskForm}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
                    >
                      task form
                    </a>{" "}
                    and co-work with reviewers in email threads.
                  </span>
                </li>
                <li className="flex gap-2.5 text-sm">
                  <span className="font-mono text-muted-foreground">2.</span>
                  <span className="text-muted-foreground leading-relaxed">
                    Send a PR in{" "}
                    <a
                      href={site.repo}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
                    >
                      benchflow-ai/FrontierPhysics
                    </a>{" "}
                    to add a task, following the{" "}
                    <a
                      href={`${site.repo}/pull/23`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
                    >
                      example PR
                    </a>
                    .
                  </span>
                </li>
              </ol>
            </div>
          </div>
        </div>
      </section>

      <section id="who" className="scroll-mt-28 space-y-6 mb-20">
        <h2 className="text-2xl font-bold tracking-tight text-center">
          Who should contribute
        </h2>
        <ul className="space-y-3">
          {ELIGIBILITY.map((item) => (
            <li key={item} className="flex gap-3 text-muted-foreground">
              <Check
                className="h-5 w-5 shrink-0 mt-0.5 text-chart-2"
                aria-hidden="true"
              />
              <span className="leading-relaxed">{item}</span>
            </li>
          ))}
        </ul>
      </section>

      <section id="ideal-task" className="scroll-mt-28 space-y-6 mb-20">
        <h2 className="text-2xl font-bold tracking-tight text-center">
          What makes an ideal task
        </h2>
        <p className="text-muted-foreground leading-relaxed">
          All three. A task that misses any one will not merge.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {CRITERIA.map((item) => (
            <div
              key={item.title}
              className="flex flex-col rounded-2xl border border-border bg-card p-6"
            >
              <span
                className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${item.tint} ${item.accent} mb-4`}
              >
                <item.icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="font-semibold tracking-tight mb-2">
                {item.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed grow">
                {item.body}
              </p>
              {/* Two lines are reserved so the rule sits at the same height in
                  every card, whether the question wraps or not. */}
              <p className="mt-4 pt-4 border-t border-border text-sm font-medium leading-5 min-h-14">
                {item.check}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section id="two-stages" className="scroll-mt-28 space-y-6 mb-20">
        <div className="space-y-3">
          <h2 className="text-2xl font-bold tracking-tight text-center">
            Two stages, two graders
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Every task is graded in two stages, and you write the grader for
            each.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {stages.map((stage) => (
            <div
              key={stage.step}
              className="rounded-2xl border border-border bg-card p-6 space-y-2"
            >
              <span className="font-mono text-sm text-muted-foreground">
                {stage.step}
              </span>
              <h3 className="font-semibold tracking-tight">{stage.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {stage.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section id="key-parts" className="scroll-mt-28 space-y-6 mb-20">
        <h2 className="text-2xl font-bold tracking-tight text-center">
          Key parts of a task
        </h2>

        <div className="rounded-2xl border border-border bg-card divide-y divide-border">
          {KEY_PARTS.map((part) => (
            <div
              key={part.name}
              className="p-6 grid grid-cols-1 sm:grid-cols-[8rem_1fr] gap-2 sm:gap-6"
            >
              <h3 className="font-mono text-sm font-semibold tracking-tight">
                {part.name}
              </h3>
              <div className="space-y-2.5">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {part.body}
                </p>
                {part.parts && (
                  <ol className="space-y-1.5">
                    {part.parts.map(([label, detail], i) => (
                      <li key={label} className="flex gap-2.5 text-sm">
                        <span className="font-mono text-muted-foreground">
                          {i + 1}.
                        </span>
                        <span className="text-muted-foreground leading-relaxed">
                          <span className="font-medium text-foreground">
                            {label}
                          </span>{" "}
                          — {detail}
                        </span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="submission" className="scroll-mt-28 space-y-6 mb-20">
        <div className="space-y-3">
          <h2 className="text-2xl font-bold tracking-tight text-center">
            The final submission
          </h2>
          <p className="text-muted-foreground leading-relaxed">
            Three things. Open it as a draft long before it is finished —
            reviewing and revising a task takes days of back-and-forth, and a
            draft is the cheapest way to find out early that an idea will not
            clear the bar.
          </p>
        </div>

        <ol className="space-y-5">
          {SUBMISSION.map((item, index) => (
            <li key={item.title} className="flex gap-5">
              <span className="font-mono text-sm text-muted-foreground pt-0.5 shrink-0">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="space-y-1.5">
                <h3 className="font-semibold tracking-tight">{item.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {item.body}
                  {item.example ? (
                    <>
                      {" "}
                      <a
                        href={item.example.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-foreground underline underline-offset-4 hover:text-muted-foreground transition-colors"
                      >
                        {item.example.label}
                      </a>
                    </>
                  ) : null}
                </p>
                {"report" in item && item.report ? (
                  <div className="overflow-x-auto pt-1">
                    <table className="w-full text-sm border-collapse">
                      <thead>
                        <tr className="border-b border-border">
                          <th className="text-left font-medium py-2 pr-4">
                            Report
                          </th>
                          <th className="text-left font-medium py-2 whitespace-nowrap">
                            Minimum
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {item.report.map(([field, minimum]) => (
                          <tr key={field} className="border-b border-border/60">
                            <td className="py-2 pr-4 text-muted-foreground leading-relaxed">
                              {field}
                            </td>
                            <td className="py-2 font-medium tabular-nums whitespace-nowrap">
                              {minimum}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                {"checks" in item && item.checks ? (
                  <ul className="space-y-2 pt-1">
                    {item.checks.map((check) => (
                      <li key={check} className="flex gap-2.5 text-sm">
                        <Check
                          className="h-4 w-4 shrink-0 mt-0.5 text-chart-2"
                          aria-hidden="true"
                        />
                        <span className="text-muted-foreground leading-relaxed">
                          {check}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
