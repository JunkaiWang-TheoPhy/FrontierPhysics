"use client";

import type { TreeNode } from "@/lib/example-task";
import { CodeLines } from "@/components/TaskFileView";
import {
  ChevronRight,
  File,
  Folder,
  FolderOpen,
  WrapText,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

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
  /** File opened in the viewer on first render. */
  defaultSelected?: string;
}

/**
 * A GitHub/VS Code-style split browser for a task package: the file tree
 * stays as a left sidebar and the selected file renders in the pane beside
 * it, fetched read-only from the static snapshot under
 * `public/example-task/`, so nothing links out to a branch that may move or
 * merge.
 */
export function TaskFileTree({
  rootLabel,
  nodes,
  defaultOpen = [],
  defaultSelected,
}: TaskFileTreeProps) {
  const [open, setOpen] = useState<ReadonlySet<string>>(
    () => new Set(defaultOpen),
  );
  const [view, setView] = useState<FileView | null>(() =>
    defaultSelected ? { path: defaultSelected, status: "loading" } : null,
  );
  const [wrap, setWrap] = useState(true);
  const viewPathRef = useRef<string | null>(defaultSelected ?? null);
  const cache = useRef(new Map<string, string>());

  const loadFile = (path: string) => {
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

  const fetchFile = (path: string) => {
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
    loadFile(path);
  };

  // The default file starts in the "loading" state from the useState
  // initializer; the mount effect only performs the fetch itself.
  useEffect(() => {
    if (defaultSelected) loadFile(defaultSelected);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden text-left">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5 font-mono text-xs text-muted-foreground">
        <span className="truncate" title={`${rootLabel}${view?.path ?? ""}`}>
          {rootLabel}
          {view && <span className="text-foreground">{view.path}</span>}
        </span>
        {view && (
          <button
            type="button"
            onClick={() => setWrap((w) => !w)}
            aria-pressed={wrap}
            title={wrap ? "Disable word wrap" : "Enable word wrap"}
            className={`ml-auto inline-flex shrink-0 items-center gap-1 rounded-md border border-border px-2 py-1 cursor-pointer transition-colors ${
              wrap
                ? "bg-accent text-foreground"
                : "bg-muted text-muted-foreground hover:bg-accent hover:text-foreground"
            }`}
          >
            <WrapText className="h-3.5 w-3.5" aria-hidden="true" />
            Wrap
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[15rem_minmax(0,1fr)]">
        <div className="max-h-48 overflow-y-auto border-b border-border p-2 md:max-h-[560px] md:border-b-0 md:border-r">
          <TreeLevel
            nodes={nodes}
            depth={0}
            open={open}
            selected={view?.path ?? null}
            onToggle={toggle}
            onOpenFile={fetchFile}
          />
        </div>
        <div className="max-h-[560px] overflow-auto">
          {view ? (
            <FileContent view={view} wrap={wrap} />
          ) : (
            <p className="px-5 py-10 text-center font-mono text-xs text-muted-foreground">
              Select a file to view it.
            </p>
          )}
        </div>
      </div>
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

  return <CodeLines text={view.text} path={view.path} wrap={wrap} />;
}

function TreeLevel({
  nodes,
  depth,
  open,
  selected,
  onToggle,
  onOpenFile,
}: {
  nodes: TreeNode[];
  depth: number;
  open: ReadonlySet<string>;
  selected: string | null;
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
            selected={selected === node.path}
            onToggle={onToggle}
            onOpenFile={onOpenFile}
          />
          {node.children && open.has(node.path) && (
            <TreeLevel
              nodes={node.children}
              depth={depth + 1}
              open={open}
              selected={selected}
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
  selected,
  onToggle,
  onOpenFile,
}: {
  node: TreeNode;
  depth: number;
  open: boolean;
  selected: boolean;
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
        aria-current={selected ? "true" : undefined}
        className={`${rowClass} cursor-pointer transition-colors ${
          selected
            ? "bg-accent text-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-foreground"
        }`}
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
