# Workflow: List bundles

Triggered by `/llm-wiki-list-bundles`, or run implicitly whenever another
workflow needs to show the user which bundles exist (an unmatched bundle
name, a missing bundle for a scoped command, the "ask which bundle is
meant" step in default-bundle resolution — see AGENTS.md, "Default-
bundle resolution"). Strictly read-only, like Query — never writes
anything, never commits, never acquires a lock.

For each bundle under `bundles/` (each subfolder with an `index.md`),
read its frontmatter and report:

- name
- description
- `default_language`
- its taxonomy's type names (from `types:`)

Mark which bundle is the persistent default (`bundles/.default-bundle`,
if set) and which one — if any — is the session default from
`/llm-wiki-set-default-bundle` in this chat. If the repo has no bundles
at all, say so and suggest `/llm-wiki-add-bundle`.
