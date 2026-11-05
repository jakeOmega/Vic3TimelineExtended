#!/usr/bin/env python3
r"""Sweep the localization and the player guide to American spelling.

The mod's text is American English, as the base game's is (owner, 2026-10-27):
program, defense, license, labor, color, center, -ize. This script rewrites the
British spellings in WORDS wherever players read them:

- the values of ``localization/english/**/*.yml`` (``replace/`` included). It
  never touches a key, a comment line or what follows a value's closing quote,
  and inside a value it leaves alone what the engine reads: ``$splice$``
  references, ``[...]`` data expressions (except a ``Concept('key', 'text')``
  call's display text), ``@icon!`` and ``£...£`` tokens, ``#format`` codes,
  ``\n``-style escapes, any word with an underscore (a script key) and paths;
- the prose of ``docs/player_guide/*.md``. It never touches fenced code, a code
  span, a link target or a URL. When a heading's spelling changes, its anchor
  does too, and every guide link to the old anchor follows.

A phrase in ALLOWLIST keeps its own spelling (a proper noun, an official name,
a title). A mod key that also exists in vanilla keeps any British word that
vanilla's text for that key has (from the committed
``vanilla_parsed/localization_english.json``), so a vanilla override reads as
vanilla does.

    python3 scripts/analysis/check_loc_spelling.py           # rewrite in place
    python3 scripts/analysis/check_loc_spelling.py --check   # write nothing, list
                                                             # what is left, exit 1 if any

The default run prints how many of each word it changed and every allowlisted
phrase it kept. It is idempotent: a second run changes nothing. The word list
is curated, not a blanket rule: "-ise" goes "-ize" only for the stems in
_ISE_STEMS, so rise, promise, exercise, advertise, compromise, enterprise,
franchise, surprise, revise, supervise and the like stay. Words American
English also spells this way (dialogue, towards, tonne, cancellation,
enrolled, fulfilled, programmed) and in-game names the base game spells the
British way (its Aeroplanes good) are not in the list.

Generated loc files are swept too; where a generator writes British text, fix
its source so its next run agrees (docs/auto_generated_files.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOC_DIR = REPO_ROOT / "localization" / "english"
GUIDE_DIR = REPO_ROOT / "docs" / "player_guide"
VANILLA_LOC = REPO_ROOT / "vanilla_parsed" / "localization_english.json"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_player_guide import github_slug, iter_headings  # noqa: E402
from mod_state import split_loc_line  # noqa: E402

# ── The word list ───────────────────────────────────────────────────────────
# Every entry is a whole lower-case word; matching ignores case and keeps it
# (Programme -> Program, DEFENCE -> DEFENSE).


def _expand(pairs, suffixes, prefixes=("",)):
    out = {}
    for brit, amer in pairs:
        for pre in prefixes:
            for suf in suffixes:
                out[pre + brit + suf] = pre + amer + suf
    return out


WORDS: dict[str, str] = {}

# -our -> -or. (Glamour stays: American English uses it too.)
_OUR = [
    "arbour", "ardour", "armour", "behaviour", "candour", "clamour", "colour", "demeanour",
    "endeavour", "favour", "fervour", "flavour", "harbour", "honour", "humour", "labour",
    "neighbour", "odour", "parlour", "rancour", "rigour", "rumour", "saviour", "savour",
    "splendour", "succour", "tumour", "valour", "vapour", "vigour",
]
WORDS.update(_expand(
    [(w, w[:-2] + "r") for w in _OUR],
    ("", "s", "ed", "ing", "er", "ers", "able", "ably", "ite", "ites", "itism", "ful", "fully",
     "less", "hood", "hoods", "ly", "al", "ally", "ism", "ist", "ists", "y", "ies", "ish",
     "ise", "ised", "ising", "isation"),
    ("", "un", "dis", "mis"),
))
# "-ourise" goes "-orize": vapourise -> vaporize, not vaporise.
for _brit, _amer in list(WORDS.items()):
    if "ouris" in _brit:
        WORDS[_brit] = _amer.replace("oris", "oriz")

# -re -> -er.
_RE = [
    "centre", "epicentre", "metre", "kilometre", "centimetre", "millimetre", "nanometre",
    "micrometre", "litre", "millilitre", "theatre", "amphitheatre", "fibre", "calibre",
    "sombre", "spectre", "meagre", "lustre", "lacklustre", "sabre", "goitre", "mitre",
    "saltpetre", "sepulchre", "reconnoitre", "sceptre", "nitre",
]
WORDS.update(_expand([(w, w[:-2] + "er") for w in _RE], ("", "s")))
WORDS.update({
    "centred": "centered", "centring": "centering", "centrepiece": "centerpiece",
    "centrepieces": "centerpieces", "theatregoer": "theatergoer", "theatregoers": "theatergoers",
    "fibreglass": "fiberglass", "sabred": "sabered",
    "sombrely": "somberly", "manoeuvre": "maneuver", "manoeuvres": "maneuvers",
    "manoeuvred": "maneuvered", "manoeuvring": "maneuvering", "manoeuvrable": "maneuverable",
    "manoeuvrability": "maneuverability", "reconnoitred": "reconnoitered",
    "reconnoitring": "reconnoitering",
})

# -ence -> -ense (license is noun and verb in American), practise -> practice.
WORDS.update({
    "defence": "defense", "defences": "defenses", "defenceless": "defenseless",
    "offence": "offense", "offences": "offenses", "pretence": "pretense", "pretences": "pretenses",
    "licence": "license", "licences": "licenses", "licenced": "licensed", "licencing": "licensing",
    "practise": "practice", "practises": "practices", "practised": "practiced",
    "practising": "practicing",
})

# -ise -> -ize, for these stems only. Words that are -ise in American English too
# (rise, promise, exercise, advertise, compromise, enterprise, franchise, comprise,
# surprise, otherwise, precise, concise, expertise, premise, merchandise, televise,
# supervise, revise, devise, improvise, disguise, chastise, excise, incise, despise,
# apprise, advise, arise, praise, poise, cruise, treatise, paradise, turquoise) have
# no stem here.
_ISE_STEMS = [
    "actual", "agon", "american", "anglic", "annual", "apolog", "author", "brutal", "capital",
    "carbon", "categor", "central", "character", "christian", "civil", "colon", "commercial",
    "computer", "criminal", "critic", "crystall", "custom", "decarbon", "decentral", "decolon",
    "decriminal", "demilitar", "democrat", "demobil", "demonet", "demoral", "denuclear",
    "deodor", "deput", "desensit", "destabil", "digit", "disorgan", "dollar", "dramat", "econom",
    "emphas", "energ", "equal", "european", "evangel", "external", "familiar", "fantas",
    "fertil", "final", "formal", "fossil", "fratern", "galvan", "general", "global", "harmon",
    "hospital", "human", "hypothes", "ideal", "immobil", "immun", "incentiv", "individual",
    "industrial", "initial", "institutional", "internal", "international", "ion", "item",
    "jeopard", "legal", "legitim", "liberal", "local", "magnet", "marginal", "maxim", "mechan",
    "memor", "mesmer", "militar", "minim", "mobil", "modern", "monet", "monopol", "moral",
    "motor", "national", "natural", "neutral", "normal", "optim", "organ", "ostrac", "oxid",
    "pasteur", "patron", "penal", "personal", "polar", "politic", "popular", "pressur",
    "priorit", "privat", "proselyt", "public", "radical", "random", "rational", "real",
    "recapital", "recogn", "regular", "reorgan", "revital", "revolution", "romantic", "sanit",
    "satir", "scrutin", "secular", "sensit", "serial", "social", "special", "stabil",
    "standard", "steril", "subsid", "summar", "symbol", "sympath", "synchron", "synthes",
    "systemat", "tantal", "terror", "theor", "tranquil", "trivial", "tyrann", "union", "urban",
    "util", "vandal", "vapor", "verbal", "victim", "visual", "vulcan", "weapon", "western",
]
_ISE_SUFFIXES = ("ise", "ises", "ised", "ising", "iser", "isers", "isation", "isations",
                 "isational", "isable")
for _stem in _ISE_STEMS:
    for _suf in _ISE_SUFFIXES:
        WORDS[_stem + _suf] = _stem + "iz" + _suf[2:]

# -yse -> -yze. Not "-yses": analyses and paralyses are also the plurals of
# analysis and paralysis, which American English spells the same.
WORDS.update(_expand(
    [(s + "yse", s + "yze") for s in ("anal", "paral", "catal", "hydrol", "electrol", "dial",
                                      "psychoanal")],
    ("", "d", "r", "rs"),
))
WORDS.update({k.replace("ysed", "ysing"): v.replace("yzed", "yzing")
              for k, v in list(WORDS.items()) if k.endswith("ysed")})

# Doubled l before a suffix -> single l (the stress is not on the last syllable).
_LL = {
    "travel": ("led", "ling", "ler", "lers"), "cancel": ("led", "ling"),
    "label": ("led", "ling"), "model": ("led", "ling", "ler", "lers"),
    "fuel": ("led", "ling"), "signal": ("led", "ling"), "channel": ("led", "ling"),
    "total": ("led", "ling"), "level": ("led", "ling", "ler", "lers"),
    "counsel": ("led", "ling", "lor", "lors"), "marvel": ("led", "ling", "lous", "lously"),
    "quarrel": ("led", "ling"), "jewel": ("led", "ler", "lers", "lery"),
    "duel": ("led", "ling", "list", "lists"), "equal": ("led", "ling"),
    "grovel": ("led", "ling"), "panel": ("led", "ling", "list", "lists"),
    "pedal": ("led", "ling"), "rival": ("led", "ling"), "shovel": ("led", "ling"),
    "swivel": ("led", "ling"), "tunnel": ("led", "ling", "ler", "lers"),
    "unravel": ("led", "ling"), "dial": ("led", "ling"), "spiral": ("led", "ling"),
    "initial": ("led", "ling"), "enamel": ("led", "ling"), "bevel": ("led", "ling"),
    "libel": ("led", "ling", "lous"), "snorkel": ("led", "ling"), "cudgel": ("led", "ling"),
    "gruel": ("ling",), "dishevel": ("led",), "wool": ("len", "lens"),
    "trial": ("led", "ling"), "marshal": ("led", "ling"), "martial": ("led", "ling"),
}
for _stem, _sufs in _LL.items():
    for _suf in _sufs:
        for _pre in ("", "re", "un", "mis"):
            WORDS[_pre + _stem + "l" + _suf[1:]] = _pre + _stem + _suf[1:]
WORDS["jewellery"] = "jewelry"
# Single l in British where American doubles it.
WORDS.update({
    "enrol": "enroll", "enrols": "enrolls", "enrolment": "enrollment",
    "enrolments": "enrollments", "fulfil": "fulfill", "fulfils": "fulfills",
    "fulfilment": "fulfillment", "fulfilments": "fulfillments", "instil": "instill",
    "instils": "instills", "distil": "distill", "distils": "distills", "enthral": "enthrall",
    "enthrals": "enthralls", "instalment": "installment", "instalments": "installments",
    "skilful": "skillful", "skilfully": "skillfully", "wilful": "willful",
    "wilfully": "willfully",
})

# Single words.
WORDS.update({
    "programme": "program", "programmes": "programs",
    "catalogue": "catalog", "catalogues": "catalogs", "catalogued": "cataloged",
    "cataloguing": "cataloging",
    "cheque": "check", "cheques": "checks", "chequebook": "checkbook",
    "chequebooks": "checkbooks", "chequered": "checkered",
    "grey": "gray", "greys": "grays", "greyed": "grayed", "greying": "graying",
    "greyish": "grayish", "greyer": "grayer", "greyest": "grayest", "greyness": "grayness",
    "sceptic": "skeptic", "sceptics": "skeptics", "sceptical": "skeptical",
    "sceptically": "skeptically", "scepticism": "skepticism",
    "judgement": "judgment", "judgements": "judgments", "judgemental": "judgmental",
    "ageing": "aging",
    "tyre": "tire", "tyres": "tires",
    "kerb": "curb", "kerbs": "curbs", "kerbside": "curbside",
    "storey": "story", "storeys": "stories", "storeyed": "storied",
    "plough": "plow", "ploughs": "plows", "ploughed": "plowed", "ploughing": "plowing",
    "ploughman": "plowman", "ploughmen": "plowmen", "ploughshare": "plowshare",
    "ploughshares": "plowshares",
    "mould": "mold", "moulds": "molds", "moulded": "molded", "moulding": "molding",
    "mouldy": "moldy",
    "smoulder": "smolder", "smoulders": "smolders", "smouldered": "smoldered",
    "smouldering": "smoldering",
    "gaol": "jail", "gaols": "jails", "gaoled": "jailed", "gaoler": "jailer",
    "pyjamas": "pajamas", "moustache": "mustache", "moustaches": "mustaches",
    "cosy": "cozy",
    "artefact": "artifact", "artefacts": "artifacts",
    "caesium": "cesium", "aluminium": "aluminum",
    "sulphur": "sulfur", "sulphuric": "sulfuric", "sulphurous": "sulfurous",
    "sulphate": "sulfate", "sulphates": "sulfates", "sulphide": "sulfide",
    "sulphides": "sulfides", "sulphite": "sulfite",
    "foetus": "fetus", "foetuses": "fetuses", "foetal": "fetal",
    "haemorrhage": "hemorrhage", "haemorrhages": "hemorrhages", "anaemia": "anemia",
    "anaemic": "anemic", "leukaemia": "leukemia", "haemoglobin": "hemoglobin",
    "haematology": "hematology", "oesophagus": "esophagus", "oestrogen": "estrogen",
    "paediatric": "pediatric", "paediatrics": "pediatrics", "paediatrician": "pediatrician",
    "orthopaedic": "orthopedic", "encyclopaedia": "encyclopedia",
    "encyclopaedias": "encyclopedias", "mediaeval": "medieval", "diarrhoea": "diarrhea",
    "anaesthetic": "anesthetic", "anaesthetics": "anesthetics", "anaesthesia": "anesthesia",
    "oedema": "edema", "palaeontology": "paleontology", "palaeolithic": "paleolithic",
    "enquiry": "inquiry", "enquiries": "inquiries", "enquire": "inquire",
    "enquired": "inquired", "enquiring": "inquiring",
    "speciality": "specialty", "specialities": "specialties",
    "orientated": "oriented", "maths": "math",
    "sizeable": "sizable", "likeable": "likable", "saleable": "salable",
    "acknowledgement": "acknowledgment", "acknowledgements": "acknowledgments",
    "whilst": "while", "amongst": "among", "learnt": "learned",
    "despatch": "dispatch", "despatches": "dispatches", "despatched": "dispatched",
    "draughtsman": "draftsman", "draughtsmen": "draftsmen",
    "focussed": "focused", "focussing": "focusing", "benefitted": "benefited",
    "benefitting": "benefiting", "combatting": "combating",
    "pedlar": "peddler", "pedlars": "peddlers", "leafletting": "leafleting",
    "leafletted": "leafleted", "queueing": "queuing",
})

# ── Phrases that keep their spelling ────────────────────────────────────────
# Official names, matched case-sensitively as whole phrases (and in capitals)
# before the word rules. Only a name whose own official English spelling is
# British belongs here: "Kenyatta International Convention Centre" is, but a
# landmark the text translates ("Roman Theater of Mérida", "Amphitheater of El
# Djem") or a name the mod made up ("Civil Defense", "National Exhibition
# Center") goes American. Check each entry against the text it protects.
ALLOWLIST: list[str] = [
    "Kenyatta International Convention Centre",  # the wonder (Nairobi's KICC)
    "UN Environment Programme",                  # UNEP's own name
    "United Nations Environment Programme",
    "Tyre",                                      # the Lebanese city; the product is lower case
]

# Keys whose whole value keeps its spelling, such as a historical text quoted
# word for word. None so far.
KEY_ALLOWLIST: set[str] = set()

# ── Matching ────────────────────────────────────────────────────────────────

# A word is a run of word characters; one in WORDS (any case) is British.
_WORD_RE = re.compile(r"\w+")


def british_words(text: str):
    """The matches in ``text`` that are a British spelling in WORDS."""
    return [m for m in _WORD_RE.finditer(text) if m.group(0).lower() in WORDS]


def _allowlist_re(phrases):
    if not phrases:
        return None
    alts = []
    for phrase in sorted(set(phrases), key=len, reverse=True):
        alts.append(re.escape(phrase))
        if phrase.upper() != phrase:
            alts.append(re.escape(phrase.upper()))
    return re.compile(r"(?<![\w])(?:" + "|".join(alts) + r")(?![\w])")


_ALLOW_RE = _allowlist_re(ALLOWLIST)


def match_case(source: str, target: str) -> str:
    """``target`` in the case pattern of ``source``."""
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source[0].isupper():
        return target[0].upper() + target[1:]
    return target


@dataclass
class Hit:
    word: str        # as written
    american: str    # its replacement, case kept
    start: int       # offset in the text passed to americanize_text


def _text_hits(text: str, keep: frozenset[str]) -> tuple[list[Hit], list[str]]:
    """Word hits in plain text, and the allowlisted phrases that blocked some."""
    blocked: list[tuple[int, int]] = []
    allowed: list[str] = []
    if _ALLOW_RE is not None:
        for m in _ALLOW_RE.finditer(text):
            if british_words(m.group(0)):
                blocked.append((m.start(), m.end()))
                allowed.append(m.group(0))
    hits = []
    for m in british_words(text):
        word = m.group(0)
        if word.lower() in keep:
            allowed.append(word + " (as in vanilla's text for the key)")
            continue
        if any(a <= m.start() < b for a, b in blocked):
            continue
        hits.append(Hit(word, match_case(word, WORDS[word.lower()]), m.start()))
    return hits, allowed


def _apply(text: str, hits: list[Hit], offset: int = 0) -> str:
    out = []
    pos = 0
    for hit in hits:
        start = hit.start - offset
        out.append(text[pos:start])
        out.append(hit.american)
        pos = start + len(hit.word)
    out.append(text[pos:])
    return "".join(out)


# ── Localization values ─────────────────────────────────────────────────────

# Parts of a value the engine reads. Order matters: the first alternative that
# matches at a position wins.
_LOC_PROTECTED = re.compile(
    r"""
      \\.                                  # an escape: \n, \", \t
    | \$[^$\s"]*\$                         # $splice$ / $KEY|format$
    | @[\w]+!                              # @icon!
    | £[^£\s"]*£?                          # £icon£
    | \#[^\s\#"]*                          # #format code (#v, #tooltippable;tooltip:x, #!)
    | (?:gfx|common|events|gui|localization|map_data)/[\w./-]+   # a path
    | [\w./-]+\.(?:dds|png|tga|jpg|txt|gui|yml)\b
    | [\w-]*_[\w-]*                        # an identifier with an underscore
    """,
    re.VERBOSE,
)
_CONCEPT_CALL = re.compile(r"""(Concept\(\s*'[^']*'\s*,\s*')([^']*)(')""")


def _bracket_end(value: str, start: int) -> int:
    """Index just past the ``]`` that closes the ``[`` at ``start``."""
    depth = 0
    i = start
    while i < len(value):
        c = value[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(value)


def _value_segments(value: str):
    """Yield ``(start, text)`` for the parts of a loc value that are prose."""
    i = 0
    n = len(value)
    text_start = 0
    while i < n:
        if value[i] == "[":
            if text_start < i:
                yield from _plain_segments(value, text_start, i)
            end = _bracket_end(value, i)
            # A Concept('key', 'Display text') call's display text is prose.
            for m in _CONCEPT_CALL.finditer(value, i, end):
                yield from _plain_segments(value, m.start(2), m.end(2))
            i = text_start = end
            continue
        i += 1
    if text_start < n:
        yield from _plain_segments(value, text_start, n)


def _plain_segments(value: str, start: int, end: int):
    pos = start
    for m in _LOC_PROTECTED.finditer(value, start, end):
        if m.start() > pos:
            yield pos, value[pos:m.start()]
        pos = m.end()
    if pos < end:
        yield pos, value[pos:end]


def americanize_value(value: str, keep: frozenset[str] = frozenset()):
    """``(new_value, hits, allowed)`` for one loc value."""
    hits: list[Hit] = []
    allowed: list[str] = []
    for start, text in _value_segments(value):
        seg_hits, seg_allowed = _text_hits(text, keep)
        for hit in seg_hits:
            hit.start += start
        hits.extend(seg_hits)
        allowed.extend(seg_allowed)
    hits.sort(key=lambda h: h.start)
    return _apply(value, hits), hits, allowed


def _load_vanilla() -> dict[str, str]:
    try:
        with open(VANILLA_LOC, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _vanilla_keep(vanilla_value: str | None) -> frozenset[str]:
    """The British words vanilla's own text for a key uses."""
    if not vanilla_value:
        return frozenset()
    return frozenset(m.group(0).lower() for m in british_words(str(vanilla_value)))


def _value_span(line: str):
    """``(key, start, end)`` of the value inside ``line``, or None."""
    parsed = split_loc_line(line)
    if parsed is None:
        return None
    key, value, _trailing = parsed
    stripped = line.lstrip()
    lead = len(line) - len(stripped)
    colon = stripped.index(":")
    start = lead + colon + 1 + stripped[colon + 1:].index('"') + 1
    return key, start, start + len(value)


@dataclass
class Change:
    path: Path
    line: int
    word: str
    american: str
    context: str


def sweep_loc_text(text: str, vanilla: dict[str, str]):
    """``(new_text, changes, allowed)`` for one loc file's text (BOM stripped)."""
    out_lines = []
    changes: list[tuple[int, Hit, str]] = []
    allowed: list[str] = []
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        span = _value_span(line)
        if span is None:
            out_lines.append(line)
            continue
        key, start, end = span
        if key in KEY_ALLOWLIST:
            out_lines.append(line)
            continue
        value = line[start:end]
        new_value, hits, line_allowed = americanize_value(value, _vanilla_keep(vanilla.get(key)))
        allowed.extend(line_allowed)
        for hit in hits:
            changes.append((number, hit, value))
        out_lines.append(line[:start] + new_value + line[end:])
    return "".join(out_lines), changes, allowed


# ── The player guide ────────────────────────────────────────────────────────

_MD_PROTECTED = re.compile(
    r"""
      `+[^`]*?`+                         # a code span
    | \]\([^)\s]*(?:\s+"[^"]*")?\)        # a link or image target
    | <https?://[^>]*>                    # an autolink
    | https?://\S+                        # a bare URL
    """,
    re.VERBOSE,
)
_FENCE = re.compile(r"^\s*(```|~~~)")
_LINK_FRAGMENT = re.compile(r"\]\(((?:\d\d-[A-Za-z0-9_-]+\.md)?)#([^)\s]+)\)")


def _md_segments(line: str):
    pos = 0
    for m in _MD_PROTECTED.finditer(line):
        if m.start() > pos:
            yield pos, line[pos:m.start()]
        pos = m.end()
    if pos < len(line):
        yield pos, line[pos:]


def americanize_md_line(line: str):
    hits: list[Hit] = []
    allowed: list[str] = []
    for start, text in _md_segments(line):
        seg_hits, seg_allowed = _text_hits(text, frozenset())
        for hit in seg_hits:
            hit.start += start
        hits.extend(seg_hits)
        allowed.extend(seg_allowed)
    hits.sort(key=lambda h: h.start)
    return _apply(line, hits), hits, allowed


def sweep_md_text(text: str):
    """``(new_text, changes, allowed)`` for one chapter (links not yet fixed)."""
    out = []
    changes: list[tuple[int, Hit, str]] = []
    allowed: list[str] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        new_line, hits, line_allowed = americanize_md_line(line)
        allowed.extend(line_allowed)
        for hit in hits:
            changes.append((number, hit, line))
        out.append(new_line)
    return "".join(out), changes, allowed


def _americanize_slug(slug: str) -> str:
    return "-".join(WORDS.get(part, part) for part in slug.split("-"))


def fix_guide_links(texts: dict[str, str]) -> tuple[dict[str, str], int]:
    """Point links whose anchor no longer exists at the renamed heading.

    A link fragment that names no heading in its target chapter, but would
    once its words are American, is rewritten; any other link is left for the
    style lint to report."""
    anchors: dict[str, set[str]] = {
        name: {github_slug(h) for _, _, h in iter_headings(text)} for name, text in texts.items()
    }
    fixed = 0
    out = {}
    for name, text in texts.items():
        def repl(m: re.Match) -> str:
            nonlocal fixed
            target, fragment = m.group(1), m.group(2)
            pool = anchors.get(target or name, set())
            if fragment in pool:
                return m.group(0)
            renamed = _americanize_slug(fragment)
            if renamed != fragment and renamed in pool:
                fixed += 1
                return "](" + target + "#" + renamed + ")"
            return m.group(0)

        out[name] = _LINK_FRAGMENT.sub(repl, text)
    return out, fixed


# ── Files ───────────────────────────────────────────────────────────────────

BOM = b"\xef\xbb\xbf"


def loc_paths(loc_dir: Path = LOC_DIR) -> list[Path]:
    return sorted(loc_dir.rglob("*.yml"))


def guide_paths(guide_dir: Path = GUIDE_DIR) -> list[Path]:
    return sorted(guide_dir.glob("*.md"))


def _read(path: Path) -> tuple[bytes, str]:
    raw = path.read_bytes()
    bom = BOM if raw.startswith(BOM) else b""
    return bom, raw[len(bom):].decode("utf-8")


def run(check: bool, loc_dir: Path = LOC_DIR, guide_dir: Path = GUIDE_DIR,
        vanilla: dict[str, str] | None = None, out=sys.stdout) -> int:
    if vanilla is None:
        vanilla = _load_vanilla()
    changes: list[Change] = []
    allowed: Counter = Counter()
    writes: dict[Path, bytes] = {}

    for path in loc_paths(loc_dir):
        bom, text = _read(path)
        new_text, file_changes, file_allowed = sweep_loc_text(text, vanilla)
        allowed.update(file_allowed)
        for number, hit, context in file_changes:
            changes.append(Change(path, number, hit.word, hit.american, context))
        if new_text != text:
            writes[path] = bom + new_text.encode("utf-8")

    guide_texts: dict[str, tuple[Path, bytes, str, str]] = {}
    for path in guide_paths(guide_dir):
        bom, text = _read(path)
        new_text, file_changes, file_allowed = sweep_md_text(text)
        allowed.update(file_allowed)
        for number, hit, context in file_changes:
            changes.append(Change(path, number, hit.word, hit.american, context))
        guide_texts[path.name] = (path, bom, text, new_text)
    linked, links_fixed = fix_guide_links({name: t[3] for name, t in guide_texts.items()})
    for name, (path, bom, text, _new) in guide_texts.items():
        if linked[name] != text:
            writes[path] = bom + linked[name].encode("utf-8")

    def shown(path: Path) -> str:
        try:
            return path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return str(path)

    if check:
        for c in changes:
            print(f"{shown(c.path)}:{c.line}: {c.word} -> {c.american}", file=out)
        if links_fixed:
            print(f"{links_fixed} guide link(s) point at a heading's British anchor", file=out)
        total = len(changes) + links_fixed
        print(f"{total} British spelling(s) left" if total else "no British spellings left",
              file=out)
        return 1 if total else 0

    for path, data in writes.items():
        path.write_bytes(data)
    per_word = Counter((c.word.lower(), WORDS[c.word.lower()]) for c in changes)
    for (brit, amer), n in sorted(per_word.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"{n:6}  {brit} -> {amer}", file=out)
    print(f"{len(changes)} change(s) in {len(writes)} file(s); {links_fixed} guide link(s) "
          "repointed", file=out)
    for phrase, n in sorted(allowed.items()):
        print(f"kept {n:4}  {phrase}", file=out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="write nothing; list every British spelling left, exit 1 if any")
    args = parser.parse_args(argv)
    return run(check=args.check)


if __name__ == "__main__":
    sys.exit(main())
