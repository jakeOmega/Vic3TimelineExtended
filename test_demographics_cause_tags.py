"""Causes of Death's tags (owner, 2026-10-22): every state-level mortality line the census leaves on top carries a
script-only copy of its value naming the cause its deaths count under (demographics_params.DEATH_CAUSE_TAGS), so the
section can show the deaths the game adds on top of the census under their causes rather than as a slice of their own.
Vanilla's carriers are tagged by gen_demographics.py's INJECTs, the mod's own by hand beside the line."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import demographics_params as P  # noqa: E402
import gen_demographics as G  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

FIELD = "state_mortality_mult"
# common/ folders that hold script, not carriers: they read the field or apply the census's own terms
SCRIPT_FOLDERS = {"scripted_effects", "script_values", "scripted_triggers", "on_actions", "modifier_type_definitions",
                  "scripted_guis", "scripted_buttons", "history", "defines"}
TAG_TYPES = set(P.DEATH_CAUSE_TYPES.values())


def _value(v):
    while isinstance(v, (list, tuple)):
        v = v[-1]
    return v


def _blocks(body, path=()):
    """(path, block) for every dict in a parsed body that holds the mortality field or a tag, the body itself included."""
    if isinstance(body, (list, tuple)):
        for v in body:
            yield from _blocks(v, path)
        return
    if not isinstance(body, dict):
        return
    if FIELD in body or TAG_TYPES & set(body):
        yield path, body
    for k, v in body.items():
        yield from _blocks(v, path + (k,))


def _vanilla_carriers():
    out = {}
    for f in sorted((ROOT / "vanilla_parsed" / "common").glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for name, body in data.get("data", data).items():
            if any(FIELD in b for _p, b in _blocks(body)):
                out[name] = f.stem
    return out


def _mod_entities():
    """{name: (directive, folder, body)} across the mod's data folders."""
    out = {}
    for path in sorted((ROOT / "common").rglob("*.txt")):
        folder = path.relative_to(ROOT / "common").parts[0]
        if folder in SCRIPT_FOLDERS:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if FIELD not in text and "state_death_cause_" not in text and "REPLACE:" not in text:
            continue
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        for key, body in parser.data.items():
            directive, _, name = key.rpartition(":")
            out.setdefault(name, []).append((directive, path.name, body))
    return out


class TestCauseTags(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = _vanilla_carriers()
        cls.mod = _mod_entities()

    def _mod_carriers(self):
        """Names whose mod definition (a plain one, a REPLACE or an INJECT) holds the mortality field outside the
        generated tag files."""
        return {name for name, defs in self.mod.items()
                for _d, fname, body in defs
                if fname != G.CAUSE_TAGS_FILE and any(FIELD in b for _p, b in _blocks(body))}

    def _replaced_away(self):
        """Vanilla carriers the mod REPLACEs without the field: not carriers in game."""
        return {name for name in self.vanilla
                for d, _f, body in self.mod.get(name, [])
                if d == "REPLACE" and not any(FIELD in b for _p, b in _blocks(body))}

    def test_every_carrier_has_a_cause(self):
        carriers = (set(self.vanilla) - self._replaced_away()) | self._mod_carriers()
        known = set(P.DEATH_CAUSE_OF) | P.DEATH_CAUSE_UNTAGGED
        self.assertEqual(sorted(carriers - known), [], "a mortality line with no cause: tag it in DEATH_CAUSE_TAGS")
        self.assertEqual(sorted(known - carriers), [], "a tag or exception on something that carries no mortality line")

    def test_each_tag_sits_beside_its_line_at_its_value(self):
        """In the generated INJECT or the mod's own block, the tag is the line's value on its cause's type: the engine
        then scales them alike. Pollution's tag is vanilla's 0.5 plus the mod's INJECTed 0.05."""
        vanilla_field = {}
        for name, db in self.vanilla.items():
            data = json.loads((ROOT / "vanilla_parsed" / "common" / f"{db}.json").read_text(encoding="utf-8"))
            body = data.get("data", data)[name]
            vanilla_field[name] = {p: float(_value(b[FIELD])) for p, b in _blocks(body) if FIELD in b}
        tagged = {}
        for name, defs in self.mod.items():
            for _d, _f, body in defs:
                for p, b in _blocks(body):
                    for t in TAG_TYPES & set(b):
                        tagged.setdefault(name, []).append((p[1:] if p and p[0] == "=" else p, t, float(_value(b[t])),
                                                            float(_value(b[FIELD])) if FIELD in b else None))
        for name, cause in P.DEATH_CAUSE_OF.items():
            with self.subTest(name=name):
                rows = tagged.get(name, [])
                self.assertEqual(len(rows), 1, rows)
                path, t, value, own = rows[0]
                self.assertEqual(t, P.DEATH_CAUSE_TYPES[cause])
                base = sum(v for v in vanilla_field.get(name, {}).values())
                if own is None:
                    self.assertAlmostEqual(value, base, places=6)        # a generated INJECT: vanilla's line
                else:
                    injected = any(d == "INJECT" for d, _f, _b in self.mod[name])
                    self.assertAlmostEqual(value, own + (base if injected else 0.0), places=6)

    def test_the_tags_are_census_types(self):
        """In the census's types file, so a release without the census comments them out with the rest."""
        text = (ROOT / "common" / "modifier_type_definitions" / "demographics_modifier_types.txt").read_text(
            encoding="utf-8-sig")
        for t in TAG_TYPES:
            self.assertRegex(text, rf"(?m)^{t} = \{{[^}}]*script_only = yes")
            self.assertNotIn("state_demog_", t)

    def test_the_generated_injects_are_current(self):
        for folder, path in G.CAUSE_TAGS.items():
            with self.subTest(path=str(path)):
                self.assertEqual((ROOT / path).read_text(encoding="utf-8-sig"), G.render_cause_tags(folder, ROOT))
        lines = G.cause_tag_lines(ROOT)
        self.assertIn(("state_region_devastation", None, "war", 1.0), lines["static_modifiers"])
        self.assertNotIn("state_region_pollution_health", [r[0] for r in lines["static_modifiers"]],
                         "the mod's own INJECT of pollution carries its tag")

    def test_the_tags_have_loc(self):
        loc = (ROOT / "localization" / "english" / "te_modifiers_l_english.yml").read_text(encoding="utf-8-sig")
        for t in TAG_TYPES:
            self.assertRegex(loc, rf'(?m)^ {t}:0 "Counted in Causes of Death under ')
            self.assertRegex(loc, rf"(?m)^ {t}_desc:0 ")

    def test_the_self_check_reads_the_tags_against_the_lines_on_top(self):
        """TE_SELF_CHECK cause_tags_read: once a game, from the refresh's deaths term under Full, the first state whose
        lines on top come to a tenth either way; the play-test list names it."""
        text = (ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt").read_text(encoding="utf-8-sig")
        body = text.split("te_debug_demog_cause_tags_selfcheck = {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("NOT = { has_global_variable = te_demog_selfcheck_tags_done }", body)
        self.assertIn("set_global_variable = { name = te_demog_selfcheck_tags_done value = yes }", body)
        self.assertIn("te_debug_demog_selfchecks_run = yes", body)
        self.assertIn("local_var:te_dg_rate_os >= 0.1", body)
        for t in TAG_TYPES:
            self.assertIn(f"modifier:{t}", body)
        self.assertEqual(body.count("TE_SELF_CHECK OK cause_tags_read"), 1)
        self.assertEqual(body.count("TE_SELF_CHECK BROKEN cause_tags_read"), 1)
        self.assertNotRegex(body, r"[<>]=? \{", "no comparison with an inline value block")
        rates = (ROOT / "common" / "scripted_effects" / "te_demog_rate_effects.txt").read_text(encoding="utf-8-sig")
        refresh = rates.split("te_demog_rates_refresh = {", 1)[1]
        self.assertLess(refresh.index("set_variable = { name = te_dg_os_d value = local_var:te_dg_rate_os }"),
                        refresh.index("te_debug_demog_cause_tags_selfcheck = yes"))
        doc = (ROOT / "docs" / "testing" / "demographics-playtest.md").read_text(encoding="utf-8")
        self.assertIn("cause_tags_read", doc)


if __name__ == "__main__":
    unittest.main()
