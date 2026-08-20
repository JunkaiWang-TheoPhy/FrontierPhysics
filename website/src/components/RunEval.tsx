"use client";

import runs from "@/data/example-run.json";
import {
  ChevronDown,
  CircleCheck,
  CircleX,
  ExternalLink,
  FileText,
  LoaderCircle,
  Play,
} from "lucide-react";
import { useEffect, useState } from "react";

/** Where the recorded-run assets are served from (see next.config.ts). */
const RUN_ASSET_BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/example-run`;

interface RunTest {
  name: string;
  passed: boolean;
}

interface RunCriterion {
  name: string;
  blocker: boolean;
  weight: number;
  explanation: string;
  outcome?: string;
  score?: number;
}

interface RunData {
  model: string;
  agent: string;
  effort: string;
  steps: number;
  toolCalls: number;
  wallClock: string;
  reward: number;
  testsPassed: number;
  testsTotal: number;
  tests: RunTest[];
  criteria: RunCriterion[];
  scoring: {
    weightedPoints: number;
    maxWeightedPoints: number;
    rawQuality: number;
    failedBlockers: string[];
    gatedQuality: number;
    decision: string;
  };
  resultMd: string;
}

const RUNS = runs as Record<string, RunData>;
const RUN_IDS = Object.keys(RUNS);

/** Staged status lines shown while the recorded run "executes". */
const STAGES = [
  "Provisioning sandbox…",
  "Building task image…",
  "Agent working…",
  "Running verifier…",
  "Grading rubric…",
];

function StatusChip({
  tone,
  children,
}: {
  tone: "good" | "warn" | "bad" | "neutral";
  children: React.ReactNode;
}) {
  const tones = {
    good: "border-emerald-600/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    warn: "border-amber-600/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    bad: "border-rose-600/40 bg-rose-500/10 text-rose-700 dark:text-rose-300",
    neutral: "border-border bg-muted text-muted-foreground",
  } as const;
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xxs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function CriterionRow({ criterion }: { criterion: RunCriterion }) {
  const [open, setOpen] = useState(false);
  const isBlocker = criterion.blocker;
  const result =
    criterion.outcome !== undefined
      ? criterion.outcome === "pass"
        ? { tone: "good" as const, label: "pass" }
        : { tone: "bad" as const, label: "FAIL" }
      : criterion.score === 2
        ? { tone: "good" as const, label: "2/2" }
        : criterion.score === 1
          ? { tone: "warn" as const, label: "1/2" }
          : { tone: "bad" as const, label: "0/2" };

  return (
    <li className="border-b border-border last:border-b-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left hover:bg-accent/50 transition-colors"
      >
        <ChevronDown
          className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${
            open ? "" : "-rotate-90"
          }`}
          aria-hidden="true"
        />
        <span className="min-w-0 flex-1 truncate font-mono text-xs">
          {criterion.name}
        </span>
        <StatusChip tone="neutral">
          {isBlocker ? "blocker" : `w${criterion.weight}`}
        </StatusChip>
        <StatusChip tone={result.tone}>
          {result.tone === "good" ? (
            <CircleCheck className="h-3 w-3" aria-hidden="true" />
          ) : result.tone === "bad" ? (
            <CircleX className="h-3 w-3" aria-hidden="true" />
          ) : null}
          {result.label}
        </StatusChip>
      </button>
      {open && (
        <p className="px-9 pb-3 font-mono text-xs leading-5 text-muted-foreground">
          {criterion.explanation}
        </p>
      )}
    </li>
  );
}

function PaperPanel({ runId }: { runId: string }) {
  const [open, setOpen] = useState(false);
  const href = `${RUN_ASSET_BASE}/${runId}-paper.pdf`;
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          className="flex min-w-0 flex-1 cursor-pointer items-center gap-2 text-left font-mono text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronDown
            className={`h-3.5 w-3.5 shrink-0 transition-transform ${
              open ? "" : "-rotate-90"
            }`}
            aria-hidden="true"
          />
          <FileText className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          paper.pdf — the agent&apos;s final paper draft
        </button>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 font-mono text-xxs text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <ExternalLink className="h-3 w-3" aria-hidden="true" />
          open in tab
        </a>
      </div>
      {open && (
        /* Mounted only when expanded, so the PDF is not fetched up front. */
        <iframe
          src={href}
          title="Agent paper.pdf"
          className="h-[38rem] w-full border-t border-border bg-white"
        />
      )}
    </div>
  );
}

function RunResults({ run, runId }: { run: RunData; runId: string }) {
  const { scoring } = run;
  return (
    <div className="space-y-5">
      {/* Verdict banner: label + icon carry the state; color reinforces. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-rose-600/40 bg-rose-500/10 px-4 py-3">
        <span className="inline-flex items-center gap-1.5 font-semibold text-rose-700 dark:text-rose-300">
          <CircleX className="h-4 w-4" aria-hidden="true" />
          Fail · reward {run.reward}
        </span>
        <span className="font-mono text-xs text-foreground/80">
          {run.testsPassed}/{run.testsTotal} deterministic checks ·{" "}
          {run.steps} steps · {run.toolCalls} tool calls · {run.wallClock}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <section className="rounded-xl border border-border bg-card overflow-hidden">
          <h4 className="border-b border-border px-3 py-2 font-mono text-xs text-muted-foreground">
            Deterministic verifier · {run.testsPassed}/{run.testsTotal}
          </h4>
          <ul>
            {run.tests.map((t) => (
              <li
                key={t.name}
                className="flex items-center gap-2 border-b border-border px-3 py-1.5 last:border-b-0"
              >
                {t.passed ? (
                  <CircleCheck
                    className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"
                    aria-hidden="true"
                  />
                ) : (
                  <CircleX
                    className="h-3.5 w-3.5 shrink-0 text-rose-600 dark:text-rose-400"
                    aria-hidden="true"
                  />
                )}
                <span className="min-w-0 flex-1 truncate font-mono text-xs">
                  {t.name}
                </span>
                <span className="font-mono text-xxs text-muted-foreground">
                  {t.passed ? "pass" : "fail"}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="border-b border-border px-3 py-2">
            <h4 className="font-mono text-xs text-muted-foreground">
              Rubric review (reviewer agent)
            </h4>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <StatusChip tone="neutral">
                {scoring.weightedPoints}/{scoring.maxWeightedPoints} weighted
              </StatusChip>
              <StatusChip tone="neutral">
                raw {(scoring.rawQuality * 100).toFixed(1)}%
              </StatusChip>
              <StatusChip tone="bad">
                <CircleX className="h-3 w-3" aria-hidden="true" />
                {scoring.decision.replace(/_/g, " ")}
              </StatusChip>
            </div>
          </div>
          <ul>
            {run.criteria.map((c) => (
              <CriterionRow key={c.name} criterion={c} />
            ))}
          </ul>
        </section>
      </div>

      <PaperPanel runId={runId} />

      <details className="rounded-xl border border-border bg-card">
        <summary className="cursor-pointer px-3 py-2 font-mono text-xs text-muted-foreground hover:text-foreground transition-colors">
          result.md — the agent&apos;s reported values
        </summary>
        <pre className="overflow-x-auto border-t border-border px-4 py-3 font-mono text-xs leading-5 text-foreground/90">
          {run.resultMd}
        </pre>
      </details>
    </div>
  );
}

/**
 * Replays a recorded benchmark rollout of the example task: press Run eval,
 * watch the staged pipeline, then read the verdict, the deterministic checks,
 * and the graded rubric — real data from the task's PR benchmarking, not a
 * live evaluation.
 */
export function RunEval() {
  const [selected, setSelected] = useState(RUN_IDS[0]);
  const [revealed, setRevealed] = useState<ReadonlySet<string>>(new Set());
  const [runningStage, setRunningStage] = useState<number | null>(null);

  const run = RUNS[selected];
  const done = revealed.has(selected);

  useEffect(() => {
    if (runningStage === null) return;
    const t = setTimeout(() => {
      if (runningStage + 1 >= STAGES.length) {
        setRevealed((prev) => new Set(prev).add(selected));
        setRunningStage(null);
      } else {
        setRunningStage(runningStage + 1);
      }
    }, 550);
    return () => clearTimeout(t);
  }, [runningStage, selected]);

  return (
    <div className="mt-10 rounded-2xl border border-border bg-card p-5 text-left">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="font-mono text-sm font-semibold tracking-tight">
          Run eval
        </h3>
        <div
          className="inline-flex overflow-hidden rounded-md border border-border"
          role="group"
          aria-label="Model"
        >
          {RUN_IDS.map((id) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setSelected(id);
                setRunningStage(null);
              }}
              aria-pressed={selected === id}
              className={`px-2.5 py-1 font-mono text-xs cursor-pointer transition-colors ${
                selected === id
                  ? "bg-accent text-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {RUNS[id].model}
            </button>
          ))}
        </div>
        {!done && runningStage === null && (
          <button
            type="button"
            onClick={() => setRunningStage(0)}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground cursor-pointer hover:opacity-90 transition-opacity"
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            Run eval
          </button>
        )}
        <span className="ml-auto font-mono text-xxs text-muted-foreground">
          {run.agent} · effort {run.effort} · no-skill
        </span>
      </div>

      {(done || runningStage !== null) && (
        <div className="mt-4">
          {done ? (
            <RunResults run={run} runId={selected} />
          ) : (
            <div className="flex items-center gap-2 rounded-xl border border-border bg-muted/50 px-4 py-6 font-mono text-xs text-muted-foreground">
              <LoaderCircle
                className="h-4 w-4 animate-spin text-chart-2"
                aria-hidden="true"
              />
              {STAGES[Math.min(runningStage ?? 0, STAGES.length - 1)]}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
