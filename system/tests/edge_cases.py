#!/usr/bin/env python3
"""Adversarial edge-case suite (synthetic data only, real file format).

    python3 system/tests/edge_cases.py [path/to/system/run ...]

Each case builds a tiny data folder, runs every given system on it and checks the decision for
hit H-000001 against the set of decisions POLICY.md allows. A case marked AMBIGUOUS is one where
the policy text does not settle the answer; its expectation is the safe one (never a clearance).
UNSAFE = the system cleared (DIFFERENT_ENTITY) a hit whose allowed answers exclude a clearance.
See EDGE_CASES.md for the catalogue and the policy reasoning behind every expectation.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RUN = os.path.join(os.path.dirname(HERE), "run")
VARIANTS = {"description": "synthetic",
            "groups": [["muhammad", "mohammed", "mohammad", "mohamed"], ["james", "jim", "jimmy"], ["robert", "rob", "bob"],
                       ["abdul", "abdel"], ["aleksandr", "alexander", "sasha"]],
            "company_legal_forms": ["ltd", "limited", "llc", "gmbh", "sa", "plc", "inc", "co", "corp", "ag", "bv", "srl", "spa"]}
SCREENED = "2026-11-10"
D, S, R = "DIFFERENT_ENTITY", "SAME_ENTITY", "REVIEW"
NOT_CLEAR = {S, R}


class W:
    """A tiny data room."""
    def __init__(self):
        self.t = {k: [] for k in ("customers", "accounts", "onboarding", "kyc_checks", "alerts", "hits", "notes", "search_results")}

    def cust(self, rid, name, dob, nat="United Kingdom", res="GB", email=None, phone=None, etype="Individual", city="London", **kw):
        r = {"record_id": rid, "entity_type": etype, "full_name": name, "preferred_name": None, "login_name": None, "dob": dob,
             "nationality": nat, "residence_country": res, "city": city, "address": "1 High St, %s" % city,
             "email": email or (rid.lower() + "@mail.example"), "phone": phone or ("+44 7" + "".join(c for c in rid if c.isdigit()).rjust(9, "5")),
             "occupation": None, "employer": None, "registration_number": None, "onboarded_at": "2020-01-01", "status": "active",
             "last_kyc_refresh": None}
        r.update(kw)
        self.t["customers"].append(r)
        return self

    def acc(self, aid, cid, login=None, status="active"):
        self.t["accounts"].append({"account_id": aid, "customer_id": cid, "login_handle": login, "phone": None, "opened_at": "2020-01-01", "status": status})
        return self

    def onb(self, aid, cid, app):
        self.t["onboarding"].append({"account_id": aid, "customer_id": cid, "kyc_applicant_id": app, "onboarded_at": "2020-01-01"})
        return self

    def kyc(self, kid, app, name, dob, country="United Kingdom", result="approved", date="2024-01-01", doc=None, dtype="passport"):
        self.t["kyc_checks"].append({"check_id": kid, "applicant_id": app, "provider": "Onfido", "verified_name": name, "verified_dob": dob,
                                     "document_type": dtype, "document_number": doc or ("P" + kid[-6:] + "77"), "document_country": country,
                                     "result": result, "checked_at": date})
        return self

    def note(self, nid, email, text, channel="kyc", date="2024-06-01"):
        self.t["notes"].append({"note_id": nid, "requester_email": email, "created_at": date, "channel": channel, "text": text})
        return self

    def alert(self, aid, name, hits, dob=None, account=None, etype="Individual", country=None, city=None, login=None, email=None, screened=SCREENED):
        self.t["alerts"].append({"alert_id": aid, "screened_at": screened, "customer": {"name": name, "entity_type": etype, "dob": dob,
                                 "country": country, "city": city}, "account_ref": account, "login_handle": login, "email": email, "hit_ids": hits})
        return self

    def hit(self, hid, aid, name, etype="Individual", dobs=(), countries=("United Kingdom",), notes=None, deceased=None, cats=("PEP",),
            aliases=(), primary=None, nationality=(), addresses=(), pob=None, life="Alive"):
        self.t["hits"].append({"hit_id": hid, "alert_id": aid, "match_score": 95, "entity_type": etype, "name": name, "first_name": None,
                               "middle_name": None, "last_name": None, "best_matching_name": name, "aliases": list(aliases), "gender": None,
                               "dobs": list(dobs), "place_of_birth": pob, "life_status": life, "deceased_date": deceased,
                               "nationality": list(nationality), "citizenship": [], "countries": list(countries), "addresses": list(addresses),
                               "identifiers": [], "categories": list(cats), "primary_category": primary or (cats[0] if cats else None),
                               "subcategories": [], "position_or_allegation": None, "details": {}, "relationships": [],
                               "profile_notes": notes, "sources": [], "source_urls": []})
        return self

    def sr(self, rid, query, snippet, title=None):
        self.t["search_results"].append({"result_id": rid, "query": query, "title": title or (query.title() + " - news"), "snippet": snippet, "source": "news.example"})
        return self

    def write(self, d):
        for name, rows in self.t.items():
            with open(os.path.join(d, name + ".jsonl"), "w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(os.path.join(d, "name_variants.json"), "w") as fh:
            json.dump(VARIANTS, fh)


def std(cname="John Smith", cdob="1980-03-03", hname="Smith, John", hdobs=("1980",), kyc=None, notes=(), srs=(), ckw=None, hkw=None, akw=None):
    """One customer CUS-000001 behind ACC-000001 / APP-000001, one alert, one hit."""
    w = W().cust("CUS-000001", cname, cdob, **(ckw or {})).acc("ACC-000001", "CUS-000001").onb("ACC-000001", "CUS-000001", "APP-000001")
    if kyc:
        for i, k in enumerate(kyc if isinstance(kyc, list) else [kyc]):
            k = dict(k)
            w.kyc(k.pop("id", "KYC-00000%d" % (i + 1)), "APP-000001", **k)
    for i, n in enumerate(notes):
        n = dict(n)
        w.note(n.pop("id", "NOTE-00000%d" % (i + 1)), n.pop("email", "cus-000001@mail.example"), **n)
    for i, (q, s) in enumerate(srs):
        w.sr("SR-00000%d" % (i + 1), q, s)
    a = dict(account="ACC-000001")
    a.update(akw or {})
    w.alert("A-000001", a.pop("name", cname), ["H-000001"], **a)
    w.hit("H-000001", "A-000001", hname, dobs=hdobs, **(hkw or {}))
    return w


CASES = []


def case(cid, area, desc, want, amb=False):
    def deco(fn):
        CASES.append({"id": cid, "area": area, "desc": desc, "want": set(want) if not isinstance(want, str) else {want}, "amb": amb, "fn": fn})
        return fn
    return deco


def K(name="John Smith", dob="1980-03-03", **kw):
    d = {"name": name, "dob": dob}
    d.update(kw)
    return d


# ============================================================== customer resolution
@case("R01", "resolution", "joint account: screened DOB picks the second holder (hit DOB fits them, not the first)", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1960-01-01").cust("CUS-000002", "John Smith", "1990-05-05")
    w.acc("ACC-000001", "CUS-000001").acc("ACC-000001", "CUS-000002")
    return w.alert("A-000001", "John Smith", ["H-000001"], dob="1990-05-05", account="ACC-000001").hit("H-000001", "A-000001", "Smith, John", dobs=["1990-05-05"])


@case("R02", "resolution", "joint account, screened details fit both holders, they lead to different decisions -> REVIEW", {R})
def _():
    w = W().cust("CUS-000001", "John Smith", "1960-01-01").cust("CUS-000002", "John Smith", "1990-05-05")
    w.acc("ACC-000001", "CUS-000001").acc("ACC-000001", "CUS-000002")
    return w.alert("A-000001", "John Smith", ["H-000001"], account="ACC-000001").hit("H-000001", "A-000001", "Smith, John", dobs=["1990-05-05"])


@case("R03", "resolution", "duplicate CRM record (same phone + same DOB) adds Kenya: location cannot clear", NOT_CLEAR)
def _():
    w = std(hdobs=(), hkw={"countries": ["Kenya"]})
    w.cust("CUS-000002", "John Smith", "1980-03-03", nat="Kenya", res="KE", phone=w.t["customers"][0]["phone"])
    return w


@case("R04", "resolution", "transitive chain: phone+DOB link to record 2, doc-number link from record 2 to record 3 (Kenya)", NOT_CLEAR)
def _():
    w = std(hdobs=(), hkw={"countries": ["Kenya"]})
    ph = w.t["customers"][0]["phone"]
    w.cust("CUS-000002", "John Smith", "1980-03-03", phone=ph).acc("ACC-000002", "CUS-000002").onb("ACC-000002", "CUS-000002", "APP-000002")
    w.cust("CUS-000003", "J Smith", "1980-03-03", nat="Kenya", res="KE").acc("ACC-000003", "CUS-000003").onb("ACC-000003", "CUS-000003", "APP-000003")
    w.kyc("KYC-000002", "APP-000002", "John Smith", "1980-03-03", doc="X99887766").kyc("KYC-000003", "APP-000003", "John Smith", "1980-03-03", country="Kenya", doc="X99887766")
    return w


@case("R05", "resolution", "shared phone, different DOB (family member in Kenya) does not merge: location clears", {D})
def _():
    w = std(hdobs=(), hkw={"countries": ["Kenya"]})
    w.cust("CUS-000002", "Mary Smith", "1955-07-07", nat="Kenya", res="KE", phone=w.t["customers"][0]["phone"])
    return w


@case("R06", "resolution", "twin: same DOB, different phone, Kenyan nationality, not merged: location clears", {D})
def _():
    w = std(hdobs=(), hkw={"countries": ["Kenya"]})
    w.cust("CUS-000002", "Jane Smith", "1980-03-03", nat="Kenya", res="KE")
    return w


@case("R07", "resolution", "same document number but on a REJECTED check does not merge: location clears", {D})
def _():
    w = std(hdobs=(), hkw={"countries": ["Kenya"]}, kyc=K(doc="Z11223344"))
    w.cust("CUS-000002", "John Smith", "1971-01-01", nat="Kenya", res="KE").acc("ACC-000002", "CUS-000002").onb("ACC-000002", "CUS-000002", "APP-000002")
    w.kyc("KYC-000009", "APP-000002", "John Smith", "1971-01-01", country="Kenya", doc="Z11223344", result="rejected")
    return w


@case("R08", "resolution", "no link, three namesakes: screened DOB picks one, hit DOB matches it", {S})
def _():
    w = W()
    for i, dob in enumerate(("1950-01-01", "1980-03-03", "1999-09-09")):
        w.cust("CUS-00000%d" % (i + 1), "John Smith", dob)
    return w.alert("A-000001", "John Smith", ["H-000001"], dob="1980-03-03").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("R09", "resolution", "no link, two namesakes: screened country picks the Kenyan one", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1950-01-01").cust("CUS-000002", "John Smith", "1980-03-03", nat="Kenya", res="KE", city="Nairobi")
    return w.alert("A-000001", "John Smith", ["H-000001"], country="Kenya").hit("H-000001", "A-000001", "Smith, John", dobs=["1980"], countries=["Kenya"])


@case("R10", "resolution", "no link, no matching customer record; screened DOB contradicts hit", {R, D}, amb=True)
def _():
    w = W().cust("CUS-000001", "Peter Brown", "1970-01-01")
    return w.alert("A-000001", "Ivan Petrov", ["H-000001"], dob="1990-01-01").hit("H-000001", "A-000001", "Petrov, Ivan", dobs=["1950"], countries=["Russia"])


@case("R11", "resolution", "email link with different case and surrounding spaces", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03", email="john.smith@mail.example")
    return w.alert("A-000001", "John Smith", ["H-000001"], email="  John.Smith@MAIL.example ").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("R12", "resolution", "KYC note filed under an upper-case email still belongs to the customer (verified DOB 1985 beats record 1980)", NOT_CLEAR)
def _():
    return std(hdobs=("1985-04-12",), notes=[{"email": "CUS-000001@Mail.Example", "text": "Onfido verified the passport of JOHN SMITH, born 12 April 1985, on 2024-06-01."}])


@case("R13", "resolution", "closed account still links the customer", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03").acc("ACC-000001", "CUS-000001", status="closed")
    return w.alert("A-000001", "John Smith", ["H-000001"], account="ACC-000001").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("R14", "resolution", "login-handle link", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03").acc("ACC-000001", "CUS-000001", login="jsmith80")
    w.cust("CUS-000002", "John Smith", "1950-01-01")
    return w.alert("A-000001", "John Smith", ["H-000001"], login="jsmith80").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("R15", "resolution", "account_ref that exists nowhere: fall back to a search on the screened details", {S})
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03")
    return w.alert("A-000001", "John Smith", ["H-000001"], dob="1980-03-03", account="ACC-FFFFFF").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("R16", "resolution", "no link; screened nickname 'Jim' finds record 'James Brown' (variant list)", {S})
def _():
    w = W().cust("CUS-000001", "James Brown", "1980-03-03")
    return w.alert("A-000001", "Jim Brown", ["H-000001"], dob="1980-03-03").hit("H-000001", "A-000001", "Brown, James", dobs=["1980"])


@case("R17", "resolution", "two people fit, both lead to the same clearance -> that decision, record AMBIGUOUS", {D})
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03").cust("CUS-000002", "John Smith", "1981-04-04")
    return w.alert("A-000001", "John Smith", ["H-000001"]).hit("H-000001", "A-000001", "Smith, John", dobs=["1950"])


# ============================================================== KYC
@case("K01", "kyc", "two approved checks on the same date with different DOBs; hit fits one of them", NOT_CLEAR, amb=True)
def _():
    return std(hdobs=("1990-05-05",), kyc=[K(dob="1980-03-03", date="2024-01-01"), K(dob="1990-05-05", date="2024-01-01")])


@case("K02", "kyc", "latest approved check gives a year-only DOB that agrees with the hit; an older full DOB would contradict", NOT_CLEAR)
def _():
    return std(cdob="1980-03-03", hdobs=("1980-07-01",), kyc=[K(dob="1980-03-03", date="2020-01-01"), K(dob="1980", date="2024-01-01")])


@case("K03", "kyc", "approved check, then a later rejected check with another DOB: the approved one counts", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(date="2022-01-01"), K(dob="1990-01-01", date="2025-01-01", result="rejected")])


@case("K04", "kyc", "latest check expired with another name: the earlier approved name counts", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(date="2022-01-01"), K(name="Peter Jones", date="2025-01-01", result="expired")])


def _note_dob(text):
    return std(hdobs=("1985-04-12",), notes=[{"text": text}])


@case("K05", "kyc", "note-only check, ISO DOB (record DOB 1980 is stale)", NOT_CLEAR)
def _():
    return _note_dob("Onfido verified the passport of JOHN SMITH, DOB 1985-04-12, on 2024-06-01.")


@case("K06", "kyc", "note-only check, '12th April 1985'", NOT_CLEAR)
def _():
    return _note_dob("Veriff approved JOHN SMITH (date of birth 12th April 1985) using a passport on 2024-06-01.")


@case("K07", "kyc", "note-only check, 'April 12th, 1985'", NOT_CLEAR)
def _():
    return _note_dob("On 2024-06-01 Persona confirmed the passport of JOHN SMITH, born April 12th, 1985.")


@case("K08", "kyc", "note-only check, '12.04.1985' dotted", NOT_CLEAR)
def _():
    return _note_dob("Passport of JOHN SMITH verified by Sumsub on 2024-06-01, DOB 12.04.1985.")


@case("K09", "kyc", "note-only check, two-digit year '12/04/85'", NOT_CLEAR, amb=True)
def _():
    return _note_dob("Passport of JOHN SMITH verified by Sumsub on 2024-06-01, DOB 12/04/85.")


@case("K10", "kyc", "note-only check written month-first (check date 06/25/2024 shows the order), DOB 04/12/1985", NOT_CLEAR, amb=True)
def _():
    return _note_dob("Passport of JOHN SMITH verified by Sumsub on 06/25/2024, DOB 04/12/1985.")


@case("K11", "kyc", "note-only check, DOB stated after the date ('1985-04-12 is the date of birth on the passport')", NOT_CLEAR)
def _():
    return _note_dob("We approved JOHN SMITH's passport through Onfido on 2024-06-01; 1985-04-12 is the date of birth it shows.")


@case("K12", "kyc", "note-only check with the check date written in words before an ISO DOB", NOT_CLEAR)
def _():
    return _note_dob("On 1 June 2024 Onfido verified JOHN SMITH, born 1985-04-12, with a United Kingdom passport.")


@case("K13", "kyc", "note says the check FAILED: its DOB is not evidence; record DOB 1980 contradicts hit 1985", {D})
def _():
    return _note_dob("Onfido could not verify the passport of JOHN SMITH, DOB 1985-04-12, on 2024-06-01; the check failed.")


@case("K14", "kyc", "KYC table check newer than a note check: the table check wins", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(date="2025-01-01")],
               notes=[{"text": "Onfido verified the passport of JOHN SMITH, born 1985-04-12, on 2023-01-01.", "date": "2023-01-01"}])


@case("K15", "kyc", "note check newer than the KYC table check: the note wins (verified DOB 1985 fits hit)", NOT_CLEAR)
def _():
    return std(hdobs=("1985-04-12",), kyc=[K(date="2021-01-01")],
               notes=[{"text": "Onfido verified the passport of JOHN SMITH, born 1985-04-12, on 2024-06-01.", "date": "2024-06-01"}])


@case("K16", "kyc", "verified name written 'SMITH, John'", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(name="SMITH, John"))


@case("K17", "kyc", "latest approved check has no DOB: other DOBs still count, no contradiction", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03-03",), kyc=K(dob=None))


@case("K18", "kyc", "note marked pending, later than the approved table check: not an approved check", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(date="2022-01-01")],
               notes=[{"text": "Passport check for PETER JONES, DOB 1990-01-01, is pending with Onfido (submitted 2024-06-01).", "date": "2024-06-01"}])


@case("K19", "kyc", "support note 'details verified on the phone' is not an identity check", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(date="2022-01-01")],
               notes=[{"text": "Customer called about a card payment; identity verified on the phone by security questions.", "channel": "phone", "date": "2025-02-02"}])


@case("K20", "kyc", "note mixes a month-first check date with an ambiguous DOB 04/12/1985: keep only the year", NOT_CLEAR)
def _():
    return std(hdobs=("1985-12-04",), notes=[{"text": "Passport of JOHN SMITH verified by Sumsub on 06/25/2024, DOB 04/12/1985."}])


# ============================================================== names (a verified name is present, so a wrong name rule clears)
def _nm(vname, hname, hdobs=("1980-03-03",), aliases=(), cname=None, hkw=None):
    h = {"aliases": list(aliases)}
    h.update(hkw or {})
    return std(cname=cname or vname, hname=hname, hdobs=hdobs, kyc=K(name=vname), hkw=h)


for _cid, _v, _h, _d in [
        ("N01", "Mohammed Ali Khan", "Muhammad Ali Khan", "variant list transliteration"),
        ("N02", "Abdulsalam Bello", "Abdul Salam Bello", "joined vs split part"),
        ("N03", "Jonas Peters", "Jonas Petrs", "one edit on a 6-letter part"),
        ("N04", "Anna Kowalski", "Anna Kowalksi", "transposition on an 8-letter part (2 edits allowed)"),
        ("N07", "J. Robert Smith", "Robert Smith", "initial is not a part"),
        ("N08", "John Smith", "Smith, John (Johnny)", "brackets ignored"),
        ("N09", "Ludwig van der Berg", "Ludwig Berg", "particles: every part of the shorter name matches"),
        ("N10", "Anna-Maria Lopez-Garcia", "Anna Maria Lopez Garcia", "hyphenated parts"),
        ("N11", "Juan Carlos Garcia Lopez", "GARCIA LOPEZ, Juan Carlos", "Spanish surname order"),
        ("N12", "Ivan Petrovich Sidorov", "Sidorov, Ivan", "Russian patronymic dropped on the hit"),
        ("N13", "Khalid bin Salman Al-Rashid", "Khalid Al Rashid", "Arabic bin / Al- particle"),
        ("N14", "Wang Xiaoming", "Xiaoming Wang", "Chinese order swapped"),
        ("N15", "José Müller", "Jose Muller", "diacritics"),
        ("N16", "Işık Yılmaz", "Isik Yilmaz", "Turkish dotless i"),
        ("N17", "Johann Strauß", "Johann Strauss", "German sharp s"),
        ("N18", "Sean O'Brien", "Sean OBrien", "apostrophe"),
        ("N19", "Аnna Smith", "Anna Smith", "Cyrillic look-alike A in the verified name"),
        ("N22", "James Brown", "Jim Brown", "nickname in the variant list"),
        ("N27", "Aleksandr Volkov", "Alexander Volkov", "transliteration in the variant list"),
        ("N28", "Nguyễn Văn An", "Nguyen Van An", "Vietnamese diacritics, short parts identical"),
        ("N29", "Siobhán Ní Bhriain", "Siobhan Ni Bhriain", "Irish fada"),
        ("N30", "Mary-Kate O'Neill-Smith", "Mary Kate Oneill Smith", "hyphens and apostrophes together"),
]:
    case(_cid, "names", "verified '%s' vs hit '%s': %s (agree, must not clear on name)" % (_v, _h, _d), NOT_CLEAR)(
        (lambda v, h: (lambda: _nm(v, h)))(_v, _h))


@case("N05", "names", "transposition in a 5-letter part (2 edits > 1): only one part matches -> name mismatch clears", {D})
def _():
    return _nm("Anna Smith", "Anna Simth")


@case("N06", "names", "parts under 4 letters must be identical ('Li' vs 'Le'): name mismatch clears", {D})
def _():
    return _nm("Li Wei", "Le Wei")


@case("N20", "names", "mononym customer (one real part) cannot be cleared or confirmed on name", {R})
def _():
    return _nm("Madonna", "Ciccone, Madonna Louise")


@case("N21", "names", "placeholders in the verified name leave one real part: no name decision", {R})
def _():
    return _nm("TEST UNKNOWN Smith", "John Smith")


@case("N23", "names", "nickname NOT in the variant list ('Bobby' vs verified 'Robert'): only surname matches -> clears", {D})
def _():
    return _nm("Roberta Brown", "Bobby Brown")


@case("N24", "names", "alias-only match", NOT_CLEAR)
def _():
    return _nm("John Smith", "Ahmed Musa", aliases=["John Smith (AKA)"])


@case("N25", "names", "hit's single-part alias agrees with the customer's name", NOT_CLEAR)
def _():
    return _nm("John Smith", "Xavier Quinto", aliases=["Smith"])


@case("N26", "names", "maiden name: record and hit 'Mary Jones', latest verified 'Mary Smith' -> verified name mismatch", {D})
def _():
    return _nm("Mary Smith", "Mary Jones", cname="Mary Jones")


@case("N31", "names", "verified name in ALL CAPS with extra middle names vs short hit", NOT_CLEAR)
def _():
    return _nm("MARIA DEL CARMEN GONZALEZ RUIZ", "Gonzalez, Maria")


@case("N32", "names", "screened name is a typo of the record, verified name agrees with hit", {S})
def _():
    w = std(hdobs=("1980-03-03",), kyc=K())
    w.t["alerts"][0]["customer"]["name"] = "Jhon Smiht"
    return w


@case("N33", "names", "verified name written in Cyrillic ('Иван Петров') vs Latin hit 'Ivan Petrov': cannot be compared, never clear on it", NOT_CLEAR)
def _():
    return _nm("Иван Петров", "Ivan Petrov", cname="Ivan Petrov")


@case("N34", "names", "Icelandic thorn/eth ('Þór Guðmundsson' vs 'Thor Gudmundsson')", NOT_CLEAR)
def _():
    return _nm("Þór Guðmundsson", "Thor Gudmundsson")


def _co(cname, hname, kname=None, hdobs=(), cdob="2001-01-01", hkw=None):
    h = {"countries": ["United Kingdom"]}
    h.update(hkw or {})
    return std(cname=cname, cdob=cdob, hname=hname, hdobs=hdobs, kyc=K(name=kname or cname, dob=cdob, dtype="registry extract"),
               ckw={"etype": "Company"}, hkw=dict(h, etype="Company"), akw={"etype": "Company"})


@case("N40", "companies", "'Acme Trading Ltd' vs 'ACME TRADING LIMITED'", NOT_CLEAR)
def _():
    return _co("Acme Trading Ltd", "ACME TRADING LIMITED")


@case("N41", "companies", "'The Acme Group plc' vs 'Acme Group'", NOT_CLEAR)
def _():
    return _co("The Acme Group plc", "Acme Group")


@case("N42", "companies", "'Banco Sol S.A.' vs 'Banco Sol SA'", NOT_CLEAR)
def _():
    return _co("Banco Sol S.A.", "Banco Sol SA")


@case("N43", "companies", "company names share only a legal form ('Northwind Ltd' vs 'Southwind Holdings Ltd')", {D})
def _():
    return _co("Northwind Ltd", "Eastgate Holdings Ltd")


@case("N44", "companies", "trading-as name: customer 'Acme Ltd t/a Blue Harbour Cafe' vs hit 'Blue Harbour Cafe'", NOT_CLEAR, amb=True)
def _():
    return _co("Acme Ltd t/a Blue Harbour Cafe", "Blue Harbour Cafe")


@case("N45", "companies", "company incorporated after the hit's incorporation date in dobs -> DOB mismatch", {D})
def _():
    return _co("Acme Trading Ltd", "Acme Trading Limited", hdobs=["1990-05-05"])


@case("N46", "companies", "company: 'founded in 1990' in notes is NOT an incorporation date", NOT_CLEAR)
def _():
    return _co("Acme Trading Ltd", "Acme Trading Limited", hkw={"notes": "Acme Trading Limited was founded in 1990 in London."})


@case("N47", "companies", "company 'GmbH & Co. KG' forms", NOT_CLEAR)
def _():
    return _co("Müller Logistik GmbH & Co. KG", "Muller Logistik GmbH")


# ============================================================== dates
@case("T01", "dates", "year-only hit vs full customer DOB agree", {S})
def _():
    return std(hdobs=("1980",), kyc=K())


@case("T02", "dates", "every hit DOB more than a year away -> DOB mismatch", {D})
def _():
    return std(hdobs=("1977", "1983"), kyc=K())


@case("T03", "dates", "one of two hit DOBs agrees -> no clearance", NOT_CLEAR)
def _():
    return std(hdobs=("1975-01-01", "1980-03-03"), kyc=K())


@case("T04", "dates", "hit DOB is a range '1979-1981'", NOT_CLEAR, amb=True)
def _():
    return std(hdobs=("1979-1981",), kyc=K())


@case("T05", "dates", "hit DOB 'circa 1980'", NOT_CLEAR, amb=True)
def _():
    return std(hdobs=("circa 1980",), kyc=K())


def _age(cdob, notes="John Smith, aged 45, was sentenced in March 2019."):
    return std(cdob=cdob, hdobs=(), kyc=K(dob=cdob), hkw={"notes": notes})


@case("T06", "dates", "aged 45 in March 2019 -> 1973/1974; customer 1974-12-01 agrees", {S})
def _():
    return _age("1974-12-01")


@case("T07", "dates", "aged 45 in March 2019; customer 1975 is within one year -> no clearance", NOT_CLEAR)
def _():
    return _age("1975-01-01")


@case("T08", "dates", "aged 45 in March 2019; customer 1976 is >1 year outside -> DOB mismatch", {D})
def _():
    return _age("1976-01-01")


@case("T09", "dates", "aged 45 in March 2019; customer 1972 is within one year of 1973 -> no clearance", NOT_CLEAR)
def _():
    return _age("1972-06-06")


@case("T10", "dates", "two inconsistent ages in the first paragraph; one agrees -> no clearance", NOT_CLEAR)
def _():
    return _age("1974-06-06", "John Smith, aged 45, was sentenced in March 2019. A 2019 May report gave his age as 50 in May 2019.")


@case("T11", "dates", "29 February both sides", {S})
def _():
    return std(cdob="1980-02-29", hdobs=("29 Feb 1980",), kyc=K(dob="1980-02-29"))


@case("T12", "dates", "same year, different month -> mismatch", {D})
def _():
    return std(cdob="1980-05-05", hdobs=("1980-06-05",), kyc=K(dob="1980-05-05"))


@case("T13", "dates", "same year and month, different day -> mismatch", {D})
def _():
    return std(cdob="1980-05-05", hdobs=("1980-05-06",), kyc=K(dob="1980-05-05"))


@case("T14", "dates", "hit gives year and month only ('May 1980'); customer 1980-05-17 agrees", {S})
def _():
    return std(cdob="1980-05-17", hdobs=("May 1980",), kyc=K(dob="1980-05-17"))


def _rep(cdob, lines, company=False):
    notes = "Profile summary.\n\n" + "\n".join(lines)
    if company:
        return _co("Acme Trading Ltd", "Acme Trading Limited", cdob=cdob, hkw={"notes": notes})
    return std(cdob=cdob, hdobs=(), kyc=K(dob=cdob), hkw={"notes": notes})


@case("T15", "dates", "exactly 16 on the earliest report date -> not too young", NOT_CLEAR)
def _():
    return _rep("2000-09-10", ["According to Reuters; September 10, 2016: named in a fraud inquiry."])


@case("T16", "dates", "one day short of 16 on the earliest report date -> temporal impossibility", {D})
def _():
    return _rep("2000-09-11", ["According to Reuters; September 10, 2016: named in a fraud inquiry."])


@case("T17", "dates", "report before the customer was born", {D})
def _():
    return _rep("2005-01-01", ["According to BBC; March 3, 2001: subject of an investigation."])


@case("T18", "dates", "reports out of order: the earliest one decides (customer 10 then)", {D})
def _():
    return _rep("2000-01-01", ["According to BBC; March 3, 2020: charged.", "According to AP; June 1, 2010: first named."])


@case("T19", "dates", "lower-case 'according to' line is not a dated report", NOT_CLEAR)
def _():
    return _rep("2005-01-01", ["according to BBC; March 3, 2001: subject of an investigation."])


@case("T20", "dates", "dated-report form embedded mid-line is not a dated report", NOT_CLEAR, amb=True)
def _():
    return _rep("2005-01-01", ["Press: According to BBC; March 3, 2001: subject of an investigation."])


@case("T21", "dates", "company incorporated on the report date (not after)", NOT_CLEAR)
def _():
    return _rep("2010-03-03", ["According to BBC; March 3, 2010: fined."], company=True)


@case("T22", "dates", "company incorporated the day after the earliest report", {D})
def _():
    return _rep("2010-03-04", ["According to BBC; March 3, 2010: fined."], company=True)


@case("T23", "dates", "deceased_date after screening -> not deceased", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": "2026-12-01"})


@case("T24", "dates", "deceased_date before screening -> DECEASED", {D})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": "2019-05-01", "life": "Deceased"})


@case("T25", "dates", "a relative's death in the notes is not the hit's death", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"notes": "John Smith is a regional official. His father died on March 3, 2001."})


@case("T26", "dates", "deceased_date equal to the screening date -> not before", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": SCREENED})


@case("T27", "dates", "dobs empty; 'born on 3 March 1980' in the first paragraph", {S})
def _():
    return std(hdobs=(), kyc=K(), hkw={"notes": "John Smith, born on 3 March 1980, is a regional official."})


@case("T28", "dates", "birth sentence only in the second paragraph does not count; no other DOB", NOT_CLEAR)
def _():
    return std(cdob="1990-01-01", hdobs=(), kyc=K(dob="1990-01-01"), hkw={"notes": "John Smith is a regional official.\n\nHe was born on 3 March 1960."})


@case("T29", "dates", "dobs field wins over a different year in the notes", {S})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"notes": "John Smith, born in 1960, is a regional official."})


@case("T30", "dates", "deceased_date in provider slash format before screening", {D})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": "05/01/2019", "life": "Deceased"})


@case("T31", "dates", "hit DOB 'circa 1980', customer 1983: approximate, never a contradiction", NOT_CLEAR)
def _():
    return std(cdob="1983-01-01", hdobs=("circa 1980",), kyc=K(dob="1983-01-01"))


@case("T32", "dates", "hit DOB '1980s' (a decade), customer 1985: agrees, no clearance", NOT_CLEAR)
def _():
    return std(cdob="1985-01-01", hdobs=("1980s",), kyc=K(dob="1985-01-01"))


@case("T33", "dates", "hit DOB range '1979-1981', customer 1984: every year >1 away -> DOB mismatch", {D})
def _():
    return std(cdob="1984-01-01", hdobs=("1979-1981",), kyc=K(dob="1984-01-01"))


@case("T34", "dates", "name and DOB agree but customer under 16 at the earliest report (inconsistent hit) -> REVIEW", {R, D}, amb=True)
def _():
    return std(cdob="2005-01-01", hdobs=("2005",), kyc=K(dob="2005-01-01"),
               hkw={"notes": "Profile.\n\nAccording to BBC; March 3, 2012: named in an inquiry."})


# ============================================================== search results
def _sr(snips, cdob="1960-01-01", hkw=None):
    return std(cdob=cdob, hdobs=(), kyc=K(dob=cdob), srs=[("john smith", s) for s in snips], hkw=hkw)


@case("S01", "search", "namesake: listing phrase right, country wrong -> ignored", NOT_CLEAR)
def _():
    return _sr(["John Smith, 30, a politically exposed person in Canada, was named in May 2010."])


@case("S02", "search", "namesake: country right, listing phrase wrong -> ignored", NOT_CLEAR)
def _():
    return _sr(["John Smith, 30, a taxi driver in United Kingdom, won an award in May 2010."])


@case("S03", "search", "about the hit (phrase + country + age) -> contradicts customer -> DOB mismatch", {D})
def _():
    return _sr(["John Smith, 30, a politically exposed person in United Kingdom, was named in May 2010."])


@case("S04", "search", "two results about the hit with different ages, one agrees -> no clearance", NOT_CLEAR)
def _():
    return _sr(["John Smith, 30, a politically exposed person in United Kingdom, was named in May 2010.",
                "In June 2010 John Smith, 50, a politically exposed person in United Kingdom, resigned."])


@case("S05", "search", "hit has a DOB in notes: search results must not be used", {S})
def _():
    return _sr(["John Smith, 30, a politically exposed person in United Kingdom, was named in May 2010."],
               hkw={"notes": "John Smith, born 1960, is a regional official."})


@case("S06", "search", "primary category Sanctions: 'a sanctioned individual' phrase counts, PEP phrase does not", {D})
def _():
    return _sr(["John Smith, 30, a sanctioned individual in United Kingdom, was listed in May 2010."], hkw={"cats": ["Sanctions", "PEP"]})


@case("S07", "search", "other category -> 'named on a watchlist'", {D})
def _():
    return _sr(["John Smith, 30, named on a watchlist in United Kingdom, was mentioned in May 2010."], hkw={"cats": ["Regulatory"]})


# ============================================================== countries (no DOB on the hit, name agrees: only location can clear)
def _ct(cnat, cres, hc, hkw=None, kyc_country="United Kingdom", notes=()):
    h = {"countries": hc}
    h.update(hkw or {})
    return std(hdobs=(), kyc=K(country=kyc_country if kyc_country else cnat), ckw={"nat": cnat, "res": cres}, hkw=h, notes=notes)


for _cid, _n, _r, _hc, _d in [
        ("C01", "United Kingdom", "GB", ["Great Britain"], "Great Britain = United Kingdom"),
        ("C02", "United Kingdom", "GB", ["England"], "England is part of the United Kingdom"),
        ("C03", "United Kingdom", "GB", ["Northern Ireland"], "Northern Ireland is part of the United Kingdom"),
        ("C06", "Côte d'Ivoire", "CI", ["Ivory Coast"], "Ivory Coast = Côte d'Ivoire"),
        ("C07", "Czechia", "CZ", ["Czech Republic"], "Czechia = Czech Republic"),
        ("C08", "Myanmar", "MM", ["Burma"], "Burma = Myanmar"),
        ("C09", "Eswatini", "SZ", ["Swaziland"], "Swaziland = Eswatini"),
        ("C10", "Nigerian", "NG", ["Nigeria"], "demonym"),
        ("C11", "NGA", "NGA", ["Nigeria"], "ISO3 code"),
        ("C20", "USA", "U.S.", ["United States of America"], "USA / U.S."),
        ("C21", "South Korea", "KR", ["Republic of Korea"], "Republic of Korea"),
        ("C22", "DR Congo", "CD", ["Congo"], "bare 'Congo' is ambiguous between two countries"),
        ("C23", "Kosovo", "XK", ["Kosovo"], "XK code"),
        ("C24", "Türkiye", "TR", ["Turkey"], "Türkiye = Turkey"),
        ("C25", "Holland", "NL", ["Netherlands"], "Holland = Netherlands"),
        ("C26", "United Arab Emirates", "AE", ["UAE"], "UAE"),
        ("C27", "Russian Federation", "RU", ["Russia"], "Russian Federation"),
        ("C28", "Korea", "KR", ["South Korea"], "bare 'Korea' on the customer side"),
]:
    case(_cid, "countries", "customer %s/%s vs hit %s: %s (must not clear on location)" % (_n, _r, _hc, _d), NOT_CLEAR,
         amb=_cid in ("C02", "C03", "C22", "C28"))((lambda n, r, hc: (lambda: _ct(n, r, hc, kyc_country=None)))(_n, _r, _hc))


@case("C04", "countries", "Hong Kong is its own territory: customer China only vs hit Hong Kong only -> location clears", {D})
def _():
    return _ct("China", "CN", ["Hong Kong"], kyc_country="China")


@case("C05", "countries", "territory: Puerto Rico vs United States -> own country, location clears", {D})
def _():
    return _ct("United States", "US", ["Puerto Rico"], kyc_country="United States")


@case("C12", "countries", "dual picture: nationality UK, residence Kenya; hit Kenya", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "KE", ["Kenya"])


@case("C13", "countries", "former residence in a support note ('lived in Kenya until 2015')", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Kenya"], notes=[{"text": "Customer mentioned they lived in Kenya until 2015 before moving to London.", "channel": "email"}])


@case("C14", "countries", "'International' / 'Europe' are not countries: no location clearance", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["International", "Europe"])


@case("C15", "countries", "hit address last part 'Nairobi, Kenya' vs customer Kenya", NOT_CLEAR)
def _():
    return _ct("Kenya", "KE", [], hkw={"addresses": ["12 Moi Avenue, Nairobi, Kenya"]}, kyc_country="Kenya")


@case("C16", "countries", "hit place of birth only, Kenya, customer Kenya", NOT_CLEAR)
def _():
    return _ct("Kenya", "KE", [], hkw={"pob": "Mombasa, Kenya"}, kyc_country="Kenya")


@case("C17", "countries", "approved document country Kenya counts", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Kenya"], kyc_country="Kenya")


@case("C18", "countries", "EXPIRED document country does not count -> location clears", {D})
def _():
    w = _ct("United Kingdom", "GB", ["Kenya"])
    w.kyc("KYC-000009", "APP-000001", "John Smith", "1980-03-03", country="Kenya", result="expired", date="2025-01-01")
    return w


@case("C19", "countries", "hit nationality given as a demonym 'Kenyan'", NOT_CLEAR)
def _():
    return _ct("Kenya", "KE", [], hkw={"nationality": ["Kenyan"]}, kyc_country="Kenya")


@case("C29", "countries", "plain disjoint countries -> location clears", {D})
def _():
    return _ct("United Kingdom", "GB", ["Kenya"])


@case("C30", "countries", "hit country an unrecognised value ('Freedonia') -> no clearance", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Freedonia"])


@case("C31", "countries", "Macao is its own territory: customer China only vs hit 'Macao Special Administrative Region of China'", {D})
def _():
    return _ct("China", "CN", ["Macao Special Administrative Region of China"], kyc_country="China")


@case("C32", "countries", "Scotland / Wales are the United Kingdom", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Scotland", "Wales"])


@case("C33", "countries", "'Taiwan, Province of China' is not read as a country: no clearance against China", NOT_CLEAR, amb=True)
def _():
    return _ct("China", "CN", ["Taiwan, Province of China"], kyc_country="China")


@case("C34", "countries", "Taiwan vs China: separate countries/territories -> location clears", {D}, amb=True)
def _():
    return _ct("China", "CN", ["Taiwan"], kyc_country="China")


# ============================================================== hits / type
@case("H01", "hits", "hit entity type missing: no type contradiction", NOT_CLEAR)
def _():
    w = _co("Acme Trading Ltd", "Acme Trading Limited")
    w.t["hits"][0]["entity_type"] = None
    return w


@case("H02", "hits", "person vs company -> entity type mismatch", {D})
def _():
    return std(hdobs=(), kyc=K(), hkw={"etype": "Company"})


@case("H03", "hits", "customer company, hit 'Organisation' (a company by another word)", NOT_CLEAR, amb=True)
def _():
    w = _co("Acme Trading Ltd", "Acme Trading Limited")
    w.t["hits"][0]["entity_type"] = "Organisation"
    return w


@case("H04", "hits", "name + DOB agree but countries disjoint -> REVIEW", {R})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"countries": ["Kenya"]})


@case("H05", "hits", "hit dobs entry is a placeholder ('UNKNOWN')", NOT_CLEAR)
def _():
    return std(hdobs=("UNKNOWN",), kyc=K(dob="1960-01-01"), cdob="1960-01-01")


# ============================================================== placeholders
@case("P01", "placeholders", "record 'N/A Smith', verified 'UNKNOWN SMITH': fewer than two real parts", {R})
def _():
    return std(cname="N/A Smith", hname="John Smith", hdobs=("1980-03-03",), kyc=K(name="UNKNOWN SMITH"))


@case("P02", "placeholders", "customer DOB '-' and no check: no DOB clearance", NOT_CLEAR)
def _():
    return std(cdob="-", hdobs=("1950",))


@case("P03", "placeholders", "customer DOB '0000-00-00': no DOB clearance", NOT_CLEAR)
def _():
    return std(cdob="0000-00-00", hdobs=("1950",))


@case("P04", "placeholders", "customer nationality 'UNKNOWN', residence '?': no customer country, no location clearance", NOT_CLEAR)
def _():
    return std(hdobs=(), ckw={"nat": "UNKNOWN", "res": "?"}, hkw={"countries": ["Kenya"]})


@case("P05", "placeholders", "two records share placeholder phone '0000000000' and DOB; second is Kenyan (policy text says merge)", NOT_CLEAR, amb=True)
def _():
    w = std(hdobs=(), ckw={"phone": "0000000000"}, hkw={"countries": ["Kenya"]})
    w.cust("CUS-000002", "John Smith", "1980-03-03", nat="Kenya", res="KE", phone="0000000000")
    return w


@case("P08", "placeholders", "placeholder phone + same DOB would import another person's later verified name -> must not clear on name", NOT_CLEAR, amb=True)
def _():
    w = std(hdobs=(), kyc=K(date="2021-01-01"), ckw={"phone": "+44 7000000000"})
    w.cust("CUS-000002", "Peter Jones", "1980-03-03", phone="+44 7000000000").acc("ACC-000002", "CUS-000002").onb("ACC-000002", "CUS-000002", "APP-000002")
    w.kyc("KYC-000002", "APP-000002", "Peter Jones", "1980-03-03", date="2025-01-01")
    return w


@case("P09", "placeholders", "real (non-placeholder) shared phone + same DOB still merges: the duplicate's Kenya blocks a location clearance", NOT_CLEAR)
def _():
    w = std(hdobs=(), ckw={"phone": "+44 7911123456"}, hkw={"countries": ["Kenya"]})
    w.cust("CUS-000002", "John Smith", "1980-03-03", nat="Kenya", res="KE", phone="+44 7911123456")
    return w


@case("P06", "placeholders", "verified name 'XXX XXX': no name decision", NOT_CLEAR)
def _():
    return std(cname="John Smith", hname="Peter Jones", hdobs=(), kyc=K(name="XXX XXX"))


@case("P07", "placeholders", "screened name 'TEST' only, no link", NOT_CLEAR)
def _():
    w = W().cust("CUS-000001", "John Smith", "1980-03-03")
    return w.alert("A-000001", "TEST", ["H-000001"]).hit("H-000001", "A-000001", "Peter Jones", dobs=["1950"])


# ============================================================== batch 2 (X-series): KYC ordering, merged-record KYC
@case("XK01", "kyc2", "approved (1980) -> rejected -> approved (1990): latest approved DOB 1990-05-05 fits the hit", {S, R})
def _():
    return std(hdobs=("1990-05-05",), kyc=[K(date="2022-01-01"), K(dob="1950-01-01", date="2023-01-01", result="rejected"),
                                          K(dob="1990-05-05", date="2025-01-01")])


@case("XK02", "kyc2", "approved -> rejected -> approved: an older approved DOB contradicting the hit must not be used to clear", NOT_CLEAR)
def _():
    return std(cdob="1990-05-05", hdobs=("1990-05-05",), kyc=[K(dob="1950-01-01", date="2022-01-01"),
                                                              K(dob="1950-01-01", date="2023-01-01", result="rejected"), K(dob="1990-05-05", date="2025-01-01")])


@case("XK03", "kyc2", "two approved checks on the same day with times; the later (17:00) contradicts the hit", {D, R}, amb=True)
def _():
    return std(hdobs=("1980-03-03",), kyc=[K(dob="1980-03-03", date="2024-01-01T09:00:00Z"), K(dob="1990-05-05", date="2024-01-01T17:00:00Z")])


@case("XK04", "kyc2", "merged duplicate (phone + DOB) has an approved Kenyan passport: hit in Kenya cannot clear on location", NOT_CLEAR)
def _():
    w = std(hdobs=(), kyc=K(date="2021-01-01"), hkw={"countries": ["Kenya"]}, ckw={"phone": "+44 7911654321"})
    w.cust("CUS-000002", "John Smith", "1980-03-03", phone="+44 7911654321").acc("ACC-000002", "CUS-000002").onb("ACC-000002", "CUS-000002", "APP-000002")
    w.kyc("KYC-000002", "APP-000002", "John Smith", "1980-03-03", country="Kenya", date="2022-01-01")
    return w


@case("XK05", "kyc2", "merged duplicate's newer approved check gives another legal name (policy: latest approved wins)", {D, R}, amb=True)
def _():
    w = std(hdobs=(), kyc=K(date="2021-01-01"), ckw={"phone": "+44 7911654322"})
    w.cust("CUS-000002", "John Smith", "1980-03-03", phone="+44 7911654322").acc("ACC-000002", "CUS-000002").onb("ACC-000002", "CUS-000002", "APP-000002")
    w.kyc("KYC-000002", "APP-000002", "Peter Jones", "1980-03-03", date="2025-01-01")
    return w


@case("XK06", "kyc2", "only check is 'pending' with another name: no verified name, cannot clear on name", NOT_CLEAR)
def _():
    return std(hdobs=(), kyc=K(name="Peter Jones", result="pending"))


@case("XK07", "kyc2", "note records a REJECTED check with DOB 1950; record + hit agree on 1985 -> rejected note is not evidence", NOT_CLEAR)
def _():
    return std(cdob="1985-04-12", hdobs=("1985-04-12",), notes=[{"text": "Onfido rejected the passport of JOHN SMITH, born 1 January 1950, on 2024-06-01."}])


# ============================================================== batch 2: dates of birth
@case("XB01", "dob2", "hit gives two DOBs, one agrees and one contradicts: one agreeing date prevents clearance", NOT_CLEAR)
def _():
    return std(hdobs=("1965-07-07", "1980-03-03"), kyc=K())


@case("XB02", "dob2", "hit gives years 1965 and 1980; customer 1980-03-03", NOT_CLEAR)
def _():
    return std(hdobs=("1965", "1980"), kyc=K())


@case("XB03", "dob2", "DOB only in a search result about a namesake (wrong listing phrase): not attributable, no DOB clearance", NOT_CLEAR)
def _():
    return _sr(["John Smith, 25, a sanctioned individual in United Kingdom, was named in May 2010."])


@case("XB04", "dob2", "leap day: customer 1980-02-29, hit '29 Feb 1980'", NOT_CLEAR)
def _():
    return std(cdob="1980-02-29", hdobs=("29 Feb 1980",), kyc=K(dob="1980-02-29"))


@case("XB05", "dob2", "leap day: customer 1980-02-29, hit 1980-03-01 (month differs in same year) -> DOB mismatch allowed", {D, R})
def _():
    return std(cdob="1980-02-29", hdobs=("1980-03-01",), kyc=K(dob="1980-02-29"))


@case("XB06", "dob2", "hit DOB year-month '1980-03' agrees with 1980-03-03", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03",), kyc=K())


@case("XB07", "dob2", "hit DOB year-month '1980-07' vs 1980-03-03: month differs", {D, R})
def _():
    return std(hdobs=("1980-07",), kyc=K())


@case("XB08", "dob2", "hit DOB in the future (2031): typo, contradiction by the letter of the policy", {D, R}, amb=True)
def _():
    return std(hdobs=("2031-03-03",), kyc=K())


@case("XB09", "dob2", "customer 1981-03-03 vs hit year 1980: within one year, no clearance", NOT_CLEAR)
def _():
    return std(cdob="1981-03-03", hdobs=("1980",), kyc=K(dob="1981-03-03"))


@case("XB10", "dob2", "age in notes with no year ('aged 45, was sentenced in March'): no birth year, no clearance", NOT_CLEAR)
def _():
    return _age("1960-01-01", notes="John Smith, aged 45, was sentenced in March.")


@case("XB11", "dob2", "hit DOB '03/04/1980' (day/month order unknown) vs 1980-04-03", NOT_CLEAR)
def _():
    return std(cdob="1980-04-03", hdobs=("03/04/1980",), kyc=K(dob="1980-04-03"))


@case("XB12", "dob2", "hit DOB with an ISO timestamp '1980-03-03T00:00:00Z'", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03-03T00:00:00Z",), kyc=K())


# ============================================================== batch 2: deceased
@case("XE01", "deceased2", "date of death AFTER the screening date: not DECEASED; name + DOB agree", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": "2026-12-01", "life": "Deceased"})


@case("XE02", "deceased2", "death claim only in a search result; profile says Alive with no date", NOT_CLEAR)
def _():
    return _sr(["John Smith, a politically exposed person in United Kingdom, died in 2019."], cdob="1980-03-03")


@case("XE03", "deceased2", "life_status 'Deceased' but no date of death", NOT_CLEAR)
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"life": "Deceased"})


@case("XE04", "deceased2", "date of death given as a year only (2019), before screening", {D, R})
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": "2019", "life": "Deceased"})


@case("XE05", "deceased2", "date of death on the screening day itself (not before)", NOT_CLEAR, amb=True)
def _():
    return std(hdobs=("1980-03-03",), kyc=K(), hkw={"deceased": SCREENED, "life": "Deceased"})


# ============================================================== batch 2: name forms
for _cid, _v, _h, _al, _d in [
        ("XN01", "John Andrew Smith", "J. A. SMITH", (), "initials only"),
        ("XN02", "Maria Garcia-Lopez", "GARCIA LOPEZ, Maria", (), "hyphenated double surname, comma form"),
        ("XN03", "Ivan Petrovich Sidorov", "Sidorov Ivan", (), "patronymic dropped, surname first"),
        ("XN04", "Ahmad bin Ismail", "Ahmad Ismail", (), "'bin' particle"),
        ("XN05", "Siti binti Rahman", "Siti Rahman", (), "'binti' particle"),
        ("XN06", "Abdullah Al-Rashid", "Abdullah Alrashid", (), "'Al-' joined"),
        ("XN07", "Aleksandr Ivanov", "Alexander Ivanov", (), "transliteration in the variant list"),
        ("XN08", "Mohamad Khan", "Mohammed Khan", (), "transliteration not in the variant list"),
        ("XN09", "John Smith", "Peter Jones", ("John Smith",), "alias matches the customer, primary does not"),
        ("XN10", "Jose Maria Alvarez de la Cruz Fernandez Ortega", "Jose Alvarez de la Cruz Fernandez Ortega", (), "very long name, one part dropped"),
        ("XN11", "John\u00a0Smith", "Smith,\u2003John", (), "unicode non-breaking / em spaces"),
        ("XN12", "Jos\u00e9 M\u00fcller", "Jose Mueller", (), "diacritics and ue transliteration")]:
    case(_cid, "names2", "verified '%s' vs hit '%s': %s -> no name clearance" % (_v, _h, _d), NOT_CLEAR)(
        (lambda v, h, al: (lambda: _nm(v, h, hdobs=(), aliases=al)))(_v, _h, _al))


# ============================================================== batch 2: companies vs people
@case("XC01", "companies2", "'Smith & Sons Ltd' vs 'SMITH AND SONS LIMITED', both companies in the UK", NOT_CLEAR)
def _():
    return _co("Smith & Sons Ltd", "SMITH AND SONS LIMITED")


@case("XC02", "companies2", "hit entity_type missing; name 'John Lewis' looks personal or corporate", NOT_CLEAR)
def _():
    w = std(cname="John Lewis", hname="John Lewis", hdobs=(), kyc=K(name="John Lewis"))
    w.t["hits"][0]["entity_type"] = None
    return w


# ============================================================== batch 2: countries
@case("XL01", "countries2", "hit nationality given as an adjective 'British' only; customer UK", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", [], hkw={"nationality": ["British"]})


@case("XL02", "countries2", "hit country 'Iranian' (adjective); customer nationality Iran, residence GB", NOT_CLEAR)
def _():
    return _ct("Iran", "GB", ["Iranian"])


@case("XL03", "countries2", "dual nationality: record UK, approved passport Iran; hit Iran", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Iran"], kyc_country="Iran")


@case("XL04", "countries2", "hit countries Iran, but an address ends in United Kingdom", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Iran"], hkw={"addresses": ["12 Park Road, London, United Kingdom"]})


@case("XL05", "countries2", "hit place_of_birth 'Tehran, Iran' only; customer nationality Iran", NOT_CLEAR)
def _():
    return _ct("Iran", "GB", [], hkw={"pob": "Tehran, Iran"})


@case("XL06", "countries2", "hit countries 'International' and 'Europe' only: no country to compare", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["International", "Europe"])


@case("XL07", "countries2", "customer residence code 'GB' vs hit 'Great Britain'", NOT_CLEAR)
def _():
    return _ct("GB", "GB", ["Great Britain"], kyc_country=None)


@case("XL08", "countries2", "hit Kenya; a KYC note says the customer previously lived in Nairobi, Kenya", NOT_CLEAR)
def _():
    return _ct("United Kingdom", "GB", ["Kenya"], notes=[{"text": "Customer confirmed they previously lived in Nairobi, Kenya until 2015."}])


# ============================================================== batch 2: links, duplicates, robustness
@case("XZ01", "links2", "account link -> CUS-1 (DOB 1950), email link -> CUS-2 (DOB matches hit): conflicting links", NOT_CLEAR, amb=True)
def _():
    w = W().cust("CUS-000001", "John Smith", "1950-01-01").acc("ACC-000001", "CUS-000001")
    w.cust("CUS-000002", "John Smith", "1980-03-03", email="js80@mail.example")
    return w.alert("A-000001", "John Smith", ["H-000001"], account="ACC-000001", email="js80@mail.example").hit("H-000001", "A-000001", "Smith, John", dobs=["1980-03-03"])


@case("XZ02", "links2", "no link and no customer record at all", NOT_CLEAR)
def _():
    return W().alert("A-000001", "John Smith", ["H-000001"]).hit("H-000001", "A-000001", "Smith, John", dobs=["1950"])


@case("XZ03", "links2", "duplicate hits on one alert: H-000002 is a clearable namesake, H-000001 matches", NOT_CLEAR)
def _():
    w = std(hdobs=("1980-03-03",), kyc=K())
    w.t["alerts"][0]["hit_ids"].append("H-000002")
    return w.hit("H-000002", "A-000001", "Smith, John", dobs=["1950"])


@case("XZ04", "robust2", "empty-string countries everywhere: no country evidence", NOT_CLEAR)
def _():
    return _ct("", "", [""], kyc_country="")


@case("XZ05", "robust2", "hit name null; only an alias carries 'John Smith'", NOT_CLEAR)
def _():
    w = std(hdobs=(), kyc=K(), hkw={"aliases": ["John Smith"]})
    w.t["hits"][0]["name"] = None
    w.t["hits"][0]["best_matching_name"] = None
    return w


@case("XZ06", "robust2", "customer DOB null and approved check DOB null: no DOB clearance", NOT_CLEAR)
def _():
    return std(cdob=None, hdobs=("1950",), kyc=K(dob=None))


# ============================================================== runner
def run_all(runners):
    results = {r: {} for r in runners}
    tmp = tempfile.mkdtemp()
    try:
        for c in CASES:
            d = os.path.join(tmp, c["id"])
            os.makedirs(d)
            c["fn"]().write(d)
            for r in runners:
                out = os.path.join(d, "out_%d.jsonl" % runners.index(r))
                p = subprocess.run([r, d, out], capture_output=True, text=True)
                got = None
                if p.returncode == 0 and os.path.exists(out):
                    for line in open(out, encoding="utf-8"):
                        x = json.loads(line)
                        if x["hit_id"] == "H-000001":
                            got = x
                results[r][c["id"]] = got
    finally:
        shutil.rmtree(tmp)
    return results


def verdict(c, got):
    if got is None:
        return "ERROR"
    if got["decision"] in c["want"]:
        return "PASS"
    if got["decision"] == D:
        return "UNSAFE"
    return "FAIL"


def main(argv):
    runners = [os.path.abspath(a) for a in argv] or [DEFAULT_RUN]
    res = run_all(runners)
    totals = {r: {} for r in runners}
    print("%-4s %-12s %-3s %-24s %s" % ("id", "area", "amb", "allowed", "  ".join("sys%d" % i for i in range(len(runners)))))
    for c in CASES:
        vs = []
        for r in runners:
            g = res[r][c["id"]]
            v = verdict(c, g)
            totals[r][v] = totals[r].get(v, 0) + 1
            vs.append("%s:%s" % (v, (g or {}).get("reason_code", "-")) if v != "PASS" else "PASS")
        print("%-4s %-12s %-3s %-24s %s" % (c["id"], c["area"], "A" if c["amb"] else "", "/".join(sorted(x[:4] for x in c["want"])), "  ".join(vs)))
    for i, r in enumerate(runners):
        print("sys%d %s: %s" % (i, r, totals[r]))
    return 0 if all(t.get("UNSAFE", 0) == 0 and t.get("ERROR", 0) == 0 for t in totals.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
