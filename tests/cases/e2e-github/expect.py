#!/usr/bin/env python3
"""End-to-end: clone, own repo, create a bundle, ingest, lint, push.

This is the whole chain a new user walks through, asserted from the
outside. It is the case most likely to catch a break introduced
somewhere unrelated, because nothing here is faked: a real clone of the
published repository, a real bundle-setup dialogue resolved
autonomously, a real document, real commits, a real push.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

DOC = "ceph-bluestore-notes.md"


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main(workdir):
    failures = []
    wiki = os.path.join(workdir, "wiki")
    if not os.path.isdir(os.path.join(wiki, ".git")):
        return ["no repository at %s/wiki" % workdir]

    # 1. The framework arrived intact.
    for path in ("AGENTS.md", "workflows/ingest.md", "docs/SPEC.md"):
        if not os.path.exists(os.path.join(wiki, path)):
            failures.append("%s missing from the clone" % path)

    # 2. A bundle called "storage" exists, with a taxonomy of its own.
    bundle = os.path.join(wiki, "bundles", "storage")
    if not os.path.isdir(bundle):
        found = sorted(os.listdir(os.path.join(wiki, "bundles"))) \
            if os.path.isdir(os.path.join(wiki, "bundles")) else []
        return failures + ["no bundle at bundles/storage (found: %s)" % ", ".join(found)]

    index = os.path.join(bundle, "index.md")
    if not os.path.exists(index):
        failures.append("the bundle has no index.md")
    else:
        head = read(index)
        # SPEC.md, "Bundle taxonomy": the key is `types:`, and each
        # entry names a folder. Checking for the word "taxonomy" would
        # test the prose rather than the format.
        if not re.search(r"^types:", head, re.M):
            failures.append("index.md has no types: block — the taxonomy is "
                            "not declared in the form SPEC.md specifies")
        elif not re.search(r"^\s+-\s+name:", head, re.M):
            failures.append("types: is present but declares no entries")
        if not re.search(r"^bundle:\s*storage", head, re.M):
            failures.append("index.md does not declare bundle: storage")
        if not re.search(r"default_language:\s*(en|english)", head, re.I):
            failures.append("index.md does not record English as the content language")

    for required in ("raw", "sources", "log.md"):
        if not os.path.exists(os.path.join(bundle, required)):
            failures.append("the bundle has no %s" % required)

    # 3. The document is in raw/, byte-identical to what was handed over.
    original = os.path.join(workdir, DOC)
    raw_dir = os.path.join(bundle, "raw")
    copies = [f for f in os.listdir(raw_dir)] if os.path.isdir(raw_dir) else []
    if not copies:
        failures.append("raw/ is empty — the document was never brought in")
    elif os.path.exists(original):
        want = hashlib.sha256(open(original, "rb").read()).hexdigest()
        got = [hashlib.sha256(open(os.path.join(raw_dir, f), "rb").read()).hexdigest()
               for f in copies]
        if want not in got:
            failures.append("the copy in raw/ is not byte-identical to the "
                            "document that was handed over")

    # 4. It was ingested: a summary with a hash, and at least one typed
    #    page that cites it.
    sources = os.path.join(bundle, "sources")
    summaries = [f for f in os.listdir(sources) if f.endswith(".md")] \
        if os.path.isdir(sources) else []
    if not summaries:
        failures.append("no source summary — the document was copied but not ingested")
    elif not any("raw_hash" in read(os.path.join(sources, f)) for f in summaries):
        failures.append("no source summary records a raw_hash")

    typed = []
    for entry in sorted(os.listdir(bundle)):
        path = os.path.join(bundle, entry)
        if os.path.isdir(path) and entry not in ("raw", "sources"):
            typed += [os.path.join(entry, f) for f in os.listdir(path)
                      if f.endswith(".md") and f != "index.md"]
    if not typed:
        failures.append("no typed pages were written")
    else:
        uncited = [p for p in typed if "sources/" not in read(os.path.join(bundle, p))]
        if uncited:
            failures.append("typed pages with no source link: %s"
                            % ", ".join(sorted(uncited)[:4]))

    # 5. Committed and pushed to the repo that was handed over.
    code, status = git(wiki, "status", "--porcelain")
    if code == 0 and status:
        failures.append("uncommitted changes left behind: %s"
                        % status.replace("\n", "; ")[:200])
    _, url = git(wiki, "remote", "get-url", "origin")
    if "github.com" in url:
        failures.append("origin was never repointed away from the template")
    target = os.path.join(workdir, "target.git")
    _, head = git(wiki, "rev-parse", "HEAD")
    _, refs = git(target, "for-each-ref", "--format=%(objectname)")
    if head and head not in refs.split():
        failures.append("the work was committed but never pushed")

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
