"""Helper for paraphrase_check.py: writes rewritten copies of a data folder (p1: KYC notes + age phrases, p2: also residence notes, search snippets, age sentences)."""
import json, random, re, sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.environ['PARA_SRC']; WORK = os.environ['PARA_WORK']
os.makedirs(WORK + '/p1', exist_ok=True)
for f in os.listdir(SRC):
    if f not in ('notes.jsonl', 'hits.jsonl') and not os.path.exists(WORK + '/p1/' + f):
        os.symlink(os.path.join(SRC, f), WORK + '/p1/' + f)
import screen as S
rng = random.Random(7)
MN = ["January","February","March","April","May","June","July","August","September","October","November","December"]
def fmt(d, k):
    y,m,dd = d
    if not (m and dd): return S.fmt_date(d)
    return [f"{y:04d}-{m:02d}-{dd:02d}", f"{dd:02d}/{m:02d}/{y}", f"{dd} {MN[m-1]} {y}", f"{MN[m-1]} {dd}, {y}", f"{dd} {MN[m-1][:3]} {y}"][k]
out = open(WORK + '/p1/notes.jsonl','w')
for l in open(SRC + '/notes.jsonl'):
    n = json.loads(l)
    if n['channel']=='kyc':
        k = S.parse_kyc_note(n)
        if k and k['name'] and k['dob']:
            nm = k['name'] if rng.random()<0.7 else k['name'].title()
            doc = rng.choice(["passport","national ID card","driving licence","residence permit"])
            c = k['country'] or 'Unknown'
            dd = fmt(k['dob'], rng.randrange(5)); cd = fmt(k['date'], rng.randrange(5)) if k['date'] else n['created_at']
            t = rng.choice([
              f"Identity check passed for {nm}; date of birth {dd}; {doc} issued in {c}; checked {cd}.",
              f"On {cd} the {c} {doc} of {nm} (born {dd}) was successfully verified.",
              f"{nm} — DOB: {dd} — {doc} ({c}) approved by the provider on {cd}.",
              f"Verification complete on {cd}: applicant {nm}, birth date {dd}, document {doc} from {c}.",
            ])
            n['text'] = t
    out.write(json.dumps(n)+"\n")
out.close()
out = open(WORK + '/p1/hits.jsonl','w')
for l in open(SRC + '/hits.jsonl'):
    h = json.loads(l)
    if h.get('profile_notes'):
        p = h['profile_notes']
        p = re.sub(r"\baged (\d+)", r"then \1 years old", p)
        p = re.sub(r"\ba (\d+)-year-old", r"a \1 year old", p)
        h['profile_notes'] = p
    out.write(json.dumps(h, ensure_ascii=False)+"\n")
out.close()

MN = ["January","February","March","April","May","June","July","August","September","October","November","December"]
rng = random.Random(11)
MN = ["January","February","March","April","May","June","July","August","September","October","November","December"]
os.makedirs(WORK + '/p2', exist_ok=True)
src = SRC
for f in os.listdir(src):
    if f not in ('search_results.jsonl', 'hits.jsonl', 'notes.jsonl'):
        dst = WORK + '/p2/' + f
        if not os.path.exists(dst): os.symlink(os.path.join(src, f), dst)
# notes: reuse the kyc paraphrase from dev_p; reword residence notes
out = open(WORK + '/p2/notes.jsonl', 'w')
for l in open(WORK + '/p1/notes.jsonl'):
    n = json.loads(l)
    if n['channel'] != 'kyc':
        cs = S.note_countries(n)
        ys = re.findall(r'\b(19|20)\d{2}\b', n['text'])
        if len(cs) == 1:
            yy = re.findall(r'\b(?:19|20)\d{2}\b', n['text'])
            n['text'] = rng.choice(["Customer mentioned previously living in %s (%s).", "Address history shows a stay in %s, %s.", "Per the client, home and work were in %s during %s."]) % (cs[0], "-".join(yy) or "the past")
    out.write(json.dumps(n) + "\n")
out.close()
# search results: regenerate snippets from extracted facts
PH = list(S.CAT_PHRASE.values()) + ["named on a watchlist"]
out = open(WORK + '/p2/search_results.jsonl', 'w')
for l in open(src + '/search_results.jsonl'):
    s = json.loads(l); sn = s['snippet']
    ds = S.find_dates(sn); st = sn
    for a, b, d in sorted(ds, reverse=True): st = st[:a] + ' DATE ' + st[b:]
    ages = S.extract_age_loose(st); cs = S.CT.find_in_text(sn)
    ph = [p for p in PH if p in sn]
    name = s['title'].split(' - ')[0]
    if len(ages) == 1 and len(ds) == 1 and len(cs) == 1 and ds[0][2][1]:
        age = ages.pop(); y, m, _ = ds[0][2]; role = ph[0] if ph else rng.choice(["a bus driver", "a florist", "a chess coach"])
        s['snippet'] = rng.choice([
            "%s (%d), %s based in %s, appeared in coverage dated %s %d." % (name, age, role, cs[0], MN[m-1], y),
            "Coverage from %s %d: %s, aged %d, %s in %s." % (MN[m-1][:3], y, name, age, role, cs[0]),
            "In %s of %d the %d-year-old %s, %s from %s, was mentioned." % (MN[m-1], y, age, name, role, cs[0]),
        ])
    out.write(json.dumps(s, ensure_ascii=False) + "\n")
out.close()
# hits: regenerate first-paragraph age sentences
out = open(WORK + '/p2/hits.jsonl', 'w')
for l in open(WORK + '/p1/hits.jsonl'):
    h = json.loads(l)
    nd = S.hit_dobs_from_notes(h)
    if nd and nd[0][0] == 'age':
        fp = S.first_paragraph(h['profile_notes'])
        sent = nd[0][2]
        ds = S.find_dates(sent); st = sent
        for a, b, d in sorted(ds, reverse=True): st = st[:a] + ' DATE ' + st[b:]
        age = S.extract_age(st).pop(); y, m, _ = ds[0][2]
        name = h['name'] if ',' not in h['name'] else ' '.join(reversed([x.strip() for x in h['name'].split(',', 1)]))
        new = rng.choice(["%s was arrested in %s %d at the age of %d." % (name, MN[(m or 1)-1], y, age),
                          "In %s %d, %s, then %d years of age, was charged." % (MN[(m or 1)-1], y, name, age),
                          "%s (%d) was questioned by police in %s %d." % (name, age, MN[(m or 1)-1], y)])
        h['profile_notes'] = h['profile_notes'].replace(sent, new, 1)
    out.write(json.dumps(h, ensure_ascii=False) + "\n")
out.close()
