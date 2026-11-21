#!/usr/bin/env python3
"""Second perturbation stage for paraphrase_check: same facts, different structured formats.
Usage: _structured.py <src folder> <dst folder>. Seeded, so repeatable."""
import json, os, random, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import countries as CT  # noqa: E402
from screen import parse_date  # noqa: E402

rng = random.Random(23)
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NAME2ISO = {name: iso for iso, name in CT.ISO2CANON.items()}


def fmt(v):
    d = parse_date(v) if isinstance(v, str) else None
    if not d or not d[1] or not d[2] or rng.random() > 0.6:
        return v
    y, m, dd = d
    return rng.choice(["%04d-%02d-%02d" % (y, m, dd), "%d %s %d" % (dd, MONTHS[m - 1], y), "%s %d, %d" % (MONTHS[m - 1], dd, y),
                       "%02d/%02d/%04d" % (dd, m, y), "%d %s %d" % (dd, MONTHS[m - 1][:3], y)])


def ctry(v):
    c = CT.canon(v) if isinstance(v, str) else None
    if not c or rng.random() > 0.5:
        return v
    iso = NAME2ISO.get(c)
    return rng.choice([c, iso or c, c.upper()])


def main(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    def rw(name, fn):
        path = os.path.join(dst, name)
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        with open(path, "w", encoding="utf-8") as fh:
            for r in rows:
                fn(r)
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    def cust(r):
        r["dob"] = fmt(r.get("dob"))
        r["nationality"] = ctry(r.get("nationality"))
        r["residence_country"] = ctry(r.get("residence_country"))
        if r.get("full_name") and rng.random() < 0.3:
            r["full_name"] = r["full_name"].upper() if rng.random() < 0.5 else r["full_name"].title()

    def kyc(r):
        r["verified_dob"] = fmt(r.get("verified_dob"))
        r["checked_at"] = fmt(r.get("checked_at"))
        r["document_country"] = ctry(r.get("document_country"))

    rw("customers.jsonl", cust)
    rw("kyc_checks.jsonl", kyc)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
