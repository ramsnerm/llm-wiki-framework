# Workflow: Query (answer a question) — strictly read-only

Triggered by `/llm-wiki-query [bundle] <question>` (default-bundle
resolution as in AGENTS.md, "Default-bundle resolution") or an informal
question in chat. Read this file in full before running the command.

**Query never writes, commits, or pushes anything — no exceptions**,
even if answering surfaces gaps in the wiki. It never acquires the
advisory lock (see AGENTS.md, "Git & Versioning") either — there is
nothing to coordinate around when nothing is being written.

1. First read `bundles/<name>/index.md` and the typed pages it links to
   — don't dig directly into `raw/`.
2. Only if the wiki pages don't cover the question, also inspect
   `sources/` and, if still insufficient, `raw/` — read-only, same as
   step 1.
3. Answer with a reference to the wiki page(s)/source(s) the info came
   from, and with the bundle tag (see AGENTS.md, "Bundle tag in
   responses"). If a page carries `valid_until` in the past or
   `status: historical`/`disputed` (see SPEC.md, typed-page
   frontmatter), say so plainly rather than presenting it as current
   fact.
4. If the answer reveals that relevant information exists only in
   `sources/`/`raw/` and hasn't been compiled into a typed page yet,
   say so and suggest running `/llm-wiki-ingest` — don't write anything
   yourself during Query, no matter how small the fix would be.
