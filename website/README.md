# FrontierPhysics website

The public site for [FrontierPhysics](https://github.com/benchflow-ai/FrontierPhysics),
built with Next.js and Tailwind. Two pages — a landing page and a contributor
guide — which is all this benchmark needs while it is still work in progress.

## Run locally

```bash
cd website
npm install
npm run dev
# open http://localhost:3000/frontierphysics
```

The path is not a typo — the site is served from a sub-path in production, and
`basePath` applies in development too so local matches deployed. To run it at a
root instead, set `BASE_PATH=` (empty).

`npm run build` produces the production build; `npm start` serves it.

## Pages

| Route | Purpose |
|---|---|
| `/` | Hero, task anatomy, live task list, contribution CTA |
| `/contribute` | What makes a good task, the four steps, the AI-delegation boundary, pre-PR checks |

## Layout

```text
src/
  app/
    layout.tsx        # navbar + footer + theme provider
    page.tsx          # landing page
    contribute/       # contributor guide
    globals.css       # design tokens
  components/
    Navbar.tsx        # floating pill nav with theme switcher
    Footer.tsx
    HeroBackground.tsx # animated atom field + vignette behind the hero
    Atoms.tsx         # canvas atom lattice, drifting diagonally
    ui/button.tsx
  lib/
    site.ts           # every external link, plus the authorship point values
    tasks.ts          # reads ../tasks/*/task.md at build time
```

`src/lib/` is re-included by `website/.gitignore`. The repository root
`.gitignore` excludes `lib/` as a Python packaging convention, which would
otherwise drop this directory from commits without any error.

## Editing notes

- **Colours and radii** are CSS custom properties in `globals.css`. Both light
  and dark are defined; the navbar switcher writes `class="dark"` on `<html>`.
- **Task cards are generated**, not hand-written. `lib/tasks.ts` reads
  `../tasks/*/task.md` frontmatter at build time, so the list cannot drift out
  of sync with the repository the way a hand-maintained list would.
- **All outbound links live in `lib/site.ts`.** Change them in one place.
- **No benchmark results are published yet.** There is deliberately no
  leaderboard and no performance claim anywhere on the site — add those only
  when the task set is large enough to support them.

## Deploy

The site is published at **<https://www.benchflow.ai/frontierphysics>**, as its
own deployment that benchflow.ai proxies to. Keeping it a separate project means
this repository owns its own release cycle and a broken build here cannot take
down any other page on benchflow.ai.

`basePath` is already set to `/frontierphysics` in `next.config.ts`, so the
build emits correctly prefixed assets and links.

### 1. Create the project (once)

Point a new Vercel project at this repository with:

| Setting | Value |
|---|---|
| Root Directory | `website` |
| Framework preset | Next.js |
| Build / install command | default |

Leave "Include files outside the root directory" **enabled** — the build reads
`../tasks/*/task.md` to generate the task cards and will fail without the whole
repository checked out.

`vercel.json` sets an `ignoreCommand` so a push that touches neither `website/`
nor `tasks/` is skipped rather than rebuilt.

### 2. Route benchflow.ai to it (once, in the benchflow.ai repo)

Add a rewrite so the sub-path is served from this deployment. Nothing else on
the site is affected — only the `/frontierphysics` prefix is matched:

```json
{
  "rewrites": [
    {
      "source": "/frontierphysics/:path*",
      "destination": "https://<this-project>.vercel.app/frontierphysics/:path*"
    }
  ]
}
```

Keep `/frontierphysics` in the destination: this deployment serves under that
prefix, so stripping it would 404.

### Continuous deployment

Vercel's Git integration redeploys on every push to `main` that touches
`website/` or `tasks/`; no tokens or secrets are needed in this repository.

`.github/workflows/website.yml` is the correctness gate that runs alongside it —
it installs from the lockfile, lints, builds, and asserts that every task in
`tasks/` actually appears in the rendered page, so an empty task list fails CI
instead of shipping quietly.

### Serving from somewhere else

Any static-capable Next.js host works. Set the root directory to `website`,
ensure the whole repository is checked out, and set `BASE_PATH` to whatever
prefix that host serves from — or to an empty string to serve from a domain
root.
