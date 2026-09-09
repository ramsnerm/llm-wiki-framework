# Workflow: Framework-file sync with the origin repo

Covers both directions of keeping this instance's framework files
(`AGENTS.md`, `workflows/*.md`, `SKILL.md`, `SPEC.md`, `QUICKSTART.md`,
`README.md`, `templates/*`, `scripts/*`, `CLAUDE.md`, `GEMINI.md` — see
AGENTS.md, "Framework files vs. bundle content") in sync with the
public template they came from. `bundles/` content is never part of
either direction, regardless of anything in `FRAMEWORK-SYNC.md`. Read
this file in full before running `/llm-wiki-check-updates`, or before
proposing a framework-file change upstream.

## Direction 1: proposing this instance's changes upstream

`FRAMEWORK-SYNC.md`, if present at the repo root, holds this instance's
origin repository and the mechanism for proposing framework-file
changes back to it. It's **authored directly by the user** (its content
is static and known upfront — this repo's own origin doesn't change per
instance) — see `templates/framework-sync.md` for the expected
structure. The agent only ever **reads** it; it never creates, edits, or
regenerates it itself. If no such file exists — the default for any repo
generated from the public template — skip this entirely; there's nothing
to sync, for anyone, and this section has no effect.

When `FRAMEWORK-SYNC.md` exists and a **framework file** gets edited in
this instance: before committing, ask the user whether the same change
should also be proposed to the upstream repository, following whatever
`FRAMEWORK-SYNC.md` specifies. Never propose an upstream change
automatically, and never apply this to `bundles/` content under any
circumstance — bundle content stays local no matter what
`FRAMEWORK-SYNC.md` says. This genuinely depends on `FRAMEWORK-SYNC.md`
existing, because it needs its propose-upstream mechanism, not just the
origin location.

## Direction 2: checking whether the origin has newer framework files

The reverse — checking whether the origin template has newer framework
files than this instance — only needs to know *where* the origin repo
is, which is a much smaller ask and doesn't inherently require the rest
of `FRAMEWORK-SYNC.md`'s setup:

- **`/llm-wiki-check-updates`** — the full workflow, described below.
  Does **not** require `FRAMEWORK-SYNC.md` to exist. Determines the
  origin repo in this order: `FRAMEWORK-SYNC.md` if it exists → check
  available Git remotes (if Git access exists) for one that plausibly
  still points at the known public template repo — this is common when
  the instance was created via a plain `git clone` rather than Forgejo's
  "Generate Repository" (which starts independent history with no
  remote link back) — use that automatically, without asking → only if
  neither yields an answer, ask the user for the origin repo (owner/
  name, and URL if not obvious) just for this run. That's a one-time
  question, not a precondition for the command to work at all — always
  try to find the answer yourself before asking. Never write or create
  `FRAMEWORK-SYNC.md` from any of this — that file stays exclusively
  user-authored (see above); the origin determined here is used only
  for this check.
- **Inside `/llm-wiki-maintenance`** — a lightweight version: steps 1–3
  only (report which files differ), no pulling. This variant **does**
  require `FRAMEWORK-SYNC.md` to exist, since an automatic Maintenance
  run shouldn't interrupt itself with an unrelated question about where
  the origin repo lives, and checking Git remotes on every Maintenance
  run just for this note would be excessive. See
  `workflows/maintenance.md`.

Neither variant runs automatically or silently in the background outside
of being explicitly triggered — a direct `/llm-wiki-check-updates` call,
or being inside a Maintenance run. At most, mention once per chat that
`/llm-wiki-check-updates` exists if the user is working with a framework
file — never perform the check itself without being asked or without
being inside a Maintenance run.

1. Determine the origin repo — see the fallback order above (only
   applies to `/llm-wiki-check-updates` run directly; Maintenance's
   built-in note skips entirely if `FRAMEWORK-SYNC.md` is absent, see
   above).
2. For each file in the "Framework files" list (AGENTS.md, "Framework
   files vs. bundle content", or `FRAMEWORK-SYNC.md`'s own list if that
   file exists and specifies one — keep both lists in sync when a file
   is added to the framework), fetch its current content from the
   origin repo's default branch (via whatever Git/repo tool is
   available) and compare against the local copy.
3. Report per file: identical / differs / missing locally / missing
   upstream. For files that differ, a short summary of what changed is
   enough — not a full diff dump, unless the user asks for one.
4. For each file that differs, ask the user **individually** whether to
   pull the upstream version into this instance — never a blanket
   "update everything" without per-file confirmation. (This step and
   the next only apply when running `/llm-wiki-check-updates` directly
   — Maintenance's built-in note stops after step 3.)
5. If confirmed for a file: overwrite the local file with the upstream
   version — say plainly, before doing it, that any local edits to that
   file are then lost — then commit that file on its own (see AGENTS.md,
   "Git & Versioning", for the commit message pattern).
6. If the origin repo isn't reachable (no suitable tool, auth failure,
   etc.), report that plainly rather than guessing or staying silent.

Pulling an upstream framework file is its own commit per file — see
AGENTS.md, "Git & Versioning".
