#!/usr/bin/env python3
"""Assertions for a Lint run over a bundle with known defects.

The fixture contains three, planted deliberately:

  1. entities/timescaledb.md links to influxdb.md, which does not exist
  2. concepts/chunk-exclusion.md is an orphan — nothing links to it
  3. concepts/hypertable.md has no `updated:` field

What is checked is that Lint did what the spec says for each: auto-fill
the unambiguous missing field, and *report* -- without editing -- the
dead link and the orphan, since guessing a target or deleting a sentence
would destroy more than it fixes.

Since workflows/lint.md now requires a run that finds anything to record
it in log.md, the findings are checkable rather than lost in a terminal:
each planted defect must be named there, whether it was fixed or left
for the user.
"""

import json
import os
import re
import subprocess
import sys

BUNDLE = "bundles/testbundle"


def git(repo, *args):
    result = subprocess.run(["git", "-C", repo] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main(workdir):
    instance = os.path.join(workdir, "instance")
    bundle = os.path.join(instance, BUNDLE)
    failures = []
    if not os.path.isdir(bundle):
        return ["the fixture bundle is gone"]

    entity = os.path.join(bundle, "entities", "timescaledb.md")
    orphan = os.path.join(bundle, "concepts", "chunk-exclusion.md")
    missing_field = os.path.join(bundle, "concepts", "hypertable.md")

    # The written record: log entry plus commit subjects. A finding that
    # exists only in the chat is gone the moment the terminal closes.
    _, subjects = git(instance, "log", "--format=%s%n%b")
    log_path = os.path.join(bundle, "log.md")
    log_text = read(log_path) if os.path.exists(log_path) else ""
    record = subjects + "\n" + log_text

    # The log entry itself: required whenever a run finds anything, and
    # this fixture guarantees it finds three things.
    if not re.search(r"^##.*lint", log_text, re.I | re.M):
        failures.append("log.md has no entry for the lint run")

    # 1. Dead link: either removed from the page, or named in the record.
    if os.path.exists(entity):
        text = read(entity)
        # workflows/lint.md: a dead link with no unambiguous match is
        # reported, not guessed at. So the page must still be intact --
        # what would be wrong is inventing a target or deleting the
        # sentence.
        if "influxdb.md" not in text and not re.search(r"influxdb", record, re.I):
            failures.append("the dead link was removed without a word about it "
                            "— lint reports this defect, it does not silently "
                            "edit the sentence away")
        if not re.search(r"influxdb", log_text, re.I):
            failures.append("log.md does not record the dead link — a finding "
                            "nobody wrote down is a finding nobody can act on")
        if re.search(r"\[InfluxDB\]\((?!influxdb\.md)", text):
            failures.append("the dead link was repointed at something else — "
                            "lint may only auto-fix an unambiguous match")
    else:
        failures.append("entities/timescaledb.md was deleted")

    # 2. Orphan page: must not be silently deleted, and must be noticed.
    if not os.path.exists(orphan):
        failures.append("concepts/chunk-exclusion.md was deleted — an orphan "
                        "page is a finding to report, not something to remove "
                        "without asking")
    else:
        linked_from_anywhere = False
        for folder in ("entities", "concepts", ""):
            path = os.path.join(bundle, folder) if folder else bundle
            if not os.path.isdir(path):
                continue
            for name in os.listdir(path):
                if not name.endswith(".md") or name == "chunk-exclusion.md":
                    continue
                if "chunk-exclusion" in read(os.path.join(path, name)):
                    linked_from_anywhere = True
        # An orphan is reported, never removed or wired up on a guess.
        if linked_from_anywhere and not re.search(r"chunk.exclusion", record, re.I):
            failures.append("the orphaned page was linked into the wiki without "
                            "any record of the decision")
        if not re.search(r"chunk.exclusion|orphan", log_text, re.I):
            failures.append("log.md does not record the orphaned page")

    # 3. Missing frontmatter field: fixed, or reported.
    if os.path.exists(missing_field):
        head = read(missing_field).split("---")[1] if read(missing_field).startswith("---") else ""
        if "updated:" not in head and not re.search(r"updated|frontmatter|hypertable",
                                                    record, re.I):
            failures.append("concepts/hypertable.md still has no updated: field "
                            "and nothing records that this was noticed")
    else:
        failures.append("concepts/hypertable.md was deleted")

    # 4. The raw source is never touched by a lint run.
    raw = os.path.join(bundle, "raw", "2026-01-02-timescaledb-notes.md")
    if not os.path.exists(raw):
        failures.append("lint deleted a raw source")
    else:
        # Only what happened after the fixture commit: the fixture itself
        # added raw/, and counting that was a false positive on the first
        # run of this case.
        _, base = git(instance, "rev-list", "--max-parents=0", "HEAD")
        _, changed = git(instance, "diff", "--name-only", "%s..HEAD" % base,
                         "--", "%s/raw" % BUNDLE)
        if changed.strip():
            failures.append("lint modified raw/: %s" % changed.strip()[:120])

    # 5. Nothing left uncommitted.
    code, status = git(instance, "status", "--porcelain")
    if code == 0 and status:
        failures.append("lint left uncommitted changes: %s"
                        % status.replace("\n", "; ")[:200])

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
