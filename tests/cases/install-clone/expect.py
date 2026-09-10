#!/usr/bin/env python3
"""Assertions for the "clone into a repo of your own" prompt.

Prints a JSON list of failures; an empty list means the case passed.
Everything here is read off the filesystem and out of Git -- nothing
depends on what the agent said it did.
"""

import json
import os
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(
        ["git", "-C", repo] + list(args),
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip()


def main(workdir):
    failures = []
    wiki = os.path.join(workdir, "my-wiki")

    if not os.path.isdir(wiki):
        return ["./my-wiki was not created"]
    if not os.path.isdir(os.path.join(wiki, ".git")):
        return ["my-wiki exists but is not a Git repository"]

    # The three files the prompt asks to confirm, plus the two the
    # framework cannot work without.
    for path in ("AGENTS.md",
                 "skills/llm-wiki-framework/SKILL.md",
                 "docs/SPEC.md",
                 "docs/HANDBOOK.md",
                 "workflows/ingest.md"):
        if not os.path.exists(os.path.join(wiki, path)):
            failures.append("%s missing from the clone" % path)

    # The remote was actually repointed, not merely added alongside.
    code, remotes = git(wiki, "remote")
    names = remotes.split()
    if code != 0:
        failures.append("could not read remotes")
    else:
        if "origin" not in names:
            failures.append("no 'origin' remote after the rewrite")
        else:
            _, url = git(wiki, "remote", "get-url", "origin")
            if "github.com" in url:
                failures.append("origin still points at the template: %s" % url)
            elif not url.endswith("target.git"):
                failures.append("origin points somewhere unexpected: %s" % url)

    # The push landed: the bare repo has the same commit the clone is on.
    target = os.path.join(workdir, "target.git")
    code, head = git(wiki, "rev-parse", "HEAD")
    if code != 0:
        failures.append("clone has no HEAD")
    else:
        code, refs = git(target, "for-each-ref", "--format=%(objectname)")
        if code != 0:
            failures.append("target repository unreadable")
        elif head not in refs.split():
            failures.append("nothing was pushed to the target repository")

    # Nothing was left half-done in the working tree.
    code, status = git(wiki, "status", "--porcelain")
    if code == 0 and status:
        failures.append("clone left uncommitted changes: %s"
                        % status.replace("\n", "; ")[:200])

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
