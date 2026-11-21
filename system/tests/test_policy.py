#!/usr/bin/env python3
"""Synthetic policy tests for rare cases. Run: python3 system/tests/test_policy.py
Each case builds a tiny data folder, runs the system on it and checks the decision."""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import screen  # noqa: E402

VARIANTS = {"groups": [["james", "jim", "jimmy"], ["mohammed", "muhammad", "mohamed"]],
            "company_legal_forms": ["ltd", "gmbh", "sa", "llc", "plc", "limited"]}


def cust(rid, name, dob, nat="United Kingdom", res="GB", email=None, phone="+44 7000000000", etype="Individual", city="London"):
    return {"record_id": rid, "entity_type": etype, "full_name": name, "preferred_name": None, "login_name": None, "dob": dob,
            "nationality": nat, "residence_country": res, "city": city, "address": "1 High St, " + city,
            "email": email or (rid.lower() + "@x.example"), "phone": phone, "occupation": None, "employer": None,
            "registration_number": None, "onboarded_at": "2020-01-01", "status": "active", "last_kyc_refresh": None}


def hit(hid, aid, name, etype="Individual", dobs=(), countries=(), notes=None, deceased=None, cats=("PEP",), aliases=()):
    return {"hit_id": hid, "alert_id": aid, "match_score": 100, "entity_type": etype, "name": name, "first_name": None,
            "middle_name": None, "last_name": None, "best_matching_name": None, "aliases": list(aliases), "gender": None,
            "dobs": list(dobs), "place_of_birth": None, "life_status": None, "deceased_date": deceased, "nationality": [],
            "citizenship": [], "countries": list(countries), "addresses": [], "identifiers": [], "categories": list(cats),
            "primary_category": None, "subcategories": [], "position_or_allegation": None, "details": {}, "relationships": [],
            "profile_notes": notes, "sources": [], "source_urls": []}


def alert(aid, name, hit_ids, dob=None, account=None, etype="Individual", country=None):
    return {"alert_id": aid, "screened_at": "2026-11-10", "customer": {"name": name, "entity_type": etype, "dob": dob,
            "country": country, "city": None}, "account_ref": account, "login_handle": None, "email": None, "hit_ids": hit_ids}


def kyc(cid, app, name, dob, country="United Kingdom", result="approved", date="2024-01-01", doc="P1"):
    return {"check_id": cid, "applicant_id": app, "provider": "Onfido", "verified_name": name, "verified_dob": dob,
            "document_type": "passport", "document_number": doc, "document_country": country, "result": result, "checked_at": date}


def run_case(customers, accounts, onboarding, kycs, alerts, hits, notes=(), search=()):
    d = tempfile.mkdtemp()
    try:
        for name, rows in (("customers", customers), ("accounts", accounts), ("onboarding", onboarding), ("kyc_checks", kycs),
                           ("alerts", alerts), ("hits", hits), ("notes", notes), ("search_results", search)):
            with open(os.path.join(d, name + ".jsonl"), "w") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
        json.dump(VARIANTS, open(os.path.join(d, "name_variants.json"), "w"))
        out = os.path.join(d, "out.jsonl")
        screen.run(d, out)
        return {json.loads(l)["hit_id"]: json.loads(l) for l in open(out)}
    finally:
        shutil.rmtree(d)


def acc(aid, cid):
    return {"account_id": aid, "customer_id": cid, "login_handle": None, "phone": None, "opened_at": "2020-01-01", "status": "active"}


def onb(aid, cid, app):
    return {"account_id": aid, "customer_id": cid, "kyc_applicant_id": app, "onboarded_at": "2020-01-01"}


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def company_incorporated_after_report():
    r = run_case([cust("CUS-000001", "Acme Widgets Ltd", "2015-06-01", etype="Company")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Acme Widgets Ltd", ["H-000001"], account="ACC-000001", etype="Company")],
                 [hit("H-000001", "A-000001", "Acme Widgets Limited", etype="Company", countries=["United Kingdom"],
                      notes="According to fca.org.uk; March 3, 2010: Acme Widgets was fined.")])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "TEMPORAL_IMPOSSIBILITY"


@case
def too_young_at_earliest_report():
    r = run_case([cust("CUS-000001", "Tom Okafor", "2004-02-02")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Tom Okafor", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Okafor, Tom", countries=["United Kingdom"],
                      notes="According to news.example; May 5, 2019: later.\n\nAccording to bbc.co.uk; June 1, 2011: Tom Okafor was charged.")])
    return r["H-000001"]["reason_code"] == "TEMPORAL_IMPOSSIBILITY"


@case
def sixteen_at_report_is_not_impossible():
    r = run_case([cust("CUS-000001", "Tom Okafor", "1995-01-01")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Tom Okafor", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Okafor, Tom", countries=["United Kingdom"],
                      notes="According to bbc.co.uk; June 1, 2011: Tom Okafor was charged.")])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def death_before_screening():
    r = run_case([cust("CUS-000001", "John Smith", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "John Smith", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "John Smith", countries=["United Kingdom"], deceased="2021-08")])
    return r["H-000001"]["reason_code"] == "DECEASED"


@case
def doc_number_link_adds_country():
    # CUS-2 shares an approved document number with CUS-1 (different phones): one person, so Kenya counts and blocks a location clearance
    cs = [cust("CUS-000001", "Jane Doe", "1980-01-01", phone="+44 1"), cust("CUS-000002", "Jane Doe", "1980-01-01", nat="Kenya", res="KE", phone="+254 2")]
    r = run_case(cs, [acc("ACC-000001", "CUS-000001"), acc("ACC-000002", "CUS-000002")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001"), onb("ACC-000002", "CUS-000002", "APP-000002")],
                 [kyc("KYC-000001", "APP-000001", "Jane Doe", "1980-01-01", doc="X71726641"), kyc("KYC-000002", "APP-000002", "Jane Doe", "1980-01-01", country="Kenya", doc="X71726641", date="2023-01-01")],
                 [alert("A-000001", "Jane Doe", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Doe, Jane", countries=["Kenya"])])
    return r["H-000001"]["decision"] != "DIFFERENT_ENTITY"


@case
def shared_phone_alone_is_not_same_person():
    cs = [cust("CUS-000001", "Jane Doe", "1980-01-01", phone="+44 1"), cust("CUS-000002", "John Doe", "1950-05-05", nat="Kenya", res="KE", phone="+44 1")]
    r = run_case(cs, [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Jane Doe", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Doe, Jane", countries=["Kenya"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "LOCATION_MISMATCH"


@case
def rejected_latest_check_is_ignored():
    # latest check is rejected and carries another name; the older approved check's name agrees -> no name clearance
    r = run_case([cust("CUS-000001", "Peter Brown", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Peter Brown", None, date="2022-01-01"), kyc("KYC-000002", "APP-000001", "Simon Green", None, result="rejected", date="2025-01-01")],
                 [alert("A-000001", "Peter Brown", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Brown, Peter", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def expired_check_is_ignored():
    r = run_case([cust("CUS-000001", "Peter Brown", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Simon Green", "1990-01-01", result="expired", date="2025-01-01")],
                 [alert("A-000001", "Peter Brown", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Brown, Peter", countries=["United Kingdom"], dobs=["1960"])])
    # the expired check's name/DOB must not be used; the record has no DOB -> REVIEW
    return r["H-000001"]["decision"] == "REVIEW"


@case
def latest_approved_wins():
    r = run_case([cust("CUS-000001", "Peter Brown", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Peter Brown", "1960-03-03", date="2020-01-01"), kyc("KYC-000002", "APP-000001", "Peter Brown", "1990-03-03", date="2024-01-01")],
                 [alert("A-000001", "Peter Brown", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Brown, Peter", countries=["United Kingdom"], dobs=["1960"])])
    return r["H-000001"]["reason_code"] == "DOB_MISMATCH" and r["H-000001"]["evidence"] == ["KYC-000002"]


@case
def rejected_kyc_note_is_ignored():
    c = cust("CUS-000001", "Peter Brown", None, email="pb@x.example")
    notes = [{"note_id": "NOTE-000001", "requester_email": "pb@x.example", "created_at": "2025-01-01", "channel": "kyc",
              "text": "Onfido rejected the passport from United Kingdom for SIMON GREEN (DOB 1990-01-01) on 2025-01-01."}]
    r = run_case([c], [acc("ACC-000001", "CUS-000001")], [], [], [alert("A-000001", "Peter Brown", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Brown, Peter", countries=["United Kingdom"], dobs=["1960"])], notes=notes)
    return r["H-000001"]["decision"] == "REVIEW"


@case
def support_note_saying_verified_is_not_an_identity_check():
    # a later support note "verified through the app" must not replace the approved KYC check
    c = cust("CUS-000001", "Peter Brown", "1953-01-03", email="pb@x.example")
    notes = [{"note_id": "NOTE-000001", "requester_email": "pb@x.example", "created_at": "2026-01-01", "channel": "email",
              "text": "Customer updated their mobile number after changing provider. Verified through the app."}]
    r = run_case([c], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Peter Brown", "1959-05-12", date="2025-01-01")],
                 [alert("A-000001", "Peter Brown", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Brown, Peter", countries=["United Kingdom"], dobs=["1959"])], notes=notes)
    return r["H-000001"]["decision"] == "SAME_ENTITY" and "KYC-000001" in r["H-000001"]["evidence"]


@case
def year_only_agrees_with_full_date():
    r = run_case([cust("CUS-000001", "Li Wei", "1975")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Li Wei", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Wei, Li", countries=["United Kingdom"], dobs=["1975-03-02"])])
    return r["H-000001"]["decision"] == "SAME_ENTITY"


@case
def same_year_different_month_is_mismatch():
    r = run_case([cust("CUS-000001", "Li Wei", "1975-04")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Li Wei", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Wei, Li", countries=["United Kingdom"], dobs=["1975-03"])])
    return r["H-000001"]["reason_code"] == "DOB_MISMATCH"


@case
def one_year_apart_is_not_mismatch():
    r = run_case([cust("CUS-000001", "Li Wei", "1976-05-05")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Li Wei", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Wei, Li", countries=["United Kingdom"], dobs=["1975-03-02"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def age_at_date_gives_two_years():
    notes = "Anna Petrova, aged 45, was sentenced in March 2019."
    ok = True
    for dob, want in (("1975-01-01", "REVIEW"), ("1976-01-01", "DIFFERENT_ENTITY"), ("1974-06-06", "SAME_ENTITY")):
        r = run_case([cust("CUS-000001", "Anna Petrova", dob)], [acc("ACC-000001", "CUS-000001")], [], [],
                     [alert("A-000001", "Anna Petrova", ["H-000001"], account="ACC-000001")],
                     [hit("H-000001", "A-000001", "Petrova, Anna", countries=["United Kingdom"], notes=notes)])
        ok &= r["H-000001"]["decision"] == want
    return ok


@case
def name_dob_agree_country_differs_is_review():
    r = run_case([cust("CUS-000001", "Li Wei", "1975-03-02")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Li Wei", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Wei, Li", countries=["Singapore"], dobs=["1975"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def placeholder_single_part_name_cannot_clear_on_name():
    r = run_case([cust("CUS-000001", "Madonna", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "TEST Madonna", None)],
                 [alert("A-000001", "Madonna", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ciccone, Louise", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def ambiguous_people_different_decisions():
    cs = [cust("CUS-000001", "Mohammed Khan", "1990-01-01", nat="Pakistan", res="PK", phone="+92 1"),
          cust("CUS-000002", "Muhammad Khan", "1990-02-02", nat="United Kingdom", res="GB", phone="+44 2")]
    r = run_case(cs, [], [], [], [alert("A-000001", "Mohammed Khan", ["H-000001"], dob="1990")],
                 [hit("H-000001", "A-000001", "Khan, Mohammed", countries=["Pakistan"])])
    x = r["H-000001"]
    return x["decision"] == "REVIEW" and x["reason_code"] == "AMBIGUOUS_CUSTOMER_RECORD" and x["customer_record_id"] == "AMBIGUOUS"


@case
def entity_type_mismatch():
    r = run_case([cust("CUS-000001", "Jordan Smith", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Jordan Smith", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Jordan Smith Ltd", etype="Company", countries=["United Kingdom"])])
    return r["H-000001"]["reason_code"] == "ENTITY_TYPE_MISMATCH"


@case
def search_result_only_counts_with_listing_and_country():
    srs = [{"result_id": "SR-000001", "query": "anna petrova", "title": "Anna Petrova - news", "snippet": "Anna Petrova, 30, a taxi driver in Russia, won an award in May 2010.", "source": "x"},
           {"result_id": "SR-000002", "query": "anna petrova", "title": "Anna Petrova - news", "snippet": "Anna Petrova, 30, a politically exposed person in Spain, was named in May 2010.", "source": "x"}]
    r = run_case([cust("CUS-000001", "Anna Petrova", "1960-01-01", nat="Russia", res="RU")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Anna Petrova", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Petrova, Anna", countries=["Russia"])], search=srs)
    # neither result is about the hit (wrong role / wrong country) -> no hit DOB -> REVIEW
    return r["H-000001"]["decision"] == "REVIEW"


@case
def unknown_country_blocks_location_clearance():
    r = run_case([cust("CUS-000001", "John Smith", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "John Smith", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "John Smith", countries=["Freedonia"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def provider_dob_field_vetoes_but_never_decides():
    # "DOB: 6/20/1955" in the first paragraph contradicts a search-result age that agrees -> REVIEW, not SAME;
    # it supports the customer while a search-result age contradicts -> REVIEW, not a DOB clearance;
    # alone (no other hit DOB) it is not used, so the hit stays REVIEW for lack of a DOB.
    notes = "Name: Petrova, Anna\nDOB: 6/20/1955\nSex: F"
    ok = True
    for dob, snip, want in (("1955-11-19", "Anna Petrova, 55, a politically exposed person in United Kingdom, was named in March 2011.", "REVIEW"),
                            ("1955-06-20", "Anna Petrova, 30, a politically exposed person in United Kingdom, was named in March 2011.", "REVIEW"),
                            ("1955-11-19", None, "REVIEW"),
                            ("1955-06-20", "Anna Petrova, 55, a politically exposed person in United Kingdom, was named in March 2011.", "SAME_ENTITY")):
        srs = [{"result_id": "SR-000001", "query": "anna petrova", "title": "Anna Petrova - news", "snippet": snip, "source": "x"}] if snip else []
        r = run_case([cust("CUS-000001", "Anna Petrova", dob)], [acc("ACC-000001", "CUS-000001")], [], [],
                     [alert("A-000001", "Anna Petrova", ["H-000001"], account="ACC-000001")],
                     [hit("H-000001", "A-000001", "Petrova, Anna", countries=["United Kingdom"], notes=notes)], search=srs)
        ok &= r["H-000001"]["decision"] == want
    return ok


def _note_case(text, record_name, hit_name):
    c = cust("CUS-000001", record_name, "1979-08-10", email="m@x.example")
    notes = [{"note_id": "NOTE-000001", "requester_email": "m@x.example", "created_at": "2023-05-10", "channel": "kyc", "text": text}]
    r = run_case([c], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", record_name, ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", hit_name, countries=["United Kingdom"])], notes=notes)
    return r["H-000001"]


@case
def possessive_name_in_kyc_note_is_read_whole():
    # "MARCUS DAVID MILLER's passport": the possessive must not cut the surname off (that would clear on name)
    r = _note_case("We approved MARCUS DAVID MILLER's passport from United Kingdom through Veriff on 2023-05-10. "
                   "The document gives August 10, 1979 as the birth date.", "Marcus David Miller", "Marcus Miller")
    return r["decision"] == "REVIEW"


@case
def truncated_note_name_never_clears_on_name():
    # a note-parsed verified name that is a strict part of the record name is treated as a parsing miss
    r = _note_case("Veriff approved the passport of MARCUS DAVID miller (born 1979-08-10) on 2023-05-10.", "Marcus David Miller", "Marcus Miller")
    return r["decision"] == "REVIEW"


if __name__ == "__main__":
    import io
    import contextlib
    failed = 0
    for fn in CASES:
        with contextlib.redirect_stderr(io.StringIO()):
            ok = fn()
        print(("PASS " if ok else "FAIL ") + fn.__name__)
        failed += not ok
    print("%d/%d passed" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)
