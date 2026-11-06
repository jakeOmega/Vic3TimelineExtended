"""A law variant carries what the mod adds to its parent (#1406).

Vanilla's flavor variants (`parent = law_x`: Shinsengumi for Secret Police,
Bakufu for Autocracy, the Millet System for State Religion, ...) take their
parent's ideology stances but none of its modifiers. So a line the mod injects
into a parent's `modifier` or `institution_modifier` block reaches no country
on a variant unless the variant is injected too, and nothing logs it. Before
#1406, ten variants missed lines their parents carry: Shinsengumi had none
of Secret Police's tourism, intelligence or colonial lines, and Bakufu and
Neo-Absolutism none of Autocracy's colonial or standard-of-living ones.

The same goes for anything the mod gates on a parent. `unlocking_laws` and
`disallowing_laws` name laws one by one, so a list that names Secret Police
names each of its variants too (the Ministries of Propaganda and Thought
Control named none of Secret Police's three until #1406, nor did the
Consciousness Network's methods).

The checks, over `common/laws/*.txt`, `common/production_methods/*.txt` and
the committed `vanilla_parsed/` laws and methods:
  * every key the mod adds to a parent law's `modifier` or
    `institution_modifier` (an `INJECT`'s keys, or a `REPLACE`'s keys vanilla's
    law lacks) is in each variant's block of the same name, vanilla's or the
    mod's (values may differ: Women in the Fields takes Women Own Property's).
    A variant with no `institution` has nothing to scale an
    `institution_modifier`, so it carries the parent's institution lines in its
    `modifier` block instead, as vanilla's Shinsengumi does;
  * every `unlocking_laws` / `disallowing_laws` entry the mod writes in a law
    or a production method that names a parent sits beside each of the
    parent's variants.

A gap that is deliberate is excused by
`# REVIEWED YYYY-MM-DD (law_variant_parity): rationale` on the parent's key
line (for every variant) or on the list's entry line.
"""
from __future__ import annotations

import glob
import json
import os
import re
import unittest
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
BLOCKS = ("modifier", "institution_modifier")
LISTS = ("unlocking_laws", "disallowing_laws")
_ENTITY_RE = re.compile(r"^(?:(?P<prefix>[A-Z_]+):)?(?P<name>[a-z][a-z0-9_]*)\s*=\s*\{", re.M)
_FIELD_RE = re.compile(r"(?<![A-Za-z0-9_])(?P<field>[a-z_]+)\s*=\s*\{")
_ASSIGN_RE = re.compile(r"(?<![A-Za-z0-9_])([a-z_0-9]+)\s*=")
_REVIEWED_RE = re.compile(r"#\s*REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(law_variant_parity\)\s*:\s*\S")
_REPLACING = {"", "REPLACE", "REPLACE_OR_CREATE", "TRY_REPLACE"}


def _blank_comments(text: str) -> str:
    """Comments become spaces, so offsets (and line numbers) survive."""
    return re.sub(r"#[^\n]*", lambda m: " " * len(m.group(0)), text)


def _close(text: str, open_brace: int) -> int:
    """Index of the `}` matching the `{` at open_brace."""
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced braces")


def _top_fields(text: str, start: int, end: int):
    """(field, body_start, body_end) for each `field = {` directly inside text[start:end]."""
    i = start
    while True:
        m = _FIELD_RE.search(text, i, end)
        if not m:
            return
        open_brace = m.end() - 1
        close = _close(text, open_brace)
        yield m.group("field"), open_brace + 1, close
        i = close + 1


def _unwrap(value):
    while isinstance(value, list) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


class _Law:
    def __init__(self):
        self.parent: str | None = None
        self.added = {b: set() for b in BLOCKS}       # keys the mod adds
        self.present = {b: set() for b in BLOCKS}     # keys the law ends up with
        self.lists = {k: set() for k in LISTS}        # entries the law ends up with
        self.mod_entries = []                         # (list, law, file, line) the mod writes
        self.key_lines = defaultdict(list)            # (block, key) -> [(file, line)]
        self.replaced = False
        self.institution: str | None = None


def _entities(folder: str, snapshot: str) -> dict[str, _Law]:
    """Every entity in common/<folder>/*.txt over vanilla_parsed/common/<snapshot>."""
    with open(os.path.join(REPO, "vanilla_parsed", "common", snapshot), encoding="utf-8") as fh:
        vanilla = {name: _unwrap(value) for name, value in json.load(fh).items()}

    def vanilla_keys(name: str, block: str) -> set[str]:
        body = vanilla.get(name)
        value = _unwrap(body.get(block)) if isinstance(body, dict) else None
        return set(value) if isinstance(value, dict) else set()

    def vanilla_list(name: str, field: str) -> set[str]:
        body = vanilla.get(name)
        value = _unwrap(body.get(field)) if isinstance(body, dict) else None
        if isinstance(value, dict):
            return set(value)
        if isinstance(value, list):
            return {v for v in value if isinstance(v, str)}
        return set()

    laws: dict[str, _Law] = defaultdict(_Law)
    for name, body in vanilla.items():
        if isinstance(body, dict):
            if "parent" in body:
                laws[name].parent = _unwrap(body["parent"])
            if "institution" in body:
                laws[name].institution = _unwrap(body["institution"])

    sources: list[tuple[str, str, str, str]] = []
    for path in sorted(glob.glob(os.path.join(REPO, "common", folder, "*.txt"))):
        with open(path, encoding="utf-8-sig") as fh:
            raw = fh.read()
        sources.append((os.path.relpath(path, REPO), raw, _blank_comments(raw), path))

    for rel, raw, text, _path in sources:
        raw_lines = raw.splitlines()
        for m in _ENTITY_RE.finditer(text):
            prefix, name = m.group("prefix") or "", m.group("name")
            law = laws[name]
            close = _close(text, m.end() - 1)
            replacing = prefix in _REPLACING
            body = text[m.end():close]
            if replacing:
                law.replaced = True
                pm = re.search(r"(?<![a-z_])parent\s*=\s*(law_[a-z0-9_]+)", body)
                law.parent = pm.group(1) if pm else None
                law.institution = None
            im = re.search(r"(?<![a-z_])institution\s*=\s*([a-z0-9_]+)", body)
            if im:
                law.institution = im.group(1)
            for field, b_start, b_end in _top_fields(text, m.end(), close):
                if field in BLOCKS:
                    for km in _ASSIGN_RE.finditer(text, b_start, b_end):
                        key = km.group(1)
                        line = text.count("\n", 0, km.start()) + 1
                        law.present[field].add(key)
                        if not (replacing and key in vanilla_keys(name, field)):
                            law.added[field].add(key)
                            law.key_lines[(field, key)].append((rel, raw_lines[line - 1]))
                elif field in LISTS:
                    for em in re.finditer(r"law_[a-z0-9_]+", text[b_start:b_end]):
                        line = text.count("\n", 0, b_start + em.start()) + 1
                        law.lists[field].add(em.group(0))
                        law.mod_entries.append((field, em.group(0), rel, raw_lines[line - 1]))

    # What an entity ends up with: vanilla's, unless the mod replaces it, plus the mod's.
    for name, law in laws.items():
        if not law.replaced and name in vanilla:
            for block in BLOCKS:
                law.present[block] |= vanilla_keys(name, block)
            for field in LISTS:
                law.lists[field] |= vanilla_list(name, field)
    return laws


def load_laws() -> dict[str, _Law]:
    return _entities("laws", "laws.json")


def load_methods() -> dict[str, _Law]:
    return _entities("production_methods", "pms.json")


def variants(laws: dict[str, _Law]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for name, law in laws.items():
        if law.parent:
            out[law.parent].append(name)
    return {parent: sorted(kids) for parent, kids in out.items()}


def modifier_gaps(laws: dict[str, _Law]) -> list[str]:
    gaps = []
    for parent, kids in sorted(variants(laws).items()):
        for block in BLOCKS:
            for key in sorted(laws[parent].added[block]):
                if any(_REVIEWED_RE.search(line) for _rel, line in laws[parent].key_lines[(block, key)]):
                    continue
                for kid in kids:
                    # No institution to scale it: the line belongs in the plain modifier.
                    carried = block if block == "modifier" or laws[kid].institution else "modifier"
                    if key not in laws[kid].present[carried]:
                        where = laws[parent].key_lines[(block, key)][0][0]
                        gaps.append(f"{kid} lacks {parent}'s {block} line {key} ({where})")
    return gaps


def list_gaps(laws: dict[str, _Law], entities: dict[str, _Law] | None = None) -> list[str]:
    """Gating-list gaps in `entities` (the laws themselves by default)."""
    kids_of = variants(laws)
    gaps = []
    for name, law in sorted((entities if entities is not None else laws).items()):
        for field, entry, rel, line in law.mod_entries:
            if entry not in kids_of or _REVIEWED_RE.search(line):
                continue
            missing = [kid for kid in kids_of[entry] if kid not in law.lists[field]]
            if missing:
                gaps.append(f"{name}'s {field} names {entry} but not {', '.join(missing)} ({rel})")
    return sorted(set(gaps))


class LawVariantParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.laws = load_laws()

    def test_variants_carry_their_parents_mod_lines(self):
        gaps = modifier_gaps(self.laws)
        self.assertEqual(gaps, [], "inject each line into the variant too, or mark the parent's "
                                   "line # REVIEWED YYYY-MM-DD (law_variant_parity): why")

    def test_gating_lists_name_every_variant(self):
        gaps = list_gaps(self.laws)
        self.assertEqual(gaps, [], "name the variants beside their parent, or mark the entry "
                                   "# REVIEWED YYYY-MM-DD (law_variant_parity): why")

    def test_production_method_lists_name_every_variant(self):
        gaps = list_gaps(self.laws, load_methods())
        self.assertEqual(gaps, [], "name the variants beside their parent, or mark the entry "
                                   "# REVIEWED YYYY-MM-DD (law_variant_parity): why")

    def test_a_variant_without_an_institution_carries_institution_lines_flat(self):
        # Vanilla's Shinsengumi has no institution; Okhrana has Home Affairs.
        self.assertIsNone(self.laws["law_shinsengumi"].institution)
        self.assertEqual(self.laws["law_okhrana"].institution, "institution_home_affairs")
        self.assertIn("country_colonial_garrison_effectiveness_add",
                      self.laws["law_secret_police"].added["institution_modifier"])
        self.assertIn("country_colonial_garrison_effectiveness_add",
                      self.laws["law_shinsengumi"].present["modifier"])

    def test_the_scan_sees_the_known_variants_and_lines(self):
        # Guards the scanner: these are what #1406 found and fixed.
        kids = variants(self.laws)
        self.assertIn("law_shinsengumi", kids["law_secret_police"])
        self.assertIn("law_millet_system", kids["law_state_religion"])
        self.assertIn("goods_output_tourism_mult", self.laws["law_secret_police"].added["modifier"])
        self.assertIn("goods_output_tourism_mult", self.laws["law_shinsengumi"].present["modifier"])
        self.assertIn("law_okhrana", self.laws["law_ministry_of_propaganda"].lists["unlocking_laws"])

    def test_a_replaced_laws_vanilla_lines_are_not_mod_lines(self):
        # Subjecthood is REPLACEd; its assimilation line is vanilla's own, which
        # Official Nationality was written without.
        subjecthood = self.laws["law_subjecthood"]
        self.assertTrue(subjecthood.replaced)
        self.assertNotIn("state_assimilation_mult", subjecthood.added["modifier"])
        self.assertIn("country_cultural_pull_mult", subjecthood.added["modifier"])


class ScannerTests(unittest.TestCase):
    def test_nested_modifier_blocks_are_not_read_as_the_laws(self):
        text = "law_x = {\n\tai_enact_weight_modifier = {\n\t\tmodifier = { a = 1 }\n\t}\n\tmodifier = { b = 1 }\n}\n"
        fields = [f for f, _s, _e in _top_fields(text, text.index("{") + 1, _close(text, text.index("{")))]
        self.assertEqual(fields, ["ai_enact_weight_modifier", "modifier"])

    def test_reviewed_tag_must_name_this_check(self):
        self.assertTrue(_REVIEWED_RE.search("\tk = 1 # REVIEWED 2026-11-05 (law_variant_parity): parent only"))
        self.assertFalse(_REVIEWED_RE.search("\tk = 1 # REVIEWED 2026-11-05: parent only"))


if __name__ == "__main__":
    unittest.main()
