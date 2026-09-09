# Workflow: Maintenance (Ingest, then Lint)

Triggered by `/llm-wiki-maintenance [bundle]` (bundle scope: see
AGENTS.md, "Bundle scope for Ingest / Lint / Maintenance"). Read this
file, `workflows/ingest.md`, and `workflows/lint.md` in full before
running the command. Runs the Ingest workflow followed immediately by
the Lint workflow, on the same bundle(s), and combines their reports
into one summary per bundle with a single bundle tag. This is the "do
both, I always want both" shortcut — functionally identical to running
`/llm-wiki-ingest` then `/llm-wiki-lint` back to back on the same scope.

**Framework-update note (once per run, not per bundle):** if
`FRAMEWORK-SYNC.md` exists at the repo root, Maintenance additionally
performs the read-only comparison step of "Checking for upstream
framework updates" (see `workflows/check-updates.md`) — steps 1–3 only
(fetch, compare, report which framework files differ) — and appends
that as its own short section at the end of the report, outside the
per-bundle sections. It does **not** pull anything itself; if any files
differ, it points the user at `/llm-wiki-check-updates` to review and
pull them individually. If `FRAMEWORK-SYNC.md` doesn't exist, this note
is skipped entirely — no mention, no attempted fetch, and no question
asked either (an automatic run shouldn't interrupt itself to ask where
the origin repo is — that's what makes this variant require
`FRAMEWORK-SYNC.md` while the standalone command doesn't; see
`workflows/check-updates.md`). If the origin repo isn't reachable,
report that plainly in this section rather than failing the whole
Maintenance run.

Commits and the advisory lock follow whatever Ingest and Lint would do
individually on the same scope — see AGENTS.md, "Git & Versioning".
Acquire the lock once for the whole Maintenance run rather than
separately for its Ingest and Lint halves.
