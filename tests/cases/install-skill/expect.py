#!/usr/bin/env python3
"""Assertions for the "install as a skill without cloning" prompt.

The interesting part is the last instruction in that prompt: fix up the
relative links to match the flattened layout. An installed skill whose
links point at ../../AGENTS.md is silently broken -- the file is there,
the pointer is not. That is exactly what this checks.
"""

import json
import os
import re
import sys

LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def main(workdir):
    failures = []
    skill = os.path.join(workdir, "skills", "llm-wiki-framework")

    if not os.path.isdir(skill):
        return ["the skill folder was not created at skills/llm-wiki-framework"]

    skill_md = os.path.join(skill, "SKILL.md")
    if not os.path.exists(skill_md):
        return ["SKILL.md is not at the root of the skill folder"]

    # Frontmatter is what makes a skill discoverable at all.
    with open(skill_md, encoding="utf-8") as handle:
        text = handle.read()
    if not text.startswith("---"):
        failures.append("SKILL.md has no frontmatter block")
    else:
        head = text.split("---", 2)[1]
        for field in ("name:", "description:"):
            if field not in head:
                failures.append("SKILL.md frontmatter is missing %s" % field)
        if "name: llm-wiki-framework" not in head:
            failures.append("SKILL.md does not declare name: llm-wiki-framework")

    # The files the prompt asks for, beside SKILL.md.
    for path in ("AGENTS.md", "templates"):
        if not os.path.exists(os.path.join(skill, path)):
            failures.append("%s was not installed next to SKILL.md" % path)
    if not any(os.path.exists(os.path.join(skill, candidate))
               for candidate in ("docs/SPEC.md", "SPEC.md")):
        failures.append("SPEC.md was not installed")

    # Nothing may point outside the skill folder: the whole point of the
    # flattened layout is that the skill is self-contained.
    for line_no, line in enumerate(text.splitlines(), 1):
        for target in LINK.findall(line):
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            relative = target.split("#")[0]
            if not relative:
                continue
            resolved = os.path.normpath(os.path.join(skill, relative))
            if not resolved.startswith(os.path.normpath(skill)):
                failures.append(
                    "SKILL.md:%d still points outside the skill folder: %s"
                    % (line_no, target))
            elif not os.path.exists(resolved):
                failures.append(
                    "SKILL.md:%d link does not resolve: %s" % (line_no, target))

    return failures


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1])))
