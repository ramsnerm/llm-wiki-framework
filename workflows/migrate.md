# Workflow: Migrate an existing wiki into a bundle

Triggered by `/llm-wiki-migrate <path-or-repo> [bundle]`, or when the
user wants an existing collection of notes — an Obsidian vault, another
LLM-wiki instance, a folder of Markdown, an exported knowledge base —
brought into this framework. Read this file in full before running it.

This is a one-time, high-risk operation: it is the only workflow that
takes in content someone else's tool produced, at a scale where
improvising is tempting. Follow the steps; do not shortcut them because
the source folder "looks like a wiki already".

**The rule everything else follows from**: nothing is imported directly
as a wiki page. Every file is copied into `raw/` unchanged and ingested
from there, so each resulting page cites something that actually exists.
What a file is cited *as* depends on what it can vouch for — an original
document stands as a source in its own right, a page from the old wiki
stands only as "this is what the previous wiki said, as of this date"
(step 3 sorts the two apart). Never invent a source for imported
content, and never write a typed page whose claims trace back to
nothing.

## 1. Understand what is being migrated, before touching anything

Ask, unless the user already said:

- Where the existing material is (path, or repo URL to clone somewhere
  outside this repo — never clone it into `bundles/`).
- Whether it should become **one** bundle or several. A vault covering
  three unrelated domains is three bundles; deciding that now is much
  cheaper than splitting later.
- Whether anything in it must **not** be migrated (private notes, drafts,
  material belonging to someone else).
- Whether it already keeps original source files of its own — see step
  2b, which is where that case is handled.

Then look at it and report back before doing anything:

- how many files, which formats, roughly what topics
- what structure it already has (folders, tags, frontmatter, naming)
- anything you cannot read (binaries, proprietary formats, encrypted
  files) — these are named now, not discovered silently later
- app-specific syntax that will not survive as-is: `[[wikilinks]]`,
  Obsidian callouts, Dataview queries, plugin blocks

Do not proceed until the user has confirmed the scope.

## 2. Propose a taxonomy derived from what is there

The existing structure is already an argument about the subject — folder
names, tags and recurring page shapes encode how the author thought
about it. Use it rather than starting from a blank taxonomy dialogue:

1. Derive a proposed taxonomy from the existing folders, tags and page
   types — which knowledge types exist, which folders they map to.
2. Show it as a proposal, side by side with what it came from ("your
   `people/` becomes `entities/`; `moc/` pages look like index pages,
   not knowledge pages").
3. Say plainly what does **not** map cleanly, and ask — never fold an
   awkward category silently into a neighbouring one.
4. Only after confirmation, create the bundle per
   `workflows/create-bundle.md` with the agreed taxonomy, including the
   content language question.

If the source is another instance of this framework (it has a
`bundles/<name>/index.md` with a taxonomy in its frontmatter), take that
taxonomy as the proposal directly, and say so.

## 3. Sort primary sources from derived pages

Ask and look, before archiving anything. A collection built along the
Karpathy pattern — or another instance of this framework, or an OKF
wiki — usually keeps its own `raw/` (or `sources/`, `attachments/`,
`assets/`) holding the *actual* originals: PDFs, articles, transcripts,
exports. That changes what is being migrated, so establish it now.

The distinction that matters is what a file can vouch for:

- **A primary source** — the PDF, the article, the transcript — vouches
  for its own content. It belongs in the new `raw/` as a source in its
  own right, exactly as if the user had just added it.
- **A derived page** — a wiki page someone wrote from those sources —
  vouches only for what the previous wiki said. That is the case step 4
  handles: the page becomes its own source, cited as such.

Treating a real PDF as if it were "the previous wiki's claim about
itself" throws away provenance the user already had. Treating a derived
page as a primary source invents provenance that never existed. Both are
wrong; which one applies is a property of the file, so sort them:

1. **Primary sources** keep their identity: archived into `raw/` under
   their own names — no prefix, since they are not imported wiki content
   but the material that wiki was built from — and ingested as ordinary
   sources. Where the old system
   recorded a hash, compare it — if it still matches, say so in the
   source summary; if it does not, the file changed after it was
   recorded and that is worth reporting.
2. **Derived pages** are archived under the `imported-<source-name>/`
   prefix and ingested as in step 4, with their source summary stating
   plainly that this is a page from the previous wiki, not an original.
3. **The old system's own source summaries**, if it had any, are
   archived too. They often carry the link, date or citation of a
   primary source that is otherwise lost — read them for that, and carry
   those references into the new source summaries.
4. **Deduplicate by content hash** across everything copied in. A
   migrated collection frequently holds the same PDF twice under two
   names; the second copy is skipped and the skip is reported, never
   silently dropped.

When both exist for the same knowledge, the primary source carries the
factual claims and the derived page contributes only what it adds:
synthesis, structure, connections someone drew by hand. Cite each for
what it actually supports, rather than backing a claim with the page
that merely repeated it.

If a derived page cites a primary source that was **not** migrated — a
URL, a book, a paper that never existed as a file — carry that reference
across as a citation, and do not invent a raw file for it.

## 4. Archive the originals in `raw/`

Copy every in-scope file into `bundles/<name>/raw/` **unchanged**:

- **Primary sources** (step 3) go directly into `raw/` under their own
  filenames — not under any prefix. They are sources in their own right,
  and filing them as imported wiki content hides the distinction step 3
  exists to draw. On a name collision, suffix `-02`, `-03`, …
- **Derived pages** keep their original relative structure under a
  single prefix, `raw/imported-<source-name>/<original path>`, so it
  stays obvious what came from where and nothing collides.
- Never edit, reformat, rename beyond the prefix, or "clean up" a file on
  the way in. `raw/` is append-only and immutable — see AGENTS.md,
  "Deleting & Editing". Conversion happens later, on the typed pages,
  never on the archived original.
- On a filename collision, suffix `-02`, `-03`, … as everywhere else.
- Binaries and unreadable files are copied in too, and each gets a
  `blocked`/`unsupported` source-summary record per `workflows/ingest.md`
  — so they are visibly present rather than quietly dropped.

One commit for this step, separate from everything that follows:
`migrate: <bundle> — archive <n> source files`. This is the point of no
return worth having on its own — if the rest goes wrong, the originals
are already safely in Git.

## 5. Ingest, in batches, with the user watching

From here on this is `workflows/ingest.md`, with three additions:

- **Work in batches**, not all at once: a coherent group of files
  (one folder, one topic), then a short report, then the next. A
  migration of two hundred files reported only at the end is impossible
  to check, and a taxonomy mistake in file three would be repeated two
  hundred times.
- **Convert app-specific syntax** as it is written into typed pages:
  `[[wikilinks]]` become relative Markdown links where the target
  actually exists in the new bundle, and are otherwise turned into plain
  text — never a link to a page that does not exist. Callouts, Dataview
  blocks and plugin syntax become plain CommonMark or are dropped, and
  what was dropped is named in the report.
- **Every typed page cites its archived original** under `## Sources`,
  like any other ingested source. Where a claim came from somewhere the
  old wiki named — a URL, a book, a paper — carry that reference across
  as well, in the source summary.

Where two old pages clearly describe the same subject, apply the normal
page identity rules (SPEC.md, "Page identity matching") — do not merge on
topical similarity alone; ask.

## 6. Report what changed shape

After the last batch, give the user a written account of:

- how many source files were archived, how many typed pages resulted
- pages that were merged, and on what grounds
- content that was dropped or turned into plain text (plugin syntax,
  dead links, empty stubs), listed rather than summarised as "some"
- files recorded as blocked/unsupported
- contradictions found between old pages — these are surfaced, not
  resolved silently: an old wiki that grew over time usually contains a
  few, and they are exactly what the new one should record under
  `## Open contradictions`

Then run `/llm-wiki-lint` on the bundle and report its findings too.

## The original stays where it is

Migration never deletes, moves or modifies the source material. When it
is finished, the user still has their old wiki exactly as it was, and
decides for themselves whether to keep it. Say so at the end — nobody
should have to guess whether their previous work still exists.

## Commits

Per AGENTS.md, "Git & Versioning", plus the archive commit from step 4:

```
migrate: <bundle> — archive <n> source files
migrate: <bundle> — <batch description>
```

The advisory lock is acquired once for the whole migration and released
at the end, not per batch — a migration is one long operation on one
bundle, and a second agent should stay out of it throughout.
