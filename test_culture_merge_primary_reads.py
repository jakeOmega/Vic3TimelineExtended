"""A switched part leaves the primary cultures once nothing is tied to it (owner, 2026-11-09).

The inventory of vanilla's reads (``culture_merge_primary_reads``), the ledger that turns them into holds
(``culture_merge_primary_ledger``), and what ``gen_culture_merges`` writes from the two: the hold trigger per culture,
the chain resolution, the strip of a never-begun merge's culture, the tradition carry-over, the formables' definition
lists and the restated vanilla trigger. The removal line itself is pinned in ``test_culture_merge_switch.py``.
"""

import json
import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merge_primary_ledger as ledger  # noqa: E402
import culture_merge_primary_reads as reads  # noqa: E402
import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402

GEN_TRIGGERS = ROOT / gen.TRIGGERS_GEN_OUT
GEN_EFFECTS = ROOT / gen.EFFECTS_GEN_OUT
DEFINITIONS = ROOT / gen.DEFINITIONS_OUT
VANILLA_TRIGGERS = ROOT / gen.VANILLA_TRIGGERS_OUT
GOVERNMENT_TYPES = ROOT / gen.GOVERNMENT_TYPES_OUT
ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_on_actions.txt"


def text_of(path):
    return Path(path).read_text(encoding="utf-8-sig")


def squash(text):
    return " ".join(re.sub(r"#[^\n]*", "", text).split())


def block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    match = re.search(r"^%s = \{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("no block %s" % name)
    depth, index = 1, match.end()
    while depth:
        depth += text[index] == "{"
        depth -= text[index] == "}"
        index += 1
    return text[match.end():index - 1]


def new_results():
    return {merge.result for merge in cfg.MERGES if merge.new is not None}


class ScanTest(unittest.TestCase):
    PARTS = frozenset({"north_german", "serb"})

    def scan(self, text):
        return [(entity, part) for entity, part, _line in reads.scan_text(text, self.PARTS)]

    def test_a_plain_read(self):
        self.assertEqual(
            self.scan("je_x = {\n\tpossible = {\n\t\tcountry_has_primary_culture = cu:north_german\n\t}\n}\n"),
            [("je_x", "north_german")],
        )

    def test_a_block_over_several_lines(self):
        text = "names = {\n\ttrigger = {\n\t\tany_primary_culture = {\n\t\t\tOR = {\n\t\t\t\tthis = cu:serb\n\t\t\t\tthis = cu:greek\n\t\t\t}\n\t\t}\n\t}\n}\n"
        self.assertEqual(self.scan(text), [("names", "serb")])

    def test_is_primary_culture_of(self):
        self.assertEqual(self.scan("ev.1 = {\n\tcu:serb = { is_primary_culture_of = root }\n}\n"), [("ev.1", "serb")])

    def test_what_is_not_a_read(self):
        for text in (
            "e = { add_primary_culture = cu:serb }",
            "e = { remove_primary_culture = cu:serb }",
            "e = { has_pop_culture = serb }",
            "e = { culture = cu:serb }",
            "e = { country_has_primary_culture = cu:greek }",
            "e = { # country_has_primary_culture = cu:serb\n}",
            "e = { any_scope_state = { is_homeland = cu:serb } }",
        ):
            self.assertEqual(self.scan(text), [], text)

    def test_a_read_after_a_list_block_keeps_its_entity(self):
        text = "e = {\n\tstates = { STATE_A STATE_B }\n\tpossible = { country_has_primary_culture = cu:serb }\n}\nf = { country_has_primary_culture = cu:serb }\n"
        self.assertEqual(self.scan(text), [("e", "serb"), ("f", "serb")])

    def test_the_trace_stops_at_journal_entries(self):
        index = {
            "ev.1": {("common/journal_entries/a.txt", "je_a"), ("events/x.txt", "ev.2")},
            "ev.2": {("common/journal_entries/b.txt", "je_b")},
            "ev.9": {("common/on_actions/o.txt", "on_yearly_pulse")},
        }
        self.assertEqual(reads.trace_entries("events/x.txt", "ev.1", index), ["je_a", "je_b"])
        self.assertEqual(reads.trace_entries("common/journal_entries/a.txt", "je_a", index), ["je_a"])
        self.assertEqual(reads.trace_entries("events/x.txt", "ev.9", index), [])  # an on-action reaches it
        self.assertEqual(reads.trace_entries("events/x.txt", "ev.7", index), [])  # nothing does


class InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = reads.load()

    def test_it_was_scanned_from_the_snapshots_vanilla_version(self):
        self.assertEqual(
            self.inventory["game_version"], reads.game_version(),
            "vanilla moved on: rescan on the machine with the game (culture_merge_primary_reads.py --write) and "
            "classify what is new in culture_merge_primary_ledger.py",
        )

    def test_it_covers_the_rosters_parts(self):
        self.assertEqual(
            self.inventory["parts"], reads.part_cultures(),
            "the roster's parts changed: rescan (culture_merge_primary_reads.py --write)",
        )
        self.assertEqual(self.inventory["parts"], gen.switchable_cultures(cfg.MERGES))

    def test_the_committed_file_is_the_rendered_inventory(self):
        self.assertEqual(text_of(ROOT / reads.INVENTORY), reads.render(self.inventory))

    def test_it_matches_the_installed_game(self):
        game = reads.installed_game()
        if game is None:
            self.skipTest("no installed game")
        self.assertEqual(reads.render(reads.scan(game)), text_of(ROOT / reads.INVENTORY))

    def test_every_formable_lists_a_part(self):
        parts = set(self.inventory["parts"])
        for tag, formable in self.inventory["formables"].items():
            self.assertTrue(parts.intersection(formable["cultures"]), tag)
        # The start tags: the ones a merged culture is never added to.
        self.assertEqual(
            sorted(tag for tag, formable in self.inventory["formables"].items() if formable["exists_at_start"]),
            ["CLM", "FRA", "GBR", "POL", "PRU", "RUS", "SPA", "SWE", "USA"],
        )


class LedgerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = reads.load()
        cls.holds = ledger.part_holds(cls.inventory)

    def test_every_read_has_a_disposition(self):
        unclassified = sorted(
            {"%s: %s" % (row["file"], row["entity"]) for row in self.inventory["reads"] if ledger.classify(row) is None}
        )
        self.assertEqual(unclassified, [], "give each a disposition in culture_merge_primary_ledger.py")

    def test_every_case_is_ruled_and_used(self):
        used = {d.case for d in map(ledger.classify, self.inventory["reads"]) if d.kind == ledger.CASE}
        self.assertEqual(used, set(ledger.CASES))
        for name, case in ledger.CASES.items():
            self.assertTrue(case.ruled, "%s waits for the owner's ruling" % name)

    def test_the_owners_rulings(self):
        # 2026-11-09: no hold for cosmetic reads, company eligibility, AI weights or movements; the others hold, and
        # none past 1936.
        self.assertEqual(
            {name for name, case in ledger.CASES.items() if case.hold},
            {"historical_characters", "laws", "siberian_exile", "standalone"},
        )
        self.assertEqual(ledger.WINDOW_END, "1936.1.1")
        kinds = {}
        for row in self.inventory["reads"]:
            kinds.setdefault(row["file"].split("/")[1] if row["file"].startswith("common/") else "events", set()).add(
                ledger.classify(row).kind
            )
        for folder in ("parties", "interest_groups", "flag_definitions", "power_bloc_names"):
            self.assertEqual(kinds[folder], {ledger.COSMETIC}, folder)
        # A ruler's title is cosmetic too, and holds nothing; the ones that belonged to a whole merged people are restated.
        self.assertEqual(kinds["government_types"], {ledger.COSMETIC, ledger.MIRRORED})
        self.assertEqual(kinds["company_types"], {ledger.COMPANY})
        self.assertEqual(kinds["journal_entries"], {ledger.ENTRIES})

    def test_no_entity_override_is_stale(self):
        entities = {row["entity"] for row in self.inventory["reads"]}
        self.assertEqual(sorted(set(ledger._ENTITIES) - entities), [])
        self.assertEqual(sorted(set(ledger.TRIGGER_OVERRIDES) - entities), [])

    def test_every_named_entry_is_a_vanilla_journal_entry(self):
        with open(ROOT / "vanilla_parsed" / "common" / "journal_entries.json", encoding="utf-8") as handle:
            vanilla = set(json.load(handle))
        named = {entry for hold in self.holds.values() for entry in hold.entries}
        self.assertEqual(sorted(named - vanilla), [])
        self.assertGreater(len(named), 40)

    def test_every_unformed_tag_is_a_vanilla_formable(self):
        with open(ROOT / "vanilla_parsed" / "common" / "country_formation.json", encoding="utf-8") as handle:
            vanilla = set(json.load(handle))
        named = {tag for hold in self.holds.values() for tag in hold.unformed}
        self.assertEqual(sorted(named - vanilla), [])

    def test_what_holds_a_few_parts(self):
        self.assertFalse(self.holds["corsican"].any)
        self.assertFalse(self.holds["karelian"].any)
        russian = self.holds["russian"]
        self.assertEqual(russian.cases, ("laws", "siberian_exile", "standalone"))
        self.assertIn("RUS", russian.unformed)  # a start tag: Russian is held while Russia is dead
        self.assertIn("je_russia_civil_war", russian.entries)
        german = self.holds["north_german"]
        self.assertIn("je_german_unification_idea", german.entries)
        self.assertIn("PRU", german.unformed)
        self.assertNotIn("GER", german.unformed)  # mirrored: GER's definition gains cm_german
        # A journal entry's events, buttons and helpers hold through the entry.
        self.assertIn("je_belle_epoque", self.holds["french"].entries)
        self.assertIn("je_danubian_federation", self.holds["czech"].entries)

    def test_a_formable_that_lacks_an_absorb_result_holds_the_part(self):
        # Only a merge's new culture joins a definition. Where the part becomes a vanilla culture the list lacks, the
        # part is held while the tag does not exist.
        new = new_results()
        # A formable whose own trigger names the part (Italy's `possible`) holds it too: a row, not a definition.
        by_trigger = {
            (row["entity"], row["part"]) for row in self.inventory["reads"] if ledger.classify(row).kind == ledger.UNFORMED
        }
        for tag, formable in self.inventory["formables"].items():
            listed = set(formable["cultures"])
            for culture in formable["cultures"]:
                if culture not in self.holds:
                    continue
                lacking = any(s not in new and s not in listed for s in cfg.successors_of(culture))
                self.assertEqual(
                    tag in self.holds[culture].unformed,
                    bool(lacking or formable["exists_at_start"] or (tag, culture) in by_trigger),
                    (tag, culture),
                )


class HoldTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(GEN_TRIGGERS)
        cls.holds = ledger.part_holds()

    def body(self, culture):
        return squash(block(self.text, "te_cmg_part_held_%s" % culture))

    def test_one_per_switchable_culture(self):
        names = re.findall(r"^te_cmg_part_held_(\w+) = \{", self.text, re.M)
        self.assertEqual(names, gen.switchable_cultures(cfg.MERGES))

    def test_a_culture_nothing_holds_is_never_held(self):
        free = [culture for culture, hold in self.holds.items() if not hold.any]
        self.assertGreater(len(free), 40)
        for culture, hold in self.holds.items():
            self.assertEqual(self.body(culture) == "always = no", not hold.any, culture)

    def test_only_a_running_entry_holds_past_the_window(self):
        # Owner: "none should hold past 1936". Outside the window clause there is nothing but has_journal_entry.
        for culture, hold in self.holds.items():
            if not hold.any:
                continue
            body = self.body(culture)
            self.assertTrue(body.startswith("OR = { "), culture)
            if hold.cases:
                self.assertIn("game_date < 1936.1.1 ", body, culture)
                self.assertNotIn("has_inactive_journal_entry", body, culture)
                self.assertNotIn("exists = c:", body, culture)
            else:
                self.assertIn("AND = { game_date < 1936.1.1 OR = { ", body, culture)
            outside = re.sub(r"AND = \{ game_date < 1936\.1\.1 OR = \{.*?\} \} (?=any_country|\}$)", "", body)
            outside = outside.replace("game_date < 1936.1.1 ", "")
            for word in re.findall(r"[a-z_]+(?= = )", outside):
                self.assertIn(word, ("any_country", "has_journal_entry"), "%s: %s" % (culture, word))
            for entry in hold.entries:
                self.assertEqual(body.count("has_journal_entry = %s" % entry), 1, (culture, entry))

    def test_a_merge_that_never_began(self):
        for merge in cfg.MERGES:
            name = "te_cmg_%s_untouched" % merge.key
            if merge.new is None:
                self.assertNotIn(name + " = {", self.text)
                continue
            body = squash(block(self.text, name))
            self.assertTrue(body.startswith("NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 " % (merge.key, merge.key)))
            joined = re.findall(r"has_global_variable = te_cm_joined_%s_(\w+)" % merge.key, body)
            self.assertEqual(joined, gen._joinable_slot_cultures(merge), merge.key)


class EffectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(GEN_EFFECTS)
        cls.vanilla = gen.load_vanilla()

    def test_the_chain_is_followed_lowest_first(self):
        body = squash(block(self.text, "te_cmg_resolve_switched_result"))
        order = re.findall(r"scope:te_cm_switched_result \?= cu:(\w+)", body)
        results = {merge.result for merge in cfg.MERGES}
        self.assertEqual(sorted(order), sorted(c for c in gen.switchable_cultures(cfg.MERGES) if c in results))
        for culture in order:
            self.assertIn(
                "if = { limit = { has_global_variable = te_cm_switched_%s scope:te_cm_switched_result ?= cu:%s } "
                "global_var:te_cm_switched_%s = { save_temporary_scope_as = te_cm_switched_result } }"
                % (culture, culture, culture),
                body,
            )
            # Whatever this culture can switch into is tested after it, so one pass reaches the end of a chain.
            for successor in cfg.successors_of(culture):
                if successor in order:
                    self.assertLess(order.index(culture), order.index(successor), (culture, successor))

    def test_the_strip_takes_a_never_begun_merges_culture_off(self):
        body = squash(block(self.text, "te_cmg_strip_untouched_results"))
        for merge in cfg.MERGES:
            line = (
                "if = { limit = { exists = cu:%s country_has_primary_culture = cu:%s te_cmg_%s_untouched = yes "
                "any_primary_culture = { NOT = { this = cu:%s } } } remove_primary_culture = cu:%s "
                "te_cm_chk_strip = { CULTURE = %s } }"
                % (merge.result, merge.result, merge.key, merge.result, merge.result, merge.result)
            )
            self.assertEqual(body.count(line), int(merge.new is not None), merge.key)
        self.assertEqual(body.count("remove_primary_culture"), len(new_results()))

    def test_the_strip_runs_monthly_and_on_formation_with_no_rule_gate(self):
        on_actions = text_of(ON_ACTIONS)
        self.assertEqual(
            squash(block(on_actions, "te_cm_strip_on_action")),
            "effect = { if = { limit = { any_scope_state = { always = yes } } te_cmg_strip_untouched_results = yes } }",
        )
        for hook in ("on_monthly_pulse_country", "on_country_formed"):
            self.assertIn("te_cm_strip_on_action", squash(block(on_actions, hook)), hook)

    def test_traditions_pass_from_core_parts_only(self):
        carried = gen.carried_traditions(self.vanilla, cfg.MERGES)
        self.assertEqual(carried[("east_slavic", "russian")], ["tradition_russosphere"])
        self.assertIn("tradition_rumelian", carried[("yugoslav", "bosniak")])
        # A result that is itself a part passes on what it took.
        self.assertIn("tradition_russosphere", carried[("pan_slavic", "cm_east_slavic")])
        # Not an optional part, and not the pairs left out by hand.
        self.assertNotIn(("german", "alemannic"), carried)
        self.assertNotIn(("german", "east_german"), carried)
        self.assertNotIn(("japanese", "ryukyuan"), carried)
        for (key, part), traditions in carried.items():
            merge = cfg.merge_by_key(key)
            self.assertTrue(any(part in slot.cultures for slot in merge.core), (key, part))
            self.assertTrue(traditions, (key, part))
            for tradition in traditions:
                self.assertNotIn(tradition, gen.own_traditions(merge.result, self.vanilla, cfg.MERGES))
        for pair, why in cfg.TRADITIONS_NOT_CARRIED.items():
            self.assertGreater(len(why), 30, pair)
            self.assertTrue(any(pair[1] in slot.cultures for slot in cfg.merge_by_key(pair[0]).core), pair)

    def test_the_carry_effect_adds_each_tradition_once_guarded(self):
        body = squash(block(self.text, "te_cmg_carry_traditions"))
        carried = gen.carried_traditions(self.vanilla, cfg.MERGES)
        for (key, part), traditions in carried.items():
            result = cfg.merge_by_key(key).result
            for tradition in traditions:
                self.assertIn(
                    "if = { limit = { global_var:te_cm_switched_%s ?= cu:%s cu:%s = { NOT = { has_discrimination_trait = %s } } } "
                    "cu:%s = { add_tradition_trait = %s } set_local_variable = { name = te_cm_trad_added value = 1 } }"
                    % (part, result, result, tradition, result, tradition),
                    body,
                )
        self.assertEqual(body.count("add_tradition_trait"), sum(len(t) for t in carried.values()))
        self.assertIn("te_cmg_carry_traditions = yes", squash(block(text_of(ON_ACTIONS), "te_cm_fervor_on_action")))


class DefinitionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = reads.load()
        cls.text = text_of(DEFINITIONS)

    def test_each_block_restates_vanillas_list_and_adds_new_cultures_only(self):
        blocks = dict(re.findall(r"^INJECT:(\w+) = \{\n\tcultures = \{ ([^}]*) \}\n\}", self.text, re.M))
        self.assertEqual(blocks.keys(), gen.definition_additions(self.inventory).keys())
        new = new_results()
        for tag, listed in blocks.items():
            formable = self.inventory["formables"][tag]
            self.assertFalse(formable["exists_at_start"], tag + " owns a state in 1836: it would start with an empty culture")
            cultures = listed.split()
            vanilla = formable["cultures"]
            self.assertEqual(cultures[:len(vanilla)], vanilla, tag)
            added = cultures[len(vanilla):]
            self.assertTrue(added, tag)
            self.assertLessEqual(set(added), new, tag)
            self.assertEqual(len(set(cultures)), len(cultures), tag)
            # Every new culture a listed part can become, all the way up its chain.
            wanted = {s for c in vanilla if c in self.inventory["parts"] for s in cfg.successors_of(c)} & new
            self.assertEqual(set(added), wanted, tag)
        self.assertIn("cm_german", blocks["GER"].split())
        for merged in ("cm_german", "cm_italian", "cm_latin"):
            self.assertIn(merged, blocks["HRE"].split())

    def test_the_file_sorts_after_vanillas_definitions(self):
        # Not needed for an INJECT (directives apply after every bare definition), but it keeps the file out of the
        # way of a bare definition's order.
        self.assertTrue(DEFINITIONS.name.startswith("zz_te_"))

    def test_the_mods_own_formables_list_them_too(self):
        self.assertEqual(
            gen.mod_definition_gaps(), {},
            "add these merged cultures to the tag's `cultures` list in common/country_definitions/te_formable_countries.txt",
        )
        definitions = gen.mod_formable_definitions()
        self.assertIn("EUN", definitions)
        self.assertIn("cm_german", definitions["EUN"])

    def test_no_country_starts_with_a_merged_culture(self):
        # The only definitions that list a cm_ culture are formables that own no state in 1836.
        start = {tag for tag, formable in self.inventory["formables"].items() if formable["exists_at_start"]}
        self.assertFalse(start & set(re.findall(r"^INJECT:(\w+)", self.text, re.M)))
        history = ROOT / "common" / "history"
        for tag in gen.mod_formable_definitions():
            for path in history.rglob("*.txt") if history.is_dir() else ():
                self.assertNotRegex(text_of(path), r"\bc:%s\b" % tag, "%s owns something at the start (%s)" % (tag, path.name))


class VanillaTriggerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = reads.load()
        cls.text = text_of(VANILLA_TRIGGERS)

    def test_the_copy_is_read_before_vanillas(self):
        for name in ledger.TRIGGER_OVERRIDES:
            vanilla_file = os.path.basename(self.inventory["trigger_lists"][name]["file"])
            self.assertLess(VANILLA_TRIGGERS.name, vanilla_file, "the first bare definition wins: ours must sort first")

    def test_it_is_vanillas_list_with_the_successors_added(self):
        new = new_results()
        for name in ledger.TRIGGER_OVERRIDES:
            body = squash(block(self.text, name))
            listed = self.inventory["trigger_lists"][name]["cultures"]
            added = gen.trigger_override_additions(self.inventory)[name]
            expected = "OR = { " + " ".join("country_has_primary_culture = cu:%s" % c for c in listed)
            for culture in added:
                if culture in new:
                    expected += " AND = { exists = cu:%s country_has_primary_culture = cu:%s }" % (culture, culture)
                else:
                    expected += " country_has_primary_culture = cu:%s" % culture
            self.assertEqual(body, expected + " }", name)
            wanted = {s for c in listed if c in self.inventory["parts"] for s in cfg.successors_of(c)} - set(listed)
            self.assertEqual(set(added), wanted, name)
        self.assertEqual(gen.trigger_override_additions(self.inventory)["has_indian_primary_culture"], ["cm_dravidian"])

    def test_the_file_holds_nothing_else(self):
        self.assertEqual(sorted(re.findall(r"^(\w+) = \{", self.text, re.M)), sorted(ledger.TRIGGER_OVERRIDES))


class GovernmentTypeTest(unittest.TestCase):
    """Ruler titles (owner, 2026-11-09): a vanilla government type that names every core culture of a merge is
    restated with the merged culture, so a German empire keeps its Kaiser once North and South German have gone."""

    @classmethod
    def setUpClass(cls):
        cls.inventory = reads.load()
        cls.text = text_of(GOVERNMENT_TYPES)
        cls.restated = ledger.restated_government_types(cls.inventory)

    def test_which_types_are_restated(self):
        self.assertEqual(
            self.restated,
            {
                "gov_kaiser": ["cm_german"],
                "gov_regency_kaiser": ["cm_german"],
                "gov_social_monarchy_kaiser": ["cm_german"],
                "gov_social_monarchy_kaiser_absolutist": ["cm_german"],
                "gov_social_monarchy_kaiser_fascist": ["cm_german"],
                "gov_fascist_corporate_state": ["cm_german"],
                "gov_volksgemeinschaft": ["cm_german"],
                "gov_american_parliamentary": ["cm_american"],
                "gov_american_parliamentary_dictator": ["cm_american"],
                "gov_american_theocracy_democratic": ["cm_american"],
                "gov_american_theocracy_dictatorial": ["cm_american"],
            },
        )
        # One nation's title is not handed to the others: French alone of Latin's core cultures, Swedish alone of
        # Scandinavian's, Swahili alone of East African's.
        for name in ("gov_french_3rd_republic_presidential", "gov_folkhemmet", "gov_swahili_sultanate"):
            self.assertIn(name, self.inventory["government_types"])
            self.assertNotIn(name, self.restated)

    def test_the_file_replaces_exactly_those(self):
        self.assertEqual(re.findall(r"^REPLACE:(\w+) = \{", self.text, re.M), list(self.restated))
        self.assertNotRegex(self.text, r"(?m)^gov_\w+ = \{")  # no bare copy: it would be dropped, or take vanilla's place

    def test_each_copy_is_vanillas_text_plus_the_guarded_merged_culture(self):
        for name, results in self.restated.items():
            vanilla = self.inventory["government_types"][name]["text"].split("\n")
            start = self.text.index("REPLACE:%s = {" % name)
            end = self.text.index("\n}\n", start) + 2
            ours = self.text[start:end].split("\n")
            self.assertEqual(ours[0], "REPLACE:%s = {" % name)
            added = [line for line in ours[1:] if line not in vanilla]
            self.assertEqual(
                {line.strip() for line in added},
                {"AND = { exists = cu:%s country_has_primary_culture = cu:%s }" % (r, r) for r in results},
                name,
            )
            self.assertEqual([line for line in ours[1:] if line in vanilla], vanilla[1:], name)
            # Each added line follows a list of the merge's cultures, inside an OR.
            for index, line in enumerate(ours):
                if line in added:
                    self.assertRegex(ours[index - 1], r"^\t+country_has_primary_culture = cu:\w+$", name)
                    self.assertEqual(ours[index - 1].count("\t"), line.count("\t"), name)

    def test_a_list_outside_an_or_or_short_of_the_core_is_refused(self):
        german = "gov_x = {\n\tpossible = {\n\t\tOR = {\n\t\t\tcountry_has_primary_culture = cu:north_german\n\t\t\tcountry_has_primary_culture = cu:south_german\n\t\t}\n\t}\n}"
        self.assertIn("exists = cu:cm_german", gen.restate_with_result("gov_x", german, "cm_german"))
        for bad in (
            german.replace("\t\t\tcountry_has_primary_culture = cu:south_german\n", ""),  # one core culture only
            german.replace("OR = {", "NOR = {"),
            "gov_x = {\n\tpossible = {\n\t\tcountry_has_primary_culture = cu:north_german\n\t\tcountry_has_primary_culture = cu:south_german\n\t}\n}",
            "gov_x = {\n\tpossible = {\n\t\thas_law = law_type:law_monarchy\n\t}\n}",
        ):
            with self.assertRaises(ValueError):
                gen.restate_with_result("gov_x", bad, "cm_german")

    def test_no_mod_file_injects_into_a_restated_type(self):
        # Every INJECT on a key applies before a plain REPLACE, so it would be lost.
        for path in (ROOT / "common" / "government_types").glob("*.txt"):
            for name in self.restated:
                self.assertNotRegex(text_of(path), r"(?m)^(TRY_)?INJECT(_OR_CREATE)?:%s\b" % name, path.name)


class ModCompanyTest(unittest.TestCase):
    def test_a_company_the_mod_keys_on_a_part_names_what_it_merges_into(self):
        # Owner, 2026-11-09: "I think they should also be available to the merged culture."
        text = text_of(ROOT / "common/company_types/extra_companies_flavored.txt")
        parts = set(reads.part_cultures())
        named = set(re.findall(r"country_has_primary_culture = cu:(\w+)", text))
        for culture in named & parts:
            for successor in cfg.successors_of(culture):
                self.assertIn(successor, named, "%s without %s" % (culture, successor))
        self.assertNotIn("culture_merge_ref", text)  # no company declines a merged culture


class CandidateTest(unittest.TestCase):
    def test_a_merges_result_makes_a_candidate(self):
        # After a merge returned to idle with a core part switched and removed, the result is all a country has left.
        text = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            for name in ("is_candidate", "can_start", "start_basics"):
                if "te_cmg_%s_%s = {" % (merge.key, name) not in text:
                    continue
                body = squash(block(text, "te_cmg_%s_%s" % (merge.key, name)))
                if name == "can_start" and "te_cmg_%s_start_basics = yes" % merge.key in body:
                    continue
                self.assertIn("country_has_primary_culture = cu:%s" % merge.result, body, (merge.key, name))


if __name__ == "__main__":
    unittest.main()
