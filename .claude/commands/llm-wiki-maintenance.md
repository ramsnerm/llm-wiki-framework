---
description: Ingest, then Lint, in one run — plus a one-time framework-update note if FRAMEWORK-SYNC.md exists
argument-hint: [bundle]
---

Run `/llm-wiki-maintenance` exactly as AGENTS.md defines it.

1. Read `AGENTS.md` in full, unless you already have in this session.
2. Read `workflows/maintenance.md`, then `workflows/ingest.md`, then `workflows/lint.md` in full before doing anything — the procedure lives there,
   not in this file.
3. Everything in AGENTS.md applies — trust boundary, bundle resolution,
   Git discipline, the Rules. This file adds nothing to them; it only
   makes the command typeable in Claude Code.

Arguments: $ARGUMENTS
