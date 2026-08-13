import { timeline, type Sentence } from "@/lib/site";
import { Fragment } from "react";

/** Emphasised runs — deadlines and venues — rendered inside a policy sentence. */
function Emphasised({ parts }: { parts: Sentence }) {
  return (
    <>
      {parts.map((part, index) =>
        typeof part === "string" ? (
          <Fragment key={index}>{part}</Fragment>
        ) : (
          <strong
            key={index}
            className={`font-semibold text-foreground${part.journal ? " italic" : ""}`}
          >
            {part.text}
          </strong>
        ),
      )}
    </>
  );
}

/** Flattens a sentence back to plain text, for React keys. */
const plain = (sentence: Sentence) =>
  sentence.map((part) => (typeof part === "string" ? part : part.text)).join("");

interface TimelineProps {
  /** Classes for the section wrapper. */
  className?: string;
  /** Heading size varies between pages, so each one passes its own. */
  headingClassName?: string;
}

/**
 * The two authorship deadlines. Shared by the landing page and the contributor
 * guide so a date can never say one thing on one page and another elsewhere.
 */
export function Timeline({
  className = "",
  headingClassName = "text-2xl",
}: TimelineProps) {
  return (
    <section id="timeline" className={`scroll-mt-28 space-y-6 ${className}`}>
      <h2 className={`${headingClassName} font-bold tracking-tight text-center`}>
        Timeline
      </h2>

      <p className="text-muted-foreground leading-relaxed">
        <Emphasised parts={timeline.summary} />
      </p>

      <ul className="rounded-2xl border border-border bg-card divide-y divide-border">
        {timeline.milestones.map((milestone) => (
          <li
            key={plain(milestone.sentence)}
            className="p-6 flex items-center gap-5"
          >
            {/* The paper version whose author list this deadline closes. */}
            <span className="inline-flex h-10 shrink-0 items-center justify-center rounded-xl bg-chart-2/10 px-3 font-mono text-sm font-medium text-chart-2 tabular-nums">
              {milestone.version}
            </span>
            <p className="text-sm text-muted-foreground leading-relaxed">
              <Emphasised parts={milestone.sentence} />
            </p>
          </li>
        ))}
      </ul>

      <p className="text-sm text-muted-foreground leading-relaxed">
        Merged, not opened — reviewing and revising a task takes days of
        back-and-forth, so a PR opened close to a deadline is unlikely to land
        in time.
      </p>
    </section>
  );
}
