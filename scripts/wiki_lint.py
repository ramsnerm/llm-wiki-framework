#!/usr/bin/env python3
"""
wiki_lint.py -- optional helper for the LLM-Wiki Framework.

Stdlib-only (Python 3.7+), no dependencies, no network access. Performs the
*deterministic* checks described in AGENTS.md (Ingest step 2, Lint workflow)
so an agent with script execution access doesn't have to compute SHA-256
hashes or cross-check links by reasoning alone. Entirely optional: an agent
without script execution can and should perform the same checks by reading
files directly -- this script only makes that step faster and less error-
prone where available. See AGENTS.md, "Optional helper scripts".

Usage:
    python3 wiki_lint.py hash <file>
        Print the SHA-256 hex digest of a single file. Used during Ingest
        to fill raw_hash: and to detect accidental duplicate uploads.

    python3 wiki_lint.py lint <bundle-dir>
        Run all deterministic checks against one bundle directory
        (e.g. bundles/homelab/) and print a JSON report to stdout:

        {
          "raw_files": {"<raw/relpath>": "<sha256>", ...},
          "duplicate_raw_files": [
            ["raw/a.md", "raw/b.md"]   # same content hash, different files
          ],
          "raw_hash_mismatches": [
            {"source": "sources/2026-01-01-x.md", "raw_ref": "raw/x.md",
             "stored_hash": "...", "actual_hash": "..."}
          ],
          "missing_frontmatter": [
            {"file": "entities/foo.md", "missing": ["updated"]}
          ],
          "dead_links": [
            {"file": "entities/foo.md", "link": "../concepts/bar.md"}
          ],
          "orphan_pages": ["entities/unused.md"],
          "raw_missing_referenced_by_source": [
            {"source": "sources/2026-01-01-x.md", "raw_ref": "raw/x.md"}
          ]
        }

        The agent still makes every judgment call (auto-fix vs. report vs.
        ask, per AGENTS.md's Lint table) -- this script only surfaces facts,
        it never edits any file.

Exit code is always 0 on a successful run (findings are data, not errors).
Non-zero exit means the script itself failed (bad path, bad args, etc.).
"""

import hashlib
import json
import os
import re
import sys

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

# tags/sources are required *keys* (presence check only -- an empty list
# like `tags: []` is a legitimate value and still counts as present).
REQUIRED_FIELDS_TYPED = ["type", "title", "created", "updated", "tags", "sources"]
REQUIRED_FIELDS_SOURCE_EXTRA = ["raw_ref", "raw_hash"]
# source pages don't carry a `sources:` field pointing at themselves
REQUIRED_FIELDS_SOURCE_EXCLUDE = ["sources"]

SKIP_DIRS = {"raw"}
SKIP_FILES = {"log.md"}  # index.md IS link-checked, just handled separately
INDEX_FILE = "index.md"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_frontmatter(text):
    """Minimal frontmatter parser: flat key: value pairs only. Good enough
    to check field *presence*, not to fully validate YAML structure -- the
    agent still reads the file itself for anything beyond presence."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fields = {}
    for line in m.group(1).splitlines():
        fm = FIELD_RE.match(line)
        if fm:
            value = fm.group(2).strip()
            # YAML quoting is legitimate and SPEC.md's own examples use
            # it. Without this, a quoted raw_hash never equals the digest
            # it is compared against, and the script reports a mismatch
            # that does not exist -- which is worse than reporting
            # nothing, because someone will try to "fix" the file.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[fm.group(1)] = value
    return fields


def list_all_files(root, exclude_dirs=frozenset()):
    """All files (any extension) under root, honoring exclude_dirs."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for fn in filenames:
            out.append(os.path.join(dirpath, fn))
    return out


def list_md_files(root, exclude_dirs=frozenset()):
    return [p for p in list_all_files(root, exclude_dirs) if p.endswith(".md")]


def relpath(bundle_dir, path):
    return os.path.relpath(path, bundle_dir).replace(os.sep, "/")


def extract_links(text):
    """Yield markdown link targets, skipping external/anchor/mailto links."""
    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        yield target


def cmd_hash(args):
    if len(args) != 1:
        print("usage: wiki_lint.py hash <file>", file=sys.stderr)
        return 2
    path = args[0]
    if not os.path.isfile(path):
        print(f"error: not a file: {path}", file=sys.stderr)
        return 2
    print(sha256_of(path))
    return 0


def cmd_lint(args):
    if len(args) != 1:
        print("usage: wiki_lint.py lint <bundle-dir>", file=sys.stderr)
        return 2
    bundle_dir = args[0]
    if not os.path.isdir(bundle_dir):
        print(f"error: not a directory: {bundle_dir}", file=sys.stderr)
        return 2

    raw_dir = os.path.join(bundle_dir, "raw")

    # 1. Hash every file under raw/, of any extension (raw/ may hold any
    #    source format, not just .md).
    raw_files = {}
    if os.path.isdir(raw_dir):
        for path in list_all_files(raw_dir):
            raw_files[relpath(bundle_dir, path)] = sha256_of(path)

    # 1b. Duplicate content across ALL raw files -- regardless of whether
    #     either one has been ingested into a source summary yet. This is
    #     the actual accidental-re-upload signal: two raw files with
    #     identical bytes, found purely from what's on disk.
    hash_to_refs = {}
    for ref, h in raw_files.items():
        hash_to_refs.setdefault(h, []).append(ref)
    duplicate_raw_files = [
        sorted(refs) for refs in hash_to_refs.values() if len(refs) > 1
    ]
    duplicate_raw_files.sort()

    # 2. Read every typed page's frontmatter (everything outside raw/,
    #    excluding log.md; index.md is included here so its links get
    #    dead-link-checked, but it's excluded from the orphan-detection
    #    pool below since it structurally links to almost everything).
    typed_pages = []
    for p in list_md_files(bundle_dir, exclude_dirs=SKIP_DIRS):
        rel = relpath(bundle_dir, p)
        if rel in SKIP_FILES:
            continue
        typed_pages.append(p)

    missing_frontmatter = []
    raw_hash_mismatches = []
    raw_missing_referenced_by_source = []
    page_texts = {}

    for p in typed_pages:
        rel = relpath(bundle_dir, p)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        page_texts[rel] = text

        if rel == INDEX_FILE:
            # index.md has its own schema (bundle taxonomy), not the typed
            # page / source frontmatter checked below.
            continue

        fm = parse_frontmatter(text)
        is_source = fm.get("type") == "source" or rel.startswith("sources/")

        required = list(REQUIRED_FIELDS_TYPED)
        if is_source:
            required = [k for k in required if k not in REQUIRED_FIELDS_SOURCE_EXCLUDE]
            required += REQUIRED_FIELDS_SOURCE_EXTRA

        missing = [k for k in required if k not in fm]
        if missing:
            missing_frontmatter.append({"file": rel, "missing": missing})

        if is_source and "raw_ref" in fm:
            raw_ref = fm["raw_ref"]
            raw_hash = fm.get("raw_hash", "")
            actual_hash = raw_files.get(raw_ref)
            if actual_hash is None:
                raw_missing_referenced_by_source.append(
                    {"source": rel, "raw_ref": raw_ref}
                )
            elif raw_hash and raw_hash != actual_hash:
                # The stored raw_hash no longer matches the actual file on
                # disk -- since raw/ is supposed to be immutable, this
                # means either the summary was written against a different
                # version, or (should never happen) the raw file changed.
                raw_hash_mismatches.append(
                    {
                        "source": rel,
                        "raw_ref": raw_ref,
                        "stored_hash": raw_hash,
                        "actual_hash": actual_hash,
                    }
                )

    # 3. Link check (all typed pages, index.md included) + orphan
    #    detection. Two different scopes on purpose:
    #    - dead_links: checked against every page's outgoing links,
    #      index.md included, since a dead link in index.md is just as
    #      real a problem as one anywhere else.
    #    - orphan_pages incoming count: only links originating from
    #      non-source, non-index pages are counted. index.md structurally
    #      links to (almost) everything, and a source summary's own links
    #      back to the pages it fed are not the same as another page's
    #      prose cross-referencing it -- counting either would make the
    #      orphan check nearly meaningless. This flags pages that no
    #      *other content page's prose* cross-references, which is the
    #      useful signal per AGENTS.md's Lint table.
    dead_links = []
    incoming = {rel: 0 for rel in page_texts if rel != INDEX_FILE}
    for rel, text in page_texts.items():
        page_dir = os.path.dirname(os.path.join(bundle_dir, rel))
        counts_as_incoming_source = (rel != INDEX_FILE) and not rel.startswith("sources/")
        for target in extract_links(text):
            target_path = os.path.normpath(os.path.join(page_dir, target))
            target_rel = relpath(bundle_dir, target_path)
            if target_rel.startswith("raw/"):
                # links into raw/ are validated separately by
                # raw_missing_referenced_by_source; skip here
                continue
            if not os.path.isfile(target_path):
                dead_links.append({"file": rel, "link": target})
            elif counts_as_incoming_source and target_rel in incoming:
                incoming[target_rel] += 1

    orphan_pages = sorted(
        rel for rel, count in incoming.items()
        if count == 0 and not rel.startswith("sources/")
    )

    report = {
        "raw_files": raw_files,
        "duplicate_raw_files": duplicate_raw_files,
        "raw_hash_mismatches": raw_hash_mismatches,
        "missing_frontmatter": missing_frontmatter,
        "dead_links": dead_links,
        "orphan_pages": orphan_pages,
        "raw_missing_referenced_by_source": raw_missing_referenced_by_source,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def main():
    # An explicitly requested help text is a successful run: it prints to
    # stdout and exits 0, so `wiki_lint.py --help` can be used as a smoke
    # test in CI. A missing or unknown command is a usage error: stderr,
    # exit 2.
    if len(sys.argv) >= 2 and sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if len(sys.argv) < 2 or sys.argv[1] not in ("hash", "lint"):
        print(__doc__, file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    args = sys.argv[2:]
    if cmd == "hash":
        return cmd_hash(args)
    return cmd_lint(args)


if __name__ == "__main__":
    sys.exit(main())
