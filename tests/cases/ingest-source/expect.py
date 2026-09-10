#!/usr/bin/env python3
"""Assertions for a plain Ingest run.

Checks the invariants the framework promises about ingestion: the raw
file is untouched, a source summary records its hash, typed pages went
into folders the bundle's taxonomy actually declares, and the index and
log were updated in the same breath.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

RAW = "bundles/testbundle/raw/2026-01-02-timescaledb-notes.md"
# The hash of the fixture raw file, computed here rather than hardcoded,
# so the case survives an edit to the fixture.


def sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def frontmatter(text):
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    fields = {}
    for line in block.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def main(workdir):
    instance = os.path.join(workdir, "instance")
    bundle = os.path.join(instance, "bundles", "testbundle")
    failures = []

    if not os.path.isdir(bundle):
        return ["the fixture bundle is gone"]

    # 1. The raw file must be exactly as it was. This is the framework's
    #    hardest promise and the easiest one to break by "tidying up".
    raw = os.path.join(instance, RAW)
    if not os.path.exists(raw):
        failures.append("the raw source was deleted")
    else:
        _, changed = git(instance, "diff", "HEAD~10..HEAD", "--name-only", "--", RAW)
        if RAW in changed:
            failures.append("the raw source was modified during ingest")

    # 2. A source summary exists and records the raw file's real hash.
    sources = os.path.join(bundle, "sources")
    summaries = [f for f in os.listdir(sources) if f.endswith(".md")] \
        if os.path.isdir(sources) else []
    if not summaries:
        failures.append("no source summary was written")
    else:
        found_hash = False
        actual = sha256(raw) if os.path.exists(raw) else ""
        for name in summaries:
            text = open(os.path.join(sources, name), encoding="utf-8").read()
            fields = frontmatter(text)
            stored = (fields.get("raw_hash") or "").strip("\"'")
            if stored:
                found_hash = True
                if actual and stored not in (actual, "sha256:" + actual):
                    failures.append(
                        "sources/%s records raw_hash %s but the file hashes to %s"
                        % (name, stored[:16], actual[:16]))
        if not found_hash:
            failures.append("no source summary records a raw_hash")

    # 3. At least one typed page, and only in folders the taxonomy declares.
    declared = {"entities", "concepts"}
    pages = []
    for folder in declared:
        path = os.path.join(bundle, folder)
        if os.path.isdir(path):
            pages += [os.path.join(folder, f) for f in os.listdir(path)
                      if f.endswith(".md") and f != "index.md"]
    if not pages:
        failures.append("no typed page was created in entities/ or concepts/")

    stray = [name for name in os.listdir(bundle)
             if os.path.isdir(os.path.join(bundle, name))
             and name not in declared | {"raw", "sources"}]
    if stray:
        failures.append("folders created outside the declared taxonomy: %s"
                        % ", ".join(sorted(stray)))

    # 4. Every typed page cites a source; an uncited page is the failure
    #    the whole raw/ discipline exists to prevent.
    for page in pages:
        text = open(os.path.join(bundle, page), encoding="utf-8").read()
        if "sources/" not in text:
            failures.append("%s does not link to any source summary" % page)

    # 5. index.md and log.md were updated, not left at the fixture state.
    index = open(os.path.join(bundle, "index.md"), encoding="utf-8").read()
    if "_(none yet)_" in index:
        failures.append("index.md still shows the empty fixture state")
    log = open(os.path.join(bundle, "log.md"), encoding="utf-8").read()
    if len(log.strip().splitlines()) < 2:
        failures.append("log.md has no entry for the ingest")

    # 6. The work was committed, with the message pattern AGENTS.md fixes.
    code, status = git(instance, "status", "--porcelain")
    if code == 0 and status:
        failures.append("ingest left uncommitted changes: %s"
                        % status.replace("\n", "; ")[:200])
    _, subjects = git(instance, "log", "--format=%s")
    if not any(re.match(r"^ingest: testbundle — ", line) for line in subjects.splitlines()):
        failures.append("no commit matching 'ingest: <bundle> — ...' (subjects: %s)"
                        % "; ".join(subjects.splitlines()[:3]))

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
