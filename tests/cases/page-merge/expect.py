#!/usr/bin/env python3
"""Assertions for ingesting a second source about a subject already covered.

The failure this guards against is a duplicate: a second page about the
same subject under a slightly different filename, leaving the wiki with
two partial truths and no indication which is current. The framework's
answer is page identity matching — same filename or a declared alias
means the same page, and the new material is worked into it.

The second source also contradicts the first. The correction has to land
on the page rather than sit unread in sources/.
"""

import json
import os
import re
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def main(workdir):
    instance = os.path.join(workdir, "instance")
    bundle = os.path.join(instance, "bundles", "testbundle")
    failures = []

    entities = os.path.join(bundle, "entities")
    if not os.path.isdir(entities):
        return ["entities/ is gone"]

    pages = sorted(f for f in os.listdir(entities)
                   if f.endswith(".md") and f != "index.md")

    # 1. No second page about TimescaleDB.
    timescale = [p for p in pages if "timescale" in p.lower()]
    if not timescale:
        failures.append("entities/timescaledb.md disappeared")
    elif len(timescale) > 1:
        failures.append("the subject was duplicated instead of merged: %s"
                        % ", ".join(timescale))

    # 2. The existing page actually grew — the new source has to land
    #    somewhere, and sources/ alone is not the wiki.
    page = os.path.join(entities, "timescaledb.md")
    if os.path.exists(page):
        text = open(page, encoding="utf-8").read()
        if len(text) <= 900:
            failures.append("entities/timescaledb.md barely changed (%d chars) "
                            "— the follow-up may not have been worked in" % len(text))
        # The follow-up's substance, in whatever wording: compression
        # figures, and the pg_dump qualification.
        if not re.search(r"9\d\s?%|92|compress", text, re.I):
            failures.append("the compression finding is not on the page")
        if not re.search(r"pg_dump|extension has to be created|restore", text, re.I):
            failures.append("the pg_dump qualification is not on the page")

    # 3. Both sources are cited from the page.
    if os.path.exists(page):
        text = open(page, encoding="utf-8").read()
        for marker in ("2026-01-02", "2026-02-10"):
            if marker not in text:
                failures.append("the page does not cite the %s source" % marker)

    # 4. A second source summary exists for the follow-up.
    sources = os.path.join(bundle, "sources")
    summaries = [f for f in os.listdir(sources) if f.endswith(".md")] \
        if os.path.isdir(sources) else []
    if len(summaries) < 2:
        failures.append("no source summary was written for the follow-up "
                        "(found %d)" % len(summaries))

    # 5. The first raw file is untouched; both are still present.
    raw = os.path.join(bundle, "raw")
    raws = sorted(os.listdir(raw)) if os.path.isdir(raw) else []
    if len(raws) != 2:
        failures.append("raw/ should still hold exactly the two sources, found: %s"
                        % ", ".join(raws))

    # 6. Committed, and nothing left dangling.
    code, status = git(instance, "status", "--porcelain")
    if code == 0 and status:
        failures.append("uncommitted changes left behind: %s"
                        % status.replace("\n", "; ")[:200])

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
