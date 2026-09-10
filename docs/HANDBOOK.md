# Handbook

How this wiki works and how to use it. [`README.md`](../README.md) says
what the project is and why; this file is the reference you come back
to. Three parts: **Concepts**, what a bundle is, what holds everywhere,
and how the framework reaches your particular tool; **Everyday tasks**, one section per command in the order you
meet them; **One-time setup**, the two things you do once if your
situation calls for them.

The formal format specification lives in [SPEC.md](SPEC.md), and the
exact procedure an agent follows per command is in
[workflows/](../workflows/) — this file is for you, those are for it.

---

# Concepts

## Bundles

The wikis live under `bundles/` — one **bundle** per knowledge domain,
each an independent wiki with its own taxonomy. The rest of the repo is
the framework that maintains them.

Neither the term nor the split is ours: `bundle` is
[OKF](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf)'s
word for a knowledge directory, and
[okf-wiki](https://github.com/mchu1966/okf-wiki) already holds several.

Fixed in every bundle: `raw/` (unmodified sources), `sources/`
(summaries), `index.md` (taxonomy + overview), `log.md` (change log).
Every other folder follows from the bundle's own taxonomy, which is
worked out with the agent when the bundle is created — see
[workflows/create-bundle.md](../workflows/create-bundle.md) for the
procedure and [SPEC.md](SPEC.md) for the format.

## Conventions

These hold in every bundle, whatever its taxonomy:

- Cross-references as plain relative Markdown links (`[text](../x/y.md)`),
  no `[[wikilinks]]`
- Relationships/graphs as **Mermaid diagrams** directly in `index.md`,
  derived by a fully deterministic algorithm (see docs/SPEC.md)
- `raw/` is immutable per bundle
- Plain CommonMark + YAML frontmatter, no app-specific callouts/plugins

Format details in [SPEC.md](SPEC.md), agent behaviour in
[AGENTS.md](../AGENTS.md) and [workflows/](../workflows/).

## Repo layout

Everything outside `bundles/` is the framework; the wikis live inside it.
The full tree — including what a single bundle contains and the two
files that are easy to miss (`bundles/.default-bundle` and a bundle's
transient `.lock`) — is in [SPEC.md](SPEC.md), "Repo level". It is kept
in one place on purpose: a layout listed twice is a layout that goes
stale in one of them.

## Which tool reads what

| Tool                                  | reads natively            | bridge in this repo |
|----------------------------------------|----------------------------|---------------------------|
| OpenAI Codex, Cursor, Jules, Aider, Windsurf, Zed, Amp | [`AGENTS.md`](../AGENTS.md) directly (delegates to `workflows/*.md` per command) | — |
| Claude Code, Cursor, and other [Agent Skills](https://agentskills.io)-aware tools | [`skills/llm-wiki-framework/SKILL.md`](../skills/llm-wiki-framework/SKILL.md) (name+description frontmatter, discovered automatically) | points to `AGENTS.md` as source of truth |
| Claude Code (via `AGENTS.md` bridge)   | [`CLAUDE.md`](../CLAUDE.md)                   | imports `AGENTS.md` |
| Gemini CLI                             | [`GEMINI.md`](../GEMINI.md)                     | imports `AGENTS.md` (or set `context.fileName` to `AGENTS.md` in settings.json) |
| GitHub Copilot                          | `.github/copilot-instructions.md`, plus `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` (nearest-wins) | reads AGENTS.md directly |
| Grok / xAI                               | no reliably documented repo-file convention found | — |

`AGENTS.md` is the source of truth for cross-cutting rules — the other
files (`skills/llm-wiki-framework/SKILL.md`, `CLAUDE.md`, `GEMINI.md`)
are just thin redirects and discovery entry points, and
`workflows/*.md` holds the full step-by-step
procedure for each individual command (read only the one relevant to
the command being run — see AGENTS.md, "Workflow files"). Nothing has
to be maintained twice.

## Skills, and tools that have none

Agent Skills are how tools like Claude Code, Cursor and Codex discover
this framework on their own. [`SKILL.md`](../skills/llm-wiki-framework/SKILL.md)
carries a `name` and a `description` in its frontmatter; the tool reads
those, decides the skill is relevant, and loads it. The file itself
stays short on purpose — it summarises what the framework is and points
at [`AGENTS.md`](../AGENTS.md) for the rules and at `workflows/` for the
per-command procedure. Nothing is duplicated into it, so nothing in it
can drift out of date.

**A skill is a convenience, not a requirement.** The framework is
written to work in tools that have no skill mechanism at all — which
includes M365 Copilot in a corporate tenant, where Agent Builder offers
instructions and knowledge sources but no skill discovery. There you
paste [`AGENTS.md`](../AGENTS.md) into the agent's instructions
yourself. Same source of truth, handed over by hand instead of found
automatically.

That is why nothing depends on a tool-specific feature:

- The commands are trigger words recognised in ordinary chat, not
  entries in a slash-command registry. Typing
  `/llm-wiki-ingest` works, and so does asking for it in plain words.
- `AGENTS.md` is plain Markdown with no frontmatter requirement of its
  own, so it can be pasted anywhere an agent takes instructions.
- The helper scripts are optional throughout: an agent that cannot
  execute anything performs the same checks by reading files, and the
  rules do not change either way.

What such a tool cannot do is write. Copilot Agent Builder reads its
knowledge source but never writes back, so bundle setup and Ingest have
to happen somewhere with file access — see "Copilot with OneDrive"
under One-time setup.

---

# Everyday tasks

In the order you actually meet them: set a bundle up, put sources in,
ask questions, keep it tidy.

## Create a new bundle

```
/llm-wiki-add-bundle
```

The agent asks about the topic, proposes a taxonomy — which knowledge
types, which folders — and sets the structure up once you confirm. You
do not need to work the folder layout out beforehand; that is the point
of the dialogue. It also asks for the bundle's content language here.

## Add a source

```
/llm-wiki-ingest              # process new raw sources in ALL bundles
/llm-wiki-ingest <bundle>     # ...only this one
```

1. Drop a file into `bundles/<name>/raw/` — copying it in is enough.
2. Run the command.

No filename or path is needed: the agent scans `raw/` itself and picks
up whatever it has not seen before, recognising it by content hash
rather than by name. Leaving `<bundle>` out runs across every bundle in
the repo — not the default one.

## Capture chat content

```
/llm-wiki-capture <what it's about>
/llm-wiki-capture <bundle> <what it's about>
```

For knowledge that came up in conversation and has no file. The agent
writes a raw artifact from it first — date, which tool the chat was
held with, the relevant excerpt — and then continues into Ingest
normally. Past that point there is no difference from a file source.

## Ask questions

```
/llm-wiki-query <question>
/llm-wiki-query <bundle> <question>
```

Without a bundle, the default one is used. Every answer starts with
`**Bundle: <name>**`, so it is clear where it came from. Query never
writes: if it finds a gap it says so and points you at
`/llm-wiki-ingest` rather than filling it in silently.

## Lint the wiki

```
/llm-wiki-lint                # consistency checks in ALL bundles
/llm-wiki-lint <bundle>       # ...only this one
```

Dead links, orphaned pages, missing frontmatter fields, raw-hash
mismatches, an `index.md` graph that no longer matches the actual links.
Findings that are unambiguous get fixed, the rest is reported for you to
decide on.

## Ingest and lint in one run

```
/llm-wiki-maintenance         # ALL bundles
/llm-wiki-maintenance <bundle>
```

The usual housekeeping pass: everything Ingest does, then everything
Lint does, per bundle. If `FRAMEWORK-SYNC.md` exists, it also mentions
in passing whether the framework files upstream have moved on — read
only, nothing is pulled.

## See what bundles exist

```
/llm-wiki-list-bundles
```

Read-only overview: name, description, content language and taxonomy
types per bundle, plus which one is currently the default.

## Switch the default bundle

```
/llm-wiki-set-default-bundle <bundle>              # this chat only
/llm-wiki-set-persistent-default-bundle <bundle>   # permanently, in the repo
```

Both check that the bundle exists before switching. The default applies
to `/llm-wiki-capture` and `/llm-wiki-query` only — Ingest, Lint and
Maintenance run across all bundles unless you name one.

## Change a bundle's content language

```
/llm-wiki-set-bundle-language <bundle> <language>
```

Asked once when the bundle is created, changeable at any time. It
affects new and updated content only, never rewrites existing pages, and
has nothing to do with the language you are chatting in (see
[AGENTS.md](../AGENTS.md), "Language").

## Check for upstream framework updates

```
/llm-wiki-check-updates
```

Works with or without `FRAMEWORK-SYNC.md`: if that file exists, the
origin repo named in it is used; otherwise the agent looks at the Git
remotes, and only asks you if neither answers. It then compares this
instance's framework files — [`AGENTS.md`](../AGENTS.md),
`skills/llm-wiki-framework/SKILL.md`, [`SPEC.md`](SPEC.md) and the rest
— against that origin and reports which differ. Pulling is confirmed per
file, never in bulk, and always overwrites the local version.

---

# One-time setup

Neither of these is part of using the wiki; both are things you do once,
if your situation calls for them.

## Bring an existing wiki in

```
/llm-wiki-migrate <path-or-repo> [bundle]
```

If you already keep notes somewhere — an Obsidian vault, another
LLM-wiki, a folder of Markdown — this imports them without losing the
traceability the rest of the framework rests on.

The trick is that your old pages are not imported as pages. Each one is
copied into `raw/` unchanged and then ingested like any other source, so
the resulting wiki page cites the archived copy of itself. The citation
reads "this is what the previous wiki said, as of this date", which is
true, instead of a claim with no origin at all. Your old text stays in
the repo verbatim either way.

If your old setup already kept original sources of its own — PDFs,
articles, transcripts, because you had been following the Karpathy
pattern already — those are not treated that way. They come across as
what they are: real sources, under their own names, ingested normally.
Only the pages someone wrote by hand become sources of themselves. The
difference is what a file can vouch for, and the migration sorts the two
apart before anything is copied.

What happens, in order: the agent looks at what is there and reports
back before touching anything; proposes a taxonomy derived from the
folders and tags you already have, since that structure already says
something about the subject; archives the originals in one commit;
then ingests them in batches, reporting after each, so a wrong
assumption surfaces at file three rather than file two hundred.
`[[wikilinks]]` become real relative links where the target exists and
plain text where it does not; plugin syntax is dropped and named in the
report. At the end you get an account of what merged, what was dropped,
what could not be read, and which contradictions between old pages
turned up — those get recorded rather than quietly resolved.

Your original wiki is never touched. It is read, copied and left exactly
where it was.

## A public-sync CI mirror

The framework ships no CI: a publishing pipeline depends on the forge,
its runner labels and its branch layout, so it is instance mechanics
rather than a framework file. If you want a mirror that publishes the
framework and never the knowledge, have your agent build one:

```
I want this repo mirrored to a public repo, framework files only —
never bundles/, never FRAMEWORK-SYNC.md, and never any block wrapped
in private markers. Build a CI workflow for <my forge> that
publishes the cleaned tree as an orphan commit (its parent must be the
previous published tip, never a commit from this repo's history, or the
stripped content stays recoverable). Tell me which credentials I have
to set up myself — don't attempt those yourself.
```

## Copilot with OneDrive, without local file access

1. Mirror the bundle folder into OneDrive/SharePoint (manual upload, or
   Git sync where available).
2. In M365 Copilot → Agent Builder, create an agent, paste
   [`AGENTS.md`](../AGENTS.md) as its instructions, and link the
   OneDrive folder as a knowledge source.
3. The limit: Agent Builder only reads. There is no write-back, so the
   bundle-setup dialogue and Ingest cannot run there.
4. What works instead: do bundle setup and Ingest where an agent has
   full write access, then sync the finished wiki to OneDrive — Copilot
   at work reads it, nothing more.
