"""gen_assimilation_cultures: the hybrid cultures, their heritage traits, the nine entries each needs, the loc, and
the ladder that saves the host language's hybrids.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m pytest test_gen_assimilation_cultures.py -q
"""

import json
import os
import re
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import assimilation_cultures_config as cfg  # noqa: E402
import culture_merges_config as cm_cfg  # noqa: E402
import gen_assimilation_cultures as gen  # noqa: E402
import gen_culture_merges as cm_gen  # noqa: E402
import organize_loc  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

BOM = b"\xef\xbb\xbf"
cultures = cm_gen.load_vanilla()
plan = cm_gen.build_plan(cultures)
PAIRS = cfg.pairs(cultures, plan)
VANILLA_LOC = json.loads((ROOT / "vanilla_parsed/localization_english.json").read_text(encoding="utf-8"))


def unwrap(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def parse(relative):
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / relative))
    return {key: unwrap(value) for key, value in parser.data.items()}


def text_of(relative):
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def generated_loc():
    """The generated loc file's entries, key -> text without its version number or quotes."""
    out = {}
    for line in text_of(gen.LOC_OUT).splitlines():
        m = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def blocks(text):
    """The top-level ``key = { ... }`` blocks of a script text, as (key, body) in order; comments dropped."""
    text = re.sub(r"#[^\n]*", "", text)
    out = []
    i = 0
    pattern = re.compile(r"([\w:.]+) = \{")
    while True:
        m = pattern.search(text, i)
        if not m:
            break
        depth, j = 1, m.end()
        while depth:
            depth += text[j] == "{"
            depth -= text[j] == "}"
            j += 1
        out.append((m.group(1), text[m.end():j - 1]))
        i = j
    return out


def ladder():
    """The branches of te_hcg_save_targets, as (keyword, body)."""
    effects = dict(blocks(text_of(gen.EFFECTS_OUT)))
    return blocks(effects[gen.SAVE_EFFECT])


def by_language():
    out = defaultdict(list)
    for pair in PAIRS:
        out[pair.language.key].append(pair)
    return out


class CulturesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cultures = parse(gen.CULTURES_OUT)

    def test_one_culture_per_pair_with_its_two_traits(self):
        self.assertEqual(len(PAIRS), 584)
        self.assertEqual(list(self.cultures), [pair.culture for pair in PAIRS])
        for pair in PAIRS:
            body = self.cultures[pair.culture]
            self.assertEqual(unwrap(body["language"]), "language_" + pair.language.key, pair.culture)
            self.assertEqual(unwrap(body["heritage"]), pair.group.heritage, pair.culture)

    def test_a_culture_takes_its_names_from_its_language_and_its_looks_from_its_group(self):
        merge_fields = {entry.merge.result: entry.fields for entry in plan}
        for pair in PAIRS:
            body = self.cultures[pair.culture]
            names = merge_fields.get(pair.language.names_from) or cm_gen.culture_fields(cultures[pair.language.names_from])
            looks = cm_gen.culture_fields(cultures[pair.group.looks_from])
            self.assertEqual(unwrap(body["religion"]), cm_gen.single(names, "religion", pair.culture))
            for name in cm_gen.NAME_LISTS:
                self.assertEqual(cm_gen.name_list(body, name), cm_gen.name_list(names, name), (pair.culture, name))
            self.assertEqual(unwrap(body.get("name_format")), unwrap(names.get("name_format")), pair.culture)
            self.assertEqual(unwrap(body["graphics"]), cm_gen.single(looks, "graphics", pair.culture))
            self.assertEqual(cm_gen.ethnicities(body), cm_gen.ethnicities(looks), pair.culture)

    def test_no_traditions_obsessions_taboos_or_assimilation_rate(self):
        for pair in PAIRS:
            body = self.cultures[pair.culture]
            self.assertEqual(unwrap(body["traditions"]), {}, pair.culture)
            for name in ("obsessions", "taboos", "assimilation_rate", "seal_and_signature_texture"):
                self.assertNotIn(name, body, (pair.culture, name))

    def test_each_culture_has_the_nine_entries_the_engine_expects(self):
        statics = parse(gen.STATIC_MODIFIERS_OUT)
        types = parse(gen.MODIFIER_TYPES_OUT)
        keys = [pair.culture for pair in PAIRS]
        self.assertEqual(set(statics), {k for c in keys for k in cm_gen.culture_static_modifier_keys(c)})
        self.assertEqual(set(types), {t for c in keys for t in cm_gen.culture_modifier_types(c)})
        for culture in keys:
            for key in cm_gen.culture_static_modifier_keys(culture):
                fields = [name for name in statics[key] if name != "icon"]
                self.assertEqual(len(fields), 1, key)
                self.assertIn(fields[0], types, key)

    def test_nine_heritage_traits_are_minted_in_their_vanilla_groups(self):
        traits = parse(gen.TRAITS_OUT)
        self.assertEqual(list(traits), [key for key, _ in cfg.minted_heritages()])
        self.assertEqual(len(traits), 9)
        vanilla_groups = {cm_cfg.trait_group(t, cultures) for t in cultures[cm_cfg.TRAITS_KEY]}
        for key, group in cfg.minted_heritages():
            body = {k: unwrap(v) for k, v in traits[key].items()}
            self.assertEqual(body, {"type": "heritage", "trait_group": "heritage_group_" + group}, key)
            self.assertIn("heritage_group_" + group, vanilla_groups, key)
            self.assertNotIn(key, cultures[cm_cfg.TRAITS_KEY])

    def test_colors_are_valid_and_differ_within_a_language(self):
        colors = {}
        for pair in PAIRS:
            raw = unwrap(self.cultures[pair.culture]["color"])
            m = re.fullmatch(r"rgb\{ (\d+) (\d+) (\d+) \}", raw)
            self.assertIsNotNone(m, (pair.culture, raw))
            rgb = tuple(int(v) for v in m.groups())
            self.assertTrue(all(0 <= v <= 255 for v in rgb), (pair.culture, rgb))
            colors[pair.culture] = rgb
        for language, members in by_language().items():
            seen = [colors[pair.culture] for pair in members]
            self.assertEqual(len(seen), len(set(seen)), language)

    def test_a_color_is_the_mean_of_its_two_reference_cultures(self):
        pair = next(p for p in PAIRS if p.culture == cfg.SENTINEL)
        british = gen.color_rgb(unwrap(cm_gen.culture_fields(cultures["british"])["color"]))
        hausa = gen.color_rgb(unwrap(cm_gen.culture_fields(cultures["hausa"])["color"]))
        self.assertEqual(gen.hybrid_color(pair, cultures, plan), tuple((a + b + 1) // 2 for a, b in zip(british, hausa)))
        latin = next(p for p in PAIRS if p.culture == "hc_cm_latin_african")
        latin_color = next(entry.merge.new.color for entry in plan if entry.merge.result == "cm_latin")
        self.assertEqual(gen.hybrid_color(latin, cultures, plan), tuple((a + b + 1) // 2 for a, b in zip(latin_color, hausa)))

    def test_the_color_reader_knows_vanillas_forms_and_refuses_the_rest(self):
        self.assertEqual(gen.color_rgb("rgb{ 62 77 100 }"), (62, 77, 100))
        self.assertEqual(gen.color_rgb("hsv{ 0 0 1 }"), (255, 255, 255))
        self.assertEqual(gen.color_rgb("hsv { 0.5 1 1 }"), (0, 255, 255))
        self.assertEqual(gen.color_rgb("hsv{ 0.70 0.43 0.47}"), gen.color_rgb("hsv{ 0.70 0.43 0.47 }"))
        self.assertEqual(gen.color_rgb("hsv360{ 180 100 100 }"), (0, 255, 255))
        self.assertEqual(gen.color_rgb(["71", "112", "80"]), (71, 112, 80))
        self.assertEqual(gen.color_rgb(["0.12", "0.41", "0.54"]), (31, 105, 138))
        # Japanese's grey past white reads as white; Mongo's color past white depends on the engine's clamping.
        self.assertEqual(gen.color_rgb("hsv{ 0 0 90 }"), (255, 255, 255))
        for bad in ("hex{ ff0000 }", "rgb{ 1 2 }", "rgb{ 1 2 300 }", "rgb{ 0.5 0.5 0.5 }", "hsv{ 0.01 0.47 67 }",
                    "hsv{ 2 0 1 }", ["0", "0.5", "1"], ["1.5", "0.5", "0.5"], "red", None, {"r": 1}):
            with self.subTest(bad), self.assertRaises(ValueError):
                gen.color_rgb(bad)
        unread = []
        for culture, body in cultures.items():
            if culture != cm_cfg.TRAITS_KEY:
                try:
                    gen.color_rgb(unwrap(cm_gen.culture_fields(body)["color"]))
                except ValueError:
                    unread.append(culture)
        self.assertEqual(unread, ["mongo"])  # a vanilla patch that changes this wants a look
        references = {lang.names_from for lang in cfg.languages(plan)} | {group.looks_from for group in cfg.GROUPS}
        self.assertNotIn("mongo", references)


class LadderTest(unittest.TestCase):
    def test_the_effect_file_holds_the_one_effect(self):
        self.assertEqual([key for key, _ in blocks(text_of(gen.EFFECTS_OUT))], [gen.SAVE_EFFECT])

    def test_the_ladder_has_a_branch_per_language_in_roster_order(self):
        branches = ladder()
        self.assertEqual(len(branches), 64)
        self.assertEqual([key for key, _ in branches], ["if"] + ["else_if"] * 63)
        spoken = [re.findall(r"has_discrimination_trait = language_(\w+)", body) for _, body in branches]
        self.assertEqual(spoken, [[language.key] for language in cfg.languages(plan)])

    def test_a_branch_saves_every_hybrid_of_its_language_and_no_other(self):
        groups = by_language()
        for (_, body), language in zip(ladder(), cfg.languages(plan)):
            saved = re.findall(r"cu:(\w+) = \{ save_temporary_scope_as = (\w+) \}", body)
            self.assertEqual(saved, [(p.culture, "te_hc_t_" + p.group.key) for p in groups[language.key]], language.key)
            self.assertEqual(len(re.findall(r"save_temporary_scope_as", body)), len(saved), language.key)
            self.assertEqual(re.findall(r"set_local_variable = \{ name = (\w+) value = (\d+) \}", body),
                             [("te_hc_has_targets", "1")], language.key)

    def test_every_branch_is_guarded_by_exists_on_its_first_hybrid(self):
        groups = by_language()
        for (_, body), language in zip(ladder(), cfg.languages(plan)):
            limit = dict(blocks(body))["limit"]
            first = groups[language.key][0].culture
            self.assertEqual(re.findall(r"exists = cu:(\w+)", limit), [first], language.key)
            self.assertEqual(re.findall(r"scope:(\w+) = \{ has_discrimination_trait = (\w+) \}", limit),
                             [("te_hc_host", "language_" + language.key)], language.key)
            # Nothing is saved or set before the guard.
            self.assertTrue(body.strip().startswith("limit = {"), language.key)

    def test_the_effect_sets_nothing_outside_its_branches(self):
        effect = dict(blocks(text_of(gen.EFFECTS_OUT)))[gen.SAVE_EFFECT]
        outside = effect
        for key, body in blocks(effect):
            outside = outside.replace(body, "")
        self.assertNotIn("save_temporary_scope_as", outside)
        self.assertNotIn("set_local_variable", outside)

    def test_the_generated_script_names_no_culture_but_hc(self):
        for relative in (gen.CULTURES_OUT, gen.TRAITS_OUT, gen.STATIC_MODIFIERS_OUT, gen.MODIFIER_TYPES_OUT, gen.EFFECTS_OUT):
            tokens = re.findall(r"cu:\w+", re.sub(r"#[^\n]*", "", text_of(relative)))
            self.assertTrue(all(token.startswith("cu:hc_") for token in tokens), relative)
        self.assertTrue(re.findall(r"cu:\w+", text_of(gen.EFFECTS_OUT)))


class LocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = generated_loc()

    def test_every_culture_trait_and_static_modifier_is_named(self):
        expected = {pair.culture for pair in PAIRS} | {key for key, _ in cfg.minted_heritages()}
        expected |= set(cm_gen.static_modifier_loc_for([pair.culture for pair in PAIRS]))
        self.assertEqual(set(self.loc), expected)
        for key, text in cm_gen.static_modifier_loc_for([pair.culture for pair in PAIRS]).items():
            self.assertEqual(self.loc[key], text, key)

    def test_names_are_spliced_or_an_override_word(self):
        for pair in PAIRS:
            language = pair.language.word or "$language_%s$" % pair.language.key
            group = pair.group.word or "$heritage_group_%s$" % pair.group.key
            self.assertEqual(self.loc[pair.culture], "%s %s" % (language, group), pair.culture)
        for key, group in cfg.minted_heritages():
            self.assertEqual(self.loc[key], "$heritage_group_%s$ Diaspora" % group, key)
        # No language's or group's vanilla display name is spelled, and no word repeats vanilla's own.
        names = {VANILLA_LOC["language_" + lang.key] for lang in cfg.languages(plan) if "language_" + lang.key in VANILLA_LOC}
        names |= {VANILLA_LOC["heritage_group_" + group.key] for group in cfg.GROUPS}
        for key, text in self.loc.items():
            plain = re.sub(r"\$[\w.\-]+\$", "", text)
            for name in names:
                self.assertNotRegex(plain, r"\b%s\b" % re.escape(name), key)
        for language in cfg.languages(plan):
            if language.word:
                self.assertNotEqual(language.word, VANILLA_LOC.get("language_" + language.key), language.key)

    def test_every_splice_resolves(self):
        merge_loc = cm_gen.result_loc_keys()
        for key, text in self.loc.items():
            for splice in re.findall(r"\$([\w.\-]+)\$", text):
                self.assertTrue(splice in VANILLA_LOC or splice in merge_loc or splice in self.loc, (key, splice))

    def test_organize_loc_files_every_generated_key_in_its_category(self):
        self.assertIn(gen.LOC_CATEGORY, organize_loc.CATEGORIES)
        self.assertIn("gen_assimilation_cultures.py", organize_loc.GENERATED_CATEGORIES[gen.LOC_CATEGORY])
        self.assertEqual(gen.LOC_OUT.name, "te_%s_l_english.yml" % gen.LOC_CATEGORY.lower())
        for key in self.loc:
            self.assertEqual(organize_loc.categorize_key(key, set()), gen.LOC_CATEGORY, key)
        # Ahead of the `_add` / `_mult` rule: a culture key ending that way stays here.
        self.assertEqual(organize_loc.categorize_key("hc_x_cultural_acceptance_add", set()), gen.LOC_CATEGORY)


class FilesTest(unittest.TestCase):
    def test_the_outputs_are_current(self):
        self.assertFalse(gen.regenerate(dry_run=True)["changed"])

    def test_one_bom_and_the_header(self):
        for relative in gen.plan_outputs():
            data = (ROOT / relative).read_bytes()
            self.assertTrue(data.startswith(BOM), relative)
            self.assertFalse(data[3:].startswith(BOM), relative)
            if relative.suffix == ".txt":
                self.assertTrue(data[3:].decode("utf-8").startswith(gen.HEADER), relative)

    def test_regenerate_writes_on_change_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.symlink(ROOT / "vanilla_parsed", root / "vanilla_parsed")
            first = gen.regenerate(root=root)
            self.assertTrue(first["changed"])
            self.assertEqual(sorted(first["changed_files"]), sorted(str(p) for p in gen.plan_outputs(root)))
            self.assertFalse(gen.regenerate(root=root)["changed"])
            victim = root / gen.EFFECTS_OUT
            victim.write_bytes(victim.read_bytes() + b"# edited\n")
            self.assertTrue(gen.regenerate(root=root, dry_run=True)["changed"])
            self.assertTrue(victim.read_bytes().endswith(b"# edited\n"))
            self.assertTrue(gen.regenerate(root=root)["changed"])
            self.assertFalse(gen.regenerate(root=root)["changed"])

    def test_the_old_generator_and_its_value_are_gone(self):
        self.assertFalse((ROOT / "scripts/generators/assimilation_cultures.py").exists())
        self.assertNotIn("pop_culture_conversion_propotion_script_value",
                         text_of("common/script_values/extra_script_values.txt"))
        self.assertNotIn("scripts/generators/assimilation_cultures.py", (ROOT / "README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
