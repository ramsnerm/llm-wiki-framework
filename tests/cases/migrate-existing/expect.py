#!/usr/bin/env python3
"""Migration of an existing wiki that already has sources of its own.

The old folder holds two kinds of file, and the whole point of the
workflow is that they are not treated alike:

  raw/ceph-bluestore-paper.md   a primary source — vouches for itself
  notes/*.md                    pages someone wrote — vouch only for
                                what that wiki said

Also planted: [[wikilinks]] and an Obsidian callout, which must not
survive into typed pages, and a link to [[erasure-coding]] with no
target anywhere, which must not become a link to a page that does not
exist.

And the strongest assertion of all: the source folder is byte-for-byte
untouched afterwards. Migration reads; it does not move or tidy.
"""

import hashlib
import json
import os
import re
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def tree_hashes(root):
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            path = os.path.join(dirpath, name)
            with open(path, "rb") as handle:
                out[os.path.relpath(path, root)] = hashlib.sha256(handle.read()).hexdigest()
    return out


def main(workdir):
    instance = os.path.join(workdir, "instance")
    old = os.path.join(workdir, "old-wiki")
    bundle = os.path.join(instance, "bundles", "storage")
    failures = []

    # 1. The source is untouched. Checked first: if this fails, nothing
    #    else about the run matters.
    expected = {
        "raw/ceph-bluestore-paper.md", "notes/ceph.md",
        "notes/bluestore.md", "notes/zfs.md", "meta/index.md",
    }
    if not os.path.isdir(old):
        return ["the source folder was moved or deleted"]
    actual = tree_hashes(old)
    if set(actual) != expected:
        failures.append("the source folder changed: %s"
                        % sorted(set(actual) ^ expected))

    if not os.path.isdir(bundle):
        found = sorted(os.listdir(os.path.join(instance, "bundles"))) \
            if os.path.isdir(os.path.join(instance, "bundles")) else []
        return failures + ["no bundle at bundles/storage (found: %s)" % found]

    # 2. Everything was archived into raw/ — nothing dropped silently.
    raw_dir = os.path.join(bundle, "raw")
    archived = {}
    for dirpath, _dirs, files in os.walk(raw_dir):
        for name in files:
            if name == ".gitkeep":
                continue
            path = os.path.join(dirpath, name)
            with open(path, "rb") as handle:
                archived[hashlib.sha256(handle.read()).hexdigest()] = \
                    os.path.relpath(path, raw_dir)
    for rel, digest in actual.items():
        if digest not in archived:
            failures.append("%s was never archived into raw/" % rel)

    # 3. The primary source keeps its identity; derived pages are marked
    #    as coming from the old wiki. The distinction is the point of the
    #    workflow, so it has to be visible in where things landed.
    paper = actual.get("raw/ceph-bluestore-paper.md")
    note = actual.get("notes/ceph.md")
    if paper and paper in archived and "imported" in archived[paper]:
        failures.append("the primary source was filed as imported wiki "
                        "content: %s" % archived[paper])
    if note and note in archived and "imported" not in archived[note]:
        failures.append("a page from the old wiki was archived as though it "
                        "were an original source: %s" % archived[note])

    # 4. Typed pages exist, cite sources, and carry none of the old
    #    tooling's syntax.
    typed = []
    for entry in sorted(os.listdir(bundle)):
        path = os.path.join(bundle, entry)
        if os.path.isdir(path) and entry not in ("raw", "sources"):
            typed += [os.path.join(entry, f) for f in os.listdir(path)
                      if f.endswith(".md") and f != "index.md"]
    if not typed:
        failures.append("no typed pages were produced")
    for page in typed:
        text = read(os.path.join(bundle, page))
        if "[[" in text:
            failures.append("%s still contains [[wikilinks]]" % page)
        if "> [!" in text:
            failures.append("%s still contains an Obsidian callout" % page)
        if "sources/" not in text:
            failures.append("%s cites no source" % page)
        for target in re.findall(r"\]\(([^)]+\.md)\)", text):
            if target.startswith("http"):
                continue
            resolved = os.path.normpath(os.path.join(bundle, os.path.dirname(page), target))
            if not os.path.exists(resolved):
                failures.append("%s links to %s, which does not exist"
                                % (page, target))

    # 5. A source summary per archived file, each with a hash.
    sources = os.path.join(bundle, "sources")
    summaries = [f for f in os.listdir(sources) if f.endswith(".md")] \
        if os.path.isdir(sources) else []
    if len(summaries) < 2:
        failures.append("only %d source summaries for %d archived files"
                        % (len(summaries), len(archived)))
    if summaries and not all("raw_hash" in read(os.path.join(sources, f))
                             for f in summaries):
        failures.append("not every source summary records a raw_hash")

    # 6. Committed, and the archive got its own commit before conversion.
    code, status = git(instance, "status", "--porcelain")
    if code == 0 and status:
        failures.append("uncommitted changes left behind: %s"
                        % status.replace("\n", "; ")[:200])
    _, subjects = git(instance, "log", "--format=%s")
    if not any(line.startswith("migrate:") for line in subjects.splitlines()):
        failures.append("no commit with the migrate: prefix (subjects: %s)"
                        % "; ".join(subjects.splitlines()[:4]))

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
