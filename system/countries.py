"""Country gazetteer: canonical name -> (ISO2, aliases incl. demonyms). Stdlib only."""
_RAW = """
Afghanistan|AF|Afghan
Albania|AL|Albanian
Algeria|DZ|Algerian
Andorra|AD|Andorran
Angola|AO|Angolan
Antigua and Barbuda|AG|Antiguan
Argentina|AR|Argentine;Argentinian
Armenia|AM|Armenian
Australia|AU|Australian
Austria|AT|Austrian
Azerbaijan|AZ|Azerbaijani;Azeri
Bahamas|BS|Bahamian;The Bahamas
Bahrain|BH|Bahraini
Bangladesh|BD|Bangladeshi
Barbados|BB|Barbadian
Belarus|BY|Belarusian
Belgium|BE|Belgian
Belize|BZ|Belizean
Benin|BJ|Beninese
Bhutan|BT|Bhutanese
Bolivia|BO|Bolivian
Bosnia and Herzegovina|BA|Bosnian;Bosnia
Botswana|BW|Botswanan;Motswana
Brazil|BR|Brazilian;Brasil
Brunei|BN|Bruneian;Brunei Darussalam
Bulgaria|BG|Bulgarian
Burkina Faso|BF|Burkinabe
Burundi|BI|Burundian
Cambodia|KH|Cambodian
Cameroon|CM|Cameroonian
Canada|CA|Canadian
Cape Verde|CV|Cape Verdean;Cabo Verde
Central African Republic|CF|Central African
Chad|TD|Chadian
Chile|CL|Chilean
China|CN|Chinese;People's Republic of China;PRC
Colombia|CO|Colombian
Comoros|KM|Comoran
Congo|CG|Congolese;Republic of the Congo
Democratic Republic of the Congo|CD|DR Congo;DRC;Congo-Kinshasa
Costa Rica|CR|Costa Rican
Cote d'Ivoire|CI|Ivorian;Ivory Coast;Côte d'Ivoire;Cote D'Ivoire
Croatia|HR|Croatian
Cuba|CU|Cuban
Cyprus|CY|Cypriot
Czech Republic|CZ|Czech;Czechia
Denmark|DK|Danish
Djibouti|DJ|Djiboutian
Dominica|DM|Dominican (Dominica)
Dominican Republic|DO|Dominican
Ecuador|EC|Ecuadorian;Ecuadorean
Egypt|EG|Egyptian
El Salvador|SV|Salvadoran
Equatorial Guinea|GQ|Equatoguinean
Eritrea|ER|Eritrean
Estonia|EE|Estonian
Eswatini|SZ|Swazi;Swaziland
Ethiopia|ET|Ethiopian
Fiji|FJ|Fijian
Finland|FI|Finnish
France|FR|French
Gabon|GA|Gabonese
Gambia|GM|Gambian;The Gambia
Georgia|GE|Georgian
Germany|DE|German
Ghana|GH|Ghanaian
Greece|GR|Greek
Grenada|GD|Grenadian
Guatemala|GT|Guatemalan
Guinea|GN|Guinean
Guinea-Bissau|GW|Bissau-Guinean
Guyana|GY|Guyanese
Haiti|HT|Haitian
Honduras|HN|Honduran
Hong Kong|HK|Hong Konger;Hong Kong SAR;Hong Kong Special Administrative Region of China
Hungary|HU|Hungarian
Iceland|IS|Icelandic;Icelander
India|IN|Indian
Indonesia|ID|Indonesian
Iran|IR|Iranian;Islamic Republic of Iran
Iraq|IQ|Iraqi
Ireland|IE|Irish;Republic of Ireland
Israel|IL|Israeli
Italy|IT|Italian
Jamaica|JM|Jamaican
Japan|JP|Japanese
Jordan|JO|Jordanian
Kazakhstan|KZ|Kazakh;Kazakhstani
Kenya|KE|Kenyan
Kiribati|KI|I-Kiribati
North Korea|KP|North Korean;DPRK;Democratic People's Republic of Korea
South Korea|KR|South Korean;Korean;Republic of Korea;Korea
Kosovo|XK|Kosovar;Kosovan
Kuwait|KW|Kuwaiti
Kyrgyzstan|KG|Kyrgyz
Laos|LA|Lao;Laotian
Latvia|LV|Latvian
Lebanon|LB|Lebanese
Lesotho|LS|Basotho
Liberia|LR|Liberian
Libya|LY|Libyan
Liechtenstein|LI|Liechtensteiner
Lithuania|LT|Lithuanian
Luxembourg|LU|Luxembourgish;Luxembourger
Macao|MO|Macanese;Macau;Macao Special Administrative Region of China
Madagascar|MG|Malagasy
Malawi|MW|Malawian
Malaysia|MY|Malaysian
Maldives|MV|Maldivian
Mali|ML|Malian
Malta|MT|Maltese
Marshall Islands|MH|Marshallese
Mauritania|MR|Mauritanian
Mauritius|MU|Mauritian
Mexico|MX|Mexican
Micronesia|FM|Micronesian
Moldova|MD|Moldovan
Monaco|MC|Monegasque
Mongolia|MN|Mongolian
Montenegro|ME|Montenegrin
Morocco|MA|Moroccan
Mozambique|MZ|Mozambican
Myanmar|MM|Burmese;Burma
Namibia|NA|Namibian
Nauru|NR|Nauruan
Nepal|NP|Nepalese;Nepali
Netherlands|NL|Dutch;The Netherlands;Holland
New Zealand|NZ|New Zealander;Kiwi
Nicaragua|NI|Nicaraguan
Niger|NE|Nigerien
Nigeria|NG|Nigerian
North Macedonia|MK|Macedonian;Macedonia
Norway|NO|Norwegian
Oman|OM|Omani
Pakistan|PK|Pakistani
Palau|PW|Palauan
Palestine|PS|Palestinian;Palestina;State of Palestine;Palestinian Territories
Panama|PA|Panamanian
Papua New Guinea|PG|Papua New Guinean
Paraguay|PY|Paraguayan
Peru|PE|Peruvian
Philippines|PH|Filipino;Philippine
Poland|PL|Polish
Portugal|PT|Portuguese
Qatar|QA|Qatari
Romania|RO|Romanian
Russia|RU|Russian;Russian Federation
Rwanda|RW|Rwandan
Saint Kitts and Nevis|KN|Kittitian
Saint Lucia|LC|Saint Lucian
Saint Vincent and the Grenadines|VC|Vincentian
Samoa|WS|Samoan
San Marino|SM|Sammarinese
Sao Tome and Principe|ST|Santomean
Saudi Arabia|SA|Saudi;Saudi Arabian
Senegal|SN|Senegalese
Serbia|RS|Serbian
Seychelles|SC|Seychellois
Sierra Leone|SL|Sierra Leonean
Singapore|SG|Singaporean
Slovakia|SK|Slovak;Slovakian
Slovenia|SI|Slovenian;Slovene
Solomon Islands|SB|Solomon Islander
Somalia|SO|Somali
South Africa|ZA|South African
South Sudan|SS|South Sudanese
Spain|ES|Spanish;España
Sri Lanka|LK|Sri Lankan
Sudan|SD|Sudanese
Suriname|SR|Surinamese
Sweden|SE|Swedish
Switzerland|CH|Swiss
Syria|SY|Syrian;Syrian Arab Republic
Taiwan|TW|Taiwanese
Tajikistan|TJ|Tajik
Tanzania|TZ|Tanzanian
Thailand|TH|Thai
Timor-Leste|TL|Timorese;East Timor
Togo|TG|Togolese
Tonga|TO|Tongan
Trinidad and Tobago|TT|Trinidadian;Tobagonian
Tunisia|TN|Tunisian
Turkey|TR|Turkish;Türkiye;Turkiye
Turkmenistan|TM|Turkmen
Tuvalu|TV|Tuvaluan
Uganda|UG|Ugandan
Ukraine|UA|Ukrainian
United Arab Emirates|AE|Emirati;UAE
United Kingdom|GB|British;UK;Great Britain;England;Scotland;Wales;Northern Ireland;English;Scottish;Welsh;U.K.
United States|US|American;USA;United States of America;U.S.;U.S.A.
Uruguay|UY|Uruguayan
Uzbekistan|UZ|Uzbek
Vanuatu|VU|Ni-Vanuatu
Vatican City|VA|Holy See;Vatican
Venezuela|VE|Venezuelan
Vietnam|VN|Vietnamese;Viet Nam
Yemen|YE|Yemeni
Zambia|ZM|Zambian
Zimbabwe|ZW|Zimbabwean
Puerto Rico|PR|Puerto Rican
Northern Mariana Islands|MP|Northern Mariana Islander
Guam|GU|Guamanian
American Samoa|AS|American Samoan
US Virgin Islands|VI|United States Virgin Islands;U.S. Virgin Islands
British Virgin Islands|VG|BVI;Virgin Islands, British
Cayman Islands|KY|Caymanian
Bermuda|BM|Bermudian
Jersey|JE|Jerseyman
Guernsey|GG|Guernseyman
Isle of Man|IM|Manx
Gibraltar|GI|Gibraltarian
Greenland|GL|Greenlandic
Faroe Islands|FO|Faroese
Aruba|AW|Aruban
Curacao|CW|Curaçao
Anguilla|AI|Anguillan
Turks and Caicos Islands|TC|Turks and Caicos
Montserrat|MS|Montserratian
French Polynesia|PF|French Polynesian
New Caledonia|NC|New Caledonian
Western Sahara|EH|Sahrawi
"""
import re as _re, unicodedata as _ud

def _fold(s):
    s = _ud.normalize("NFKD", s)
    s = "".join(c for c in s if not _ud.combining(c))
    return _re.sub(r"\s+", " ", s.replace("’", "'")).strip().lower()

NAME2CANON = {}
ISO2CANON = {}
for _line in _RAW.strip().splitlines():
    _name, _iso, _al = _line.split("|")
    ISO2CANON[_iso] = _name
    NAME2CANON[_fold(_name)] = _name
    for _a in _al.split(";"):
        if _a:
            NAME2CANON[_fold(_a)] = _name
NOT_COUNTRIES = {"international", "europe", "global", "worldwide", "unknown", "none", "n/a", "na", "africa", "asia", "middle east", "eu", "european union"}


def canon(value):
    """Structured field value -> canonical country name or None."""
    if not value or not isinstance(value, str):
        return None
    v = _re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", value).strip()
    if not v:
        return None
    if v.upper() in ISO2CANON and len(v) == 2:
        return ISO2CANON[v.upper()]
    f = _fold(v)
    if f in NOT_COUNTRIES:
        return None
    if f in NAME2CANON:
        return NAME2CANON[f]
    if f.startswith("the ") and f[4:] in NAME2CANON:
        return NAME2CANON[f[4:]]
    return None


_TEXT_KEYS = sorted(NAME2CANON, key=len, reverse=True)
_TEXT_RE = _re.compile(r"(?<![A-Za-z])(" + "|".join(_re.escape(k) for k in _TEXT_KEYS if len(k) > 2 or k in ("uk",)) + r")(?![A-Za-z])")


def find_in_text(text):
    """All countries mentioned in free text (by name or demonym), in order of appearance."""
    if not text:
        return []
    f = _fold(text)
    f = _re.sub(r"\bnew (jersey|mexico|south wales|york|hampshire)\b", " ", f)
    out = []
    for m in _TEXT_RE.finditer(f):
        c = NAME2CANON[m.group(1)]
        if c not in out:
            out.append(c)
    return out
