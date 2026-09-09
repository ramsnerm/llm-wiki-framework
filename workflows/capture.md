# Workflow: Capture chat content (no raw upload)

Triggered by `/llm-wiki-capture [bundle] <what it's about>`, or when the
user informally wants content just discussed in chat to go into the wiki
without uploading a file for it (default-bundle resolution as in
AGENTS.md, "Default-bundle resolution"). Read this file in full before
running the command.

The chat itself is not a file in `raw/` — so a raw artifact is created
from it first, before anything gets typed or linked. This keeps `raw/`
the shared, immutable foundation for **every** knowledge source,
regardless of whether it arrived as a file or emerged in conversation.

1. Determine the relevant chat excerpt — not the whole chat, just the
   part that's actually relevant to the request (if unsure, briefly ask
   the user what exactly should go in).
2. Determine the tool/agent the captured chat was conducted with (e.g.
   Claude Code, Claude.ai, Copilot, ChatGPT, Gemini, Pi) — if unsure, ask
   briefly instead of guessing.
3. Create a file in `bundles/<name>/raw/`:
   `YYYY-MM-DD-chat-<short-description>.md`. If that exact filename
   already exists, append `-02`, `-03`, etc. — **never** overwrite an
   existing raw file, even one from the same day/topic. Content:
   ```markdown
   # Chat capture: <short description>

   - Date: YYYY-MM-DD
   - Chat: <name/link if available, otherwise "current conversation">
   - Tool/agent: <e.g. Claude Code, Copilot, ChatGPT, Gemini, Pi>

   ## Context

   <one or two sentences on what this was about>

   ## Relevant chat excerpt

   <the relevant user/agent messages — verbatim where exact wording
   matters, otherwise condensed>
   ```
4. From here proceed normally into `workflows/ingest.md` (it detects the
   new file via the hash comparison like any other raw source) — no
   special path for chat content in the typed pages.
5. Briefly confirm to the user which raw file was created before
   auto-processing continues — for larger/unclear excerpts, show the raw
   text first and wait for confirmation.

One commit for the new raw file, separate from the following Ingest
commit(s) — see AGENTS.md, "Git & Versioning".
