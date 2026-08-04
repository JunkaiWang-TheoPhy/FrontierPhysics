import { HeroBackground } from "@/components/HeroBackground";
import { Button } from "@/components/ui/button";
import { credit, site, stages } from "@/lib/site";
import { getTasks } from "@/lib/tasks";
import { ArrowRight, ArrowUpRight, Award } from "lucide-react";
import Link from "next/link";

const PACKAGE_TREE = `tasks/<task-id>/
  task.md            # prompt + metadata
  environment/
    Dockerfile       # frozen environment
    skills/          # mentor skills
  oracle/
    solve.sh         # must reach reward 1.0
  verifier/
    test.sh
    test_outputs.py  # checks the science`;

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
          <section id="anatomy" className="scroll-mt-28">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
              <div className="space-y-4">
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                  What a task looks like
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  A native BenchFlow{" "}
                  <code className="font-mono text-sm">task.md</code> package. The
                  prompt describes an outcome and never names any skill. The
                  oracle must pass with reward 1.0 before any agent runs, and
                  every attempt is graded in two stages.
                </p>
                <ol className="space-y-4 pt-1">
                  {stages.map((stage) => (
                    <li key={stage.step} className="flex gap-4">
                      <span className="font-mono text-sm text-muted-foreground pt-0.5 shrink-0">
                        {stage.step}
                      </span>
                      <div className="space-y-1">
                        <h3 className="font-semibold tracking-tight text-sm">
                          {stage.title}
                        </h3>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                          {stage.body}
                        </p>
                      </div>
                    </li>
                  ))}
                </ol>
                <p className="text-muted-foreground leading-relaxed">
                  Prompts, oracle logic, and the planning rubric are
                  human-authored.
                </p>
              </div>

              <pre className="rounded-2xl border border-border bg-card p-6 overflow-x-auto text-xs sm:text-sm font-mono leading-relaxed text-muted-foreground">
                {PACKAGE_TREE}
              </pre>
            </div>
          </section>

          <section id="tasks" className="scroll-mt-28">
            <div className="mb-10 space-y-3">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                Example tasks
              </h2>
              <p className="text-muted-foreground max-w-2xl leading-relaxed">
                Each one comes from research a contributor had already done.
              </p>
            </div>

            {tasks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {tasks.map((task) => (
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
            ) : (
              <p className="text-sm text-muted-foreground">
                No task packages found in this checkout.
              </p>
            )}
          </section>

        </div>
      </main>
    </div>
  );
}
