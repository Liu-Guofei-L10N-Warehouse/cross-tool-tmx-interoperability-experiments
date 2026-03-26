"""
TMX Group B generator — TMX 1.4b Level 2, simple paired tags
Reads tmx_group_a_plain.tmx and produces tmx_group_b_simple_tags.tmx

Tag design:
  - One <bpt i="1" x="1" type="bold"> / <ept i="1"> pair per TU
  - Native code: &lt;b&gt; / &lt;/b&gt;
  - Placement priority:
      1. Term dictionary (longest match first)
      2. First multi-word capitalised phrase (regex, skips sentence start)
      3. Fallback: first substantial noun phrase

Usage:
  python tmx_group_b.py tmx_group_a_plain.tmx
  Output: tmx_group_b_simple_tags.tmx
"""

import sys, re
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

OUTPUT            = "tmx_group_b_simple_tags.tmx"
CREATION_TOOL     = "Manual extraction script"
CREATION_TOOL_VER = "1.0"
CREATION_ID       = "LIU_Guofei"
O_TMF             = "justice.gc.ca XML"
SRC_LANG          = "en-CA"
TGT_LANG          = "fr-CA"

# ── TERM DICTIONARIES (longest first) ────────────────────────────────────────

TERMS_EN = sorted([
    # Institutions
    "The National Battlefields Commission",
    "National Battlefields Commission",
    "the National Battlefields Commission",
    "the Commission",
    "the commission",
    "The Commission",
    # Acts
    "The Expropriation Act",
    "the Expropriation Act",
    "The Consolidated Revenue and Audit Act",
    "The Consolidated Revenue Fund",
    "the Consolidated Revenue Fund",
    "The Canada Gazette",
    "The Privacy Act",
    "Immigration and Refugee Protection Act",
    "Financial Administration Act",
    # Officials
    "The Information Commissioner",
    "Information Commissioner",
    "the Information Commissioner",
    "The Minister of Finance",
    "the Minister of Finance",
    "Minister of Finance",
    "The Federal Court of Canada",
    "The Federal Court",
    "the Federal Court",
    "The Governor in Council",
    "the Governor in Council",
    "Governor in Council",
    "The Attorney General of Canada",
    "the Attorney General of Canada",
    "Attorney General of Canada",
    "Auditor General",
    # Bodies
    "a government institution",
    "the government institution",
    "the head of a government institution",
    "the head of the government institution",
    "Senate and House of Commons",
    "House of Commons",
    "Parliament",
    # Persons
    "Her Majesty",
    "His Majesty",
    # Geographic
    "the city of Quebec",
    "Plains of Abraham",
    "Gilmour's Hill",
    "Champlain road",
    "St. Louis road",
    "Ste. Foye road",
], key=lambda x: -len(x))

TERMS_FR = sorted([
    # Institutions
    "Commission des champs de bataille nationaux",
    "la Commission",
    "La Commission",
    # Acts
    "Loi des expropriations",
    "la Loi des expropriations",
    "Fonds du revenu consolidé",
    "le Fonds du revenu consolidé",
    "Gazette du Canada",
    "la Gazette du Canada",
    "Loi sur la protection des renseignements personnels",
    "Loi sur l'immigration et la protection des réfugiés",
    "Loi sur la gestion des finances publiques",
    # Officials
    "Commissaire à l'information",
    "le Commissaire à l'information",
    "ministre des Finances",
    "le ministre des Finances",
    "Cour fédérale du Canada",
    "la Cour fédérale du Canada",
    "Cour fédérale",
    "la Cour fédérale",
    "Gouverneur en conseil",
    "le Gouverneur en conseil",
    "gouverneur en conseil",
    "le gouverneur en conseil",
    "procureur général du Canada",
    "vérificateur général",
    # Bodies
    "une institution fédérale",
    "l'institution fédérale",
    "le responsable de l'institution fédérale",
    "le responsable d'une institution fédérale",
    "Sénat et de la Chambre des communes",
    "Chambre des communes",
    "Parlement",
    # Persons
    "Sa Majesté",
    # Geographic
    "la cité de Québec",
    "plaines d'Abraham",
    "côte Gilmour",
    "chemin Champlain",
    "chemin Saint-Louis",
    "chemin de Sainte-Foye",
], key=lambda x: -len(x))

# ── HELPERS ──────────────────────────────────────────────────────────────────

def xml_escape(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("'", "&apos;")
    text = text.replace('"', "&quot;")
    return text

def find_term(text, terms):
    for term in terms:
        idx = text.find(term)
        if idx != -1:
            return idx, idx + len(term)
    return None

def find_capitalised_phrase(text):
    """First multi-word cap phrase not at absolute sentence start."""
    m = re.search(r'(?<=[a-záàâéèêëîïôùûüçœ,;]\s)([A-ZÀ-Ü][a-zA-ZÀ-ü]+(?:\s+[A-ZÀ-Ü][a-zA-ZÀ-ü]+)+)', text)
    if m:
        return m.start(1), m.end(1)
    return None

def find_fallback(text):
    """Tag first meaningful noun phrase (skip leading function words)."""
    SKIP = {'The','A','An','In','Where','If','No','Every','This','That',
            'All','Any','Each','And','Whereas','WHEREAS','lay','remove',
            'receive','the','a','an','and','or','to','of','in'}
    words = text.split()
    # Find first content word
    start_i = 0
    for i, w in enumerate(words):
        if w.rstrip(',.;:') not in SKIP:
            start_i = i
            break
    # Take up to 4 words forming a phrase
    phrase_words = []
    for w in words[start_i:start_i+5]:
        if w.rstrip(',.;:(') in SKIP and phrase_words:
            break
        phrase_words.append(w)
    phrase = ' '.join(phrase_words[:4])
    idx = text.find(phrase)
    if idx != -1:
        return idx, idx + len(phrase)
    # absolute fallback
    first = ' '.join(words[:3])
    return 0, len(first)

def insert_tags(text, start, end):
    before = text[:start]
    target = text[start:end]
    after  = text[end:]
    return (xml_escape(before)
            + '<bpt i="1" x="1" type="bold">&lt;b&gt;</bpt>'
            + xml_escape(target)
            + '<ept i="1">&lt;/b&gt;</ept>'
            + xml_escape(after))

def tag_segment(text, terms):
    r = find_term(text, terms)
    if r:
        return insert_tags(text, *r), "dict"
    r = find_capitalised_phrase(text)
    if r:
        return insert_tags(text, *r), "regex"
    r = find_fallback(text)
    return insert_tags(text, *r), "fallback"

# ── MAIN ─────────────────────────────────────────────────────────────────────

def main(input_path):
    tree = ET.parse(input_path)
    root = tree.getroot()
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stats = {"dict": 0, "regex": 0, "fallback": 0}

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<tmx version="1.4">')
    lines.append('  <header')
    lines.append(f'    creationtool="{xml_escape(CREATION_TOOL)}"')
    lines.append(f'    creationtoolversion="{xml_escape(CREATION_TOOL_VER)}"')
    lines.append(f'    segtype="sentence"')
    lines.append(f'    o-tmf="{xml_escape(O_TMF)}"')
    lines.append(f'    adminlang="en-CA"')
    lines.append(f'    srclang="{SRC_LANG}"')
    lines.append(f'    datatype="plaintext"')
    lines.append(f'    creationdate="{now}"')
    lines.append(f'    creationid="{xml_escape(CREATION_ID)}"')
    lines.append('  />')
    lines.append('  <body>')

    for tu in root.findall(".//tu"):
        tuid_b = tu.get("tuid", "").replace("A-", "B-")
        cd     = tu.get("creationdate", now)

        en_seg = fr_seg = ""
        for tuv in tu.findall("tuv"):
            lang = (tuv.get("{http://www.w3.org/XML/1998/namespace}lang")
                    or tuv.get("xml:lang", ""))
            seg_el = tuv.find("seg")
            if seg_el is not None and seg_el.text:
                if lang.lower() == "en-ca":
                    en_seg = seg_el.text.strip()
                elif lang.lower() == "fr-ca":
                    fr_seg = seg_el.text.strip()

        en_tagged, en_method = tag_segment(en_seg, TERMS_EN)
        fr_tagged, _         = tag_segment(fr_seg, TERMS_FR)
        stats[en_method] += 1

        # Rebuild props with updated group/complexity values
        prop_lines = []
        for prop in tu.findall("prop"):
            ptype = prop.get("type", "")
            ptext = prop.text or ""
            if ptype == "x-tmx-group":
                prop_lines.append('      <prop type="x-tmx-group">B</prop>')
            elif ptype == "x-tag-complexity":
                prop_lines.append('      <prop type="x-tag-complexity">simple</prop>')
            else:
                prop_lines.append(f'      <prop type="{xml_escape(ptype)}">{xml_escape(ptext)}</prop>')

        lines.append(f'    <tu')
        lines.append(f'      tuid="{tuid_b}"')
        lines.append(f'      creationdate="{cd}"')
        lines.append(f'      datatype="plaintext"')
        lines.append(f'      segtype="sentence">')
        lines += prop_lines
        lines.append(f'      <tuv xml:lang="{SRC_LANG}">')
        lines.append(f'        <seg>{en_tagged}</seg>')
        lines.append(f'      </tuv>')
        lines.append(f'      <tuv xml:lang="{TGT_LANG}">')
        lines.append(f'        <seg>{fr_tagged}</seg>')
        lines.append(f'      </tuv>')
        lines.append(f'    </tu>')

    lines.append('  </body>')
    lines.append('</tmx>')

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    total = len(root.findall(".//tu"))
    print(f"Saved : {OUTPUT}")
    print(f"TUs   : {total}")
    print(f"\nTag placement:")
    print(f"  Dictionary : {stats['dict']} ({stats['dict']/total*100:.0f}%)")
    print(f"  Regex      : {stats['regex']} ({stats['regex']/total*100:.0f}%)")
    print(f"  Fallback   : {stats['fallback']} ({stats['fallback']/total*100:.0f}%)")

    # Preview 5 TUs
    print("\nPreview (first 5 EN segments):")
    with open(OUTPUT, encoding="utf-8") as f:
        content = f.read()
    segs = re.findall(r'xml:lang="en-CA">\s*<seg>(.*?)</seg>', content, re.DOTALL)
    for i, s in enumerate(segs[:5], 1):
        print(f"\n  B-{i:03d}: {s[:120]}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tmx_group_b.py tmx_group_a_plain.tmx")
        sys.exit(1)
    main(sys.argv[1])
