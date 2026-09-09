# QUICKSTART

## See what bundles exist

```
/llm-wiki-list-bundles
```

Read-only overview: name, description, content language, and taxonomy
types for every bundle, plus which one is the current default.

## Create a new bundle

```
git clone <repo-url>
cd ra-framework-llm-wiki
```

Start a coding agent (Claude Code, Pi, ...) and send `/llm-wiki-add-bundle`.
The agent will ask about the topic, propose a taxonomy, and set it up
after your confirmation. You don't need to figure out the folder
structure yourself beforehand.

## Ingest a source / lint the wiki

```
/llm-wiki-ingest              # process new raw sources, on ALL bundles
/llm-wiki-ingest <bundle>     # ...only this bundle
/llm-wiki-lint                # consistency checks only, on ALL bundles
/llm-wiki-lint <bundle>       # ...only this bundle
/llm-wiki-maintenance         # ingest + lint together, on ALL bundles
/llm-wiki-maintenance <bundle> # ...only this bundle
```

1. Drop a file into `bundles/<name>/raw/` (copy/upload is enough)
2. Trigger one of the commands above.

No filename/path needed for Ingest — the agent scans `raw/` itself.
Leaving out `<bundle>` runs the command across every bundle in the repo,
not just a default one — pass a bundle name to scope it to just that
one.

## Capture chat content (without a file upload)

When the content comes from the conversation itself instead of a file:

```
/llm-wiki-capture <what it's about>
/llm-wiki-capture <bundle> <what it's about>
```

The agent first creates a raw artifact in `raw/` from it (date, chat
reference, relevant excerpt) and then proceeds normally into Ingest
— no difference from a file source past this point.

## Ask questions

```
/llm-wiki-query <question>
/llm-wiki-query <bundle> <question>
```

Without a bundle given, the default bundle is used (see AGENTS.md). Every
answer starts with `**Bundle: <name>**`, so it's clear where it came
from. Query never writes anything — if it finds a gap, it'll say so and
point you at `/llm-wiki-ingest`.

## Switch the default bundle

```
/llm-wiki-set-default-bundle <bundle>              # this chat only
/llm-wiki-set-persistent-default-bundle <bundle>   # permanently in the repo
```

Both first check whether the bundle exists before switching. Note: this
default only applies to `/llm-wiki-capture` and `/llm-wiki-query` — not
to Ingest/Lint/Maintenance, which run across all bundles unless you name
one explicitly (see above).

## Change a bundle's content language

```
/llm-wiki-set-bundle-language <bundle> <language>
```

Also asked once up front when creating a bundle with `/llm-wiki-add-bundle`.
Only affects new content going forward, not existing pages, and is
independent of the language you're chatting with the agent in (see
AGENTS.md, "Language").

## Check for upstream framework updates

```
/llm-wiki-check-updates
```

Works with or without `FRAMEWORK-SYNC.md` present (see AGENTS.md,
"Checking for upstream framework updates"): if that file exists, its
origin repo is used directly; otherwise the agent checks Git remotes for
one that still points at the known public template, and only asks you
for the origin repo if neither yields an answer. Compares this
instance's framework files (`AGENTS.md`, `SKILL.md`, `SPEC.md`, etc.)
against the origin repo and reports which ones differ — you then
confirm, per file, whether to pull the upstream version.
`/llm-wiki-maintenance` also surfaces a lightweight version of this note
automatically, but only when `FRAMEWORK-SYNC.md` exists (an automatic
run shouldn't interrupt itself to ask where the origin repo is), so you
don't have to remember to run the full check separately in that case.

## Bootstrap everything via an agent (no manual Git/file steps)

If your agent (Claude Code, Codex CLI, Cursor in agent mode, ...) has
bash/git tool access, it can do the entire setup itself — cloning,
remote setup, first push, and skill installation — from a single prompt.
Adjust the URLs/paths to your situation; the agent asks for anything
genuinely missing (e.g. which folder, which bundle topic) rather than
guessing.

**Set up a brand-new personal instance from the template:**

```
Clone <template-repo-url> into ./my-wiki. Then:
1. Remove the existing "origin" remote and add a new one pointing at
   <my-new-empty-repo-url>.
2. Push the current branch to it.
3. Confirm AGENTS.md, SKILL.md, and SPEC.md are present at the repo
   root and read AGENTS.md in full.
4. If I want upstream sync later, ask me for the template's real
   origin repo/URL and set up FRAMEWORK-SYNC.md from
   templates/framework-sync.md (never invent the origin).
Then run /llm-wiki-add-bundle to set up my first bundle — ask me what
it should be about.
```

**Add this framework as a Claude Code / Codex / Cursor skill without
cloning the whole repo into your project** (useful if you already have
a wiki repo elsewhere and just want the skill available):

```
Fetch SKILL.md, AGENTS.md, SPEC.md, and everything under templates/
from <repo-url> (default branch). Install them as a local Agent Skill
at <skills-install-path-for-your-tool> under the name
"llm-wiki-framework", preserving the relative paths (templates/ stays
a subfolder next to SKILL.md). Then confirm the skill is discoverable
and read AGENTS.md in full before I use any /llm-wiki-* command.
```

(For Claude Code, `<skills-install-path-for-your-tool>` is typically
`~/.claude/skills/llm-wiki-framework/` for a personal skill, or
`.claude/skills/llm-wiki-framework/` inside a specific project. Check
your tool's current documentation for the exact path — this changes
between tools and versions, so don't hardcode it into automation you
don't control.)

**Set up the public-sync CI mirror in an already-cloned instance:**

```
Read .forgejo/workflows/public-sync.yml if it exists. If it doesn't,
copy it from <template-repo-url> unchanged (it's a framework file).
Then tell me exactly which two things I still need to do manually
(the GitHub repo + the Actions secret) — don't attempt those yourself,
just list them clearly.
```

## Corporate environment with Copilot + OneDrive (no local filesystem access)

1. Mirror the bundle folder into OneDrive/SharePoint (manual upload or
   Git sync, if available).
2. In M365 Copilot → Agent Builder → create a new agent, paste `AGENTS.md`
   as the system prompt/instruction, link the OneDrive folder as a
   knowledge source.
3. Limitation: Copilot Agent Builder only reads (no automatic write-back).
   For the actual Ingest workflow including the bundle-setup
   dialogue, you need an agent with write access to the folder.
4. Alternative: keep doing bundle setup and Ingest in the homelab
   (agent with full write access), then sync the finished wiki pages to
   OneDrive — Copilot at work only reads them.
