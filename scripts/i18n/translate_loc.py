"""Machine-translation harness for the mod's localization.

The model never edits a `.yml`. This script does everything deterministic:

    prepare   pick the keys that need translating, split them into chunks, and
              write each chunk as a text file an agent translates, with the
              glossary it needs (mod terms already fixed, vanilla terms)
    merge     read the agents' output, check every value's markup against the
              English, and add what passes to the translation memory
    status    count translated, stale and missing keys

The translation memory (`i18n/<language>/tm/*.json`, committed) maps each loc
key to the English it was translated from and the translation. Keys are looked
up globally, so a key organize_loc.py moves between files keeps its
translation. When the English under a translated key changes, the key is
"stale": it is offered for translation again, and until then the build ships
the old translation for a small wording change or English for a larger one
(`is_minor_change`).

Working files (chunks, agent output, reports) live under the gitignored
`build/i18n/<language>/`. The agent brief is `i18n/<language>/BRIEF.md`.

Usage:
    python3 scripts/i18n/translate_loc.py prepare --set names
    python3 scripts/i18n/translate_loc.py prepare --set all --files te_events --limit 1
    python3 scripts/i18n/translate_loc.py merge
    python3 scripts/i18n/translate_loc.py status
"""

from __future__ import annotations

import argparse
import difflib
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

from mod_state import split_loc_line  # noqa: E402

ENGLISH_DIR = os.path.join(REPO_ROOT, "localization", "english")
SKIP_FILES = {"te_unused_l_english.yml"}  # keys no script references

# German declines country names with the article baked in; vanilla defines
# these seven forms for every tag and dynamic name, and German text reaches
# them through GetAltName('<FORM>').
COUNTRY_FORMS = ("NOM", "GEN", "DAT", "AKK", "VON", "IN", "NACH")

# Agents carry ~100k tokens of fixed context whatever the chunk, so fewer,
# larger chunks cost less; the key cap keeps label-heavy files (3-4 words a
# key) from producing chunks of thousands of lines.
DEFAULT_CHUNK_WORDS = 9000
DEFAULT_MAX_KEYS = 700


# --------------------------------------------------------------------------
# English source


@dataclass(frozen=True)
class Entry:
    file: str  # relative to localization/english, e.g. "te_events_l_english.yml"
    key: str
    en: str


def load_english(english_dir: str = ENGLISH_DIR) -> list[Entry]:
    """Every English key in file order, `replace/` included, te_unused skipped."""
    entries = []
    for path in sorted(glob.glob(os.path.join(english_dir, "**", "*.yml"), recursive=True)):
        rel = os.path.relpath(path, english_dir)
        if os.path.basename(rel) in SKIP_FILES:
            continue
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                parsed = split_loc_line(line)
                if parsed:
                    entries.append(Entry(rel, parsed[0], parsed[1]))
    return entries


def plain_text(value: str) -> str:
    """The translatable words of a value, markup removed."""
    return re.sub(r"\$[^$]*\$|\[[^\]]*\]|#[a-zA-Z_]+[ ;]|#!|@\w+!|\\n", " ", value)


def word_count(value: str) -> int:
    return len(plain_text(value).split())


def needs_translation(value: str) -> bool:
    """False for values with nothing to translate (empty, or only markup)."""
    return bool(re.search(r"[A-Za-z]{2}", plain_text(value)))


# --------------------------------------------------------------------------
# Selection: the glossary ("names") set


_DESCRIPTIVE_KEY = re.compile(
    r"(_desc|_tooltip|_tt|\.d|\.f|_flavor|_DESC|_TOOLTIP|_TT|_reason|_status|_goal|_explanation)$"
)
_NAME_PREFIXES = (
    "concept_", "je_", "law_", "lawgroup_", "institution_", "decree_", "principle_",
    "ideology_", "building_", "ig_", "movement_", "bg_",
)
_NAME_FILES = ("te_formable_countries", "te_goods_and_needs", "te_technologies")


def is_name_like(key: str, value: str) -> bool:
    if _DESCRIPTIVE_KEY.search(key):
        return False
    return 1 <= word_count(value) <= 6 and not re.search(r"[.!?:;]$", value.strip())


def is_glossary_entry(entry: Entry) -> bool:
    """The terms every other chunk should render consistently: names of
    concepts, journal entries, laws, institutions, buildings, technologies,
    formable countries and the vanilla keys the mod renames (`replace/`)."""
    if not is_name_like(entry.key, entry.en):
        return False
    if entry.file.startswith("replace" + os.sep):
        return True
    if os.path.basename(entry.file).startswith(_NAME_FILES):
        return True
    return entry.key.startswith(_NAME_PREFIXES)


def is_country_name(entry: Entry) -> bool:
    """A formable tag (`AFU`) or dynamic country name (`dyn_c_...`); German
    needs the seven declined forms of each."""
    if not os.path.basename(entry.file).startswith("te_formable_countries"):
        return False
    if re.search(r"_(adj|ADJ)$", entry.key):
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]{2}", entry.key)) or entry.key.startswith("dyn_c_")


# --------------------------------------------------------------------------
# Translation memory


def language_dirs(language: str) -> tuple[str, str]:
    """(committed dir with BRIEF.md and tm/, gitignored working dir)."""
    return (
        os.path.join(REPO_ROOT, "i18n", language),
        os.path.join(REPO_ROOT, "build", "i18n", language),
    )


def tm_path_for(source_file: str, language: str) -> str:
    stem = source_file[: -len("_l_english.yml")] if source_file.endswith("_l_english.yml") else source_file
    return os.path.join(language_dirs(language)[0], "tm", stem + ".json")


def load_tm(language: str) -> dict[str, dict]:
    """key -> {"en": English translated from, "de"/<lang>: text, ["base": key]}"""
    tm: dict[str, dict] = {}
    for path in glob.glob(os.path.join(language_dirs(language)[0], "tm", "**", "*.json"), recursive=True):
        with open(path, encoding="utf-8") as fh:
            tm.update(json.load(fh))
    return tm


def save_tm(tm: dict[str, dict], entries: list[Entry], language: str) -> None:
    """Write the TM split by the English file each key currently lives in.
    Derived keys (country forms) go with their base key; keys whose English is
    gone are dropped."""
    file_of = {e.key: e.file for e in entries}
    by_file: dict[str, dict] = defaultdict(dict)
    for key, record in tm.items():
        source = file_of.get(record.get("base", key))
        if source is not None:
            by_file[source][key] = record
    root = os.path.join(language_dirs(language)[0], "tm")
    wanted = set()
    for source, records in by_file.items():
        path = tm_path_for(source, language)
        wanted.add(os.path.normpath(path))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        text = json.dumps(dict(sorted(records.items())), ensure_ascii=False, indent=1) + "\n"
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    for path in glob.glob(os.path.join(root, "**", "*.json"), recursive=True):
        if os.path.normpath(path) not in wanted:
            os.remove(path)


def is_minor_change(old_en: str, new_en: str) -> bool:
    """A wording tweak the old translation still covers. Short text (under six
    words: names, labels) must be unchanged apart from case, spacing and final
    punctuation, since a small edit there is usually a rename. Longer text needs
    the same numbers and 85% similarity. Anything else ships English until
    retranslated."""
    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip().rstrip(".!?:;").casefold()

    if norm(old_en) == norm(new_en):
        return True
    if min(word_count(old_en), word_count(new_en)) < 6:
        return False
    if re.findall(r"\d+(?:[.,]\d+)?", old_en) != re.findall(r"\d+(?:[.,]\d+)?", new_en):
        return False
    return difflib.SequenceMatcher(None, old_en, new_en).ratio() >= 0.85


class Overlay:
    """What a language's loc file ships for each English key: the translation,
    or English where there is none yet or the English has changed too much
    (`is_minor_change`). Also yields the declined country-name forms that
    follow their base key. `counts` tallies what was shipped."""

    def __init__(self, tm: dict[str, dict], field: str):
        self.tm = tm
        self.field = field
        self.derived: dict[str, list[str]] = defaultdict(list)
        for key, record in tm.items():
            if "base" in record:
                self.derived[record["base"]].append(key)
        self.counts: Counter = Counter()

    def _usable(self, record: dict | None, en: str) -> str | None:
        if record is None:
            return None
        if record["en"] == en:
            return "translated"
        return "stale_kept" if is_minor_change(record["en"], en) else None

    def value(self, key: str, en: str) -> str:
        record = self.tm.get(key)
        status = self._usable(record, en) if record and "base" not in record else None
        if status is None:
            if needs_translation(en):
                self.counts["english" if record is None else "stale_english"] += 1
            return en
        self.counts[status] += 1
        return record[self.field]

    def extra_lines(self, key: str, en: str) -> list[tuple[str, str]]:
        lines = []
        for derived in sorted(self.derived.get(key, ()), key=_form_order):
            record = self.tm[derived]
            if self._usable(record, en):
                lines.append((derived, record[self.field]))
        return lines


def _form_order(key: str) -> int:
    form = key.rsplit("_", 1)[-1]
    return COUNTRY_FORMS.index(form) if form in COUNTRY_FORMS else len(COUNTRY_FORMS)


def load_overlay(language: str, field: str) -> Overlay | None:
    """The language's overlay, or None if it has no translation memory."""
    if not os.path.isdir(os.path.join(language_dirs(language)[0], "tm")):
        return None
    return Overlay(load_tm(language), field)


def classify(entries: list[Entry], tm: dict[str, dict]) -> dict[str, list[Entry]]:
    """Split entries into translated / stale_minor / stale_major / missing / skip."""
    out: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        record = tm.get(entry.key)
        if not needs_translation(entry.en):
            out["skip"].append(entry)
        elif record is None:
            out["missing"].append(entry)
        elif record["en"] == entry.en:
            out["translated"].append(entry)
        elif is_minor_change(record["en"], entry.en):
            out["stale_minor"].append(entry)
        else:
            out["stale_major"].append(entry)
    return out


# --------------------------------------------------------------------------
# Markup check


_BRACKET = re.compile(r"\[[^\[\]]+\]")
_CONCEPT_PLAIN = re.compile(r"^\[concept_(\w+)(?:\|[A-Za-z]+)?\]$")
_CONCEPT_CALL = re.compile(r"^\[Concept\(\s*'concept_(\w+)'\s*,.*\)(?:\|[A-Za-z]+)?\]$", re.S)
_DOLLAR = re.compile(r"\$[A-Za-z0-9_.|+=\-%]+\$")
_ICON = re.compile(r"@[A-Za-z0-9_]+!")
_FORMAT_OPEN = re.compile(r"#(?!!)([a-zA-Z_]+)")
_ALT_NAME = re.compile(r"GetAltName(NoFlag|NoFormatting)?\('[A-Z]+'\)")


def _normalize_bracket(token: str) -> str:
    """Accessor forms German may legitimately swap in: GetAltName('DAT') for
    GetName, and a case flag (|l, |U) for capitalisation."""
    token = _ALT_NAME.sub(lambda m: "GetName" + (m.group(1) or ""), token)
    flags = re.search(r"\|([A-Za-z0-9+=\-%]*)\]$", token)
    if flags:
        kept = re.sub("[lUu]", "", flags.group(1))
        token = token[: flags.start()] + ("|" + kept if kept else "") + "]"
    return token


def markup_profile(value: str) -> dict[str, Counter]:
    concepts: Counter = Counter()
    brackets: Counter = Counter()
    for token in _BRACKET.findall(value):
        match = _CONCEPT_PLAIN.match(token) or _CONCEPT_CALL.match(token)
        if match:
            concepts[match.group(1)] += 1
        else:
            brackets[_normalize_bracket(token)] += 1
    rest = _BRACKET.sub(" ", value)
    return {
        "concept links": concepts,
        "[...] calls": brackets,
        "$...$ references": Counter(_DOLLAR.findall(rest)),
        "@icons!": Counter(_ICON.findall(rest)),
        "#format codes": Counter(_FORMAT_OPEN.findall(rest)),
        "#! closers": Counter({"#!": rest.count("#!")}),
        "\\n line breaks": Counter({"\\n": value.count("\\n")}),
    }


def check_translation(en: str, translated: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one translated value against its English."""
    errors, warnings = [], []
    if not translated.strip() and en.strip():
        return ["empty translation"], []
    en_profile, tr_profile = markup_profile(en), markup_profile(translated)
    for name, expected in en_profile.items():
        got = tr_profile[name]
        if expected != got:
            lost = expected - got
            added = got - expected
            detail = []
            if lost:
                detail.append("missing " + ", ".join(f"{k}×{n}" for k, n in lost.items()))
            if added:
                detail.append("extra " + ", ".join(f"{k}×{n}" for k, n in added.items()))
            errors.append(f"{name}: " + "; ".join(detail))
    # Characters, not words: German fuses compounds ("Ministry of Health" is
    # three words, "Gesundheitsministerium" one).
    en_plain, tr_plain = plain_text(en).strip(), plain_text(translated).strip()
    if word_count(en) >= 4 and en_plain == tr_plain:
        warnings.append("identical to English")
    elif len(en_plain) >= 20 and tr_plain and not 0.6 <= len(tr_plain) / len(en_plain) <= 2.2:
        warnings.append(f"length ratio {len(tr_plain) / len(en_plain):.2f}")
    return errors, warnings


# --------------------------------------------------------------------------
# Number format

# Languages that write 2,5 and 1.000 where English writes 2.5 and 1,000.
DECIMAL_COMMA = {"german", "french", "spanish", "braz_por", "polish", "russian", "turkish"}
_MARKUP = re.compile(r"\[[^\[\]]*\]|\$[^$]*\$|#[a-zA-Z_]+(?::\S*)?|@\w+!")
_EN_DECIMAL = re.compile(r"(?<![\w.,])\d+\.\d+(?![.,]?\d)")
_EN_THOUSANDS = re.compile(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?![.,]?\d)")


def _prose_segments(value: str) -> list[tuple[bool, str]]:
    """Split a value into (is_prose, text) runs; markup runs are left alone."""
    out, pos = [], 0
    for match in _MARKUP.finditer(value):
        out.append((True, value[pos:match.start()]))
        out.append((False, match.group(0)))
        pos = match.end()
    out.append((True, value[pos:]))
    return out


def localize_numbers(en: str, translated: str, language: str) -> str:
    """Rewrite the English-format numbers of `en` that the translation kept
    verbatim in its prose (2.5 -> 2,5, 1,000 -> 1.000). Numbers inside markup,
    and numbers the translator already converted, are left alone."""
    if language not in DECIMAL_COMMA:
        return translated
    prose = " ".join(text for is_prose, text in _prose_segments(en) if is_prose)
    swaps = {n: n.replace(".", ",") for n in _EN_DECIMAL.findall(prose)}
    swaps.update({n: n.replace(",", ".") for n in _EN_THOUSANDS.findall(prose)})
    if not swaps:
        return translated
    pattern = re.compile(r"(?<![\w.,])(" + "|".join(map(re.escape, sorted(swaps, key=len, reverse=True))) + r")(?![.,]?\d)")
    return "".join(
        pattern.sub(lambda m: swaps[m.group(1)], text) if is_prose else text
        for is_prose, text in _prose_segments(translated)
    )


# --------------------------------------------------------------------------
# Vanilla terms


def _load_vanilla(language: str) -> dict[str, str]:
    import path_constants

    root = os.path.join(path_constants.base_game_path, "game", "localization", language)
    values: dict[str, str] = {}
    for path in glob.glob(os.path.join(root, "**", "*.yml"), recursive=True):
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            for line in fh:
                parsed = split_loc_line(line)
                if parsed:
                    values[parsed[0]] = parsed[1]
    return values


class VanillaTerms:
    """Key-aligned vanilla English/target pairs, for per-chunk glossaries."""

    def __init__(self, language: str):
        self.en = _load_vanilla("english")
        self.tr = _load_vanilla(language)
        by_term: dict[str, Counter] = defaultdict(Counter)
        for key, en in self.en.items():
            tr = self.tr.get(key)
            if not tr or tr == en or en != en.strip() or not 1 <= len(en.split()) <= 4:
                continue  # (tr == en: a vanilla line left untranslated says nothing)
            if re.search(r"[\[\]$#@\\|]", en + tr) or not re.match(r"[A-Z]", en):
                continue
            # A lone word matched in free text misleads more than it helps: a
            # button label ("At"), a short form ("Capital" = Hauptsitz), or a
            # concept in another sense ("Order" = military Befehl). Concepts a
            # chunk actually links are listed under REFERENCED KEYS instead.
            # Law, interest-group, institution and ideology names are the
            # exception: distinctive single words ("Serfdom", "Intelligentsia").
            if " " not in en and not (
                key.startswith(("law_", "lawgroup_", "ig_", "institution_", "ideology_"))
                and re.fullmatch(r"[a-z_]+", key) and not key.endswith(("_short", "_name"))
            ):
                continue
            weight = 5 if key.startswith("concept_") else 1
            by_term[en][tr] += weight
        self.terms = {en: counts.most_common(1)[0][0] for en, counts in by_term.items()}


def referenced_keys(text: str) -> set[str]:
    keys = set(re.findall(r"concept_\w+", text))
    keys |= {m for m in re.findall(r"\$([a-z][a-z0-9_]*)\$", text)}
    keys |= set(re.findall(r"Get\w*Type\('(\w+)'\)", text))
    return keys


def load_terms(language: str) -> dict[str, str]:
    """`i18n/<language>/terms.json`: terms coined during translation runs
    (English -> translation), fed back into later chunks' glossaries so
    parallel agents render a recurring term the same way."""
    path = os.path.join(language_dirs(language)[0], "terms.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def chunk_glossary(chunk: list[Entry], tm: dict[str, dict], vanilla: VanillaTerms | None,
                   glossary_keys: set[str], lang_field: str, cap: int = 160,
                   terms: dict[str, str] | None = None) -> list[str]:
    text = "\n".join(e.en for e in chunk)
    in_chunk = {e.key for e in chunk}
    lines = []
    refs = sorted(referenced_keys(text) - in_chunk)
    ref_lines = []
    for key in refs:
        if key in tm:
            ref_lines.append(f"#   {key} = {tm[key][lang_field]}   (mod)")
        elif vanilla and key in vanilla.tr:
            ref_lines.append(f"#   {key} = {vanilla.tr[key]}")
    if ref_lines:
        lines.append("# REFERENCED KEYS — what these links and $references$ insert (nominative):")
        lines.extend(ref_lines[:cap])
    mod_terms = []
    for key in sorted(glossary_keys - in_chunk):
        record = tm.get(key)
        if record and " " not in record["en"].strip():
            continue  # a lone word ("Green", a veterancy level) is too ambiguous
        if record and record["en"] and re.search(r"(?<!\w)" + re.escape(record["en"]) + r"(?!\w)", text):
            mod_terms.append(f"#   {record['en']} => {record[lang_field]}")
    for en, tr in (terms or {}).items():
        if re.search(r"(?<!\w)" + re.escape(en) + r"(?!\w)", text):
            mod_terms.append(f"#   {en} => {tr}")
    if mod_terms:
        lines.append("# MOD TERMS — the mod's names, already fixed; use them wherever the English means that thing:")
        lines.extend(sorted(set(mod_terms), key=len, reverse=True)[:cap])
    if vanilla:
        hits = [t for t in vanilla.terms if t in text and re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text)]
        hits.sort(key=lambda t: (-len(t.split()), t))
        if hits:
            lines.append("# VANILLA TERMS — official German game terms; use them wherever the English means that thing:")
            lines.extend(f"#   {t} => {vanilla.terms[t]}" for t in hits[:cap])
    return lines


# --------------------------------------------------------------------------
# Chunking


def _group_stem(key: str) -> str:
    if "." in key:
        return key.rsplit(".", 1)[0]
    return re.sub(r"_(desc|tooltip|tt|flavor|short|plural|possessive|adj|ADJ|DESC|TOOLTIP)$", "", key)


def split_chunks(entries: list[Entry], budget: int, max_keys: int = 10**9) -> list[list[Entry]]:
    """Consecutive entries up to ~budget words or max_keys keys; never split a
    file mid-group (an event's .t/.d/.f/.a lines, a name and its _desc)."""
    chunks: list[list[Entry]] = []
    current: list[Entry] = []
    words = 0
    for entry in entries:
        boundary = (
            current
            and (words >= budget or len(current) >= max_keys)
            and (entry.file != current[-1].file or _group_stem(entry.key) != _group_stem(current[-1].key))
        )
        if boundary:
            chunks.append(current)
            current, words = [], 0
        current.append(entry)
        words += word_count(entry.en)
    if current:
        chunks.append(current)
    return chunks


def _loc_line(key: str, value: str) -> str:
    return f' {key}:0 "{value}"'


def write_chunk(path: str, chunk_id: str, chunk: list[Entry], glossary: list[str],
                country_names: list[Entry], language: str) -> None:
    lines = [
        f"# CHUNK {chunk_id} — translate into {language}. Instructions: i18n/{language}/BRIEF.md",
        f"# {len(chunk)} lines to translate" + (f", plus the declined forms of {len(country_names)} country names" if country_names else ""),
        "#",
        *glossary,
        "#",
        "# === LINES ===",
    ]
    current_file = None
    for entry in chunk:
        if entry.file != current_file:
            current_file = entry.file
            lines.append(f"# --- from {entry.file}")
        lines.append(_loc_line(entry.key, entry.en))
    if country_names:
        lines.append("#")
        lines.append("# === COUNTRY NAME FORMS === for each name below write "
                     + ", ".join(f"<KEY>_{f}" for f in COUNTRY_FORMS) + " (BRIEF.md § Country names)")
        for entry in country_names:
            lines.append(_loc_line(entry.key, entry.en))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------
# Commands


def cmd_prepare(args) -> int:
    language, lang_field = args.language, args.field
    entries = load_english()
    tm = load_tm(language)
    state = classify(entries, tm)
    pending = state["missing"] + state["stale_minor"] + state["stale_major"]
    order = {e.key: i for i, e in enumerate(entries)}
    pending.sort(key=lambda e: order[e.key])
    glossary_keys = {e.key for e in entries if is_glossary_entry(e)}

    country_names: list[Entry] = []
    if args.set == "names":
        pending = [e for e in pending if e.key in glossary_keys]
        country_names = [e for e in pending if is_country_name(e)]
    else:
        pending = [e for e in pending if e.key not in glossary_keys]
    if args.files:
        pending = [e for e in pending if any(os.path.basename(e.file).startswith(f) for f in args.files)]
    if not pending:
        print("Nothing to translate.")
        return 0

    budget = 10**9 if args.set == "names" else args.chunk_words
    chunks = split_chunks(pending, budget, 10**9 if args.set == "names" else args.max_keys)
    if args.limit:
        chunks = chunks[: args.limit]

    vanilla = None if args.no_vanilla else VanillaTerms(language)
    terms = load_terms(language)
    work = language_dirs(language)[1]
    chunk_dir = os.path.join(work, "chunks")
    manifest_path = os.path.join(work, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as fh:
            manifest = json.load(fh)
    prefix = "names" if args.set == "names" else "c"
    start = 1 + sum(1 for cid in manifest if cid.startswith(prefix + "-"))
    for n, chunk in enumerate(chunks, start=start):
        chunk_id = f"{prefix}-{n:03d}"
        glossary = chunk_glossary(chunk, tm, vanilla, glossary_keys, lang_field,
                                  cap=400 if args.set == "names" else 160, terms=terms)
        names_here = [e for e in country_names if e in chunk]
        write_chunk(os.path.join(chunk_dir, chunk_id + ".txt"), chunk_id, chunk, glossary, names_here, language)
        manifest[chunk_id] = {
            "keys": {e.key: e.en for e in chunk},
            "country_names": [e.key for e in names_here],
            "words": sum(word_count(e.en) for e in chunk),
        }
        print(f"{chunk_id}: {len(chunk)} keys, {manifest[chunk_id]['words']} words, "
              f"{len(glossary)} glossary lines -> {os.path.relpath(os.path.join(chunk_dir, chunk_id + '.txt'), REPO_ROOT)}")
    os.makedirs(work, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    return 0


def cmd_refresh(args) -> int:
    """Rebuild the given chunks' files (glossary header included) from the
    manifest, keeping each chunk's keys: picks up terms and TM entries added
    since `prepare`, for chunks no agent has started yet."""
    language, lang_field = args.language, args.field
    entries = load_english()
    by_key = {e.key: e for e in entries}
    tm = load_tm(language)
    glossary_keys = {e.key for e in entries if is_glossary_entry(e)}
    vanilla = VanillaTerms(language)
    terms = load_terms(language)
    work = language_dirs(language)[1]
    with open(os.path.join(work, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    for cid in args.chunks:
        chunk = [by_key[k] for k in manifest[cid]["keys"] if k in by_key]
        glossary = chunk_glossary(chunk, tm, vanilla, glossary_keys, lang_field, terms=terms)
        write_chunk(os.path.join(work, "chunks", cid + ".txt"), cid, chunk, glossary, [], language)
        print(f"{cid}: {len(chunk)} keys, {len(glossary)} glossary lines")
    return 0


def repair_bare_quotes(line: str) -> str | None:
    """The value of a line whose text runs on past a bare `"` (the model closed
    „a quotation" with a plain quote mark): everything up to the line's last
    `"`, with each bare `"` inside turned into „ or “ by whether a quotation
    is open. None if the line doesn't have that shape."""
    start = line.find('"', line.find(":"))
    end = line.rstrip().rfind('"')
    if start == -1 or end <= start:
        return None
    inner = line[start + 1:end]
    out, depth, i = [], 0, 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner):
            out.append(inner[i:i + 2])
            i += 2
            continue
        if c == "„":
            depth += 1
        elif c == "“":
            depth = max(0, depth - 1)
        elif c == '"':
            c = "“" if depth else "„"
            depth = depth - 1 if depth else 1
        out.append(c)
        i += 1
    return "".join(out)


def read_output(work: str, chunk_id: str) -> tuple[dict[str, str], set[str]]:
    """Every `key:0 "value"` line from the agent's output part files, and the
    keys whose line had to be repaired (`repair_bare_quotes`): text after the
    first closing quote, which the game's loader would cut at."""
    values: dict[str, str] = {}
    repaired: set[str] = set()
    for path in sorted(glob.glob(os.path.join(work, "out", chunk_id + ".*.txt"))):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                parsed = split_loc_line(line)
                if not parsed:
                    continue
                values[parsed[0]] = parsed[1]
                trailing = parsed[2].strip()
                if trailing and not trailing.startswith("#"):
                    fixed = repair_bare_quotes(line)
                    if fixed is not None:
                        values[parsed[0]] = fixed
                        repaired.add(parsed[0])
    return values, repaired


def cmd_merge(args) -> int:
    language, lang_field = args.language, args.field
    entries = load_english()
    by_key = {e.key: e for e in entries}
    tm = load_tm(language)
    work = language_dirs(language)[1]
    with open(os.path.join(work, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    chunk_ids = args.chunks or sorted(manifest)
    report = {}
    totals = Counter()
    for chunk_id in chunk_ids:
        output, repaired = read_output(work, chunk_id)
        if not output:
            continue
        info = manifest[chunk_id]
        source_en = info["keys"]
        expected = list(source_en)
        expected += [f"{k}_{form}" for k in info.get("country_names", []) for form in COUNTRY_FORMS]
        rejects, warns, accepted = {}, {}, 0
        for key in expected:
            if key not in output:
                rejects[key] = ["missing from output"]
                continue
            base = key if key in source_en else key.rsplit("_", 1)[0]
            if base not in by_key:
                rejects[key] = ["English key no longer exists"]
                continue
            en = source_en[base]
            value = output[key]
            if key == base:
                errors, warnings = check_translation(en, value)
            else:
                errors, warnings = ([] if value.strip() else ["empty translation"]), []
            if key in repaired:
                warnings = warnings + ['bare " inside the value, repaired to „…“']
            if errors:
                rejects[key] = errors
                continue
            if warnings:
                warns[key] = warnings
            record = {"en": en, lang_field: localize_numbers(en, value, language)}
            if key != base:
                record["base"] = base
            tm[key] = record
            accepted += 1
        extra = sorted(set(output) - set(expected))
        report[chunk_id] = {"accepted": accepted, "rejected": rejects, "warnings": warns, "unexpected_keys": extra}
        totals.update(accepted=accepted, rejected=len(rejects), warnings=len(warns))
        print(f"{chunk_id}: {accepted} accepted, {len(rejects)} rejected, {len(warns)} warnings"
              + (f", {len(extra)} unexpected keys" if extra else ""))
    save_tm(tm, entries, language)
    with open(os.path.join(work, "merge_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(f"Total: {totals['accepted']} accepted, {totals['rejected']} rejected, "
          f"{totals['warnings']} warnings. Report: {os.path.relpath(os.path.join(work, 'merge_report.json'), REPO_ROOT)}")
    return 1 if totals["rejected"] else 0


AGENT_PROMPT = """You are translating one chunk of a Victoria 3 mod's localization from English into {language_title}.

Files (absolute paths):
- Instructions, read in full first: {brief}
- Your chunk: {chunk} (a glossary header, then {lines} lines to translate{content})
- Write output to: {out}/ as {cid}.01.txt, {cid}.02.txt, … with at most {part} lines each.

Rules that override anything else:
- Write only inside the output folder. Don't edit, create or delete any other file, and don't run git or any script outside the output folder.
- Every output line has the form ` key:0 "translated value"`, with the same key as the input. No other text, no comments.
- Keep the markup exactly as BRIEF.md says; a script rejects any line whose markup differs.
- Work efficiently. Read the brief and the chunk once (the Read tool returns 2,000 lines at a time), then translate and write one part file at a time, keeping your reasoning before each write short: a single response over 64,000 output tokens fails the whole run. Do at most one quick check of your own output at the end. A merge script re-checks every line, so there's no need for repeated verification passes.

When done, reply with a short report (under 200 words): how many lines you wrote, any terms you coined that the glossary didn't cover (English → {language_title}), and any lines you were unsure about."""


def cmd_prompt(args) -> int:
    """Print the standard agent prompt for each chunk id given."""
    committed, work = language_dirs(args.language)
    with open(os.path.join(work, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    for cid in args.chunks:
        info = manifest[cid]
        words_per_line = info["words"] / max(1, len(info["keys"]))
        events = any("." in k for k in info["keys"])
        # Long event prose fills a response fast; short labels don't.
        part = 100 if events or words_per_line > 15 else 200
        print(AGENT_PROMPT.format(
            language_title=args.language.replace("_", " ").title(),
            brief=os.path.join(committed, "BRIEF.md"),
            chunk=os.path.join(work, "chunks", cid + ".txt"),
            lines=len(info["keys"]) + 7 * len(info.get("country_names", [])),
            content=", mostly event text" if events else "",
            out=os.path.join(work, "out"),
            cid=cid,
            part=part,
        ))
        print()
    return 0


def term_mismatches(tm: dict[str, dict], terms: dict[str, str], field: str) -> list[tuple[str, str, str]]:
    """(key, English term, expected rendering) for each translated line whose
    English uses a listed term but whose translation lacks that rendering.
    Inflection is allowed: each word of the rendering need only appear by its
    stem (all but its last three letters, at least four)."""
    out = []
    for en_term, rendering in terms.items():
        pattern = re.compile(r"(?<!\w)" + re.escape(en_term) + r"(?!\w)")
        stems = [w[: max(4, len(w) - 3)].casefold() for w in re.findall(r"\w+", rendering) if len(w) >= 4]
        for key, record in tm.items():
            if "base" in record or not pattern.search(record["en"]):
                continue
            text = record[field].casefold()
            if not all(stem in text for stem in stems):
                out.append((key, en_term, rendering))
    return sorted(out)


def cmd_check_terms(args) -> int:
    mismatches = term_mismatches(load_tm(args.language), load_terms(args.language), args.field)
    for key, en_term, rendering in mismatches:
        print(f"{key}: {en_term!r} should read {rendering!r}")
    print(f"{len(mismatches)} line(s) render a listed term differently.")
    return 1 if mismatches else 0


def cmd_status(args) -> int:
    entries = load_english()
    state = classify(entries, load_tm(args.language))
    for name in ("translated", "stale_minor", "stale_major", "missing", "skip"):
        group = state[name]
        print(f"{name:12} {len(group):6} keys {sum(word_count(e.en) for e in group):8} words")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--language", default="german")
    parser.add_argument("--field", default="de", help="TM field holding the translation")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--set", choices=("names", "all"), default="all")
    p.add_argument("--files", nargs="*", help="only English files whose name starts with one of these")
    p.add_argument("--limit", type=int, help="write at most this many chunks")
    p.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    p.add_argument("--max-keys", type=int, default=DEFAULT_MAX_KEYS,
                   help="also end a chunk at this many keys (label-heavy files)")
    p.add_argument("--no-vanilla", action="store_true", help="skip the vanilla glossary (no game install)")
    m = sub.add_parser("merge")
    m.add_argument("chunks", nargs="*")
    sub.add_parser("status")
    rf = sub.add_parser("refresh", help="rebuild unstarted chunks' glossaries from the manifest")
    rf.add_argument("chunks", nargs="+")
    sub.add_parser("check-terms", help="list translated lines that render a terms.json term differently")
    pr = sub.add_parser("prompt", help="print the standard agent prompt for chunks")
    pr.add_argument("chunks", nargs="+")
    args = parser.parse_args(argv)
    return {"prepare": cmd_prepare, "merge": cmd_merge, "status": cmd_status,
            "prompt": cmd_prompt, "check-terms": cmd_check_terms, "refresh": cmd_refresh}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
