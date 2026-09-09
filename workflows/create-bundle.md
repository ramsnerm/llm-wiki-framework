# Workflow: Create new bundle

Triggered by `/llm-wiki-add-bundle`. Read this file in full before
running the command — see AGENTS.md, "Workflow files", for why.

**Never** create a folder structure unprompted — it's always established
through the following dialogue:

1. Ask the user (compact, doesn't need to be all at once):
   - Name/short label for the bundle?
   - What's it about, in 1-2 sentences?
   - What recurring "kinds of knowledge" come to mind that would each
     deserve their own pages? (Examples for orientation, not prescriptive:
     for standards/RAMS e.g. standards, requirements, terms — for tool
     landscapes e.g. tools, concepts/patterns, comparisons — for people
     research e.g. people, organizations, events)
   - Does it need its own category for cross-cutting/comparison analyses?
   - Content language, if different from the repo default (English)?
2. Normalize the bundle name: it must match `^[a-z0-9][a-z0-9-]{0,62}$`
   (lowercase, digits, hyphens, starting with a letter/digit). If the
   user's suggested name doesn't match, propose a normalized version
   (lowercase it, replace spaces/invalid characters with hyphens, strip
   anything else) and confirm it with the user before using it. The
   resulting path must resolve inside `bundles/` — never accept `../`,
   an absolute path, or anything that would place the bundle outside
   that folder, and never follow symlinks pointing outside the repo.
   (This is a different normalization than "Page identity matching" in
   SPEC.md — that one is for matching subjects to existing pages, this
   one is filesystem-path safety for the bundle name itself.)
3. Build a **taxonomy proposal** from the answers: a list of `type` values
   with folder names and a one-line description each. `raw` (unmodified
   sources, no `type`) and `source` (folder `sources/`, summaries) are
   always fixed, plus the types derived from the conversation.
4. Show the proposal to the user, ask explicitly: "Set it up like this, or
   adjust?". Only implement after confirmation — on adjustment requests,
   revise the proposal and present it again.
5. After confirmation:
   - Create `bundles/<name>/index.md` (taxonomy in frontmatter, template:
     `templates/bundle-index.md`) — set `default_language:` in the
     frontmatter from the answer to the content-language question in
     step 1 (default `en` if the user didn't specify one)
   - Create `bundles/<name>/log.md`
   - Create `bundles/<name>/raw/` and `bundles/<name>/sources/`, plus one
     folder per confirmed type (`.gitkeep` for each empty folder)
   - Update the root `README.md` with the new bundle entry in the bundle
     overview
   - If this is the **first** bundle in the repo: create
     `bundles/.default-bundle` with the name (persistent default)
6. Then proceed normally into `workflows/ingest.md`, scoped to this
   bundle.

One commit for the entire setup (`index.md`, `log.md`, folders, README
entry, `.default-bundle` if applicable) — see AGENTS.md, "Git &
Versioning", for the full commit/push discipline, including the remote-
state check and the advisory lock this workflow acquires and releases
around that commit.
