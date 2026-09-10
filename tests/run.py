#!/usr/bin/env python3
"""run.py -- run a framework case against one or more agents and check the result.

Stdlib-only. Each case is a prompt plus a set of assertions about the
files that exist afterwards. The agent is free to reach the result any
way it likes; what is checked is the state it leaves behind, by reading
the filesystem and Git. No model ever judges another model's output --
that would be an opinion, not a test.

Usage:

    python3 tests/run.py --list
    python3 tests/run.py --case install-clone --model claude
    python3 tests/run.py --case all --model claude,codex --repeat 3
    python3 tests/run.py --case install-clone --model claude --dry-run

Every run happens in a throwaway directory under the system temp dir.
Nothing runs inside this repository, and no credentials are made
available to the agent, so a run cannot push anywhere real: cases that
need a remote get a local bare repository created for them.

These are not deterministic. A single failure means little; a rate over
several repeats is the number worth reading. Results land as JSON and as
a Markdown table.
"""

import argparse
import json
import pty
import re
import select
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "cases")

# The published repository the install prompts point at. Cases that clone
# use this, so the test exercises what a reader would actually run.
REPO_URL = "https://github.com/ramsnerm/llm-wiki-framework.git"

# How each agent is invoked headlessly. The prompt is passed as the final
# argument. `cwd` is the throwaway working directory.
#
# Both bypass their permission prompts: the run is unattended, and the
# directory is disposable. Do not point these adapters at a real
# checkout.
# {WORKDIR} is substituted into the command as well as into the prompt,
# for tools that do not take the working directory from `cwd`.
ADAPTERS = {
    "claude": [
        "claude", "-p", "--dangerously-skip-permissions",
    ],
    "codex": [
        "codex", "exec", "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
    ],
    # agy keeps its own workspace and ignores cwd: without --add-dir it
    # writes into its scratch directory and the case looks like the agent
    # did nothing. Flags must precede -p, which takes the prompt.
    "agy": [
        "agy", "--dangerously-skip-permissions", "--add-dir", "{WORKDIR}", "-p",
    ],
    "grok": ["grok", "--output-format", "plain", "--always-approve"],
    # Not installed here; kept so the matrix reports it rather than
    # silently omitting it.
    "gemini": ["gemini", "-p"],
}

# grok is a TUI: it refuses to start without a terminal, and having
# finished the work it keeps running rather than exiting. So it is driven
# under a pseudo-terminal and stopped once it has gone quiet -- see
# run_via_pty.
PTY_TOOLS = {"grok"}

# Tools that cannot currently be driven unattended, with the reason. They
# are listed rather than dropped: "we could not test it" is information,
# and someone will otherwise try the same thing again.
UNSUPPORTED = {}

# How long a pty-driven tool may show no sign of life before it is treated
# as finished, and the ceiling regardless. "Sign of life" counts changes
# on disk as well as output: a tool that renders into an alternate screen
# buffer produces nothing printable while working hard, and judging it by
# output alone stops it mid-task.
# 120 was still too short: grok acquires the advisory lock, then thinks
# for the better part of three minutes before writing anything. A window
# has to cover the longest silence a working agent produces, not the
# shortest one that looks finished.
PTY_IDLE = 300
PTY_MAX = 1800

ANSI = re.compile(rb"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b[@-Z\\-_]")


def run_via_pty(command, cwd):
    """Run a terminal-only tool and stop it once it stops saying anything.

    There is no exit code to wait for: the tool finishes the task and
    keeps its interface open. Spinners and title updates arrive
    constantly, so "quiet" means no new *printable* output -- escape
    sequences stripped -- for PTY_IDLE seconds.
    """
    started = time.time()
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(cwd)
        os.execvp(command[0], command)

    def workdir_fingerprint():
        """Cheap liveness signal: how the tree looks right now."""
        total = 0
        for dirpath, dirnames, filenames in os.walk(cwd):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for name in filenames:
                try:
                    stat = os.stat(os.path.join(dirpath, name))
                except OSError:
                    continue
                total += int(stat.st_mtime) + stat.st_size
        return total

    raw = b""
    meaningful = 0
    fingerprint = workdir_fingerprint()
    last_change = time.time()
    while True:
        if time.time() - started > PTY_MAX:
            reason = "hard timeout after %ds" % PTY_MAX
            break
        if time.time() - last_change > PTY_IDLE:
            reason = "no output and no file activity for %ds" % PTY_IDLE
            break
        ready, _, _ = select.select([fd], [], [], 2)
        if not ready:
            current = workdir_fingerprint()
            if current != fingerprint:
                fingerprint = current
                last_change = time.time()
            continue
        try:
            chunk = os.read(fd, 8192)
        except OSError:
            reason = "terminal closed"
            break
        if not chunk:
            reason = "output ended"
            break
        raw += chunk
        printable = len(re.sub(rb"\s+", b"", ANSI.sub(b"", raw)))
        if printable != meaningful:
            meaningful = printable
            last_change = time.time()

    for signal_number in (15, 9):
        try:
            os.kill(pid, signal_number)
            time.sleep(0.3)
        except ProcessLookupError:
            break
    try:
        os.close(fd)
    except OSError:
        pass

    text = ANSI.sub(b"", raw).decode("utf-8", "replace")
    return {
        # There is no meaningful exit code here; the run is judged by what
        # it left behind, which is true of every case anyway.
        "exit_code": 0,
        "stdout_tail": text[-4000:],
        "stderr_tail": "",
        "stopped_because": reason,
        "seconds": round(time.time() - started, 1),
    }

TIMEOUT = 900


def available(model):
    return shutil.which(ADAPTERS[model][0]) is not None


def cases():
    if not os.path.isdir(CASES):
        return []
    return sorted(
        name for name in os.listdir(CASES)
        if os.path.isfile(os.path.join(CASES, name, "prompt.txt"))
    )


REPO_ROOT = os.path.dirname(HERE)

# Copied into a case instance; everything else in the repo is either
# instance mechanics or the tests themselves.
FRAMEWORK = ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md",
             "docs", "workflows", "templates", "scripts", "skills")


def build_instance(workdir, fixture):
    """Create a working instance of the framework with the case's bundle.

    The framework comes from this working tree, not from the published
    copy: a regression suite has to test what is about to be merged. The
    fixture is laid over it, and the result is committed, so a case can
    assert against Git as well as against files.
    """
    instance = os.path.join(workdir, "instance")
    os.makedirs(instance)
    for name in FRAMEWORK:
        source = os.path.join(REPO_ROOT, name)
        if not os.path.exists(source):
            continue
        target = os.path.join(instance, name)
        if os.path.isdir(source):
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    if fixture and os.path.isdir(fixture):
        for entry in os.listdir(fixture):
            source = os.path.join(fixture, entry)
            target = os.path.join(instance, entry)
            if os.path.isdir(source):
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

    env = dict(os.environ, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="f@x",
               GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="f@x")
    for args in (["init", "-q", "-b", "main"], ["add", "-A"],
                 ["commit", "-qm", "fixture: starting state"]):
        subprocess.run(["git", "-C", instance] + args, check=True, env=env)
    return instance


def prepare(case, workdir):
    """Set a case up and return the substitutions its prompt needs."""
    subs = {"REPO_URL": REPO_URL, "WORKDIR": workdir}

    # A local bare repo stands in for "your own new repository", so the
    # push step in the install prompt can actually complete -- offline,
    # and without any credential existing anywhere.
    target = os.path.join(workdir, "target.git")
    subprocess.run(["git", "init", "--bare", "-q", target], check=True)
    subs["TARGET_REPO"] = target
    subs["SKILL_DIR"] = os.path.join(workdir, "skills", "llm-wiki-framework")

    fixture = os.path.join(CASES, case, "fixture")
    if os.path.isdir(fixture):
        subs["INSTANCE"] = build_instance(workdir, fixture)

    # A case may ship loose files -- a document to ingest, say -- that
    # belong in the working directory rather than inside an instance.
    loose = os.path.join(CASES, case, "files")
    if os.path.isdir(loose):
        for entry in os.listdir(loose):
            source = os.path.join(loose, entry)
            target = os.path.join(workdir, entry)
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)

    # End-to-end cases start from a real repository rather than a
    # fixture. This one starts from wherever *this* checkout came from,
    # whatever forge that is: the URL is read from its origin rather than
    # written down here, so nothing instance-specific ships in the public
    # template, and it is mirrored locally so the agent never needs a
    # credential of its own.
    if case.startswith("e2e-origin"):
        result = subprocess.run(["git", "-C", REPO_ROOT, "remote", "get-url", "origin"],
                                capture_output=True, text=True)
        origin = result.stdout.strip()
        if result.returncode != 0 or not origin:
            raise RuntimeError(
                "e2e-origin needs an 'origin' remote on the checkout the "
                "tests live in; none is configured")
        mirror = os.path.join(workdir, "source.git")
        subprocess.run(["git", "clone", "--quiet", "--bare", origin, mirror],
                       check=True)
        subs["SOURCE_REPO"] = mirror
    return subs


def run_case(case, model, workdir, dry_run=False):
    prompt_path = os.path.join(CASES, case, "prompt.txt")
    with open(prompt_path, encoding="utf-8") as handle:
        prompt = handle.read()
    subs = prepare(case, workdir)
    for key, value in subs.items():
        prompt = prompt.replace("{%s}" % key, value)

    command = [part.replace("{WORKDIR}", workdir) for part in ADAPTERS[model]]
    command = command + [prompt]
    if dry_run:
        print("cwd: %s" % workdir)
        print("cmd: %s" % " ".join(command[:-1]))
        print("--- prompt ---")
        print(prompt)
        return {"skipped": "dry-run"}

    env = dict(os.environ)
    # No credential helper, no prompting: a run physically cannot
    # authenticate to anything.
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "/usr/bin/false"

    if model in PTY_TOOLS:
        # env is not passed through pty.fork(); set it for this process so
        # the child inherits the same credential lockout as everyone else.
        os.environ.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/usr/bin/false"})
        agent = run_via_pty(command, workdir)
        with open(os.path.join(workdir, "agent-output.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write(agent.get("stdout_tail") or "")
        check = subprocess.run(
            [sys.executable, os.path.join(CASES, case, "expect.py"), workdir],
            capture_output=True, text=True)
        try:
            failures = json.loads(check.stdout or "[]")
        except json.JSONDecodeError:
            failures = ["expect.py produced no readable result: %s"
                        % (check.stderr.strip()[:400] or check.stdout.strip()[:400])]
        return {"agent": agent, "failures": failures,
                "passed": not failures, "errored": False}

    started = time.time()
    try:
        completed = subprocess.run(
            command, cwd=workdir, env=env, timeout=TIMEOUT,
            capture_output=True, text=True,
        )
        agent = {
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        agent = {"exit_code": None, "timeout": TIMEOUT}
    agent["seconds"] = round(time.time() - started, 1)

    # A read-only case has nothing on disk to inspect, so what the agent
    # said is the only evidence it did anything. Written to a file rather
    # than judged here: expect.py stays the single place assertions live.
    with open(os.path.join(workdir, "agent-output.txt"), "w",
              encoding="utf-8") as handle:
        handle.write(agent.get("stdout_tail") or "")

    # Assertions run as their own process so a broken case cannot take
    # the harness down with it.
    check = subprocess.run(
        [sys.executable, os.path.join(CASES, case, "expect.py"), workdir],
        capture_output=True, text=True,
    )
    try:
        failures = json.loads(check.stdout or "[]")
    except json.JSONDecodeError:
        failures = ["expect.py produced no readable result: %s"
                    % (check.stderr.strip()[:400] or check.stdout.strip()[:400])]

    # An agent that never ran is not a failing case. Conflating the two
    # poisons the rate: infrastructure noise -- an expired login, a model
    # the account cannot reach, a timeout -- would read as the framework
    # being at fault.
    errored = agent.get("exit_code") not in (0, None) or "timeout" in agent
    return {
        "agent": agent,
        "failures": failures,
        "passed": not failures and not errored,
        "errored": errored,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--case", default="all")
    parser.add_argument("--model", default="claude")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--out", default=None, help="write JSON results here")
    parser.add_argument("--keep", action="store_true",
                        help="keep the throwaway directories for inspection")
    args = parser.parse_args()

    if args.list:
        for name in cases():
            print(name)
        for model in ADAPTERS:
            print("model %-8s %s" % (model, "available" if available(model) else "NOT INSTALLED"))
        for model, reason in UNSUPPORTED.items():
            print("model %-8s UNSUPPORTED: %s" % (model, reason))
        return 0

    selected = cases() if args.case == "all" else args.case.split(",")
    models = args.model.split(",")

    for name in selected:
        if name not in cases():
            print("unknown case: %s" % name, file=sys.stderr)
            return 2
    for model in models:
        if model not in ADAPTERS:
            print("unknown model: %s" % model, file=sys.stderr)
            return 2
        if not available(model) and not args.dry_run:
            print("%s is not installed on this machine" % model, file=sys.stderr)
            return 2

    results = []
    for name in selected:
        for model in models:
            for attempt in range(1, args.repeat + 1):
                workdir = tempfile.mkdtemp(prefix="llmwiki-%s-%s-" % (name, model))
                print("· %s / %s (%d/%d) in %s" % (name, model, attempt, args.repeat, workdir))
                outcome = run_case(name, model, workdir, args.dry_run)
                outcome.update({"case": name, "model": model, "attempt": attempt,
                                "workdir": workdir})
                results.append(outcome)
                if outcome.get("errored"):
                    agent = outcome["agent"]
                    detail = (agent.get("stderr_tail") or "").strip().splitlines()
                    print("    ERROR the agent did not run (exit %s)"
                          % agent.get("exit_code"))
                    if detail:
                        print("          %s" % detail[-1][:200])
                elif outcome.get("failures"):
                    for failure in outcome["failures"]:
                        print("    FAIL %s" % failure)
                elif not args.dry_run:
                    print("    ok (%ss)" % outcome["agent"]["seconds"])
                if not args.keep and not args.dry_run:
                    shutil.rmtree(workdir, ignore_errors=True)

    if args.dry_run:
        return 0

    print("\n| case | model | passed | errored |")
    print("|---|---|---|---|")
    for name in selected:
        for model in models:
            runs = [r for r in results if r["case"] == name and r["model"] == model]
            ok = sum(1 for r in runs if r["passed"])
            bad = sum(1 for r in runs if r.get("errored"))
            usable = len(runs) - bad
            print("| %s | %s | %s | %s |" % (
                name, model,
                "%d/%d" % (ok, usable) if usable else "—",
                bad or ""))

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, indent=2)
        print("\nresults: %s" % args.out)

    usable = [r for r in results if not r.get("errored")]
    if not usable:
        print("\nno usable runs: every agent failed to start")
        return 2
    return 0 if all(r["passed"] for r in usable) else 1


if __name__ == "__main__":
    sys.exit(main())
