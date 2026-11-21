#!/usr/bin/env python3
"""Deterministic watchlist hit resolution, following POLICY.md principles 1-9.

Usage: screen.py <data folder> <output file>
Python 3 standard library only. No language model, no network, no randomness:
rules, normalisation, regex parsing of free text and fuzzy string matching.
"""
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import countries as CT  # noqa: E402

# ----------------------------------------------------------------------------- io

def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


# ----------------------------------------------------------------------------- dates
MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}
for _k, _v in list(MONTHS.items()):
    MONTHS[_k[:3]] = _v
MONTHS["sept"] = 9
MON_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?"

DATE_PATTERNS = [
    # (regex, kind)
    (re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{1,2})[/.](\d{1,2})[/.](\d{4})(?!\d)"), "dmy"),
    (re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + MON_RE + r"),?\s+(\d{4})(?!\d)", re.I), "dMy"),
    (re.compile(r"(?<![A-Za-z])(" + MON_RE + r")\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})(?!\d)", re.I), "Mdy"),
    (re.compile(r"(?<!\d)(\d{4})-(\d{1,2})(?![\d-])"), "ym"),
    (re.compile(r"(?<![A-Za-z])(" + MON_RE + r"),?\s+(?:of\s+)?(\d{4})(?!\d)", re.I), "My"),
    (re.compile(r"(?<![\d/.-])(1[89]\d{2}|20\d{2})(?![\d/-])"), "y"),
]


def _mk(y, m=None, d=None):
    y = int(y)
    m = int(m) if m else None
    d = int(d) if d else None
    if m is not None and not 1 <= m <= 12:
        return None
    if d is not None and not 1 <= d <= 31:
        return None
    if not 1800 <= y <= 2100:
        return None
    return (y, m, d)


def _month(tok):
    return MONTHS.get(tok.lower().rstrip(".")[:3]) if tok.lower().rstrip(".") not in MONTHS else MONTHS[tok.lower().rstrip(".")]


def find_dates(text):
    """All dates in text -> list of (start, end, (y,m,d)) non-overlapping, earliest-pattern-wins."""
    if not text:
        return []
    taken = []
    out = []
    for rx, kind in DATE_PATTERNS:
        for mt in rx.finditer(text):
            s, e = mt.span()
            if any(s < te and e > ts for ts, te in taken):
                continue
            g = mt.groups()
            try:
                if kind == "ymd":
                    dt = _mk(g[0], g[1], g[2])
                elif kind == "dmy":
                    dt = _mk(g[2], g[1], g[0])
                elif kind == "dMy":
                    dt = _mk(g[2], _month(g[1]), g[0])
                elif kind == "Mdy":
                    dt = _mk(g[2], _month(g[0]), g[1])
                elif kind == "ym":
                    dt = _mk(g[0], g[1])
                elif kind == "My":
                    dt = _mk(g[1], _month(g[0]))
                else:
                    dt = _mk(g[0])
            except (TypeError, ValueError):
                dt = None
            if dt:
                taken.append((s, e))
                out.append((s, e, dt))
    out.sort()
    return out


SLASH_RE = re.compile(r"(?<![\d/.])(\d{1,2})[/.](\d{1,2})[/.](\d{4})(?![\d/])")


def find_provider_dates(text):
    """Dates inside watchlist profiles, written as the provider wrote them: a slash date whose
    order cannot be told apart (both parts <= 12 and different) keeps only its year."""
    out = []
    for s, e, d in find_dates(text):
        out.append((s, e, d))
    fixed = []
    for s, e, d in out:
        m = SLASH_RE.match(text, s) if s < len(text) else None
        if m and m.end() == e:
            a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if a > 12 and b <= 12:
                d = (y, b, a)
            elif b > 12 and a <= 12:
                d = (y, a, b)
            elif a == b:
                d = (y, a, b)
            else:
                d = (y, None, None)
        fixed.append((s, e, d))
    # m/d/yyyy with month > 12 is rejected by find_dates; recover it
    for m in SLASH_RE.finditer(text):
        if any(s <= m.start() < e for s, e, _ in fixed):
            continue
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if b > 12 and a <= 12 and 1 <= b <= 31:
            fixed.append((m.start(), m.end(), (y, a, b)))
    # drop bare-year matches that sit inside a recovered slash date
    fixed.sort()
    clean = []
    for s, e, d in fixed:
        if clean and s < clean[-1][1]:
            if (e - s) > (clean[-1][1] - clean[-1][0]):
                clean[-1] = (s, e, d)
            continue
        clean.append((s, e, d))
    return clean


def parse_date(value):
    if not value or not isinstance(value, str):
        return None
    v = value.strip()
    if v.lower() in ("none", "null", "unknown", "n/a", "na", ""):
        return None
    ds = find_dates(v)
    return ds[0][2] if ds else None


def fmt_date(d):
    if not d:
        return "unknown"
    y, m, dd = d
    if m and dd:
        return "%04d-%02d-%02d" % (y, m, dd)
    if m:
        return "%04d-%02d" % (y, m)
    return "%04d" % y


def date_key(d):
    return (d[0], d[1] or 0, d[2] or 0) if d else (0, 0, 0)


# ----------------------------------------------------------------------------- names
PLACEHOLDERS = {"na", "n/a", "test", "unknown", "xxx", "xx", "none", "null", "nil", "tbd", "tba", "dummy", "noname", "anonymous",
                "unk", "nn", "fnu", "lnu", "nfn", "nln", "notknown", "notprovided", "blank", "sample", "x"}


# Cyrillic/Greek letters that look like Latin ones; mapped only inside words that also contain Latin letters
CONFUSABLE = str.maketrans("АаВЕеКкМНОоРрСсТуХхІіЈјЅѕԁΑΒΕΖΗΙΚΜΝΟοΡΤΥΧ", "AaBEeKkMHOoPpCcTyXxIiJjSsdABEZHIKMNOoPTYX")


def _unconfuse(s):
    return re.sub(r"\w+", lambda m: m.group(0).translate(CONFUSABLE) if re.search(r"[A-Za-z]", m.group(0)) else m.group(0), s)


def non_latin(s):
    """True when a name still has letters outside the Latin script after folding (e.g. written in Cyrillic)."""
    return bool(re.search(r"[^\W\d_a-z\u00c0-\u024f\u1e00-\u1eff]", fold(s or "")))


def fold(s):
    s = _unconfuse(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    repl = {"ß": "ss", "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ł": "l", "Ł": "l", "đ": "d", "Đ": "d",
            "ı": "i", "þ": "th", "ð": "d", "ħ": "h", "ŋ": "n", "ŧ": "t", "ĸ": "k"}
    s = s.lower()
    return "".join(repl.get(c, c) for c in s)


class NameModel:
    def __init__(self, variants):
        self.var = {}
        for gi, g in enumerate(variants.get("groups", [])):
            for n in g:
                self.var.setdefault(fold(n), set()).add(gi)
        self.legal = {fold(x) for x in variants.get("company_legal_forms", [])}

    def parts(self, name, company=False):
        if not name or not isinstance(name, str):
            return []
        s = re.sub(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}", " ", name)
        s = fold(s)
        if s.strip() in ("n/a",):
            return []
        s = re.sub(r"['’`´]", "", s)
        s = re.sub(r"[^a-z0-9]+", " ", s)
        out = []
        for t in s.split():
            if len(t) < 2:
                continue  # initials are not parts
            if any(ch.isdigit() for ch in t):
                continue
            if t in PLACEHOLDERS:
                continue
            if company and t in self.legal:
                continue
            if t not in out:
                out.append(t)
        return out

    @staticmethod
    def edit(a, b, limit):
        if abs(len(a) - len(b)) > limit:
            return limit + 1
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i] + [0] * len(b)
            best = cur[0]
            for j, cb in enumerate(b, 1):
                cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
                best = min(best, cur[j])
            if best > limit:
                return limit + 1
            prev = cur
        return prev[-1]

    def part_match(self, a, b):
        if a == b:
            return True
        ga, gb = self.var.get(a), self.var.get(b)
        if ga and gb and ga & gb:
            return True
        n = min(len(a), len(b))
        if n < 4:
            return False
        lim = 1 if n <= 6 else 2
        return self.edit(a, b, lim) <= lim

    def compare(self, pa, pb):
        """Return (agree, matched_count). pa, pb: part lists."""
        if not pa or not pb:
            return False, 0
        A, B = list(pa), list(pb)
        used_a, used_b = set(), set()
        matched = 0
        # joined / split parts: one part of X equals two adjacent parts of Y (either order)
        for X, Y, ux, uy, flip in ((A, B, used_a, used_b, False), (B, A, used_b, used_a, True)):
            for i, x in enumerate(X):
                if i in ux:
                    continue
                for j in range(len(Y) - 1):
                    if j in uy or j + 1 in uy:
                        continue
                    for cat in (Y[j] + Y[j + 1], Y[j + 1] + Y[j]):
                        if x == cat or (len(x) >= 7 and self.edit(x, cat, 1) <= 1):
                            ux.add(i)
                            uy.update((j, j + 1))
                            matched += 1
                            break
                    if i in ux:
                        break
        # one-to-one part matching, exact first then fuzzy (deterministic order)
        for exact in (True, False):
            for i, a in enumerate(A):
                if i in used_a:
                    continue
                for j, b in enumerate(B):
                    if j in used_b:
                        continue
                    if (a == b) if exact else self.part_match(a, b):
                        used_a.add(i)
                        used_b.add(j)
                        matched += 1
                        break
        all_a = len(used_a) == len(A)
        all_b = len(used_b) == len(B)
        shorter_all = all_a if len(A) < len(B) else all_b if len(B) < len(A) else (all_a or all_b)
        return (matched >= 2 or shorter_all), matched

    def agree(self, name_a, name_b, company=False):
        return self.compare(self.parts(name_a, company), self.parts(name_b, company))[0]


# ----------------------------------------------------------------------------- data loading

class Data:
    def __init__(self, folder):
        j = lambda n: read_jsonl(os.path.join(folder, n + ".jsonl"))
        self.alerts = j("alerts")
        self.hits = {h["hit_id"]: h for h in j("hits")}
        self.customers = {c["record_id"]: c for c in j("customers")}
        self.accounts = j("accounts")
        self.onboarding = j("onboarding")
        self.kyc = j("kyc_checks")
        self.notes = j("notes")
        self.search = j("search_results")
        vp = os.path.join(folder, "name_variants.json")
        self.nm = NameModel(json.load(open(vp, encoding="utf-8")) if os.path.exists(vp) else {})
        self.index()

    def index(self):
        nm = self.nm
        self.acc_by_id = defaultdict(list)
        self.acc_by_login = defaultdict(list)
        self.acc_by_cust = defaultdict(list)
        for a in self.accounts:
            self.acc_by_id[a["account_id"]].append(a)
            if a.get("login_handle"):
                self.acc_by_login[a["login_handle"].lower()].append(a)
            self.acc_by_cust[a["customer_id"]].append(a)
        self.app_by_cust = defaultdict(set)
        for o in self.onboarding:
            if o.get("customer_id") and o.get("kyc_applicant_id"):
                self.app_by_cust[o["customer_id"]].add(o["kyc_applicant_id"])
            elif o.get("account_id") and o.get("kyc_applicant_id"):
                for a in self.acc_by_id.get(o["account_id"], []):
                    self.app_by_cust[a["customer_id"]].add(o["kyc_applicant_id"])
        self.kyc_by_app = defaultdict(list)
        for k in self.kyc:
            self.kyc_by_app[k["applicant_id"]].append(k)
        self.cust_by_email = defaultdict(list)
        self.name_index = defaultdict(set)
        for rid, c in self.customers.items():
            if c.get("email"):
                self.cust_by_email[c["email"].lower()].append(rid)
            comp = c.get("entity_type") == "Company"
            for f in ("full_name", "preferred_name", "login_name"):
                for p in nm.parts(c.get(f), comp):
                    self.name_index[p].add(rid)
                    self.name_index["^" + p[:3]].add(rid)
                    self.name_index[p[-3:] + "$"].add(rid)
        self.notes_by_email = defaultdict(list)
        for n in self.notes:
            if n.get("requester_email"):
                self.notes_by_email[n["requester_email"].lower()].append(n)
        # search results by sorted token key
        self.sr_by_key = defaultdict(list)
        for s in self.search:
            self.sr_by_key[" ".join(sorted(nm.parts(s.get("query") or "")))].append(s)
        self.build_people()

    # ---- one person, one picture (principle 3)
    def build_people(self):
        parent = {}

        def find(x):
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                if ra < rb:
                    parent[rb] = ra
                else:
                    parent[ra] = rb

        by_phone_dob = defaultdict(list)
        for rid, c in self.customers.items():
            ph = re.sub(r"\D", "", c.get("phone") or "")
            d = parse_date(c.get("dob"))
            if len(ph) >= 6 and d and d[1] and d[2]:
                by_phone_dob[(ph, d)].append(rid)
        for rids in by_phone_dob.values():
            if len(rids) > 6:
                continue  # a phone+DOB shared this widely is a placeholder, not one person
            for r in rids[1:]:
                union(rids[0], r)
        by_doc = defaultdict(set)
        for rid in self.customers:
            for app in self.app_by_cust.get(rid, ()):
                for k in self.kyc_by_app.get(app, ()):
                    if (k.get("result") or "").lower() == "approved" and k.get("document_number"):
                        dn = re.sub(r"[^A-Z0-9]", "", k["document_number"].upper())
                        if len(dn) >= 3 and dn not in ("UNKNOWN", "NONE", "NULL", "NA", "NOTAVAILABLE", "TEST", "XXX"):
                            by_doc[dn].add(rid)
        for rids in by_doc.values():
            rids = sorted(rids)
            if len(rids) > 6:
                continue
            for r in rids[1:]:
                union(rids[0], r)
        self.person_of = {}
        groups = defaultdict(list)
        for rid in self.customers:
            groups[find(rid)].append(rid)
        for root, rids in groups.items():
            rids = sorted(rids)
            for r in rids:
                self.person_of[r] = tuple(rids)


# ----------------------------------------------------------------------------- KYC notes
NEG_RE = re.compile(r"\b(reject\w*|fail\w*|declin\w*|expired|unsuccessful\w*|could not|couldn't|unable|not (?:be )?(?:verified|approved|validated|confirmed|pass\w*)|mismatch\w*|invalid|denied|refused|cancel\w*|did not pass|no longer valid|pending|awaiting|requested|resubmi\w*|under review|in progress|incomplete|on hold|not yet|inconclusive|flagged|suspended|revoked|superseded|withdrawn|did not match|does not match|no match)\b", re.I)
VERIFY_RE = re.compile(r"\b(verif\w*|validat\w*|confirm\w*|pass(?:ed)?|approv\w*|complet\w*|check(?:ed)?|process\w*|accept\w*|clear\w*|success\w*|authenticat\w*|cleared|ok)\b", re.I)
DOB_KW = re.compile(r"(born|dob|d\.o\.b|birth|birthdate)", re.I)
DOB_PRE = re.compile(r"(?:\bborn(?:\s+on|\s+in)?|\bdob|\bd\.o\.b\.?|\bbirth(?:\s*date)?(?:\s+of)?|\bdate\s+of\s+birth(?:\s+of)?|\bbirthday)\s*[:=,(\-]?\s*$", re.I)
CAPS_STOP = {"SUMSUB", "ONFIDO", "VERIFF", "PERSONA", "JUMIO", "TRULIOO", "IDNOW", "YOTI", "MITEK", "DOB", "ID", "KYC", "UK", "US", "USA", "UAE", "EU", "D.O.B", "AML", "PEP", "N/A", "II", "III", "IV"}


TITLE_STOP = {w.lower() for w in """On In At By For Of The A An And Or Identity Identification Verification Verified Validated Check Checked
Passed Pass Approved Complete Completed Customer Client Applicant User Account Holder Document Documentation Passport National
ID Card Driving Driver Licence License Residence Permit Registry Extract Date Birth Born DOB Issued Issue Country Provider
Result Status KYC Onboarding Team Note Notes Successfully Successful Confirmed Confirmation Review Reviewed Sumsub Onfido Veriff
Persona Jumio Trulioo IDnow Yoti Mitek Mr Mrs Ms Miss Dr Sir Madam Subject Name Named Valid Expired Rejected Failed Ok Okay
According Per Via Using With From To Showing Shows Shown Record Records Bank Support Team Agent Process Processed Credentials""".split()}
TITLE_STOP |= set(MONTHS)


def titlecase_name(text):
    """Fallback when the note has no ALL-CAPS name: the longest clean run of 2-5 Title-case words
    that is not a country, month, provider or document word."""
    runs, cur = [], []
    for tok in re.findall(r"[^\s,;:()—–]+", text):
        t = tok.strip(".'\"")
        clean = re.fullmatch(r"(?:Mc|Mac|O'|D'|Al-|El-)?[A-ZÀ-ÖØ-Þ][a-zß-öø-ÿ\u0100-\u024F']+(?:-[A-ZÀ-ÖØ-Þa-zß-öø-ÿ][a-zß-öø-ÿ\u0100-\u024F']+)*", t or "") and t.lower() not in TITLE_STOP
        if clean:
            cur.append(t)
        if not clean or tok.endswith((".", ",", ";", ":")) and len(t) > 2:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    good = []
    for r in runs:
        joined = " ".join(r)
        if 2 <= len(r) <= 5 and not CT.find_in_text(joined) and not any(CT.find_in_text(x) for x in r):
            good.append(r)
    if not good:
        return None, False
    best = max(good, key=len)
    return " ".join(best), True


def _normalise_note_dates(text):
    """Bank notes write slash dates day-first. Two-digit years are expanded (yy <= 26 -> 20yy, else 19yy);
    if the note itself shows month-first order (a middle part above 12), its slash dates are swapped."""
    def yy(m):
        y = int(m.group(3))
        return "%s/%s/%d" % (m.group(1), m.group(2), (2000 + y) if y <= 26 else (1900 + y))
    text = re.sub(r"(?<![\d/.])(\d{1,2})[/.](\d{1,2})[/.](\d{2})(?![\d/]|\.\d)", yy, text)
    pairs = re.findall(r"(?<![\d/.])(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])", text)
    if any(int(b) > 12 and int(a) <= 12 for a, b, _ in pairs) and not any(int(a) > 12 for a, b, _ in pairs):
        text = re.sub(r"(?<![\d/.])(\d{1,2})/(\d{1,2})/(\d{4})(?![\d/])", lambda m: "%s/%s/%s" % (m.group(2), m.group(1), m.group(3)), text)
    return text


def parse_kyc_note(note):
    text = _normalise_note_dates(note.get("text") or "")
    if note.get("channel") != "kyc" and not re.search(r"\b(passport|national id|id card|identity card|driving licen[cs]e|driver'?s licen[cs]e|residence permit|identity document|registry extract|travel document|identity card)\b", text, re.I):
        return None
    if note.get("channel") != "kyc" and not VERIFY_RE.search(text):
        return None
    approved = not NEG_RE.search(text)
    created = parse_date(note.get("created_at"))
    dates = find_dates(text)
    dob = None
    checked = None
    cands = []
    for s, e, d in dates:
        pre = text[max(0, s - 30):s]
        if dob is None and DOB_PRE.search(pre) and (created is None or d != created):
            dob = d
        else:
            cands.append(d)
    if dob is None:
        rest = [d for d in cands if d != created]
        if created is None and len(cands) >= 2:
            rest = cands[:]
        if len(rest) == 1:
            dob = rest[0]
        elif len(rest) > 1:
            rest.sort(key=date_key)
            dob = rest[0]  # the earliest date in a verification note is the birth date
    for d in cands:
        if d != dob:
            checked = d
    checked = checked or created
    # name: longest run of ALL-CAPS words
    best = []
    cur = []
    for tok in re.findall(r"[^\s,;:()]+", text):
        t = tok.strip(".'\"")
        t = re.sub(r"(?<=[A-ZÀ-ÖØ-Þ])['\u2019]s$", "", t)  # possessive: "JOHNSON's passport"
        letters = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\u0100-\u024F]", "", t)
        is_caps = len(letters) >= 2 and letters == letters.upper() and letters.upper() != letters.lower() and t.upper() not in CAPS_STOP
        is_filler = bool(re.fullmatch(r"\d{1,6}|N/?A|X+|-+|\?+", t)) and t.upper() not in ("ID",)
        if is_caps or (is_filler and (cur or True)):
            cur.append(t)
        else:
            if len(cur) > len(best):
                best = cur
            cur = []
    if len(cur) > len(best):
        best = cur
    # strip leading/trailing filler-only tokens; keep a run only if it has a real capitalised word
    while best and not re.search(r"[A-Za-z]{2}", best[-1]):
        best = best[:-1]
    has_word = any(re.search(r"[A-Za-z]{2}", t) for t in best)
    name = " ".join(best) if has_word and len(best) >= 2 else None
    if has_word and len(best) == 1 and not CT.find_in_text(best[0]):
        name = best[0]
    name_conf = bool(name)
    if not name:
        name, name_conf = titlecase_name(text)
    ctry = CT.find_in_text(text)
    if not name and not dob:
        return None  # not an identity check record (e.g. "verified through the app")
    return {"id": note["note_id"], "src": "note", "name": name, "name_conf": name_conf, "dob": dob, "country": ctry[0] if ctry else None,
            "approved": approved, "date": checked, "text": text}


def note_countries(note):
    """Countries a support note says the customer lived/worked in (non-KYC notes)."""
    text = note.get("text") or ""
    return CT.find_in_text(text)


# ----------------------------------------------------------------------------- customer picture

class Person:
    def __init__(self, data, rids):
        self.d = data
        self.rids = sorted(rids)
        self.recs = [data.customers[r] for r in self.rids]
        self.company = any(r.get("entity_type") == "Company" for r in self.recs)
        nm = data.nm
        # checks
        checks = []
        for r in self.rids:
            for app in sorted(data.app_by_cust.get(r, ())):
                for k in data.kyc_by_app.get(app, ()):
                    checks.append({"id": k["check_id"], "src": "kyc", "name": k.get("verified_name"),
                                   "dob": parse_date(k.get("verified_dob")), "country": CT.canon(k.get("document_country")),
                                   "approved": (k.get("result") or "").strip().lower() in ("approved", "passed", "pass", "verified", "clear", "accepted"), "date": parse_date(k.get("checked_at")), "name_conf": True,
                                   "doc": k.get("document_type")})
        self.notes = []
        seen = set()
        for c in self.recs:
            for n in data.notes_by_email.get((c.get("email") or "").lower(), []):
                if n["note_id"] in seen:
                    continue
                seen.add(n["note_id"])
                self.notes.append(n)
        self.notes.sort(key=lambda n: n["note_id"])
        self.res_notes = []  # (note_id, [countries])
        for n in self.notes:
            kn = parse_kyc_note(n) if (n.get("channel") in ("kyc", None) or re.search(r"verif|validat", n.get("text") or "", re.I)) else None
            if kn:
                checks.append(kn)
            else:
                cs = note_countries(n)
                if cs:
                    self.res_notes.append((n["note_id"], cs))
        self.checks = checks
        appr = [c for c in checks if c["approved"]]
        appr.sort(key=lambda c: (date_key(c["date"]), c["src"] == "kyc", c["id"]))
        self.latest = appr[-1] if appr else None
        # verified name
        self.vname = self.latest["name"] if self.latest and self.latest.get("name") and nm.parts(self.latest["name"], self.company) else None
        # dob
        if self.latest and self.latest.get("dob"):
            self.dobs = [self.latest["dob"]]
            self.dob_src = [self.latest["id"]]
        else:
            ds = {}
            for c in self.recs:
                d = parse_date(c.get("dob"))
                if d:
                    ds.setdefault(d, []).append(c["record_id"])
            self.dobs = sorted(ds, key=date_key)
            self.dob_src = sorted({r for v in ds.values() for r in v})
        # countries with sources
        self.ctry = defaultdict(set)
        self.unknown_countries = []
        for c in self.recs:
            for f in ("residence_country", "nationality"):
                cc = CT.canon(c.get(f))
                if cc:
                    self.ctry[cc].add(c["record_id"])
                elif c.get(f) and _country_of(c[f])[1]:
                    self.unknown_countries.append(c[f])
        if self.latest and self.latest.get("country"):
            self.ctry[self.latest["country"]].add(self.latest["id"])
        for nid, cs in self.res_notes:
            for cc in cs:
                self.ctry[cc].add(nid)

    def names(self):
        """Names used for agreement: the verified legal name outranks the record names."""
        if self.vname:
            return [self.vname]
        out = []
        for c in self.recs:
            for f in ("full_name", "preferred_name"):
                if c.get(f) and c[f] not in out:
                    out.append(c[f])
        return out

    def record_names(self):
        out = []
        for c in self.recs:
            for f in ("full_name", "preferred_name", "login_name"):
                if c.get(f) and c[f] not in out:
                    out.append(c[f])
        if self.vname:
            out.append(self.vname)
        return out


# ----------------------------------------------------------------------------- hit picture
CAT_PHRASE = {"sanctions": "a sanctioned individual", "pep": "a politically exposed person", "enforcement": "the subject of enforcement action",
              "adverse media": "named in adverse media", "soe": "a state-owned enterprise official"}
# Dated reports: exactly lines of the form "According to ...; September 10, 2025: ..." (principle 5)
REPORT_RE = re.compile(r"(?m)^[ \t]*According to [^\n;]{1,300}?;[ \t]*((?i:" + MON_RE + r")[ \t]+\d{1,2},[ \t]+\d{4})[ \t]*:")
NUMWORDS = {}


def hit_names(h):
    out = []
    for n in [h.get("name"), h.get("best_matching_name")] + list(h.get("aliases") or []):
        if n and isinstance(n, str) and n not in out:
            out.append(n)
    fn = " ".join(x for x in (h.get("first_name"), h.get("middle_name"), h.get("last_name")) if x)
    if fn and fn not in out:
        out.append(fn)
    return out


def _country_of(piece):
    """Country of one address/place string: whole string first, then its last comma part.
    Returns (canonical or None, unknown_flag)."""
    piece = piece.strip()
    if not piece:
        return None, False
    c = CT.canon(piece)
    if c:
        return c, False
    last = piece.split(",")[-1].strip()
    c = CT.canon(last)
    if c:
        return c, False
    bare = CT._fold(re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", last)).strip()
    if not bare or bare in CT.NOT_COUNTRIES:
        return None, False
    return None, True


def hit_countries_ex(h):
    out, unknown = [], []
    vals = []
    for a in list(h.get("countries") or []) + list(h.get("nationality") or []) + list(h.get("citizenship") or []) + list(h.get("addresses") or []):
        if isinstance(a, str):
            vals.extend(a.split(";"))
    pob = h.get("place_of_birth")
    if isinstance(pob, str):
        vals.extend(pob.split(";"))
    for v in vals:
        c, unk = _country_of(v)
        if c and c not in out:
            out.append(c)
        if unk:
            unknown.append(v.strip())
    return sorted(out), unknown


def hit_countries(h):
    return hit_countries_ex(h)[0]


AGE_PATTERNS = [
    r"\baged\s+(\d{1,3})\b", r"\b(\d{1,3})[- ]years?[- ]old\b", r"\bage\s+of\s+(\d{1,3})\b", r"\bat\s+age\s+(\d{1,3})\b",
    r"\b(\d{1,3})\s+years?\s+of\s+age\b", r"\bage\s+(\d{1,3})\b", r"\b(?:was|is|turned|reached)\s+(\d{1,3})\b(?!\s*(?:%|percent|million|billion|thousand|people|times|counts?|years in|months|days))",
    r"\bat\s+(\d{1,3}),", r",\s*(\d{1,3}),", r"^\s*(\d{1,3}),", r"\bthen\s+(\d{1,3})\b", r"\ba\s+(\d{1,3})\s*,",
    r"\bat\s+(\d{1,3})\s*[.;]", r",\s*(\d{1,3})\s+and\b", r",\s*(\d{1,3})\s*\.\s",
    r"\((?:aged?\s*|age:?\s*)?(\d{1,3})(?:\s*(?:years?(?:\s+old)?|yrs?\.?|y/o))?\)", r"\b(\d{1,3})\s*(?:yrs?\.?|y/o)\b",
]


def extract_age_loose(stripped):
    """Search snippets only: if exactly one standalone 1-3 digit number remains (dates removed), it is the age."""
    ages = extract_age(stripped)
    if ages:
        return ages
    nums = {int(x) for x in re.findall(r"(?<![\w.,/-])(\d{1,3})(?![\w/%-]|[.,]\d)", stripped)}
    nums = {n for n in nums if 10 <= n <= 110}
    return nums if len(nums) == 1 else set()


def extract_age(sentence):
    ages = set()
    for p in AGE_PATTERNS:
        for m in re.finditer(p, sentence, re.I):
            n = int(m.group(1))
            if 10 <= n <= 110:
                ages.add(n)
    return ages


def years_from_age(age, ref):
    y = ref[0]
    if ref[1] and ref[2] is None and False:
        pass
    return {y - age - 1, y - age}


def first_paragraph(notes):
    if not notes:
        return ""
    return re.split(r"\n\s*\n", notes.strip())[0]


def split_sentences(text):
    """Sentence split that does not break after initials (Mark E. Phillips) or common abbreviations."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\u00C0-\u024F])", text)
    out = []
    for p in parts:
        if out and re.search(r"(?:^|[\s(])(?:[A-Z]|Mr|Mrs|Ms|Dr|St|Jr|Sr|No|Mt|Gen|Col|Lt|Rev|Prof|U\.S|Inc|Co|Ltd)\.$", out[-1]):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


def hit_dobs_from_notes(h):
    """Principle 5: a sentence in the first paragraph of the profile notes."""
    fp = first_paragraph(h.get("profile_notes"))
    if not fp or REPORT_RE.match(fp.strip()):
        # first paragraph is a dated report: can still carry no DOB statement
        pass
    out = []
    for sent in split_sentences(fp):
        if re.match(r"\s*According to", sent):
            continue
        # only narrative birth statements count; raw provider fields such as "DOB: 6/20/1955" inside
        # scraped profile text are not treated as the hit's date of birth (policy principle 5)
        m = re.search(r"\bborn\b[^.;]{0,40}", sent, re.I)
        if m and not re.search(r"\bborn\s+(?:out|again|into)\b", sent, re.I):
            ds = find_provider_dates(m.group(0))
            if ds:
                out.append(("born", ds[0][2], sent.strip()))
                continue
        ds = [d for d in find_dates(sent)]
        if not ds:
            continue
        stripped = sent
        for s, e, d in sorted(ds, reverse=True):
            stripped = stripped[:s] + " DATE " + stripped[e:]
        ages = extract_age(stripped)
        if len(ages) == 1 and len(ds) == 1:
            a = ages.pop()
            ref = ds[0][2]
            for y in sorted(years_from_age(a, ref)):
                out.append(("age", (y, None, None), sent.strip()))
    return out


def report_dates(h):
    out = []
    for m in REPORT_RE.finditer(h.get("profile_notes") or ""):
        d = parse_date(m.group(1))
        if d:
            out.append(d)
    return sorted(out, key=date_key)


# ----------------------------------------------------------------------------- comparison helpers

def year_range(dates):
    return sorted({d[0] for d in dates})


def dob_agree(cust, hitd):
    if cust[0] != hitd[0]:
        return False
    if cust[1] and hitd[1] and cust[1] != hitd[1]:
        return False
    if cust[1] and hitd[1] and cust[2] and hitd[2] and cust[2] != hitd[2]:
        return False
    return True


def dob_contra(cust, hitd):
    if abs(cust[0] - hitd[0]) > 1:
        return True
    if cust[0] == hitd[0] and cust[1] and hitd[1]:
        if cust[1] != hitd[1]:
            return True
        if cust[2] and hitd[2] and cust[2] != hitd[2]:
            return True
    return False


def max_age_at(dob, when):
    """Largest age the person can have at date `when` given a (possibly partial) dob."""
    y, m, d = dob
    wy, wm, wd = when
    age = wy - y
    if m and wm:
        if (wm, wd or 31) < (m, d or 1):
            age -= 1
    return age


def before(a, b):
    """True if partial date a is certainly before partial date b."""
    if a[0] != b[0]:
        return a[0] < b[0]
    if a[1] and b[1]:
        if a[1] != b[1]:
            return a[1] < b[1]
        if a[2] and b[2]:
            return a[2] < b[2]
    return False


def listing_phrase(h):
    cat = h.get("primary_category") or ((h.get("categories") or [None])[0])
    if not cat:
        return "named on a watchlist"
    return CAT_PHRASE.get(cat.strip().lower(), "named on a watchlist")


def join_names(xs):
    xs = list(xs)
    if len(xs) <= 1:
        return "".join(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1]


# ----------------------------------------------------------------------------- hit facts

def parse_dob_field(v):
    """All dates a dobs entry allows; a range like '1970-1972' or '1970 to 1972' yields every year."""
    if isinstance(v, int):
        v = str(v)
    if not isinstance(v, str):
        return []
    m = re.fullmatch(r"\s*(?:c\.|ca\.|circa|approx\.?|about)?\s*(\d{4})\s*(?:-|–|to|/)\s*(\d{4})\s*", v, re.I)
    if m and int(m.group(1)) < int(m.group(2)) <= int(m.group(1)) + 15:
        return [(y, None, None) for y in range(int(m.group(1)), int(m.group(2)) + 1)]
    return [d for _, _, d in find_provider_dates(v)]


class HitFacts:
    def __init__(self, data, h):
        self.h = h
        self.company = (h.get("entity_type") or "").lower() in ("company", "organisation", "organization", "entity", "vessel")
        self.names = hit_names(h)
        self.countries, self.unknown_countries = hit_countries_ex(h)
        self.dob_kind = None
        self.dobs = []
        self.dob_ev = []
        self.dob_text = ""
        for v in h.get("dobs") or []:
            for d in parse_dob_field(v):
                if d not in self.dobs:
                    self.dobs.append(d)
        if self.dobs:
            self.dob_kind = "listed"
        elif not self.company:
            nd = hit_dobs_from_notes(h)
            if nd:
                self.dobs = sorted({x[1] for x in nd}, key=date_key)
                self.dob_kind = "notes"
                self.dob_text = nd[0][2]
            else:
                sr = self.search_dobs(data, h)
                if sr:
                    self.dobs = sorted({d for d, _ in sr}, key=date_key)
                    self.dob_ev = sorted({sid for _, sid in sr})
                    self.dob_kind = "search"
        # provider field lines such as "DOB: 6/20/1955" in the first paragraph: never used to clear or confirm,
        # only as a veto (they block a confirmation they contradict and a DOB clearance they support)
        self.field_dobs = []
        if not self.company and self.dob_kind != "listed":
            for m in re.finditer(r"(?im)^[ \t]*(?:dob|d\.o\.b\.?|date of birth|birth ?date|born)[ \t]*[:\-][ \t]*([^\n]{4,40})$",
                                 first_paragraph(h.get("profile_notes")) or ""):
                for _s, _e, d in find_provider_dates(m.group(1)):
                    if d not in self.field_dobs:
                        self.field_dobs.append(d)
        self.reports = report_dates(h)
        _dd = find_provider_dates(h.get("deceased_date")) if isinstance(h.get("deceased_date"), str) else []
        self.deceased = _dd[0][2] if _dd else None

    def search_dobs(self, data, h):
        phrase = listing_phrase(h)
        if not self.countries:
            return []
        out = []
        seen = set()
        for n in self.names:
            key = " ".join(sorted(data.nm.parts(n)))
            if not key:
                continue
            for s in data.sr_by_key.get(key, []):
                if s["result_id"] in seen:
                    continue
                seen.add(s["result_id"])
                text = " ".join(x for x in (s.get("title"), s.get("snippet")) if x)
                snip = s.get("snippet") or ""
                if phrase.lower() not in snip.lower():
                    continue
                cs = CT.find_in_text(snip)
                if not cs or not set(cs) & set(self.countries):
                    continue
                ds = find_dates(snip)
                if len({d for _, _, d in ds}) != 1:
                    continue
                stripped = snip
                for a, b, d in sorted(ds, reverse=True):
                    stripped = stripped[:a] + " DATE " + stripped[b:]
                ages = extract_age_loose(stripped)
                if len(ages) != 1:
                    continue
                age = ages.pop()
                for y in sorted(years_from_age(age, ds[0][2])):
                    out.append(((y, None, None), s["result_id"]))
        return out

    def dob_text_desc(self, verb=False):
        ds = " or ".join(fmt_date(d) for d in self.dobs)
        v = " is " if verb else " "
        if self.dob_kind == "listed":
            return "the hit's listed date of birth%s%s" % (v, ds)
        if self.dob_kind == "notes":
            full = all(d[1] for d in self.dobs)
            if verb:
                return ("the hit's profile notes give its date of birth as %s" if full else "the hit's profile notes put its birth year at %s") % ds
            return "the hit's %s from its profile notes" % ds
        if self.dob_kind == "search":
            return ("the hit's search results (%s) put its birth year at %s" if verb else "the hit's %s from its search results (%s)") % (
                (", ".join(self.dob_ev), ds) if verb else (ds, ", ".join(self.dob_ev)))
        return ds


# ----------------------------------------------------------------------------- customer resolution

def record_fits(data, rid, sc):
    """Principle 2: does a record fit what was screened? Unknown parts are not a mismatch."""
    c = data.customers[rid]
    nm = data.nm
    comp = c.get("entity_type") == "Company"
    sname = sc.get("name")
    if sname:
        names = [c.get("full_name"), c.get("preferred_name"), c.get("login_name")]
        ok = any(n and nm.agree(n, sname, comp) for n in names)
        if not ok:
            # verified names on the record's approved checks
            for app in data.app_by_cust.get(rid, ()):
                for k in data.kyc_by_app.get(app, ()):
                    if (k.get("result") or "").lower() == "approved" and k.get("verified_name") and nm.agree(k["verified_name"], sname, comp):
                        ok = True
        if not ok:
            return False
    sd = parse_date(sc.get("dob"))
    cd = parse_date(c.get("dob"))
    if sd and cd:
        if sd[0] != cd[0] or (sd[1] and cd[1] and sd[1] != cd[1]) or (sd[2] and cd[2] and sd[2] != cd[2]):
            return False
    scn = CT.canon(sc.get("country")) if sc.get("country") else None
    if scn:
        cc = {CT.canon(c.get("residence_country")), CT.canon(c.get("nationality"))} - {None}
        if cc and scn not in cc:
            return False
    city = sc.get("city")
    if city:
        fc = fold(city).strip()
        hay = fold((c.get("city") or "") + " | " + (c.get("address") or ""))
        if (c.get("city") or c.get("address")) and fc not in hay:
            return False
    return True


def resolve(data, alert):
    """Return (list of person tuples, path list)."""
    sc = alert.get("customer") or {}
    path = []
    linked = []
    if alert.get("account_ref"):
        linked = sorted({a["customer_id"] for a in data.acc_by_id.get(alert["account_ref"], [])})
        path.append("account_ref %s -> %s" % (alert["account_ref"], ", ".join(linked) or "nothing"))
    if not linked and alert.get("login_handle"):
        linked = sorted({a["customer_id"] for a in data.acc_by_login.get(alert["login_handle"].lower(), [])})
        path.append("login_handle %s -> %s" % (alert["login_handle"], ", ".join(linked) or "nothing"))
    if not linked and alert.get("email"):
        linked = sorted(data.cust_by_email.get(alert["email"].lower(), []))
        path.append("email %s -> %s" % (alert["email"], ", ".join(linked) or "nothing"))
    linked = [r for r in linked if r in data.customers]
    if linked:
        if len({data.person_of[r] for r in linked}) > 1:
            fit = [r for r in linked if record_fits(data, r, sc)]
            if fit:
                linked = fit
                path.append("screened details pick %s" % ", ".join(fit))
        cands = linked
    else:
        # search without link
        nm = data.nm
        comp = (sc.get("entity_type") or "") == "Company"
        parts = nm.parts(sc.get("name"), comp)
        pool = set()
        for p in parts:
            pool |= data.name_index.get(p, set())
            pool |= data.name_index.get("^" + p[:3], set())
            pool |= data.name_index.get(p[-3:] + "$", set())
            for gi in nm.var.get(p, ()):
                for alt, gs in nm.var.items():
                    if gi in gs:
                        pool |= data.name_index.get(alt, set())
        # also fuzzy: variants of parts
        cands = sorted(r for r in pool if record_fits(data, r, sc))
        path.append("name/dob/country/city search -> %s" % (", ".join(cands) or "nothing"))
    people = sorted({data.person_of[r] for r in cands})
    return people, path


# ----------------------------------------------------------------------------- decide one (person, hit)

def decide_person(data, alert, hf, P):
    """Return dict(decision, code, ev, reason_sentences, codes_all)."""
    nm = data.nm
    h = hf.h
    sc = alert.get("customer") or {}
    screened = parse_date(alert.get("screened_at"))
    cust_company = P.company if P else (sc.get("entity_type") == "Company")
    contras = []  # (code, evidence list, sentence)
    rec_ids = P.rids if P else []

    # ---- type
    if hf.company != cust_company and (h.get("entity_type") and (P or sc.get("entity_type"))):
        contras.append(("ENTITY_TYPE_MISMATCH", list(rec_ids[:1]),
                        "The customer is %s but the hit is %s." % ("a company" if cust_company else "an individual",
                                                                 "a company" if hf.company else "an individual")))
        return finish(contras, [], P, hf)

    # ---- customer facts
    if P:
        cdobs, cdob_src = P.dobs, P.dob_src
        cnames = P.names()
        vname = P.vname
        cctry = P.ctry
    else:
        d = parse_date(sc.get("dob"))
        cdobs, cdob_src = ([d] if d else []), []
        cnames = [sc.get("name")] if sc.get("name") else []
        vname = None
        cctry = {}

    # ---- name
    best_name_agree = None
    name_ok_parts = any(len(nm.parts(n, cust_company)) >= (1 if cust_company else 2) for n in cnames)
    for cn in cnames:
        for hn in hf.names:
            if nm.agree(cn, hn, cust_company or hf.company):
                best_name_agree = (cn, hn)
                break
        if best_name_agree:
            break
    # a hit's single-part alias can still agree with a customer name
    name_agree = bool(best_name_agree) and name_ok_parts

    # ---- dob
    d_agree = None
    d_contra_all = bool(cdobs) and bool(hf.dobs)
    for cd in cdobs:
        for hd in hf.dobs:
            if dob_agree(cd, hd):
                d_agree = (cd, hd)
            if not dob_contra(cd, hd):
                d_contra_all = False
    dob_ev = list(cdob_src) + list(hf.dob_ev)

    # ---- time
    if hf.deceased and screened and before(hf.deceased, screened) and not hf.company:
        contras.append(("DECEASED", [], "The hit's profile gives a date of death of %s, before the customer was screened on %s." % (
            fmt_date(hf.deceased), fmt_date(screened))))
    if hf.reports and cdobs:
        first = hf.reports[0]
        if cust_company:
            if all(before(first, cd) for cd in cdobs):
                contras.append(("TEMPORAL_IMPOSSIBILITY", list(cdob_src), "The customer was incorporated on %s (%s), after the hit's earliest dated report on %s." % (
                    fmt_date(cdobs[0]), ", ".join(cdob_src), fmt_date(first))))
        else:
            ages = [max_age_at(cd, first) for cd in cdobs]
            if max(ages) < 16:
                contras.append(("TEMPORAL_IMPOSSIBILITY", list(cdob_src),
                                "The customer was born %s (%s), so they were at most %d when the hit's profile reports activity on %s." % (
                                    fmt_date(cdobs[0]), ", ".join(cdob_src), max(ages), fmt_date(first))))
    if d_contra_all:
        contras.append(("DOB_MISMATCH", dob_ev, "The customer's %s is %s (%s) but %s." % (
            "incorporation date" if cust_company else "date of birth", " or ".join(fmt_date(d) for d in cdobs), ", ".join(cdob_src) or "screened details",
            hf.dob_text_desc(verb=True))))
    # ---- verified name
    # guard: a note-parsed verified name that is a strict truncation of one of the person's record names
    # (e.g. "MARCUS DAVID" for record "Marcus David Miller") is more likely a parsing miss than a legal name
    trunc = False
    if vname and P.latest.get("src") == "note":
        vp = set(nm.parts(vname, cust_company))
        trunc = any(vp < set(nm.parts(n, cust_company)) for n in P.record_names() if n)
    if vname and non_latin(vname):
        trunc = True  # a name in another script cannot be compared part by part: never clear on it
    if vname and not trunc and P.latest.get("name_conf") and len(nm.parts(vname, cust_company)) >= (1 if cust_company else 2):
        if not any(nm.agree(vname, hn, cust_company or hf.company) for hn in hf.names) and hf.names:
            contras.append(("NAME_MISMATCH_VERIFIED", [P.latest["id"]], "The customer's verified name is %s (%s), which does not agree with the hit's name %s." % (
                vname, P.latest["id"], hf.names[0])))
    # ---- location
    shared = sorted(set(cctry) & set(hf.countries))
    unknown_loc = hf.unknown_countries or (P.unknown_countries if P else [])
    # guard: a screened country that none of the customer's records carry makes the picture incomplete
    scn = CT.canon(sc.get("country")) if sc.get("country") else None
    if scn and cctry and scn not in cctry:
        unknown_loc = list(unknown_loc) + [scn]
    if cctry and hf.countries and not shared and not unknown_loc:
        if not (name_agree and d_agree):
            ev = sorted({s for c in cctry for s in cctry[c]})
            contras.append(("LOCATION_MISMATCH", ev, "The customer is linked only to %s but the hit is linked only to %s." % (
                join_names(sorted(cctry)), join_names(hf.countries))))

    agree_info = {"name": best_name_agree if name_agree else None, "dob": d_agree, "shared": shared,
                  "dob_ev": dob_ev, "cctry": cctry}
    if name_agree and d_agree and cctry and hf.countries and not shared:
        # principle 6: a country difference does not clear a name+DOB match, but it does stop a confirmation
        agree_info["conflict"] = True
        agree_info["loc_conflict"] = (sorted(cctry), hf.countries)
    # veto from provider "DOB:" field lines (see HitFacts.field_dobs): a contradiction between sources is for a person
    if hf.field_dobs and cdobs:
        f_agree = any(dob_agree(cd, fd) for cd in cdobs for fd in hf.field_dobs)
        f_contra = all(dob_contra(cd, fd) for cd in cdobs for fd in hf.field_dobs)
        if (d_agree and f_contra) or (d_contra_all and f_agree):
            contras = [c for c in contras if c[0] != "DOB_MISMATCH"]
            if not contras:
                agree_info["conflict"] = True
                agree_info["field_dob_conflict"] = hf.field_dobs
                return finish([], agree_info, P, hf)
    if contras and name_agree and d_agree:
        # facts point both ways: a human decides -- except a date of death before screening, which the policy
        # makes a clearance on its own (a person who died before the screening is not the living customer)
        if any(c[0] == "DECEASED" for c in contras):
            contras = [c for c in contras if c[0] == "DECEASED"]
        else:
            agree_info["conflict"] = True
            contras = []
    return finish(contras, agree_info, P, hf)


PRIORITY = ["ENTITY_TYPE_MISMATCH", "DECEASED", "TEMPORAL_IMPOSSIBILITY", "DOB_MISMATCH", "NAME_MISMATCH_VERIFIED", "LOCATION_MISMATCH"]


def finish(contras, agree, P, hf):
    rec_ids = list(P.rids) if P else []
    if contras:
        contras.sort(key=lambda c: PRIORITY.index(c[0]))
        ev = []
        for c in contras:
            for e in c[1]:
                if e not in ev:
                    ev.append(e)
        return {"decision": "DIFFERENT_ENTITY", "code": contras[0][0], "codes": [c[0] for c in contras], "ev": sorted(ev),
                "sent": [c[2] for c in contras][:3]}
    a = agree or {}
    shared = a.get("shared") or []
    cctry = a.get("cctry") or {}
    loc_ev = sorted({s for c in shared for s in cctry.get(c, ())})
    sents = []
    if a.get("dob"):
        sents.append("The customer's date of birth %s (%s) agrees with %s." % (fmt_date(a["dob"][0]), ", ".join(x for x in a["dob_ev"] if not x.startswith("SR-")) or "record", hf.dob_text_desc()))
    if shared:
        sents.append("Both the customer and the hit are linked to %s." % join_names(shared))
    if a.get("name"):
        sents.append("The customer's name %s agrees with the hit's name %s." % (a["name"][0], a["name"][1]))
    if a.get("conflict"):
        if a.get("loc_conflict"):
            sents.append("But the customer is linked only to %s and the hit only to %s; a country difference cannot clear a name and date of birth match, so a person decides." % (
                join_names(a["loc_conflict"][0]), join_names(a["loc_conflict"][1])))
        elif a.get("field_dob_conflict"):
            sents.append("But the hit's profile notes also give a date of birth of %s, which disagrees with that comparison, so a person decides." % (
                " or ".join(fmt_date(d) for d in a["field_dob_conflict"])))
        else:
            sents.append("Name and date of birth agree but another fact conflicts, so the hit is left for a person to decide.")
        return {"decision": "REVIEW", "code": "INSUFFICIENT_DATA", "codes": ["INSUFFICIENT_DATA"], "ev": sorted(set(loc_ev + a.get("dob_ev", []))), "sent": sents}
    if a.get("name") and not hf.company and a.get("dob"):
        code = "NAME_DOB_LOCATION_MATCH" if shared else "NAME_DOB_MATCH"
        ev = sorted(set(rec_ids) | set(a["dob_ev"]) | set(loc_ev))
        return {"decision": "SAME_ENTITY", "code": code, "codes": [code], "ev": ev, "sent": sents + ["Nothing in the customer's records contradicts the hit."]}
    if a.get("name") and hf.company and shared:
        ev = sorted(set(rec_ids) | set(loc_ev))
        return {"decision": "SAME_ENTITY", "code": "NAME_LOCATION_MATCH", "codes": ["NAME_LOCATION_MATCH"], "ev": ev,
                "sent": sents + ["Nothing in the customer's records contradicts the hit."]}
    missing = []
    if not a.get("name"):
        missing.append("the names do not clearly agree")
    if not hf.company and not a.get("dob"):
        missing.append("the date of birth cannot be confirmed against the hit" if hf.dobs else "the hit gives no date of birth to compare")
    if hf.company and not shared:
        missing.append("no shared country confirms it")
    if not P:
        missing.insert(0, "no customer record could be resolved")
    sents.append("Nothing in the customer's records contradicts the hit, but %s, so it can be neither cleared nor confirmed." % join_names(missing or ["agreement is incomplete"]))
    ev = sorted(set(loc_ev))
    return {"decision": "REVIEW", "code": "INSUFFICIENT_DATA", "codes": ["INSUFFICIENT_DATA"], "ev": ev, "sent": sents}


# ----------------------------------------------------------------------------- main

def run(folder, out_path):
    data = Data(folder)
    rows = []
    person_cache = {}
    for alert in sorted(data.alerts, key=lambda a: a["alert_id"]):
        people, path = resolve(data, alert)
        Ps = []
        for pt in people:
            if pt not in person_cache:
                person_cache[pt] = Person(data, pt)
            Ps.append(person_cache[pt])
        hit_ids = list(alert.get("hit_ids") or [])
        for hid in sorted(set(hit_ids) | {h for h, x in data.hits.items() if x.get("alert_id") == alert["alert_id"]}):
            h = data.hits.get(hid)
            if not h:
                continue
            hf = HitFacts(data, h)
            if not Ps:
                r = decide_person(data, alert, hf, None)
                # without a resolved customer, never clear on declared screened details alone except type
                if r["decision"] == "DIFFERENT_ENTITY" and r["code"] != "ENTITY_TYPE_MISMATCH":
                    r = {"decision": "REVIEW", "code": "INSUFFICIENT_DATA", "codes": ["INSUFFICIENT_DATA"], "ev": [],
                         "sent": ["No customer record in the bank's systems could be resolved for this alert, so only the screened details are known.",
                                  "Those declared details alone are not enough to settle the hit."]}
                elif r["decision"] == "SAME_ENTITY":
                    r = {"decision": "REVIEW", "code": "INSUFFICIENT_DATA", "codes": ["INSUFFICIENT_DATA"], "ev": [],
                         "sent": ["No customer record could be resolved for this alert; the screened details agree with the hit but are unverified."]}
                cid = None
            elif len(Ps) == 1:
                r = decide_person(data, alert, hf, Ps[0])
                cid = Ps[0].rids[0]
                # prefer the record the link pointed to
                cid = pick_record(data, alert, Ps[0])
            else:
                rs = [decide_person(data, alert, hf, P) for P in Ps]
                decs = {x["decision"] for x in rs}
                cid = "AMBIGUOUS"
                allrec = sorted({rid for P in Ps for rid in P.rids})
                if len(decs) == 1:
                    r = dict(rs[0])
                    r["ev"] = sorted(set(allrec) | {e for x in rs for e in x["ev"]})
                    r["sent"] = ["%d different people in the bank's records fit this alert (%s) and each leads to the same decision." % (
                        len(Ps), ", ".join(P.rids[0] for P in Ps))] + rs[0]["sent"][:2]
                else:
                    r = {"decision": "REVIEW", "code": "AMBIGUOUS_CUSTOMER_RECORD", "codes": ["AMBIGUOUS_CUSTOMER_RECORD"], "ev": allrec,
                         "sent": ["%d different people in the bank's records fit this alert (%s)." % (len(Ps), ", ".join(P.rids[0] for P in Ps)),
                                  "They lead to different decisions on this hit (%s), so a person must decide." % ", ".join(
                                      "%s: %s" % (P.rids[0], x["decision"]) for P, x in zip(Ps, rs))]}
            reason = " ".join(r["sent"][:4]) if r["sent"] else "No decisive facts."
            rows.append({"hit_id": hid, "alert_id": alert["alert_id"], "decision": r["decision"], "reason_code": r["code"],
                         "customer_record_id": cid, "reason": reason, "evidence": r["ev"]})
            if os.environ.get("SCREEN_DEBUG"):
                rows[-1]["_codes"] = r.get("codes")
                rows[-1]["_path"] = path
    rows.sort(key=lambda x: (x["alert_id"], x["hit_id"]))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for r in rows:
            if not os.environ.get("SCREEN_DEBUG"):
                r = {k: v for k, v in r.items() if not k.startswith("_")}
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n")
    return rows


def pick_record(data, alert, P):
    linked = set()
    if alert.get("account_ref"):
        linked |= {a["customer_id"] for a in data.acc_by_id.get(alert["account_ref"], [])}
    if alert.get("login_handle"):
        linked |= {a["customer_id"] for a in data.acc_by_login.get(alert["login_handle"].lower(), [])}
    if alert.get("email"):
        linked |= set(data.cust_by_email.get(alert["email"].lower(), []))
    for r in P.rids:
        if r in linked:
            return r
    sc = alert.get("customer") or {}
    for r in P.rids:
        if record_fits(data, r, sc):
            return r
    return P.rids[0]


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: run <data folder> <output file>", file=sys.stderr)
        sys.exit(2)
    rows = run(sys.argv[1], sys.argv[2])
    from collections import Counter
    print("wrote %d lines: %s" % (len(rows), dict(Counter(r["decision"] for r in rows))), file=sys.stderr)
