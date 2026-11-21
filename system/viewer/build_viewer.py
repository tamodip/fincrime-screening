#!/usr/bin/env python3
"""Demo viewer: one self-contained HTML page (inline CSS/JS, no network) for a screening run.

    python3 system/viewer/build_viewer.py <data folder> <predictions.jsonl> <out.html> [--trace trace.jsonl] [--runtime SECONDS]

The trace is written by the engine itself when run with SCREEN_TRACE=<file> (see README); with it the
page shows exactly what the engine compared. The page embeds the records it needs from the data folder
(hits, alerts, resolved customers, their checks/notes, cited search results), so keep it out of git.
"""
import json, os, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def jl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def main(argv):
    args, opts = [], {}
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    data, pred_path, out = args
    preds = jl(pred_path)
    trace = {t["hit_id"]: t for t in jl(opts["trace"])} if opts.get("trace") else {}
    labels = {l["hit_id"]: l for l in jl(os.path.join(data, "practice_labels.jsonl"))}
    hits = {h["hit_id"]: h for h in jl(os.path.join(data, "hits.jsonl"))}
    alerts = {a["alert_id"]: a for a in jl(os.path.join(data, "alerts.jsonl"))}

    need_c, need = set(), set()
    for p in preds:
        need |= set(p.get("evidence") or [])
        if p.get("customer_record_id") and p["customer_record_id"] != "AMBIGUOUS":
            need_c.add(p["customer_record_id"])
    for t in trace.values():
        for P in t.get("people", []):
            need_c |= set(P["rids"])
            need |= set(P.get("notes", [])) | {c["id"] for c in P.get("checks", [])}
        need |= set((t.get("hit") or {}).get("dob_ev", []))
    for l in labels.values():
        need |= set(l.get("evidence") or [])
    need_c |= {x for x in need if x.startswith("CUS-")}
    acc_ids = {a.get("account_ref") for a in alerts.values() if a.get("account_ref")}

    rec = {}
    for c in jl(os.path.join(data, "customers.jsonl")):
        if c["record_id"] in need_c:
            rec[c["record_id"]] = c
    accounts = [a for a in jl(os.path.join(data, "accounts.jsonl")) if a["account_id"] in acc_ids or a["customer_id"] in need_c]
    onboard = [o for o in jl(os.path.join(data, "onboarding.jsonl")) if o["customer_id"] in need_c]
    apps = {o["kyc_applicant_id"] for o in onboard}
    for k in jl(os.path.join(data, "kyc_checks.jsonl")):
        if k["check_id"] in need or k["applicant_id"] in apps:
            rec[k["check_id"]] = k
    for n in jl(os.path.join(data, "notes.jsonl")):
        if n["note_id"] in need:
            rec[n["note_id"]] = n
    for s in jl(os.path.join(data, "search_results.jsonl")):
        if s["result_id"] in need:
            rec[s["result_id"]] = s
    for a in accounts:
        rec.setdefault(a["account_id"], a)
    for o in onboard:
        rec["ONB:" + o["customer_id"] + ":" + o["account_id"]] = o

    dec = Counter(p["decision"] for p in preds)
    by_alert = {}
    for p in preds:
        by_alert.setdefault(p["alert_id"], []).append(p["decision"])
    closed = sum(1 for v in by_alert.values() if all(d == "DIFFERENT_ENTITY" for d in v))
    prac = None
    if labels:
        pm = {p["hit_id"]: p for p in preds}
        right = sum(1 for h, l in labels.items() if h in pm and pm[h]["decision"] == l["decision"])
        unsafe = sum(1 for h, l in labels.items() if h in pm and pm[h]["decision"] == "DIFFERENT_ENTITY" and l["decision"] != "DIFFERENT_ENTITY")
        code_ok = sum(1 for h, l in labels.items() if h in pm and pm[h]["decision"] == l["decision"] and pm[h]["reason_code"] in l.get("reason_codes", []))
        cost = {("DIFFERENT_ENTITY", "SAME_ENTITY"): 60, ("DIFFERENT_ENTITY", "REVIEW"): 60, ("SAME_ENTITY", "DIFFERENT_ENTITY"): 3,
                ("REVIEW", "DIFFERENT_ENTITY"): 3, ("SAME_ENTITY", "REVIEW"): 2, ("REVIEW", "SAME_ENTITY"): 2}
        ours = sum(cost.get((pm[h]["decision"], l["decision"]), 0) for h, l in labels.items() if h in pm)
        base = sum(cost.get(("REVIEW", l["decision"]), 0) for l in labels.values())
        prac = {"n": len(labels), "right": right, "unsafe": unsafe, "code_ok": code_ok,
                "score": round(max(0.0, 100.0 * (base - ours) / base), 1) if base else None}

    payload = {
        "preds": preds, "trace": trace, "labels": {h: {"decision": l["decision"], "reason_codes": l.get("reason_codes", []),
                                                       "evidence": l.get("evidence", [])} for h, l in labels.items()},
        "hits": {h: hits[h] for h in (p["hit_id"] for p in preds) if h in hits},
        "alerts": {a: alerts[a] for a in by_alert if a in alerts},
        "records": rec, "accounts": accounts, "onboarding": onboard,
        "stats": {"hits": len(preds), "alerts": len(by_alert), "closed": closed, "dec": dict(dec),
                  "codes": dict(Counter(p["reason_code"] for p in preds)), "runtime": float(opts["runtime"]) if opts.get("runtime") else None,
                  "built": time.strftime("%Y-%m-%d %H:%M"), "practice": prac},
        "demo": [["H-58A39C", "Clear — DOB contradicts"], ["H-91AC66", "Match — name, DOB, country"], ["H-DC05D5", "Review — no hit DOB"]],
    }
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as fh:
        html = fh.read().replace("/*__DATA__*/null", blob)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("viewer: %s (%.1f MB, %d hits, %d embedded records)" % (out, os.path.getsize(out) / 1e6, len(preds), len(rec)))


if __name__ == "__main__":
    main(sys.argv[1:])
