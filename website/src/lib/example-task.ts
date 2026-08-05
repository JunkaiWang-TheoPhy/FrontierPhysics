import filePaths from "@/data/example-task-files.json";
import matter from "gray-matter";
import fs from "node:fs";
import path from "node:path";

/**
 * The showcased example task, vendored as a snapshot of PR #23
 * (benchflow-ai/FrontierPhysics#23) so the site can show the package before —
 * and independently of — the PR merging. The file list lives in
 * `src/data/example-task-files.json`, and the viewable file contents under
 * `public/example-task/`; metadata mirrors the task.md frontmatter.
 */
export const exampleTask = {
  id: "surface-ion-trap-shuttling",
  difficulty: "hard",
  subcategory: "trapped-ions",
  taskTypes: ["calculation", "simulation", "optimization"],
} as const;

export interface ConfigRow {
  label: string;
  /** A scalar renders as text, a list as chips. */
  value: string | string[];
}

export interface ConfigGroup {
  /** Top-level YAML section, e.g. `metadata`; null for root scalars. */
  title: string | null;
  rows: ConfigRow[];
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** `schema_version` → `schema version`. */
function humanize(key: string): string {
  return key.replace(/_/g, " ");
}

/** Folds unit suffixes into the value: `timeout_sec: 900` → `timeout` / `900 s`. */
function scalarRow(key: string, value: unknown): ConfigRow {
  if (typeof value === "number") {
    if (key.endsWith("_sec")) {
      return { label: humanize(key.slice(0, -4)), value: `${value} s` };
    }
    if (key.endsWith("_mb")) {
      return { label: humanize(key.slice(0, -3)), value: `${value} MB` };
    }
  }
  return { label: humanize(key), value: String(value) };
}

function toRows(section: Record<string, unknown>): ConfigRow[] {
  const rows: ConfigRow[] = [];
  for (const [key, value] of Object.entries(section)) {
    if (Array.isArray(value)) {
      rows.push({ label: humanize(key), value: value.map(String) });
    } else if (isPlainObject(value)) {
      const entries = Object.entries(value);
      if (
        entries.length > 0 &&
        entries.every(([, v]) => typeof v === "boolean")
      ) {
        // A map of switches, e.g. `hardening` — show the enabled ones.
        rows.push({
          label: humanize(key),
          value: entries.filter(([, v]) => v).map(([k]) => humanize(k)),
        });
      } else {
        for (const sub of toRows(value)) {
          rows.push({ ...sub, label: `${humanize(key)} ${sub.label}` });
        }
      }
    } else {
      rows.push(scalarRow(key, value));
    }
  }
  return rows;
}

/**
 * The task.md frontmatter as display groups — one per top-level YAML section,
 * after a leading group for root scalars — read from the vendored snapshot at
 * build time so the config panel cannot drift from the file the tree viewer
 * opens.
 */
export function getExampleTaskConfig(): ConfigGroup[] {
  const taskFile = fs.readFileSync(
    path.join(process.cwd(), "public", "example-task", "task.md"),
    "utf8",
  );
  const { data } = matter(taskFile);

  const rootRows: ConfigRow[] = [];
  const groups: ConfigGroup[] = [];
  for (const [key, value] of Object.entries(data)) {
    if (isPlainObject(value)) {
      groups.push({ title: humanize(key), rows: toRows(value) });
    } else if (Array.isArray(value)) {
      rootRows.push({ label: humanize(key), value: value.map(String) });
    } else {
      rootRows.push(scalarRow(key, value));
    }
  }

  return [{ title: null, rows: rootRows }, ...groups].filter(
    (group) => group.rows.length > 0,
  );
}

export interface TreeNode {
  name: string;
  /** Path relative to the task root; the expand/collapse key. */
  path: string;
  type: "dir" | "file";
  children?: TreeNode[];
  /** Dirs shown closed with a file count instead of their contents. */
  lockedFileCount?: number;
}

/** Bulky asset mirrors that stay closed in the browser view. */
const LOCKED_DIRS = new Set(["oracle/assets", "verifier/assets"]);

interface MutableDir {
  dirs: Map<string, MutableDir>;
  files: string[];
}

export function getExampleTaskTree(): TreeNode[] {
  const root: MutableDir = { dirs: new Map(), files: [] };

  for (const filePath of filePaths) {
    const parts = filePath.split("/");
    let current = root;
    for (const part of parts.slice(0, -1)) {
      let dir = current.dirs.get(part);
      if (!dir) {
        dir = { dirs: new Map(), files: [] };
        current.dirs.set(part, dir);
      }
      current = dir;
    }
    current.files.push(parts[parts.length - 1]);
  }

  return toNodes(root, "");
}

function countFiles(dir: MutableDir): number {
  let count = dir.files.length;
  for (const sub of dir.dirs.values()) count += countFiles(sub);
  return count;
}

/** Directories first, each group alphabetical — the GitHub tree order. */
function toNodes(dir: MutableDir, prefix: string): TreeNode[] {
  const dirNodes = [...dir.dirs.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, sub]): TreeNode => {
      const path = prefix ? `${prefix}/${name}` : name;
      if (LOCKED_DIRS.has(path)) {
        return { name, path, type: "dir", lockedFileCount: countFiles(sub) };
      }
      return { name, path, type: "dir", children: toNodes(sub, path) };
    });

  const fileNodes = [...dir.files]
    .sort((a, b) => a.localeCompare(b))
    .map(
      (name): TreeNode => ({
        name,
        path: prefix ? `${prefix}/${name}` : name,
        type: "file",
      }),
    );

  return [...dirNodes, ...fileNodes];
}
