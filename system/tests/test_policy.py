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


def hit(hid, aid, name, etype="Individual", dobs=(), countries=(), notes=None, deceased=None, cats=("PEP",), aliases=(), pob=None, nationality=(), citizenship=(), addresses=()):
    return {"hit_id": hid, "alert_id": aid, "match_score": 100, "entity_type": etype, "name": name, "first_name": None,
            "middle_name": None, "last_name": None, "best_matching_name": None, "aliases": list(aliases), "gender": None,
            "dobs": list(dobs), "place_of_birth": pob, "life_status": None, "deceased_date": deceased, "nationality": list(nationality),
            "citizenship": list(citizenship), "countries": list(countries), "addresses": list(addresses), "identifiers": [], "categories": list(cats),
            "primary_category": None, "subcategories": [], "position_or_allegation": None, "details": {}, "relationships": [],
            "profile_notes": notes, "sources": [], "source_urls": []}


def alert(aid, name, hit_ids, dob=None, account=None, etype="Individual", country=None, login=None, email=None):
    return {"alert_id": aid, "screened_at": "2026-11-10", "customer": {"name": name, "entity_type": etype, "dob": dob,
            "country": country, "city": None}, "account_ref": account, "login_handle": login, "email": email, "hit_ids": hit_ids}


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


def acc(aid, cid, login=None):
    return {"account_id": aid, "customer_id": cid, "login_handle": login, "phone": None, "opened_at": "2020-01-01", "status": "active"}


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


BELONGS = {
    "DIFFERENT_ENTITY": {"TEMPORAL_IMPOSSIBILITY", "DOB_MISMATCH", "LOCATION_MISMATCH", "NAME_MISMATCH_VERIFIED", "ENTITY_TYPE_MISMATCH", "DECEASED"},
    "SAME_ENTITY": {"NAME_DOB_LOCATION_MATCH", "NAME_DOB_MATCH", "NAME_LOCATION_MATCH"},
    "REVIEW": {"INSUFFICIENT_DATA", "AMBIGUOUS_CUSTOMER_RECORD"},
}


def _code_ok(row):
    return row["reason_code"] in BELONGS.get(row["decision"], ())


@case
def entity_type_not_fired_when_both_individuals():
    # matching types are never a type clearance; name + DOB + country confirm as usual
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1984-07-07"])])
    x = r["H-000001"]
    return x["decision"] == "SAME_ENTITY" and x["reason_code"] != "ENTITY_TYPE_MISMATCH" and _code_ok(x)


@case
def missing_hit_entity_type_is_not_a_type_mismatch():
    # missing data never counts as a mismatch: a hit with no type cannot be cleared on type
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", etype=None, countries=["United Kingdom"], dobs=["1984-07-07"])])
    return r["H-000001"]["reason_code"] != "ENTITY_TYPE_MISMATCH" and r["H-000001"]["decision"] in ("SAME_ENTITY", "REVIEW")


@case
def death_after_screening_is_not_deceased():
    r = run_case([cust("CUS-000001", "Fiona Ward", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], deceased="2026-12-01")])
    return r["H-000001"]["reason_code"] != "DECEASED" and r["H-000001"]["decision"] == "REVIEW"


@case
def death_on_screening_day_is_not_deceased():
    # a death date equal to the screening date is not "before the customer was screened"
    r = run_case([cust("CUS-000001", "Fiona Ward", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], deceased="2026-11-10")])
    return r["H-000001"]["reason_code"] != "DECEASED" and r["H-000001"]["decision"] == "REVIEW"


@case
def missing_dob_is_never_a_dob_mismatch():
    ok = True
    # customer has no DOB, hit has one
    r = run_case([cust("CUS-000001", "Fiona Ward", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1984-07-07"])])
    ok &= r["H-000001"]["reason_code"] != "DOB_MISMATCH" and r["H-000001"]["decision"] == "REVIEW"
    # customer has a DOB, hit gives none
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"])])
    ok &= r["H-000001"]["reason_code"] != "DOB_MISMATCH" and r["H-000001"]["decision"] == "REVIEW"
    return ok


@case
def two_years_apart_is_dob_mismatch():
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1982"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "DOB_MISMATCH"


@case
def same_year_different_day_is_dob_mismatch():
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1984-07-19"])])
    return r["H-000001"]["reason_code"] == "DOB_MISMATCH"


@case
def name_mismatch_verified_fires_when_legal_name_disagrees():
    r = run_case([cust("CUS-000001", "Victor Hale", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Victor Hale", None)],
                 [alert("A-000001", "Victor Hale", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "NAME_MISMATCH_VERIFIED"


@case
def declared_name_alone_cannot_clear_on_name():
    # without a verified legal name, a disagreement between the record name and the hit is not NAME_MISMATCH_VERIFIED
    r = run_case([cust("CUS-000001", "Victor Hale", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Victor Hale", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "REVIEW" and r["H-000001"]["reason_code"] != "NAME_MISMATCH_VERIFIED"


@case
def location_mismatch_fires_when_name_and_dob_do_not_both_agree():
    # countries differ and there is no agreeing DOB, so location may clear
    r = run_case([cust("CUS-000001", "Fiona Ward", None, nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["Kenya"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "LOCATION_MISMATCH"


@case
def missing_country_is_never_a_location_mismatch():
    ok = True
    r = run_case([cust("CUS-000001", "Fiona Ward", None, nat=None, res=None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["Kenya"])])
    ok &= r["H-000001"]["reason_code"] != "LOCATION_MISMATCH" and r["H-000001"]["decision"] == "REVIEW"
    r = run_case([cust("CUS-000001", "Fiona Ward", None, nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona")])
    ok &= r["H-000001"]["reason_code"] != "LOCATION_MISMATCH" and r["H-000001"]["decision"] == "REVIEW"
    return ok


@case
def international_and_europe_are_not_countries():
    # "International" and "Europe" are not countries, so they cannot support a location clearance
    r = run_case([cust("CUS-000001", "Fiona Ward", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["International", "Europe"])])
    return r["H-000001"]["reason_code"] != "LOCATION_MISMATCH" and r["H-000001"]["decision"] == "REVIEW"


@case
def place_of_birth_counts_as_a_hit_country():
    # a hit country may come only from place of birth; that overlap blocks a location clearance
    r = run_case([cust("CUS-000001", "Fiona Ward", None, nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=(), pob="London, United Kingdom")])
    return r["H-000001"]["decision"] != "DIFFERENT_ENTITY"


@case
def precedence_entity_type_over_other_clearances():
    # person vs company, plus a death date, a young-customer report, a DOB clash and a country clash: type wins
    r = run_case([cust("CUS-000001", "Nora Blake", "2004-02-02", nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Blake Holdings Ltd", etype="Company", countries=["Kenya"], dobs=["1960"],
                      deceased="2020-01-01", notes="According to bbc.co.uk; June 1, 2011: Nora Blake was charged.")])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "ENTITY_TYPE_MISMATCH"


@case
def precedence_deceased_over_other_clearances():
    r = run_case([cust("CUS-000001", "Nora Blake", "2004-02-02", nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001")], [kyc("KYC-000001", "APP-000001", "Nora Blake", "2004-02-02")],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["Kenya"], dobs=["1960"], deceased="2020-01-01",
                      notes="According to bbc.co.uk; June 1, 2011: Wei Chen was charged.")])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "DECEASED"


@case
def precedence_temporal_over_dob_name_and_location():
    r = run_case([cust("CUS-000001", "Nora Blake", "2004-02-02", nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001")], [kyc("KYC-000001", "APP-000001", "Nora Blake", "2004-02-02")],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["Kenya"], dobs=["1960"],
                      notes="According to bbc.co.uk; June 1, 2011: Wei Chen was charged.")])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "TEMPORAL_IMPOSSIBILITY"


@case
def precedence_dob_over_name_and_location():
    r = run_case([cust("CUS-000001", "Nora Blake", "2004-02-02", nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001")], [kyc("KYC-000001", "APP-000001", "Nora Blake", "2004-02-02")],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["Kenya"], dobs=["1960"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "DOB_MISMATCH"


@case
def precedence_name_over_location():
    r = run_case([cust("CUS-000001", "Nora Blake", None, nat="United Kingdom", res="GB")], [acc("ACC-000001", "CUS-000001")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001")], [kyc("KYC-000001", "APP-000001", "Nora Blake", None)],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Chen, Wei", countries=["Kenya"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "NAME_MISMATCH_VERIFIED"


@case
def name_dob_location_match_reason_code():
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1984-07-07"])])
    x = r["H-000001"]
    return x["decision"] == "SAME_ENTITY" and x["reason_code"] == "NAME_DOB_LOCATION_MATCH" and x["customer_record_id"] == "CUS-000001"


@case
def name_dob_match_reason_code_when_no_shared_country():
    # name and DOB agree; the hit gives no country, so the confirmation is NAME_DOB_MATCH
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", dobs=["1984-07-07"])])
    return r["H-000001"]["decision"] == "SAME_ENTITY" and r["H-000001"]["reason_code"] == "NAME_DOB_MATCH"


@case
def company_name_and_country_confirm():
    r = run_case([cust("CUS-000001", "Northwind Trading Ltd", "2010-03-01", etype="Company")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Northwind Trading Ltd", ["H-000001"], account="ACC-000001", etype="Company")],
                 [hit("H-000001", "A-000001", "Northwind Trading Limited", etype="Company", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "SAME_ENTITY" and r["H-000001"]["reason_code"] == "NAME_LOCATION_MATCH"


@case
def name_agreement_without_dob_is_review():
    # a person is confirmed only when name and date of birth both agree
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "REVIEW" and r["H-000001"]["reason_code"] == "INSUFFICIENT_DATA"


@case
def insufficient_data_when_nothing_settles():
    r = run_case([cust("CUS-000001", "Fiona Ward", None)], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"])])
    x = r["H-000001"]
    return x["decision"] == "REVIEW" and x["reason_code"] == "INSUFFICIENT_DATA" and _code_ok(x)


@case
def pending_check_is_ignored():
    # a later pending check's name and DOB must not be used
    r = run_case([cust("CUS-000001", "Owen Park", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Simon Green", "1990-01-01", result="pending", date="2025-01-01")],
                 [alert("A-000001", "Owen Park", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Park, Owen", countries=["United Kingdom"], dobs=["1960"])])
    return r["H-000001"]["decision"] == "REVIEW"


@case
def verified_legal_name_outranks_record_name():
    # the record name agrees with the hit, but the latest approved legal name does not -> name clearance
    r = run_case([cust("CUS-000001", "Victor Hale", None)], [acc("ACC-000001", "CUS-000001")], [onb("ACC-000001", "CUS-000001", "APP-000001")],
                 [kyc("KYC-000001", "APP-000001", "Robert Lang", None)],
                 [alert("A-000001", "Victor Hale", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Hale, Victor", countries=["United Kingdom"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "NAME_MISMATCH_VERIFIED"


@case
def login_handle_resolves_customer():
    r = run_case([cust("CUS-000001", "Owen Park", "1971-09-09")], [acc("ACC-000001", "CUS-000001", login="opark71")], [], [],
                 [alert("A-000001", "Owen Park", ["H-000001"], login="opark71")],
                 [hit("H-000001", "A-000001", "Park, Owen", countries=["United Kingdom"], dobs=["1971-09-09"])])
    x = r["H-000001"]
    return x["customer_record_id"] == "CUS-000001" and x["decision"] == "SAME_ENTITY"


@case
def email_link_resolves_customer():
    r = run_case([cust("CUS-000001", "Owen Park", "1971-09-09", email="owen.park@x.example")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Owen Park", ["H-000001"], email="owen.park@x.example")],
                 [hit("H-000001", "A-000001", "Park, Owen", countries=["United Kingdom"], dobs=["1971-09-09"])])
    x = r["H-000001"]
    return x["customer_record_id"] == "CUS-000001" and x["decision"] == "SAME_ENTITY"


@case
def phone_and_full_dob_merges_records():
    # same phone and the same full DOB: one person, so Kenya counts and blocks a location clearance
    cs = [cust("CUS-000001", "Helen Grant", "1978-04-12", phone="+44 7000111222"),
          cust("CUS-000002", "Helen Grant", "1978-04-12", nat="Kenya", res="KE", phone="+44 7000111222")]
    r = run_case(cs, [acc("ACC-000001", "CUS-000001"), acc("ACC-000002", "CUS-000002")], [], [],
                 [alert("A-000001", "Helen Grant", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Grant, Helen", countries=["Kenya"])])
    return r["H-000001"]["decision"] != "DIFFERENT_ENTITY"


@case
def year_only_dob_plus_phone_does_not_merge():
    # policy merges on a phone and a full date of birth; a year-only DOB is not enough
    cs = [cust("CUS-000001", "Helen Grant", "1978-04-12", phone="+44 7000111222"),
          cust("CUS-000002", "Helen Grant", "1978", nat="Kenya", res="KE", phone="+44 7000111222")]
    r = run_case(cs, [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Helen Grant", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Grant, Helen", countries=["Kenya"])])
    return r["H-000001"]["decision"] == "DIFFERENT_ENTITY" and r["H-000001"]["reason_code"] == "LOCATION_MISMATCH"


@case
def unresolved_customer_record_id_is_null_and_not_cleared():
    # no record in the bank's systems; even a screened DOB that would contradict the hit cannot clear it
    r = run_case([], [], [], [],
                 [alert("A-000001", "Zelda Quill", ["H-000001"], dob="1991-01-01")],
                 [hit("H-000001", "A-000001", "Quill, Zelda", countries=["United Kingdom"], dobs=["1960"])])
    x = r["H-000001"]
    return x["customer_record_id"] is None and x["decision"] == "REVIEW" and x["reason_code"] == "INSUFFICIENT_DATA"


@case
def unresolved_type_mismatch_may_clear_with_null_id():
    # the one exception: a person vs a company can still be cleared from screened type alone
    r = run_case([], [], [], [],
                 [alert("A-000001", "Zelda Quill", ["H-000001"])],
                 [hit("H-000001", "A-000001", "Zelda Quill Ltd", etype="Company", countries=["United Kingdom"])])
    x = r["H-000001"]
    return x["customer_record_id"] is None and x["decision"] == "DIFFERENT_ENTITY" and x["reason_code"] == "ENTITY_TYPE_MISMATCH"


@case
def ambiguous_same_decision_keeps_decision_and_ambiguous_id():
    # two people fit and each would be confirmed the same way: give that decision, but customer_record_id is AMBIGUOUS
    cs = [cust("CUS-000001", "Carla Nunez", "1982-05-05", phone="+44 1"),
          cust("CUS-000002", "Carla Nunez", "1982-05-05", phone="+44 2")]
    r = run_case(cs, [], [], [],
                 [alert("A-000001", "Carla Nunez", ["H-000001"])],
                 [hit("H-000001", "A-000001", "Nunez, Carla", countries=["United Kingdom"], dobs=["1982-05-05"])])
    x = r["H-000001"]
    return x["customer_record_id"] == "AMBIGUOUS" and x["decision"] == "SAME_ENTITY" and x["reason_code"] != "AMBIGUOUS_CUSTOMER_RECORD" and _code_ok(x)


@case
def output_reason_code_belongs_and_evidence_ids_exist():
    known = {"CUS-000001", "ACC-000001", "APP-000001", "KYC-000001", "A-000001", "H-000001"}
    r = run_case([cust("CUS-000001", "Fiona Ward", "1984-07-07")], [acc("ACC-000001", "CUS-000001")],
                 [onb("ACC-000001", "CUS-000001", "APP-000001")], [kyc("KYC-000001", "APP-000001", "Fiona Ward", "1984-07-07")],
                 [alert("A-000001", "Fiona Ward", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Ward, Fiona", countries=["United Kingdom"], dobs=["1984-07-07"])])
    x = r["H-000001"]
    ev_ok = all(e in known for e in x["evidence"])
    cid_ok = x["customer_record_id"] == "CUS-000001"
    return ev_ok and cid_ok and _code_ok(x) and x["decision"] == "SAME_ENTITY" and isinstance(x["reason"], str) and len(x["reason"]) > 0


@case
def company_incorporated_before_report_is_not_temporal():
    r = run_case([cust("CUS-000001", "Northwind Trading Ltd", "2008-01-01", etype="Company")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Northwind Trading Ltd", ["H-000001"], account="ACC-000001", etype="Company")],
                 [hit("H-000001", "A-000001", "Northwind Trading Limited", etype="Company", countries=["United Kingdom"],
                      notes="According to fca.org.uk; March 3, 2015: Northwind Trading was fined.")])
    return r["H-000001"]["reason_code"] != "TEMPORAL_IMPOSSIBILITY" and r["H-000001"]["decision"] == "SAME_ENTITY"


@case
def informal_report_wording_is_not_a_dated_report():
    # only the "According to …; Date: …" lines count; other wordings must not create a temporal clearance
    r = run_case([cust("CUS-000001", "Nora Blake", "2004-02-02")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Blake, Nora", countries=["United Kingdom"],
                      notes="On June 1, 2011, Nora Blake was charged.")])
    return r["H-000001"]["reason_code"] != "TEMPORAL_IMPOSSIBILITY" and r["H-000001"]["decision"] == "REVIEW"


@case
def no_dated_report_is_not_temporal():
    r = run_case([cust("CUS-000001", "Nora Blake", "2020-02-02")], [acc("ACC-000001", "CUS-000001")], [], [],
                 [alert("A-000001", "Nora Blake", ["H-000001"], account="ACC-000001")],
                 [hit("H-000001", "A-000001", "Blake, Nora", countries=["United Kingdom"])])
    return r["H-000001"]["reason_code"] != "TEMPORAL_IMPOSSIBILITY" and r["H-000001"]["decision"] == "REVIEW"



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
