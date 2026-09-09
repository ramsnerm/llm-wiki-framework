# Workflow: Ingest (process new raw sources)

Triggered by `/llm-wiki-ingest [bundle]`, or as the first step of
`/llm-wiki-maintenance` (bundle scope: see AGENTS.md, "Bundle scope for
Ingest / Lint / Maintenance"). **No** source argument — the agent scans
by itself. Read this file in full before running the command. Runs once
per bundle in scope:

`raw/` is immutable and append-only for the agent (see AGENTS.md,
Rules), so a file already referenced by a source summary can never
legitimately change — there is no "changed" case to detect. What the
hash is actually for:

1. List all files in `bundles/<name>/raw/`.
2. For each file, compute a content hash (e.g. SHA-256 — `scripts/
   wiki_lint.py hash <file>` if script execution is available, see
   AGENTS.md, "Optional helper scripts") and compare it against the
   `raw_ref`/`raw_hash` fields of the existing source summaries in
   `bundles/<name>/sources/`:
   - a source summary already has this exact `raw_ref` → already
     ingested (this includes files with `ingest_status: blocked` /
     `unsupported` / `needs-review` — see step 2b below), skip
   - the hash matches an existing source summary's `raw_hash` but under
     a **different** `raw_ref` → likely an accidental duplicate upload;
     flag it and ask the user rather than silently treating it as a new
     source
   - otherwise → **new** source

2b. **If a new file can't actually be read** — a scanned PDF with no
    extractable text layer, a password-protected file, an unsupported
    binary format, a corrupted archive, an empty file, or anything else
    that leaves you with no usable content — don't leave it with no
    record at all (that would make it look "new" again on every future
    Ingest run, forever). Instead:
    - Create a source summary (template: `templates/source-summary.md`)
      with `raw_ref` (path), `raw_hash` (current hash),
      `ingest_status: blocked` (can't be processed at all with current
      tooling) or `unsupported` (format genuinely out of scope) or
      `needs-review` (partially readable / ambiguous — flag for the
      user rather than guess), `ingest_error` (one short sentence on
      why), and `last_attempt` (today's date). Leave `## Summary` and
      `## Relevant pages` empty or a one-line placeholder — there's
      nothing to summarize.
    - Do **not** create or update any typed page for it.
    - Add a log.md entry (see SPEC.md, "Log format", for the "blocked"
      entry shape).
    - Report it clearly in the Ingest summary as blocked, with the
      reason — don't silently skip it and don't fail the whole run.
    - **On a later Ingest run**, this file's `raw_ref` already has a
      source summary, so step 1 skips it by default (no repeated
      failed attempts every run). If the user explicitly asks you to
      retry it (e.g. "try that PDF again, I OCR'd it externally" — note
      this only makes sense if the *raw file itself* changed, which per
      the immutability rule means a *new* raw file with a `supersedes`
      relationship, not editing the blocked one), process the new file
      normally; if instead the user just wants you to re-attempt
      extraction on the *same* raw file with better tooling, update
      `last_attempt` and either fill in the summary now (success) or
      update `ingest_error` (still blocked) — this is the one exception
      where a source summary's `ingest_status`/`ingest_error`/
      `last_attempt` fields get revised in place, since they describe
      the *attempt*, not the immutable raw content.
3. For each new file that *can* be read, **before writing anything**:
   fully read it and determine every taxonomy type it touches. Check
   whether all of those types already exist in the bundle's taxonomy
   (`bundles/<name>/index.md`).
   - If any needed type is missing, stop here for this source — ask the
     user whether the taxonomy should be extended, and update
     `bundles/<name>/index.md` accordingly, **before** creating or
     updating any page for this source. Don't discover a missing type
     partway through writing (e.g. after the source summary is already
     created) and leave the bundle half-updated.
   - Also check whether this source updates/corrects an already-ingested
     source on the same subject — either because the user said so when
     adding it, or because the content clearly overlaps with an existing
     source summary. If unsure, ask the user; never assume a supersede
     relationship silently.
     - If it **does** supersede an earlier source: set
       `supersedes: raw/<old-filename>` in the new source summary's
       frontmatter. When updating the affected typed pages, treat the
       new source as authoritative for the overlapping content and
       update those pages directly — this is a correction, not a
       contradiction, so it does **not** get filed under
       `## Open contradictions`. Still keep both source summaries and
       both `## Sources` links, so the correction stays traceable.
     - If it **doesn't** (independent new source, or the user confirms
       it's unrelated): process normally — contradictions with existing
       statements are handled as such (see below).
   - Once the taxonomy is confirmed complete and the supersede question
     resolved, make all the changes for this source together:
     - Create or update the source summary (template:
       `templates/source-summary.md`), including `raw_ref` (path),
       `raw_hash` (current hash), and `supersedes` if applicable. Short,
       dense summary — not a 1:1 copy of the source.
     - For each affected type: decide whether this is the **same
       subject** as an existing page or a **new** one. Only treat it as
       the same page when the subject matches that page's filename
       (its de facto id) or one of its declared `aliases:`, per the
       normalization procedure in SPEC.md, "Page identity matching" —
       never merge purely on semantic/topical similarity. If there's
       overlap but no id/alias match, ask the user whether it's the
       same subject (and should get an alias added) or a genuinely new
       page.
       - matching page confirmed? → update it, work in the info, add a
         link to the source summary
       - new page? → create it (template: `templates/typed-page.md`,
         set `type:` to the corresponding taxonomy value)
     - Contradictions between sources with **no** declared supersede
       relationship are **never overwritten silently** — note them
       under `## Open contradictions`, referencing both sources. The
       user decides what stands.
     - Traceability: every factual paragraph on the page must carry a
       relative Markdown link to the source summary that supports it.
       Conclusions you synthesize yourself (not directly stated in any
       one source) must be clearly marked as such — e.g. under a
       `## Synthesis` sub-heading or an inline "(synthesis)" note —
       rather than presented as if a source said it.
     - Freshness metadata (SPEC.md, typed-page frontmatter): if the
       source gives the content a clear temporal scope (a revision
       date, a version number, an explicit expiry), set `valid_from`/
       `valid_until` accordingly. Otherwise leave them unset — don't
       guess a date range that isn't actually stated.
     - Cross-references: link the **first meaningful occurrence** of
       another existing wiki page as a relative Markdown link. Ordinary
       terms don't need links, and never invent a link to a page that
       doesn't exist yet.
     - Update `bundles/<name>/index.md` (link new/changed pages, extend
       the Mermaid overview per the deterministic derivation algorithm
       in SPEC.md, "Graph / relationships").
     - Add one entry to `bundles/<name>/log.md` (template:
       `templates/log-entry.md`) — including the `supersedes`
       relationship where applicable.
4. Report new/superseded/blocked/skipped, with bundle tag (see AGENTS.md,
   "Bundle tag in responses"). If run across all bundles, one such
   section per bundle.

One commit per processed raw file (source summary + affected typed pages
+ `index.md` and `log.md` updates belong together in one commit — that's
the atomic, traceable unit that the `log.md` entry also describes). A
blocked-file record (step 2b) is its own small commit too. See
AGENTS.md, "Git & Versioning", for the full commit/push discipline,
including the remote-state check and the advisory lock this workflow
acquires and releases around its commits.
