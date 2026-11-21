#!/usr/bin/env python3
"""Paraphrase robustness check.

Usage: python3 system/tests/paraphrase_check.py <dev folder> <work dir>
Rewrites the free text of a data folder with new templates (KYC notes, residence notes,
search-result snippets, profile-note age sentences), then rewrites structured fields (date
formats of customer and KYC dates, country names <-> ISO codes, upper/lower case names), reruns the system on the rewritten copy
and on the original, and prints how many decisions changed. Facts are kept identical, so a
robust system should not change any decision."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    dev, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, PARA_SRC=dev, PARA_WORK=work)
    subprocess.check_call([sys.executable, os.path.join(HERE, "_paraphrase.py")], env=env)
    run = os.path.join(os.path.dirname(HERE), "run")
    subprocess.check_call([run, dev, os.path.join(work, "orig.jsonl")])
    subprocess.check_call([sys.executable, os.path.join(HERE, "_structured.py"), os.path.join(work, "p2"), os.path.join(work, "p3")])
    subprocess.check_call([run, os.path.join(work, "p3"), os.path.join(work, "para.jsonl")])
    import json
    a = {json.loads(l)["hit_id"]: json.loads(l)["decision"] for l in open(os.path.join(work, "orig.jsonl"))}
    b = {json.loads(l)["hit_id"]: json.loads(l)["decision"] for l in open(os.path.join(work, "para.jsonl"))}
    changed = sorted(k for k in a if a[k] != b.get(k))
    print("%d of %d decisions changed after paraphrasing" % (len(changed), len(a)))
    for k in changed:
        print("  %s: %s -> %s" % (k, a[k], b.get(k)))
    sys.exit(1 if changed else 0)


if __name__ == "__main__":
    main()
