# Workflow: Lint (consistency checks)

Triggered by `/llm-wiki-lint [bundle]`, or as the second step of
`/llm-wiki-maintenance` (bundle scope: see AGENTS.md, "Bundle scope for
Ingest / Lint / Maintenance"). Read this file in full before running the
command. Runs once per bundle in scope, independent of whether Ingest
just ran or not. If script execution is available, `scripts/
wiki_lint.py lint <bundle-dir>` (see AGENTS.md, "Optional helper
scripts") computes the deterministic rows below in one pass; otherwise
perform the equivalent check by reading the files directly. Per-finding
behavior:

| Finding | Behavior |
|---|---|
| Missing/incomplete frontmatter field | auto-fill only if unambiguous (e.g. a missing `updated:` → today's date); otherwise report |
| Dead link (target file doesn't exist) | auto-fix only if exactly one existing page is an unambiguous match for the link target; otherwise report, don't guess |
| Orphaned page (no incoming links) | report |
| Open contradiction not yet resolved | report |
| Taxonomy deviation (folder without a matching type, or vice versa) | **ask before changing anything** — never silently add/remove a type or move files |
| `index.md` Mermaid graph mismatch vs. actual links | deterministically regenerate the graph per the algorithm in SPEC.md, "Graph / relationships" |
| Raw file referenced by a source summary but missing from `raw/` | report — never delete the summary or recreate the file |
| Source summary with `ingest_status` other than `processed`/absent | report as a reminder it's still unresolved (see `workflows/ingest.md`, step 2b) — never auto-retry |
| Typed page with a `valid_until` date in the past | report — never auto-mark the page stale or remove content; the user decides whether it needs a fresh source or a `status: historical` update |
| Two raw files with identical content hash (`scripts/wiki_lint.py`'s `duplicate_raw_files`) | report — likely accidental duplicate upload; never delete either file |
| Source summary's stored `raw_hash` doesn't match the actual raw file's hash (`scripts/wiki_lint.py`'s `raw_hash_mismatches`) | report — this shouldn't happen given `raw/` immutability; investigate rather than auto-correcting either value |

Report findings, with bundle tag (see AGENTS.md, "Bundle tag in
responses"). If run across all bundles, one such section per bundle.

If Lint actually changes anything (auto-fills, auto-fixed dead links,
regenerated Mermaid graph), that's its own commit (or several, if
thematically separate) — see AGENTS.md, "Git & Versioning". Pure
findings with no change need no commit and don't require acquiring the
advisory lock.
