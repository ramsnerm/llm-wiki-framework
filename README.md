# LLM Wiki Framework

![LLM Wiki Framework](docs/banner.png)

An AI-agent-maintained knowledge repository built from plain Markdown +
YAML frontmatter + Mermaid. No app dependency — any environment that can
read/write Markdown files (editor, Git repo, SharePoint/OneDrive folder,
Copilot Agent Builder, Claude Code, Pi, ...) is enough.

**Version 0.0.1** — first tagged release. The format spec (`docs/SPEC.md`) and
the command set are usable but not yet frozen; expect breaking changes to
frontmatter fields and workflow procedures before 0.1.0.

## Idea

Classic RAG pulls chunks from raw sources on every question and rederives
the answer each time — nothing accumulates, every query starts from zero.

Here it works the other way around: an AI agent reads new sources once,
processes them, and **maintains a structured wiki** from them that grows
over time. You read and ask questions; the agent writes and maintains.

## Bundles

The repo is divided into **bundles** (`bundles/<name>/`) — each bundle is
an independent knowledge domain with its own taxonomy. There is
deliberately **no** repo-wide fixed folder structure for knowledge types:
a tool comparison needs different categories than a standards collection.

A bundle's taxonomy isn't designed manually — it's established in
dialogue with the agent: when creating a new bundle, the agent asks
targeted questions about the topic, turns that into a taxonomy proposal
(which knowledge types, which folders), you confirm or adjust, and only
then does it set up the structure. Details:
[workflows/create-bundle.md](workflows/create-bundle.md).

Fixed in every bundle: `raw/` (unmodified sources), `sources/`
(summaries), `index.md` (taxonomy + overview), `log.md` (change log).
Everything else is bundle-specific.

## Structure

```
ra-framework-llm-wiki/
├── README.md
├── AGENTS.md          # cross-cutting rules + entry point (cross-tool standard)
├── workflows/            # full procedure per command — see AGENTS.md,
│   ├── create-bundle.md    "Workflow files"
│   ├── list-bundles.md
│   ├── capture.md
│   ├── ingest.md
│   ├── lint.md
│   ├── maintenance.md
│   ├── query.md
│   └── check-updates.md
├── skills/
│   └── llm-wiki-framework/
│       └── SKILL.md    # Agent Skills discovery entry point (@AGENTS.md)
├── CLAUDE.md             # bridge for Claude Code (@AGENTS.md)
├── GEMINI.md              # bridge for Gemini CLI (@AGENTS.md)
├── docs/
│   ├── SPEC.md              # format/taxonomy specification
│   ├── QUICKSTART.md
│   └── banner.png
├── templates/
├── scripts/
│   └── wiki_lint.py           # optional stdlib-only helper
└── bundles/
    └── <name>/              # per bundle: its own taxonomy & folders
```

## Which tool reads what

| Tool                                  | reads natively            | bridge in this repo |
|----------------------------------------|----------------------------|---------------------------|
| OpenAI Codex, Cursor, Jules, Aider, Windsurf, Zed, Amp | `AGENTS.md` directly (delegates to `workflows/*.md` per command) | — |
| Claude Code, Cursor, and other [Agent Skills](https://agentskills.io)-aware tools | `skills/llm-wiki-framework/SKILL.md` (name+description frontmatter, discovered automatically) | points to `AGENTS.md` as source of truth |
| Claude Code (via `AGENTS.md` bridge)   | `CLAUDE.md`                   | imports `AGENTS.md` |
| Gemini CLI                             | `GEMINI.md`                     | imports `AGENTS.md` (or set `context.fileName` to `AGENTS.md` in settings.json) |
| GitHub Copilot                          | `.github/copilot-instructions.md`, plus `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` (nearest-wins) | reads AGENTS.md directly |
| Grok / xAI                               | no reliably documented repo-file convention found | — |

`AGENTS.md` is the source of truth for cross-cutting rules — the other
files (`skills/llm-wiki-framework/SKILL.md`, `CLAUDE.md`, `GEMINI.md`)
are just thin redirects/
discovery entry points, and `workflows/*.md` holds the full step-by-step
procedure for each individual command (read only the one relevant to
the command being run — see AGENTS.md, "Workflow files"). Nothing has
to be maintained twice.

## Conventions (always apply, regardless of taxonomy)

- Cross-references as plain relative Markdown links (`[text](../x/y.md)`),
  no `[[wikilinks]]`
- Relationships/graphs as **Mermaid diagrams** directly in `index.md`,
  derived by a fully deterministic algorithm (see docs/SPEC.md)
- `raw/` is immutable per bundle
- Plain CommonMark + YAML frontmatter, no app-specific callouts/plugins

Details in [SPEC.md](docs/SPEC.md), setup in [QUICKSTART.md](docs/QUICKSTART.md),
agent behavior in [AGENTS.md](AGENTS.md) and [workflows/](workflows/).

## Bundle overview

_(no bundles yet)_

## Mirroring

This repo is auto-mirrored (framework files only, no instance content)
to a public GitHub repo via CI — see `.forgejo/workflows/public-sync.yml`.
The published history is orphan-rooted (never built on top of `main`'s
history), so instance content stripped from the working tree is also
never recoverable from the mirror's Git history.

## License

MIT — see `LICENSE`. This covers the framework files (instructions,
templates, `scripts/wiki_lint.py`). Content you put into `bundles/` in
your own instance is yours and is never published by the mirror.

## Credit

Structural inspiration for the raw/wiki split and the Agent-Skills
packaging: [Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki),
building on Andrej Karpathy's original LLM-wiki idea. This repo adapts
that pattern for a multi-bundle, cross-tool (`AGENTS.md`-based),
Forgejo-hosted setup with its own taxonomy-per-bundle and public-template
mechanics — not a fork or direct derivative.
