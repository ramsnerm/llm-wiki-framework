#!/usr/bin/env python3
"""compare.py -- have models rank each other's wiki writing, blind.

This is not a test. `tests/run.py` checks properties that are true or
false: a hash matches, a link resolves, a file was not deleted. Whether
a summary is *good* is not that kind of question, and pretending
otherwise would produce a green tick that means nothing.

So this is an evaluation with an honest instrument: the same source
document is ingested by each model, the resulting pages are stripped of
anything identifying, shuffled, and shown to each judge alongside the
original source. Judges rank them and say why. What comes back is
aggregated opinion -- useful for comparing, useless as a gate.

Two biases are handled and one is not. Order is shuffled per judge, so
position does not decide. Authorship is hidden, and whether a judge
still favoured its own output is reported, because that is worth
knowing. What remains uncontrolled is that every judge is a language
model: they may share a taste that a human reader would not.

Usage:

    python3 tests/compare.py --case ingest-source \\
        --models claude,codex --judges claude,codex
    python3 tests/compare.py --case ingest-source --models claude,codex \\
        --reuse /tmp/compare-runs.json
"""

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run as harness  # noqa: E402  -- adapters, prepare(), instance building

JUDGE_PROMPT = """You are reviewing wiki pages that different systems
produced from the same source document. Judge only the writing and the
information: which rendering would serve a reader best six months from
now, when the source is forgotten and only the wiki remains.

Weigh these, in this order:

1. Faithfulness — does every claim follow from the source? A confident
   sentence the source does not support is the worst defect here.
2. Completeness — is anything load-bearing missing?
3. Usefulness — is it organised so a reader finds what they need, with
   claims attributed rather than asserted?
4. Restraint — padding, invented structure and repeated content all
   count against.

THE SOURCE DOCUMENT:

<<<SOURCE
%s
SOURCE

THE RENDERINGS:

%s

Reply with one JSON object and nothing else:

{"ranking": ["A", "B", ...], "reasons": {"A": "one sentence", ...},
 "worst_problem": "the single most serious defect you saw, and where"}

"ranking" is best first, every label exactly once.
"""


def collect_pages(instance, bundle="testbundle"):
    """The typed pages a run produced, as one readable blob."""
    root = os.path.join(instance, "bundles", bundle)
    parts = []
    if not os.path.isdir(root):
        return ""
    for folder in sorted(os.listdir(root)):
        path = os.path.join(root, folder)
        if not os.path.isdir(path) or folder in ("raw", ".git"):
            continue
        for name in sorted(os.listdir(path)):
            if not name.endswith(".md"):
                continue
            with open(os.path.join(path, name), encoding="utf-8") as handle:
                parts.append("--- %s/%s ---\n%s" % (folder, name, handle.read()))
    return "\n\n".join(parts)


def anonymise(text):
    """Remove what would identify the author rather than the writing."""
    text = re.sub(r"(?im)^\s*(created|updated):.*$", "", text)
    text = re.sub(r"(?i)\b(claude|anthropic|codex|openai|gpt|gemini|google|"
                  r"grok|xai|agy|antigravity)\b", "the agent", text)
    text = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", "<date>", text)
    return text.strip()


def produce(case, models, keep):
    """Run the case once per model; return {model: pages}."""
    outputs = {}
    for model in models:
        workdir = tempfile.mkdtemp(prefix="compare-%s-%s-" % (case, model))
        print("· producing with %s in %s" % (model, workdir))
        outcome = harness.run_case(case, model, workdir)
        if outcome.get("errored"):
            print("    ERROR %s never ran (exit %s)"
                  % (model, outcome["agent"].get("exit_code")))
        else:
            pages = collect_pages(os.path.join(workdir, "instance"))
            if pages.strip():
                outputs[model] = pages
                print("    %d characters of wiki" % len(pages))
            else:
                print("    produced no pages")
        if not keep:
            shutil.rmtree(workdir, ignore_errors=True)
    return outputs


def ask_judge(judge, prompt):
    if judge in harness.UNSUPPORTED or not harness.available(judge):
        return None, "%s cannot be driven here" % judge
    workdir = tempfile.mkdtemp(prefix="judge-%s-" % judge)
    command = [p.replace("{WORKDIR}", workdir) for p in harness.ADAPTERS[judge]]
    try:
        completed = subprocess.run(command + [prompt], cwd=workdir, timeout=600,
                                   capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        shutil.rmtree(workdir, ignore_errors=True)
        return None, "timed out"
    shutil.rmtree(workdir, ignore_errors=True)
    if completed.returncode != 0:
        return None, (completed.stderr.strip().splitlines() or ["exit %d" % completed.returncode])[-1][:160]
    # The last JSON object in the output, so surrounding chatter is fine.
    blobs = re.findall(r"\{.*\}", completed.stdout, re.S)
    for blob in reversed(blobs):
        try:
            parsed = json.loads(blob)
            if "ranking" in parsed:
                return parsed, None
        except json.JSONDecodeError:
            continue
    return None, "no ranking in the reply"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", default="ingest-source")
    parser.add_argument("--models", default="claude,codex")
    parser.add_argument("--judges", default=None,
                        help="default: the same list as --models")
    parser.add_argument("--source", default=None,
                        help="the source document shown to judges; defaults to "
                             "the single file in the case's fixture raw/")
    parser.add_argument("--reuse", default=None,
                        help="skip producing and load outputs from this JSON")
    parser.add_argument("--out", default=None)
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()

    models = args.models.split(",")
    judges = (args.judges or args.models).split(",")

    if args.reuse:
        with open(args.reuse, encoding="utf-8") as handle:
            outputs = json.load(handle)
        print("reusing %d outputs from %s" % (len(outputs), args.reuse))
    else:
        outputs = produce(args.case, models, args.keep)

    if len(outputs) < 2:
        print("\nneed at least two outputs to compare; got %d" % len(outputs))
        return 2

    source_path = args.source
    if not source_path:
        raw = os.path.join(HERE, "cases", args.case, "fixture",
                           "bundles", "testbundle", "raw")
        files = sorted(f for f in os.listdir(raw) if f.endswith(".md"))
        source_path = os.path.join(raw, files[0])
    with open(source_path, encoding="utf-8") as handle:
        source = handle.read()

    if args.out:
        with open(args.out.replace(".json", "-runs.json"), "w", encoding="utf-8") as handle:
            json.dump(outputs, handle, indent=2)

    verdicts = []
    for judge in judges:
        order = list(outputs)
        random.shuffle(order)
        labels = dict(zip("ABCDEFG", order))          # label -> model
        rendered = "\n\n".join(
            "=== RENDERING %s ===\n%s" % (label, anonymise(outputs[model]))
            for label, model in labels.items())
        parsed, error = ask_judge(judge, JUDGE_PROMPT % (source, rendered))
        if error:
            print("· judge %-8s unavailable: %s" % (judge, error))
            continue
        ranking = [labels.get(label) for label in parsed.get("ranking", [])
                   if label in labels]
        print("· judge %-8s ranks: %s" % (judge, " > ".join(ranking)))
        if parsed.get("worst_problem"):
            print("           worst: %s" % str(parsed["worst_problem"])[:200])
        verdicts.append({"judge": judge, "ranking": ranking,
                         "labels": labels, "raw": parsed})

    if not verdicts:
        print("\nno judge produced a ranking")
        return 2

    print("\n| model | mean rank | firsts | judged best by itself |")
    print("|---|---|---|---|")
    for model in outputs:
        places = [v["ranking"].index(model) + 1 for v in verdicts
                  if model in v["ranking"]]
        if not places:
            continue
        firsts = sum(1 for p in places if p == 1)
        self_first = any(v["judge"] == model and v["ranking"][:1] == [model]
                         for v in verdicts)
        print("| %s | %.2f | %d/%d | %s |" % (
            model, sum(places) / len(places), firsts, len(places),
            "yes" if self_first else "—"))

    print("\nRankings are opinion, aggregated. Read them next to the "
          "reasons, not as a score.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump({"case": args.case, "verdicts": verdicts}, handle, indent=2)
        print("details: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
