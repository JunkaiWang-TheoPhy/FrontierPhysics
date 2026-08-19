"use client";

import Prism from "prismjs";
import "prismjs/components/prism-python";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-json";
import "prismjs/components/prism-yaml";
import "prismjs/components/prism-docker";
import "prismjs/components/prism-markdown";
import "./TaskFileView.css";

/** Prism grammar per file, by basename or extension; null renders plain. */
export function languageFor(path: string): string | null {
  const name = path.split("/").pop() ?? "";
  if (name === "Dockerfile") return "docker";
  const dot = name.lastIndexOf(".");
  const ext = dot >= 0 ? name.slice(dot) : "";
  const byExt: Record<string, string> = {
    ".py": "python",
    ".sh": "bash",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".md": "markdown",
    ".toml": "yaml",
  };
  return byExt[ext] ?? null;
}

interface Run {
  text: string;
  className?: string;
}

function flattenTokens(
  tokens: (string | Prism.Token)[],
  parentClass: string | undefined,
  out: Run[],
): void {
  for (const token of tokens) {
    if (typeof token === "string") {
      out.push({ text: token, className: parentClass });
      continue;
    }
    const className = `token ${token.type}`;
    const content = token.content;
    if (typeof content === "string") {
      out.push({ text: content, className });
    } else {
      flattenTokens(
        Array.isArray(content) ? content : [content],
        className,
        out,
      );
    }
  }
}

/**
 * Tokenize once over the whole file, then split token runs at newlines, so
 * multi-line tokens (docstrings, fenced blocks) keep their styling on every
 * line they span — the per-line gutter never breaks the grammar.
 */
function tokenLines(text: string, language: string | null): Run[][] {
  const grammar = language ? Prism.languages[language] : undefined;
  const runs: Run[] = [];
  if (grammar) {
    flattenTokens(Prism.tokenize(text, grammar), undefined, runs);
  } else {
    runs.push({ text });
  }

  const lines: Run[][] = [[]];
  for (const run of runs) {
    const parts = run.text.split("\n");
    parts.forEach((part, index) => {
      if (index > 0) lines.push([]);
      if (part) {
        lines[lines.length - 1].push({ text: part, className: run.className });
      }
    });
  }
  return lines;
}

export function CodeLines({
  text,
  path,
  wrap,
}: {
  text: string;
  path: string;
  wrap: boolean;
}) {
  const lines = tokenLines(text, languageFor(path));
  return (
    <pre className="task-code px-2 py-3 font-mono text-xs leading-5 text-foreground/90">
      {lines.map((runs, i) => (
        <div key={i} className="flex items-start">
          <span
            className="w-10 shrink-0 pr-3 text-right text-muted-foreground/50 select-none"
            aria-hidden="true"
          >
            {i + 1}
          </span>
          <span
            className={
              wrap
                ? "min-w-0 flex-1 whitespace-pre-wrap break-words"
                : "whitespace-pre"
            }
          >
            {runs.length === 0
              ? "​"
              : runs.map((run, j) => (
                  <span key={j} className={run.className}>
                    {run.text}
                  </span>
                ))}
          </span>
        </div>
      ))}
    </pre>
  );
}
