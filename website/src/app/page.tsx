import { HeroBackground } from "@/components/HeroBackground";
import { TaskFileTree } from "@/components/TaskFileTree";
import { Button } from "@/components/ui/button";
import {
  exampleTask,
  getExampleTaskConfig,
  getExampleTaskTree,
} from "@/lib/example-task";
import { credit, site } from "@/lib/site";
import { getTasks } from "@/lib/tasks";
import { ArrowRight, ArrowUpRight, Award } from "lucide-react";
import Link from "next/link";

export default function Home() {
  const tasks = getTasks();

  return (
    <div className="flex flex-col min-h-screen relative text-foreground overflow-x-hidden">
      <main className="flex-1">
        <section className="flex flex-col items-center justify-center min-h-[78vh] text-center space-y-8 relative z-10 px-4 pt-20 overflow-hidden">
          <HeroBackground />
          {/* Softens the grid directly behind the headline so the type stays legible. */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-3xl h-full max-h-128 bg-background/60 blur-hero -z-10 rounded-full pointer-events-none" />

          <div className="space-y-6">
            <Link
              href="/contribute"
              className="inline-flex items-center rounded-full border border-chart-2/50 px-4 py-1.5 text-xs font-medium bg-chart-2/10 text-foreground backdrop-blur-md hover:bg-chart-2/20 hover:border-chart-2 transition-[background-color,border-color] duration-300 group"
            >
              <span className="w-2 h-2 rounded-full bg-chart-2 mr-2 animate-pulse shadow-glow" />
              Work in progress · accepting task contributions
              <ArrowRight className="ml-1.5 h-3 w-3 transition-transform group-hover:translate-x-0.5" />
            </Link>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.05] max-w-3xl mx-auto">
              Are AI agents good physicists?
            </h1>

            <p className="max-w-xl mx-auto text-lg text-foreground/80 leading-relaxed">
              FrontierPhysics: Benchmark how AI agents do frontier physics
              research.
            </p>
          </div>

          <div className="flex flex-col items-center gap-5 pt-2">
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <Button asChild>
                <Link href="/contribute">Contribute a task</Link>
              </Button>
              <Button
                asChild
                variant="secondary"
                className="border border-border hover:bg-accent transition-colors"
              >
                <a href={site.repo} target="_blank" rel="noopener noreferrer">
                  View on GitHub
                </a>
              </Button>
            </div>

            <p className="max-w-lg text-sm text-muted-foreground leading-relaxed">
              <Award
                className="inline-block h-4 w-4 -mt-0.5 mr-1.5 text-chart-2"
                aria-hidden="true"
              />
              A merged task earns{" "}
              <strong className="font-semibold text-foreground">
                {credit.task} points
              </strong>
              , a referral{" "}
              <strong className="font-semibold text-foreground">
                {credit.referral}
              </strong>
              , a review{" "}
              <strong className="font-semibold text-foreground">
                {credit.review}
              </strong>
              .
              <span className="block">
                At{" "}
                <strong className="font-semibold text-foreground">
                  {credit.authorship} points
                </strong>{" "}
                you are a{" "}
                <strong className="font-semibold text-foreground">
                  co-author
                </strong>
                .
              </span>
            </p>
          </div>
        </section>

        <div className="max-w-5xl mx-auto px-4 md:px-8 py-12 space-y-28">
          <section id="how-it-works" className="scroll-mt-28 space-y-4 text-center">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
              How FrontierPhysics Works
            </h2>
            <p className="text-muted-foreground max-w-3xl mx-auto leading-relaxed text-left">
              FrontierPhysics is a benchmark evaluating how AI agents do{" "}
              <strong className="font-medium text-foreground">
                frontier physics research iteratively
              </strong>
              . We evaluate realistic research challenges with iteration loops
              from{" "}
              <strong className="font-medium text-foreground">
                literature deep review
              </strong>{" "}
              to{" "}
              <strong className="font-medium text-foreground">
                research plan implementation
              </strong>
              . Tasks come from real research problems that take at least{" "}
              <strong className="font-medium text-foreground">
                weeks of effort
              </strong>{" "}
              for a physics PhD to do deep research and implement, and SOTA LLM
              agents{" "}
              <strong className="font-medium text-foreground">struggle</strong>{" "}
              with. The tasks are evaluated with verifiable graders and
              per-task rubric-based reviewer agents to make sure agents are
              doing research in ways{" "}
              <strong className="font-medium text-foreground">
                aligned with real frontier researchers
              </strong>
              .
            </p>
          </section>

          <section id="tasks" className="scroll-mt-28">
            <div className="mb-10 text-center">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Example tasks
              </h2>
            </div>

            <div className="mb-6 space-y-3">
              <h3 className="font-mono text-base font-semibold tracking-tight">
                {exampleTask.id}
              </h3>

              <div className="flex flex-wrap gap-1.5">
                {[
                  exampleTask.difficulty,
                  exampleTask.subcategory,
                  ...exampleTask.taskTypes,
                ]
                  .filter(Boolean)
                  .map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xxs font-medium text-muted-foreground"
                    >
                      {tag}
                    </span>
                  ))}
              </div>
            </div>

            {/* Both cards stretch to the same row height so their edges align. */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
              <div className="rounded-2xl border border-border bg-card overflow-hidden">
                <div className="border-b border-border px-4 py-2.5 font-mono text-xs text-muted-foreground">
                  task.md · config
                </div>
                <div className="max-h-[480px] overflow-y-auto px-5 divide-y divide-border">
                  {getExampleTaskConfig().map((group) => (
                    <div
                      key={group.title ?? "root"}
                      className="py-4 space-y-2.5"
                    >
                      {group.title && (
                        <p className="font-mono text-xxs uppercase tracking-widest text-muted-foreground/70">
                          {group.title}
                        </p>
                      )}
                      <dl className="space-y-1.5">
                        {group.rows.map((row) => (
                          <div
                            key={row.label}
                            className="grid grid-cols-[9rem_1fr] gap-x-3"
                          >
                            <dt className="font-mono text-xs leading-6 text-muted-foreground">
                              {row.label}
                            </dt>
                            <dd className="min-w-0 text-xs leading-6">
                              {Array.isArray(row.value) ? (
                                <span className="flex flex-wrap gap-1 py-0.5">
                                  {row.value.map((item) => (
                                    <span
                                      key={item}
                                      className="rounded-full border border-border bg-muted px-2 py-0.5 text-xxs font-medium text-muted-foreground"
                                    >
                                      {item}
                                    </span>
                                  ))}
                                </span>
                              ) : (
                                <span className="break-words text-foreground/90">
                                  {row.value}
                                </span>
                              )}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
                </div>
              </div>

              <TaskFileTree
                rootLabel={`tasks/${exampleTask.id}/`}
                nodes={getExampleTaskTree()}
                defaultOpen={["environment", "oracle", "verifier"]}
              />
            </div>

            {tasks.filter((task) => task.id !== exampleTask.id).length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
                {tasks
                  .filter((task) => task.id !== exampleTask.id)
                  .map((task) => (
                    <a
                      key={task.id}
                      href={`${site.tasksTree}/${task.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group rounded-2xl border border-border bg-card p-6 space-y-3 hover:border-foreground/25 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="font-mono text-sm font-semibold tracking-tight">
                          {task.id}
                        </h3>
                        <ArrowUpRight
                          className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                          aria-hidden="true"
                        />
                      </div>

                      <div className="flex flex-wrap gap-1.5">
                        {[task.difficulty, task.subcategory, ...task.taskTypes]
                          .filter(Boolean)
                          .map((tag) => (
                            <span
                              key={tag}
                              className="rounded-full border border-border bg-muted px-2.5 py-0.5 text-xxs font-medium text-muted-foreground"
                            >
                              {tag}
                            </span>
                          ))}
                      </div>

                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {task.summary}
                      </p>
                    </a>
                  ))}
              </div>
            )}
          </section>

        </div>
      </main>
    </div>
  );
}
