# Adversarial edge cases

Catalogue of hard cases built from POLICY.md and the brief. Every case is an automated synthetic test in
`edge_cases.py`: it writes a tiny data room in the real file format (no development data), runs a system and
checks the decision for the one hit against the decisions the policy allows.

    python3 system/tests/edge_cases.py                       # our system
    python3 system/tests/edge_cases.py system/run other/run  # side by side

* **Allowed** lists the decisions the policy permits. `REVIEW/SAME` means "must not clear": the test only
  forbids an unsafe clearance (cost 60).
* **UNSAFE** in the runner output = the system said `DIFFERENT_ENTITY` where the policy does not allow it.
* **Amb.** marks cases the policy text does not settle; their expectation is the safe one (never a clearance),
  with the reasoning in the notes below.

157 cases, 14 marked ambiguous.

## Customer resolution (principles 2-3)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| R01 | joint account: screened DOB picks the second holder (hit DOB fits them, not the first) | SAME |  |
| R02 | joint account, screened details fit both holders, they lead to different decisions -> REVIEW | REVIEW |  |
| R03 | duplicate CRM record (same phone + same DOB) adds Kenya: location cannot clear | REVIEW/SAME |  |
| R04 | transitive chain: phone+DOB link to record 2, doc-number link from record 2 to record 3 (Kenya) | REVIEW/SAME |  |
| R05 | shared phone, different DOB (family member in Kenya) does not merge: location clears | DIFFERENT |  |
| R06 | twin: same DOB, different phone, Kenyan nationality, not merged: location clears | DIFFERENT |  |
| R07 | same document number but on a REJECTED check does not merge: location clears | DIFFERENT |  |
| R08 | no link, three namesakes: screened DOB picks one, hit DOB matches it | SAME |  |
| R09 | no link, two namesakes: screened country picks the Kenyan one | SAME |  |
| R10 | no link, no matching customer record; screened DOB contradicts hit | DIFFERENT/REVIEW | yes |
| R11 | email link with different case and surrounding spaces | SAME |  |
| R12 | KYC note filed under an upper-case email still belongs to the customer (verified DOB 1985 beats record 1980) | REVIEW/SAME |  |
| R13 | closed account still links the customer | SAME |  |
| R14 | login-handle link | SAME |  |
| R15 | account_ref that exists nowhere: fall back to a search on the screened details | SAME |  |
| R16 | no link; screened nickname 'Jim' finds record 'James Brown' (variant list) | SAME |  |
| R17 | two people fit, both lead to the same clearance -> that decision, record AMBIGUOUS | DIFFERENT |  |

## Verified identity checks (principle 4)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| K01 | two approved checks on the same date with different DOBs; hit fits one of them | REVIEW/SAME | yes |
| K02 | latest approved check gives a year-only DOB that agrees with the hit; an older full DOB would contradict | REVIEW/SAME |  |
| K03 | approved check, then a later rejected check with another DOB: the approved one counts | SAME |  |
| K04 | latest check expired with another name: the earlier approved name counts | SAME |  |
| K05 | note-only check, ISO DOB (record DOB 1980 is stale) | REVIEW/SAME |  |
| K06 | note-only check, '12th April 1985' | REVIEW/SAME |  |
| K07 | note-only check, 'April 12th, 1985' | REVIEW/SAME |  |
| K08 | note-only check, '12.04.1985' dotted | REVIEW/SAME |  |
| K09 | note-only check, two-digit year '12/04/85' | REVIEW/SAME | yes |
| K10 | note-only check written month-first (check date 06/25/2024 shows the order), DOB 04/12/1985 | REVIEW/SAME | yes |
| K11 | note-only check, DOB stated after the date ('1985-04-12 is the date of birth on the passport') | REVIEW/SAME |  |
| K12 | note-only check with the check date written in words before an ISO DOB | REVIEW/SAME |  |
| K13 | note says the check FAILED: its DOB is not evidence; record DOB 1980 contradicts hit 1985 | DIFFERENT |  |
| K14 | KYC table check newer than a note check: the table check wins | SAME |  |
| K15 | note check newer than the KYC table check: the note wins (verified DOB 1985 fits hit) | REVIEW/SAME |  |
| K16 | verified name written 'SMITH, John' | SAME |  |
| K17 | latest approved check has no DOB: other DOBs still count, no contradiction | REVIEW/SAME |  |
| K18 | note marked pending, later than the approved table check: not an approved check | SAME |  |
| K19 | support note 'details verified on the phone' is not an identity check | SAME |  |

## Names (principle 8)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| N01 | verified 'Mohammed Ali Khan' vs hit 'Muhammad Ali Khan': variant list transliteration (agree, must not clear on name) | REVIEW/SAME |  |
| N02 | verified 'Abdulsalam Bello' vs hit 'Abdul Salam Bello': joined vs split part (agree, must not clear on name) | REVIEW/SAME |  |
| N03 | verified 'Jonas Peters' vs hit 'Jonas Petrs': one edit on a 6-letter part (agree, must not clear on name) | REVIEW/SAME |  |
| N04 | verified 'Anna Kowalski' vs hit 'Anna Kowalksi': transposition on an 8-letter part (2 edits allowed) (agree, must not clear on name) | REVIEW/SAME |  |
| N05 | transposition in a 5-letter part (2 edits > 1): only one part matches -> name mismatch clears | DIFFERENT |  |
| N06 | parts under 4 letters must be identical ('Li' vs 'Le'): name mismatch clears | DIFFERENT |  |
| N07 | verified 'J. Robert Smith' vs hit 'Robert Smith': initial is not a part (agree, must not clear on name) | REVIEW/SAME |  |
| N08 | verified 'John Smith' vs hit 'Smith, John (Johnny)': brackets ignored (agree, must not clear on name) | REVIEW/SAME |  |
| N09 | verified 'Ludwig van der Berg' vs hit 'Ludwig Berg': particles: every part of the shorter name matches (agree, must not clear on name) | REVIEW/SAME |  |
| N10 | verified 'Anna-Maria Lopez-Garcia' vs hit 'Anna Maria Lopez Garcia': hyphenated parts (agree, must not clear on name) | REVIEW/SAME |  |
| N11 | verified 'Juan Carlos Garcia Lopez' vs hit 'GARCIA LOPEZ, Juan Carlos': Spanish surname order (agree, must not clear on name) | REVIEW/SAME |  |
| N12 | verified 'Ivan Petrovich Sidorov' vs hit 'Sidorov, Ivan': Russian patronymic dropped on the hit (agree, must not clear on name) | REVIEW/SAME |  |
| N13 | verified 'Khalid bin Salman Al-Rashid' vs hit 'Khalid Al Rashid': Arabic bin / Al- particle (agree, must not clear on name) | REVIEW/SAME |  |
| N14 | verified 'Wang Xiaoming' vs hit 'Xiaoming Wang': Chinese order swapped (agree, must not clear on name) | REVIEW/SAME |  |
| N15 | verified 'José Müller' vs hit 'Jose Muller': diacritics (agree, must not clear on name) | REVIEW/SAME |  |
| N16 | verified 'Işık Yılmaz' vs hit 'Isik Yilmaz': Turkish dotless i (agree, must not clear on name) | REVIEW/SAME |  |
| N17 | verified 'Johann Strauß' vs hit 'Johann Strauss': German sharp s (agree, must not clear on name) | REVIEW/SAME |  |
| N18 | verified 'Sean O'Brien' vs hit 'Sean OBrien': apostrophe (agree, must not clear on name) | REVIEW/SAME |  |
| N19 | verified 'Аnna Smith' vs hit 'Anna Smith': Cyrillic look-alike A in the verified name (agree, must not clear on name) | REVIEW/SAME |  |
| N20 | mononym customer (one real part) cannot be cleared or confirmed on name | REVIEW |  |
| N21 | placeholders in the verified name leave one real part: no name decision | REVIEW |  |
| N22 | verified 'James Brown' vs hit 'Jim Brown': nickname in the variant list (agree, must not clear on name) | REVIEW/SAME |  |
| N23 | nickname NOT in the variant list ('Bobby' vs verified 'Robert'): only surname matches -> clears | DIFFERENT |  |
| N24 | alias-only match | REVIEW/SAME |  |
| N25 | hit's single-part alias agrees with the customer's name | REVIEW/SAME |  |
| N26 | maiden name: record and hit 'Mary Jones', latest verified 'Mary Smith' -> verified name mismatch | DIFFERENT |  |
| N27 | verified 'Aleksandr Volkov' vs hit 'Alexander Volkov': transliteration in the variant list (agree, must not clear on name) | REVIEW/SAME |  |
| N28 | verified 'Nguyễn Văn An' vs hit 'Nguyen Van An': Vietnamese diacritics, short parts identical (agree, must not clear on name) | REVIEW/SAME |  |
| N29 | verified 'Siobhán Ní Bhriain' vs hit 'Siobhan Ni Bhriain': Irish fada (agree, must not clear on name) | REVIEW/SAME |  |
| N30 | verified 'Mary-Kate O'Neill-Smith' vs hit 'Mary Kate Oneill Smith': hyphens and apostrophes together (agree, must not clear on name) | REVIEW/SAME |  |
| N31 | verified name in ALL CAPS with extra middle names vs short hit | REVIEW/SAME |  |
| N32 | screened name is a typo of the record, verified name agrees with hit | SAME |  |
| N33 | verified name written in Cyrillic ('Иван Петров') vs Latin hit 'Ivan Petrov': cannot be compared, never clear on it | REVIEW/SAME |  |
| N34 | Icelandic thorn/eth ('Þór Guðmundsson' vs 'Thor Gudmundsson') | REVIEW/SAME |  |

## Companies (principles 6-8)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| N40 | 'Acme Trading Ltd' vs 'ACME TRADING LIMITED' | REVIEW/SAME |  |
| N41 | 'The Acme Group plc' vs 'Acme Group' | REVIEW/SAME |  |
| N42 | 'Banco Sol S.A.' vs 'Banco Sol SA' | REVIEW/SAME |  |
| N43 | company names share only a legal form ('Northwind Ltd' vs 'Southwind Holdings Ltd') | DIFFERENT |  |
| N44 | trading-as name: customer 'Acme Ltd t/a Blue Harbour Cafe' vs hit 'Blue Harbour Cafe' | REVIEW/SAME | yes |
| N45 | company incorporated after the hit's incorporation date in dobs -> DOB mismatch | DIFFERENT |  |
| N46 | company: 'founded in 1990' in notes is NOT an incorporation date | REVIEW/SAME |  |
| N47 | company 'GmbH & Co. KG' forms | REVIEW/SAME |  |

## Dates, ages, dated reports, death (principles 5-7)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| T01 | year-only hit vs full customer DOB agree | SAME |  |
| T02 | every hit DOB more than a year away -> DOB mismatch | DIFFERENT |  |
| T03 | one of two hit DOBs agrees -> no clearance | REVIEW/SAME |  |
| T04 | hit DOB is a range '1979-1981' | REVIEW/SAME | yes |
| T05 | hit DOB 'circa 1980' | REVIEW/SAME | yes |
| T06 | aged 45 in March 2019 -> 1973/1974; customer 1974-12-01 agrees | SAME |  |
| T07 | aged 45 in March 2019; customer 1975 is within one year -> no clearance | REVIEW/SAME |  |
| T08 | aged 45 in March 2019; customer 1976 is >1 year outside -> DOB mismatch | DIFFERENT |  |
| T09 | aged 45 in March 2019; customer 1972 is within one year of 1973 -> no clearance | REVIEW/SAME |  |
| T10 | two inconsistent ages in the first paragraph; one agrees -> no clearance | REVIEW/SAME |  |
| T11 | 29 February both sides | SAME |  |
| T12 | same year, different month -> mismatch | DIFFERENT |  |
| T13 | same year and month, different day -> mismatch | DIFFERENT |  |
| T14 | hit gives year and month only ('May 1980'); customer 1980-05-17 agrees | SAME |  |
| T15 | exactly 16 on the earliest report date -> not too young | REVIEW/SAME |  |
| T16 | one day short of 16 on the earliest report date -> temporal impossibility | DIFFERENT |  |
| T17 | report before the customer was born | DIFFERENT |  |
| T18 | reports out of order: the earliest one decides (customer 10 then) | DIFFERENT |  |
| T19 | lower-case 'according to' line is not a dated report | REVIEW/SAME |  |
| T20 | dated-report form embedded mid-line is not a dated report | REVIEW/SAME | yes |
| T21 | company incorporated on the report date (not after) | REVIEW/SAME |  |
| T22 | company incorporated the day after the earliest report | DIFFERENT |  |
| T23 | deceased_date after screening -> not deceased | SAME |  |
| T24 | deceased_date before screening -> DECEASED | DIFFERENT |  |
| T25 | a relative's death in the notes is not the hit's death | SAME |  |
| T26 | deceased_date equal to the screening date -> not before | REVIEW/SAME |  |
| T27 | dobs empty; 'born on 3 March 1980' in the first paragraph | SAME |  |
| T28 | birth sentence only in the second paragraph does not count; no other DOB | REVIEW/SAME |  |
| T29 | dobs field wins over a different year in the notes | SAME |  |
| T30 | deceased_date in provider slash format before screening | DIFFERENT |  |

## Search results (principle 5)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| S01 | namesake: listing phrase right, country wrong -> ignored | REVIEW/SAME |  |
| S02 | namesake: country right, listing phrase wrong -> ignored | REVIEW/SAME |  |
| S03 | about the hit (phrase + country + age) -> contradicts customer -> DOB mismatch | DIFFERENT |  |
| S04 | two results about the hit with different ages, one agrees -> no clearance | REVIEW/SAME |  |
| S05 | hit has a DOB in notes: search results must not be used | SAME |  |
| S06 | primary category Sanctions: 'a sanctioned individual' phrase counts, PEP phrase does not | DIFFERENT |  |
| S07 | other category -> 'named on a watchlist' | DIFFERENT |  |

## Countries (principles 5-6)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| C01 | customer United Kingdom/GB vs hit ['Great Britain']: Great Britain = United Kingdom (must not clear on location) | REVIEW/SAME |  |
| C02 | customer United Kingdom/GB vs hit ['England']: England is part of the United Kingdom (must not clear on location) | REVIEW/SAME | yes |
| C03 | customer United Kingdom/GB vs hit ['Northern Ireland']: Northern Ireland is part of the United Kingdom (must not clear on location) | REVIEW/SAME | yes |
| C04 | Hong Kong is its own territory: customer China only vs hit Hong Kong only -> location clears | DIFFERENT |  |
| C05 | territory: Puerto Rico vs United States -> own country, location clears | DIFFERENT |  |
| C06 | customer Côte d'Ivoire/CI vs hit ['Ivory Coast']: Ivory Coast = Côte d'Ivoire (must not clear on location) | REVIEW/SAME |  |
| C07 | customer Czechia/CZ vs hit ['Czech Republic']: Czechia = Czech Republic (must not clear on location) | REVIEW/SAME |  |
| C08 | customer Myanmar/MM vs hit ['Burma']: Burma = Myanmar (must not clear on location) | REVIEW/SAME |  |
| C09 | customer Eswatini/SZ vs hit ['Swaziland']: Swaziland = Eswatini (must not clear on location) | REVIEW/SAME |  |
| C10 | customer Nigerian/NG vs hit ['Nigeria']: demonym (must not clear on location) | REVIEW/SAME |  |
| C11 | customer NGA/NGA vs hit ['Nigeria']: ISO3 code (must not clear on location) | REVIEW/SAME |  |
| C12 | dual picture: nationality UK, residence Kenya; hit Kenya | REVIEW/SAME |  |
| C13 | former residence in a support note ('lived in Kenya until 2015') | REVIEW/SAME |  |
| C14 | 'International' / 'Europe' are not countries: no location clearance | REVIEW/SAME |  |
| C15 | hit address last part 'Nairobi, Kenya' vs customer Kenya | REVIEW/SAME |  |
| C16 | hit place of birth only, Kenya, customer Kenya | REVIEW/SAME |  |
| C17 | approved document country Kenya counts | REVIEW/SAME |  |
| C18 | EXPIRED document country does not count -> location clears | DIFFERENT |  |
| C19 | hit nationality given as a demonym 'Kenyan' | REVIEW/SAME |  |
| C20 | customer USA/U.S. vs hit ['United States of America']: USA / U.S. (must not clear on location) | REVIEW/SAME |  |
| C21 | customer South Korea/KR vs hit ['Republic of Korea']: Republic of Korea (must not clear on location) | REVIEW/SAME |  |
| C22 | customer DR Congo/CD vs hit ['Congo']: bare 'Congo' is ambiguous between two countries (must not clear on location) | REVIEW/SAME | yes |
| C23 | customer Kosovo/XK vs hit ['Kosovo']: XK code (must not clear on location) | REVIEW/SAME |  |
| C24 | customer Türkiye/TR vs hit ['Turkey']: Türkiye = Turkey (must not clear on location) | REVIEW/SAME |  |
| C25 | customer Holland/NL vs hit ['Netherlands']: Holland = Netherlands (must not clear on location) | REVIEW/SAME |  |
| C26 | customer United Arab Emirates/AE vs hit ['UAE']: UAE (must not clear on location) | REVIEW/SAME |  |
| C27 | customer Russian Federation/RU vs hit ['Russia']: Russian Federation (must not clear on location) | REVIEW/SAME |  |
| C28 | customer Korea/KR vs hit ['South Korea']: bare 'Korea' on the customer side (must not clear on location) | REVIEW/SAME | yes |
| C29 | plain disjoint countries -> location clears | DIFFERENT |  |
| C30 | hit country an unrecognised value ('Freedonia') -> no clearance | REVIEW/SAME |  |

## Hit fields and entity type (principle 6)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| H01 | hit entity type missing: no type contradiction | REVIEW/SAME |  |
| H02 | person vs company -> entity type mismatch | DIFFERENT |  |
| H03 | customer company, hit 'Organisation' (a company by another word) | REVIEW/SAME | yes |
| H04 | name + DOB agree but countries disjoint -> REVIEW | REVIEW |  |
| H05 | hit dobs entry is a placeholder ('UNKNOWN') | REVIEW/SAME |  |

## Placeholders (principle 8)

| ID | Case | Allowed | Amb. |
|---|---|---|---|
| P01 | record 'N/A Smith', verified 'UNKNOWN SMITH': fewer than two real parts | REVIEW |  |
| P02 | customer DOB '-' and no check: no DOB clearance | REVIEW/SAME |  |
| P03 | customer DOB '0000-00-00': no DOB clearance | REVIEW/SAME |  |
| P04 | customer nationality 'UNKNOWN', residence '?': no customer country, no location clearance | REVIEW/SAME |  |
| P05 | two records share placeholder phone '0000000000' and DOB; second is Kenyan (policy text says merge) | REVIEW/SAME | yes |
| P06 | verified name 'XXX XXX': no name decision | REVIEW/SAME |  |
| P07 | screened name 'TEST' only, no link | REVIEW/SAME |  |

## Notes on ambiguous cases (safe expectation chosen)

* **R10** No customer record fits and only the screened DOB contradicts the hit. The policy resolves the customer
  first; whether the screened details alone may clear is not stated. Either REVIEW or a DOB clearance is accepted.
* **K01** Two approved checks on the same day disagree on the DOB: "the most recent approved check" is not unique.
  Never clear on one of them.
* **K09** Two-digit years (`12/04/85`): read as 1985, day first like the bank's other slash dates.
* **K10** A note whose own dates show month-first order (`06/25/2024`) is read month-first.
* **T04 / T05** A DOB range or "circa 1980" in `dobs`: never treated as a contradiction.
* **T20** The dated-report form must be a whole line ("exactly the English lines"); mid-line it is not counted,
  so it cannot clear.
* **N44** Trading-as names: the policy does not say whether a t/a name is a name of the company. Never clear.
* **H03** "Organisation" for a company: not treated as a type contradiction.
* **C02 / C03** England / Northern Ireland are parts of the United Kingdom, not territories: never clear.
* **C22 / C28** Bare "Congo" or "Korea" fits two countries: treated as unknown (blocks a location clearance).
* **P05** A placeholder-looking phone (`0000000000`) shared with the same full DOB: the policy text merges on
  phone + full DOB with no exception, which here also keeps the second record's country in the picture.

## Further ideas not yet automated

* Joint account where one holder is a company and the other a person.
* Approved KYC note and KYC-table check on the same date with different names.
* A DOB given as an age only in a KYC note ("aged 40 at verification").
* Hit `dobs` with both a full date and a different year-only value from another source.
* Hits whose aliases contain only initials ("J. S.").
* A hit `addresses` entry whose last part is a city, not a country ("Paris").
* Screened city in the address but not in the city field.
* Report lines in a non-English language with the same punctuation.
* `deceased_date` given only as a year equal to the screening year.
* Name parts that collide after folding (e.g. `Lüdtke` vs `Ludtke` vs `Luedtke`, umlaut written as `ue`).
