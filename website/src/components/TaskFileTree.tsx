"use client";

import type { TreeNode } from "@/lib/example-task";
import { CodeLines } from "@/components/TaskFileView";
import {
  ArrowLeft,
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  WrapText,
} from "lucide-react";
import { useRef, useState } from "react";

/** Where the vendored task files are served from (see next.config.ts). */
const ASSET_BASE = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/example-task`;

/** Formats without a text preview; everything else opens in the viewer. */
const BINARY_EXTENSIONS = [".npz", ".stl", ".png", ".npy", ".h5"];

type FileView =
  | { path: string; status: "loading" }
  | { path: string; status: "binary" }
  | { path: string; status: "error" }
  | { path: string; status: "ready"; text: string };

interface TaskFileTreeProps {
  /** Shown in the header bar, e.g. `tasks/<task-id>/`. */
  rootLabel: string;
  nodes: TreeNode[];
  /** Directory paths expanded on first render. */
  defaultOpen?: string[];
}

/**
 * A GitHub-style file browser for a task package. Directories expand in
 * place; files open in a read-only viewer fetched from the static snapshot
 * under `public/example-task/`, so nothing links out to a branch that may
 * move or merge.
 */
export function TaskFileTree({
  rootLabel,
  nodes,
  defaultOpen = [],
}: TaskFileTreeProps) {
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(defaultOpen),
  );
  const [view, setView] = useState<FileView | null>(null);
  const [wrap, setWrap] = useState(true);
  const viewPathRef = useRef<string | null>(null);
  const cache = useRef(new Map<string, string>());

  const toggle = (path: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });

  const openFile = (path: string) => {
    viewPathRef.current = path;

    if (BINARY_EXTENSIONS.some((ext) => path.endsWith(ext))) {
      setView({ path, status: "binary" });
      return;
    }

    const cached = cache.current.get(path);
    if (cached !== undefined) {
      setView({ path, status: "ready", text: cached });
      return;
    }

    setView({ path, status: "loading" });
    fetch(`${ASSET_BASE}/${path}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((text) => {
        cache.current.set(path, text);
        if (viewPathRef.current === path) {
          setView({ path, status: "ready", text });
        }
      })
      .catch(() => {
        if (viewPathRef.current === path) {
          setView({ path, status: "error" });
        }
      });
  };

  const closeFile = () => {
    viewPathRef.current = null;
    setView(null);
  };

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden text-left">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5 font-mono text-xs text-muted-foreground">
        {view ? (
          <>
            <button
              type="button"
              onClick={closeFile}
              aria-label="Back to file list"
              className="inline-flex shrink-0 items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 cursor-pointer text-foreground hover:bg-accent transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              Files
            </button>
            <span className="truncate" title={`${rootLabel}${view.path}`}>
              {rootLabel}
              <span className="text-foreground">{view.path}</span>
            </span>
            <span className="ml-auto flex shrink-0 items-center gap-1.5">
              <button
                type="button"
                onClick={() => setWrap((w) => !w)}
                aria-pressed={wrap}
                title={wrap ? "Disable word wrap" : "Enable word wrap"}
                className={`inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 cursor-pointer transition-colors ${
                  wrap
                    ? "bg-accent text-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
                }`}
              >
                <WrapText className="h-3.5 w-3.5" aria-hidden="true" />
                Wrap
              </button>
            </span>
          </>
        ) : (
          <span className="px-1 py-1">{rootLabel}</span>
        )}
      </div>

      {view ? (
        <FileContent view={view} wrap={wrap} />
      ) : (
        <div className="max-h-[480px] overflow-y-auto p-2">
          <TreeLevel
            nodes={nodes}
            depth={0}
            open={open}
            onToggle={toggle}
            onOpenFile={openFile}
          />
        </div>
      )}
    </div>
  );
}

function FileContent({ view, wrap }: { view: FileView; wrap: boolean }) {
  if (view.status !== "ready") {
    const message = {
      loading: "Loading…",
      binary: "Binary file — no preview on the website.",
      error: "Could not load this file.",
    }[view.status];
    return (
      <p className="px-5 py-10 text-center font-mono text-xs text-muted-foreground">
        {message}
      </p>
    );
  }

  return (
    <div className="max-h-[560px] overflow-auto">
      <CodeLines text={view.text} path={view.path} wrap={wrap} />
    </div>
  );
}

function TreeLevel({
  nodes,
  depth,
  open,
  onToggle,
  onOpenFile,
}: {
  nodes: TreeNode[];
  depth: number;
  open: ReadonlySet<string>;
  onToggle: (path: string) => void;
  onOpenFile: (path: string) => void;
}) {
  return (
    <ul>
      {nodes.map((node) => (
        <li key={node.path}>
          <TreeRow
            node={node}
            depth={depth}
            open={open.has(node.path)}
            onToggle={onToggle}
            onOpenFile={onOpenFile}
          />
          {node.children && open.has(node.path) && (
            <TreeLevel
              nodes={node.children}
              depth={depth + 1}
              open={open}
              onToggle={onToggle}
              onOpenFile={onOpenFile}
            />
          )}
        </li>
      ))}
    </ul>
  );
}

function TreeRow({
  node,
  depth,
  open,
  onToggle,
  onOpenFile,
}: {
  node: TreeNode;
  depth: number;
  open: boolean;
  onToggle: (path: string) => void;
  onOpenFile: (path: string) => void;
}) {
  const indent = { paddingLeft: `${depth * 14 + 8}px` };
  const rowClass =
    "flex w-full items-center gap-2 rounded-md px-2 py-1 font-mono text-[13px]";

  if (node.type === "file") {
    return (
      <button
        type="button"
        onClick={() => onOpenFile(node.path)}
        className={`${rowClass} cursor-pointer text-muted-foreground hover:bg-accent hover:text-foreground transition-colors`}
        style={indent}
      >
        <span className="w-3.5 shrink-0" aria-hidden="true" />
        <File
          className="h-3.5 w-3.5 shrink-0 text-muted-foreground/60"
          aria-hidden="true"
        />
        <span className="truncate">{node.name}</span>
      </button>
    );
  }

  if (node.lockedFileCount !== undefined) {
    return (
      <div
        className={`${rowClass} text-muted-foreground`}
        style={indent}
        title="Assets are not expanded on the website"
      >
        <span className="w-3.5 shrink-0" aria-hidden="true" />
        <Folder
          className="h-3.5 w-3.5 shrink-0 text-chart-2/60"
          aria-hidden="true"
        />
        <span className="truncate">{node.name}</span>
        <span className="ml-auto shrink-0 rounded-full border border-border bg-muted px-2 py-0.5 text-xxs">
          {node.lockedFileCount} files
        </span>
      </div>
    );
  }

  const FolderIcon = open ? FolderOpen : Folder;
  return (
    <button
      type="button"
      onClick={() => onToggle(node.path)}
      aria-expanded={open}
      className={`${rowClass} cursor-pointer text-foreground hover:bg-accent transition-colors`}
      style={indent}
    >
      <ChevronRight
        className={`h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform ${
          open ? "rotate-90" : ""
        }`}
        aria-hidden="true"
      />
      <FolderIcon
        className="h-3.5 w-3.5 shrink-0 text-chart-2"
        aria-hidden="true"
      />
      <span className="truncate">{node.name}</span>
    </button>
  );
}
