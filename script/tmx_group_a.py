"""
TMX Group A generator — strictly conforming to TMX 1.4b specification
(LISA / OSCAR Recommendation, 26 April 2005)

Extracts plain-text sentence pairs from Canadian federal law XML files
(justice.gc.ca) and outputs a TMX 1.4b Level 1 file for Group A (no inline tags).

TMX 1.4b compliance notes:
  - UTF-8 without BOM
  - No DOCTYPE declaration (not required for well-formed documents)
  - <header> includes all 7 required attributes:
      creationtool, creationtoolversion, segtype, o-tmf,
      adminlang, srclang, datatype
  - <header> optional attributes included:
      creationdate, creationid
  - <tu> optional attributes:
      tuid (text without whitespace), creationdate, datatype, segtype
  - <tuv> required attribute: xml:lang (RFC 3066 format)
  - <prop> type values prefixed with "x-" (unpublished, tool-defined)
  - Only &amp; &lt; &gt; &apos; &quot; used as character entity references
  - <seg> content has no leading or trailing whitespace
  - Level 1 only: no inline elements (<bpt>, <ept>, <it>, <ph>, <hi>)

Language pair: en-CA / fr-CA
Source: National Battlefields at Quebec Act (N-3.4), justice.gc.ca

Usage:
  python tmx_group_a.py en.xml fr.xml
  Outputs: tmx_group_a_plain.tmx
"""

import sys
import re
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

# ── CONFIG ───────────────────────────────────────────────────────────────────

SRC_LANG            = "en-CA"
TGT_LANG            = "fr-CA"
OUTPUT              = "tmx_group_a_plain.tmx"
MAX_TUS             = 100
CREATION_TOOL       = "Manual extraction script"
CREATION_TOOL_VER   = "1.0"
CREATION_ID         = "LIU_Guofei"
O_TMF               = "justice.gc.ca XML"

# ── SKIP TAGS ────────────────────────────────────────────────────────────────

SKIP_TAGS = {
    "MarginalNote", "Label", "HistoricalNote", "HistoricalNoteSubItem",
    "BillHistory", "Stages", "Date", "YYYY", "MM", "DD",
    "Chapter", "ConsolidatedNumber", "AnnualStatuteId", "AnnualStatuteNumber",
    "ScheduleFormHeading", "TitleText", "SignatureBlock", "SignatureName",
    "SignatureTitle", "Heading", "OriginatingRef",
}

# ── HELPERS ──────────────────────────────────────────────────────────────────

def local_tag(element):
    return element.tag.split("}")[-1] if "}" in element.tag else element.tag


def extract_plain_text(element):
    parts = []
    if element.text:
        t = element.text.strip()
        if t:
            parts.append(t)
    for child in element:
        if local_tag(child) in SKIP_TAGS:
            if child.tail:
                t = child.tail.strip()
                if t:
                    parts.append(t)
            continue
        child_text = extract_plain_text(child)
        if child_text:
            parts.append(child_text)
        if child.tail:
            t = child.tail.strip()
            if t:
                parts.append(t)
    result = " ".join(parts)
    result = re.sub(r"\s+", " ", result).strip()
    return result


def collect_texts(root):
    texts = []
    for element in root.iter():
        if local_tag(element) == "Text":
            text = extract_plain_text(element)
            if text and len(text) > 15:
                texts.append(text)
    return texts


def xml_escape(text):
    """TMX 1.4b spec: only these five entity references are allowed."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("'", "&apos;")
    text = text.replace('"', "&quot;")
    return text


def is_well_aligned(en, fr, max_ratio=3.0):
    en_w = len(en.split())
    fr_w = len(fr.split())
    if en_w == 0 or fr_w == 0:
        return False
    return max(en_w, fr_w) / min(en_w, fr_w) <= max_ratio


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main(en_path, fr_path):

    en_root = ET.parse(en_path).getroot()
    fr_root = ET.parse(fr_path).getroot()

    en_texts = collect_texts(en_root)
    fr_texts = collect_texts(fr_root)

    print(f"EN segments extracted : {len(en_texts)}")
    print(f"FR segments extracted : {len(fr_texts)}")

    raw_pairs = list(zip(en_texts, fr_texts))
    aligned   = [(en, fr) for en, fr in raw_pairs if is_well_aligned(en, fr)]
    selected  = aligned[:MAX_TUS]

    print(f"Aligned pairs         : {len(aligned)}")
    print(f"TUs to write          : {len(selected)}")

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<tmx version="1.4">')

    # <header> — 7 required + 2 optional attributes
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

    for i, (en_seg, fr_seg) in enumerate(selected, 1):
        tuid   = f"A-{i:03d}"
        en_esc = xml_escape(en_seg)
        fr_esc = xml_escape(fr_seg)

        lines.append(f'    <tu')
        lines.append(f'      tuid="{tuid}"')
        lines.append(f'      creationdate="{now}"')
        lines.append(f'      datatype="plaintext"')
        lines.append(f'      segtype="sentence">')
        lines.append(f'      <prop type="x-tmx-group">A</prop>')
        lines.append(f'      <prop type="x-tag-complexity">none</prop>')
        lines.append(f'      <prop type="x-source">N-3.4 National Battlefields at Quebec Act</prop>')
        lines.append(f'      <tuv xml:lang="{SRC_LANG}">')
        lines.append(f'        <seg>{en_esc}</seg>')
        lines.append(f'      </tuv>')
        lines.append(f'      <tuv xml:lang="{TGT_LANG}">')
        lines.append(f'        <seg>{fr_esc}</seg>')
        lines.append(f'      </tuv>')
        lines.append(f'    </tu>')

    lines.append('  </body>')
    lines.append('</tmx>')

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSaved : {OUTPUT}")
    print(f"TUs written : {len(selected)}")

    print("\n── Preview (first 3 TUs) ──")
    for i, (en, fr) in enumerate(selected[:3], 1):
        print(f"\nA-{i:03d}")
        print(f"  EN: {en[:100]}")
        print(f"  FR: {fr[:100]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python tmx_group_a.py en.xml fr.xml")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
