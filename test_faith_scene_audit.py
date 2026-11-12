"""Unit tests for faith_scene_audit (#1531).

Each fixture is a throwaway mod tree: one or two event files, English loc, and
where a test needs them scripted triggers and effects. The religions come from
the committed `vanilla_parsed/` snapshot, as in a real run. The crux is the
gate: which state religions a text can be shown to, read from the triggers
around each place its key is named, against the faiths its words fit.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from faith_scene_audit import (
    CHECK, EXEMPT_KEYS, REPORT_PATH, VOCABULARY, Faiths, Matcher, Term, audit, load_religions, main,
    parse_script, prose, regenerate,
)

ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
CHRISTIAN = "religion = { has_discrimination_trait = heritage_christian }"
ISLAMIC = "religion = { has_discrimination_trait = heritage_islamic }"
DHARMIC = "religion = { has_discrimination_trait = heritage_dharmic }"
HINDU = "country_has_state_religion = rel:hindu"


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class _Fixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name

    def loc(self, *lines: str, name: str = "te_events_l_english.yml", folder: str = "") -> None:
        rel = os.path.join("localization", "english", folder, name)
        _write(self.root, rel, "l_english:\n" + "".join(f" {line}\n" for line in lines))

    def events(self, body: str, name: str = "x_events.txt") -> None:
        _write(self.root, f"events/{name}", "namespace = x\n" + body)

    def common(self, folder: str, body: str) -> None:
        _write(self.root, f"common/{folder}/test.txt", body)

    def flagged(self) -> dict:
        return {f.key: f for f in audit(self.root).flags}


class ParseTests(unittest.TestCase):
    def test_keeps_repeats_operators_and_lines(self):
        tree = parse_script(
            'a = {\n'
            '\tname = { text = one } # a comment { with a brace\n'
            '\tname = { text = "two" }\n'
            '\treligion != rel:hindu\n'
            '\tvar:x ?= 3\n'
            '\ttitle = "a # in a string"\n'
            '}\n'
        )
        self.assertEqual([n.key for n in tree], ["a"])
        kids = tree[0].children
        self.assertEqual([k.key for k in kids], ["name", "name", "religion", "var:x", "title"])
        self.assertEqual([k.children[0].value for k in kids[:2]], ["one", "two"])
        self.assertEqual((kids[2].op, kids[2].value, kids[2].line), ("!=", "rel:hindu", 4))
        self.assertEqual(kids[3].op, "?=")
        self.assertEqual(kids[4].value, "a # in a string")

    def test_bare_tokens_are_list_items(self):
        tree = parse_script("events = { x.1 x.2 }")
        self.assertEqual([(n.key, n.value, n.children) for n in tree[0].children],
                         [("x.1", None, None), ("x.2", None, None)])


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.religions = load_religions(ROOT)

    def admits(self, script: str, scope: str = "country", triggers: str = ""):
        defined = {n.key: n.children for n in parse_script(triggers)}
        faiths = Faiths(self.religions, defined)
        return faiths.gate(parse_script(script), scope, scope), faiths

    def test_a_heritage_is_a_family_and_rel_is_one_faith(self):
        (admitted, exact), faiths = self.admits(CHRISTIAN)
        self.assertTrue(exact)
        self.assertTrue({"catholic", "protestant", "orthodox", "oriental_orthodox"} <= admitted)
        self.assertFalse({"sunni", "hindu", "atheist"} & admitted)
        (admitted, exact), _ = self.admits(HINDU)
        self.assertEqual((admitted, exact), (frozenset({"hindu"}), True))
        (admitted, _), _ = self.admits("religion = rel:shinto")
        self.assertEqual(admitted, frozenset({"shinto"}))
        (admitted, _), _ = self.admits(DHARMIC)
        self.assertTrue({"hindu", "sikh", "mahayana", "theravada", "gelugpa"} <= admitted)

    def test_lines_are_anded_and_or_unions(self):
        (admitted, exact), _ = self.admits(f"{DHARMIC}\nNOT = {{ {HINDU} }}")
        self.assertTrue(exact)
        self.assertNotIn("hindu", admitted)
        self.assertIn("sikh", admitted)
        (admitted, _), _ = self.admits(f"OR = {{ {HINDU} country_has_state_religion = rel:sikh }}")
        self.assertEqual(admitted, frozenset({"hindu", "sikh"}))

    def test_a_test_it_cannot_read_admits_everyone_and_is_never_negated(self):
        (admitted, exact), faiths = self.admits("has_technology_researched = railways")
        self.assertEqual((admitted, exact), (faiths.all, False))
        # NOT of "Christian and has railways" is not "not Christian".
        (admitted, exact), faiths = self.admits(
            f"NOT = {{ {CHRISTIAN} has_technology_researched = railways }}")
        self.assertEqual((admitted, exact), (faiths.all, False))
        # ... but the readable half of an AND still narrows.
        (admitted, exact), _ = self.admits(f"{HINDU}\nhas_technology_researched = railways")
        self.assertEqual((admitted, exact), (frozenset({"hindu"}), False))

    def test_not_equal_and_always(self):
        (admitted, exact), faiths = self.admits("religion != rel:hindu")
        self.assertEqual((admitted, exact), (faiths.all - {"hindu"}, True))
        (admitted, _), faiths = self.admits("always = no")
        self.assertEqual(admitted, frozenset())
        (admitted, _), faiths = self.admits("NOR = { always = no }")
        self.assertEqual(admitted, faiths.all)

    def test_a_religion_test_in_another_scope_counts_for_nothing(self):
        for script in (f"scope:rival = {{ {HINDU} }}", f"any_scope_state = {{ owner = {{ {HINDU} }} }}",
                       f"owner = {{ {HINDU} }}"):
            (admitted, exact), faiths = self.admits(script)
            self.assertEqual((admitted, exact), (faiths.all, False), script)

    def test_in_a_state_event_the_country_is_owner(self):
        (admitted, _), _ = self.admits(f"owner = {{ {HINDU} }}", scope="holder")
        self.assertEqual(admitted, frozenset({"hindu"}))
        (admitted, _), faiths = self.admits(HINDU, scope="holder")
        self.assertEqual(admitted, faiths.all)

    def test_scripted_triggers_are_read_through(self):
        triggers = (
            "is_hindu = { country_has_state_religion = rel:hindu }\n"
            "has_faith = { country_has_state_religion = rel:$FAITH$ }\n"
            "loops = { loops = yes }\n"
        )
        (admitted, _), _ = self.admits("is_hindu = yes", triggers=triggers)
        self.assertEqual(admitted, frozenset({"hindu"}))
        (admitted, _), faiths = self.admits("is_hindu = no", triggers=triggers)
        self.assertEqual(admitted, faiths.all - {"hindu"})
        (admitted, _), _ = self.admits("has_faith = { FAITH = sikh }", triggers=triggers)
        self.assertEqual(admitted, frozenset({"sikh"}))
        (admitted, exact), faiths = self.admits("loops = yes", triggers=triggers)
        self.assertEqual((admitted, exact), (faiths.all, False))

    def test_custom_tooltip_and_hidden_trigger_are_read_through(self):
        (admitted, _), _ = self.admits(f"custom_tooltip = {{ text = some_key {HINDU} }}")
        self.assertEqual(admitted, frozenset({"hindu"}))
        (admitted, _), _ = self.admits(f"hidden_trigger = {{ {HINDU} }}")
        self.assertEqual(admitted, frozenset({"hindu"}))


class VocabularyTests(unittest.TestCase):
    def words(self, text: str) -> set:
        return {hit.word.lower() for hit in Matcher().hits(text)}

    def test_every_faith_named_exists(self):
        faiths = Faiths(load_religions(ROOT))
        for term in VOCABULARY:
            self.assertEqual(faiths.unknown(term.fits), [], term.faith)
            self.assertTrue(faiths.named(term.fits), term.faith)

    def test_the_issues_words(self):
        text = ("The priest stopped his sermon and looked at the third pew. The vicar, the pastor and "
                "the bishop of the parish left the church with a Bible and a hymnal.")
        self.assertEqual(self.words(text), {"priest", "sermon", "pew", "vicar", "pastor", "bishop",
                                            "parish", "church", "bible", "hymnal"})

    def test_other_faiths_words(self):
        self.assertEqual(self.words("The imam of the mosque, a rabbi, a guru and two swamis met a lama."),
                         {"imam", "mosque", "rabbi", "guru", "swamis", "lama"})
        self.assertEqual(self.words("Hindu, Muslim, Buddhist and Christian leaders agreed."),
                         {"hindu", "muslim", "buddhist", "christian"})

    def test_words_every_faith_shares_are_not_listed(self):
        text = ("The clergy and their congregations prayed at the temple and the shrine, a house of "
                "worship for the faithful, where a preacher read scripture to pilgrims on a holy day.")
        self.assertEqual(self.words(text), set())

    def test_father_is_a_priest_only_as_an_address_or_a_title(self):
        self.assertEqual(self.words("My father built this house. Father says the family lasts."), set())
        self.assertEqual(self.words("Dear Mother and Father, the term has begun."), set())
        self.assertEqual(self.words("\\\"Forgive me, Father,\\\" she said."), {"father"})
        self.assertEqual(self.words("They sent for Father Rossi."), {"father rossi"})

    def test_whole_words_only_and_capitals_where_they_matter(self):
        self.assertEqual(self.words("Churchill gave a pastoral speech to orthodox economists at the convention."),
                         set())
        self.assertEqual(self.words("Her tastes are catholic, and the Catholic vote is not."), {"catholic"})
        self.assertEqual(self.words("A megachurch and its churchgoers."), {"megachurch", "churchgoers"})

    def test_markup_and_names_are_not_text(self):
        value = ("[Concept('concept_church', 'church')] $bishop_key$ #b bold#! revive Old Church Slavonic "
                 "and Church Slavonic [SCOPE.sCountry('x').GetCustom('priest[1]')]")
        self.assertEqual(self.words(value), set())
        self.assertNotIn("church", prose(value).lower())

    def test_a_word_fits_the_faiths_the_table_gives_it(self):
        faiths = Faiths(load_religions(ROOT))
        fits = {hit.word.lower(): faiths.named(hit.term.fits)
                for hit in Matcher().hits("sermon priest guru monk pagoda dharma bishop")}
        self.assertIn("sunni", fits["sermon"])      # the Friday sermon
        self.assertNotIn("hindu", fits["sermon"])
        self.assertIn("hindu", fits["priest"])
        self.assertNotIn("sunni", fits["priest"])
        self.assertEqual(fits["guru"], frozenset({"hindu", "sikh"}))
        self.assertTrue({"catholic", "theravada", "shinto"} <= fits["monk"])
        self.assertIn("confucian", fits["pagoda"])
        self.assertIn("sikh", fits["dharma"])
        self.assertNotIn("protestant", fits["dharma"])
        self.assertNotIn("jewish", fits["bishop"])


class AuditTests(_Fixture):
    def test_an_ungated_scene_is_flagged(self):
        self.loc('x.1.t:0 "The Old Rules"', 'x.1.d:0 "A couple married against custom."',
                 'x.1.f:0 "The priest stopped in the middle of his sermon."', 'x.1.a:0 "So be it."')
        self.events("x.1 = {\n\ttype = country_event\n\ttitle = x.1.t\n\tdesc = x.1.d\n\tflavor = x.1.f\n"
                    "\toption = { name = x.1.a }\n}\n")
        flags = self.flagged()
        self.assertEqual(list(flags), ["x.1.f"])
        flag = flags["x.1.f"]
        self.assertEqual({w for w, _ in flag.words}, {"priest", "sermon"})
        (site, wrong), = flag.sites
        self.assertEqual((site.event, site.part, site.file, site.line), ("x.1", "flavor", "events/x_events.txt", 6))
        self.assertEqual(wrong, ())  # no gate at all

    def test_a_ladder_gates_each_rung(self):
        self.loc('x.1.f_christian:0 "The priest stopped his sermon."',
                 'x.1.f_islamic:0 "The imam finished the Friday sermon."',
                 'x.1.f_hindu:0 "The swami spoke of caste."',
                 'x.1.f:0 "The elder stopped speaking."')
        self.events(
            "x.1 = {\n\ttype = country_event\n\tflavor = {\n\t\tfirst_valid = {\n"
            f"\t\t\ttriggered_desc = {{ trigger = {{ {ISLAMIC} }} desc = x.1.f_islamic }}\n"
            f"\t\t\ttriggered_desc = {{ trigger = {{ {HINDU} }} desc = x.1.f_hindu }}\n"
            f"\t\t\ttriggered_desc = {{ trigger = {{ {CHRISTIAN} }} desc = x.1.f_christian }}\n"
            "\t\t\ttriggered_desc = { trigger = { always = yes } desc = x.1.f }\n"
            "\t\t}\n\t}\n}\n")
        result = audit(self.root)
        self.assertEqual(result.flags, [])
        self.assertEqual(result.gated_uses, 3)

    def test_the_wrong_faiths_gate_does_not_help(self):
        self.loc('x.1.f:0 "The priest stopped his sermon."')
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = {\n"
                    f"\t\ttriggered_desc = {{ trigger = {{ {ISLAMIC} }} desc = x.1.f }}\n\t}}\n}}\n")
        flag = self.flagged()["x.1.f"]
        # "sermon" fits Islam; "priest" does not.
        self.assertEqual(flag.words, [("priest", "Christian, Hindu, Shinto and Chinese")])
        # The fixture has vanilla's religions only (no common/religions/).
        self.assertEqual(set(flag.sites[0][1]), {"sunni", "shiite", "ibadi"})

    def test_a_heritage_does_not_gate_one_faiths_scene(self):
        self.loc('x.1.f:0 "Gurus and swamis have taken to television."')
        template = ("x.1 = {{\n\ttype = country_event\n\tflavor = {{\n"
                    "\t\ttriggered_desc = {{ trigger = {{ {gate} }} desc = x.1.f }}\n\t}}\n}}\n")
        self.events(template.format(gate=DHARMIC))
        flag = self.flagged()["x.1.f"]
        self.assertIn("mahayana", flag.sites[0][1])  # a Buddhist country is shown the swami
        self.assertNotIn("hindu", flag.sites[0][1])
        self.events(template.format(gate=HINDU))
        self.assertEqual(self.flagged(), {})

    def test_the_events_own_trigger_gates_all_its_text(self):
        self.loc('x.1.t:0 "The Bishop Calls"', 'x.1.a:0 "Send for the vicar."',
                 'x.1.tt:0 "The parish will remember."', 'x_mod:0 "Church Bells"',
                 'x_mod_desc:0 "The churches ring their bells."')
        body = ("x.1 = {{\n\ttype = country_event\n\ttitle = x.1.t\n{trigger}"
                "\toption = {{\n\t\tname = x.1.a\n\t\tcustom_tooltip = x.1.tt\n"
                "\t\tadd_modifier = {{ name = x_mod days = 10 }}\n\t}}\n}}\n")
        self.events(body.format(trigger=f"\ttrigger = {{ {CHRISTIAN} has_technology_researched = railways }}\n"))
        self.assertEqual(self.flagged(), {})
        self.events(body.format(trigger=""))
        flags = self.flagged()
        self.assertEqual(set(flags), {"x.1.t", "x.1.a", "x.1.tt", "x_mod", "x_mod_desc"})
        self.assertEqual({flags[k].sites[0][0].part for k in flags}, {"title", "option", "tooltip", "modifier"})

    def test_a_key_named_in_two_events_is_flagged_for_the_ungated_one(self):
        self.loc('shared.f:0 "The bishop read the letter twice."')
        self.events(
            f"x.1 = {{\n\ttype = country_event\n\ttrigger = {{ {CHRISTIAN} }}\n\tflavor = shared.f\n}}\n"
            "x.2 = {\n\ttype = country_event\n\tflavor = shared.f\n}\n")
        flag = self.flagged()["shared.f"]
        self.assertEqual([site.event for site, _ in flag.sites], ["x.2"])

    def test_a_later_rung_knows_the_rungs_above_failed(self):
        self.loc('x.1.f_other:0 "The elders met."', 'x.1.f:0 "The parish met in the church."')
        ladder = ("x.1 = {{\n\ttype = country_event\n\tflavor = {{\n\t\tfirst_valid = {{\n"
                  "\t\t\ttriggered_desc = {{ trigger = {{ {first} }} desc = x.1.f_other }}\n"
                  "\t\t\tdesc = x.1.f\n\t\t}}\n\t}}\n}}\n")
        self.events(ladder.format(first=f"NOT = {{ {CHRISTIAN} }}"))
        self.assertEqual(self.flagged(), {})
        # A rung that also tests something else can fail for that reason.
        self.events(ladder.format(first=f"NOT = {{ {CHRISTIAN} }} has_technology_researched = railways"))
        self.assertIn("x.1.f", self.flagged())

    def test_option_names_and_their_triggers(self):
        self.loc('x.1.a:0 "Call a synod."', 'x.1.b:0 "Gather the ulama."', 'x.1.c:0 "Summon the rabbis."')
        self.events(
            "x.1 = {\n\ttype = country_event\n"
            f"\toption = {{\n\t\tname = x.1.a\n\t\ttrigger = {{ {CHRISTIAN} }}\n\t}}\n"
            f"\toption = {{\n\t\tname = {{\n\t\t\ttrigger = {{ {ISLAMIC} }}\n\t\t\ttext = x.1.b\n\t\t}}\n"
            "\t\tname = {\n\t\t\ttrigger = { always = yes }\n\t\t\ttext = x.1.c\n\t\t}\n\t}\n}\n")
        self.assertEqual(list(self.flagged()), ["x.1.c"])

    def test_an_if_around_a_tooltip_gates_it_and_else_knows_it_failed(self):
        self.loc('tt_mosque:0 "The mosques are full."', 'tt_other:0 "The churches are full."')
        self.events(
            "x.1 = {\n\ttype = country_event\n\timmediate = {\n"
            f"\t\tif = {{\n\t\t\tlimit = {{ {ISLAMIC} }}\n\t\t\tcustom_tooltip = tt_mosque\n\t\t}}\n"
            "\t\telse = {\n\t\t\tcustom_tooltip = { text = tt_other }\n\t\t}\n\t}\n}\n")
        flags = self.flagged()
        self.assertEqual(list(flags), ["tt_other"])  # everyone but the Muslim countries: not only Christians
        self.assertNotIn("sunni", flags["tt_other"].sites[0][1])
        self.assertIn("hindu", flags["tt_other"].sites[0][1])

    def test_a_gate_under_a_scope_change_is_about_someone_else(self):
        self.loc('tt_mosque:0 "Their mosques are full."')
        self.events(
            "x.1 = {\n\ttype = country_event\n\toption = {\n\t\tscope:rival = {\n"
            f"\t\t\tif = {{\n\t\t\t\tlimit = {{ {ISLAMIC} }}\n\t\t\t\tcustom_tooltip = tt_mosque\n\t\t\t}}\n"
            "\t\t}\n\t}\n}\n")
        self.assertEqual(list(self.flagged()), ["tt_mosque"])

    def test_a_state_event_reads_the_owners_faith(self):
        self.loc('x.1.a:0 "Raise it as a great mosque"', 'x.1.b:0 "Raise it as a cathedral"')
        self.events(
            "x.1 = {\n\ttype = state_event\n"
            "\toption = {\n\t\tname = x.1.a\n\t\ttrigger = { owner = { religion = rel:sunni } }\n\t}\n"
            "\toption = {\n\t\tname = x.1.b\n\t\ttrigger = { religion = rel:catholic }\n\t}\n}\n")
        self.assertEqual(list(self.flagged()), ["x.1.b"])  # a state has no religion: that test reads nothing

    def test_modifiers_an_event_adds_and_scripted_effects_it_calls(self):
        self.loc('m_plain:0 "Clergy Trusted"', 'm_plain_desc:0 "The clergy were left to it."',
                 'm_enact:0 "Pulpit Advance"', 'm_arg:0 "Cathedral Fund"', 'tt_eff:0 "The bishop approves."')
        self.common("scripted_effects",
                    "x_give = {\n\tadd_modifier = { name = $MOD$ days = 10 }\n\tx_tell = yes\n}\n"
                    "x_tell = { custom_tooltip = tt_eff }\n"
                    "x_silent = { add_treasury = 5 }\n")
        self.events(
            "x.1 = {\n\ttype = country_event\n\toption = {\n"
            "\t\tadd_modifier = { name = m_plain days = 10 }\n"
            "\t\tadd_enactment_modifier = { name = m_enact }\n"
            "\t\tx_give = { MOD = m_arg }\n\t\tx_silent = yes\n\t}\n}\n")
        flags = self.flagged()
        self.assertEqual(set(flags), {"m_enact", "m_arg", "tt_eff"})
        site = flags["tt_eff"].sites[0][0]
        self.assertEqual((site.via, site.line), ("x_tell", 7))  # the event's own line, not the effect's

    def test_a_spliced_key_is_read_under_the_same_gate(self):
        self.loc('x.1.d:0 "The petition reads: $x_part$"', 'x_part:0 "signed by the bishops."')
        self.events("x.1 = {\n\ttype = country_event\n\tdesc = x.1.d\n}\n")
        flags = self.flagged()
        self.assertEqual(list(flags), ["x_part"])
        self.assertEqual(flags["x_part"].sites[0][0].key, "x.1.d")

    def test_what_is_not_read(self):
        self.loc('x.1.f:0 "The priest spoke."', 'x.2.f:0 "The priest spoke."', 'x.3.f:0 "The priest spoke."',
                 'gm_arch_site_ur_found:0 "A Taoist priest keeps the caves."', 'never_shown:0 "A bishop."')
        self.events("x.1 = {\n\ttype = country_event\n\thidden = yes\n\tflavor = x.1.f\n}\n"
                    "x.3 = {\n\ttype = country_event\n\tflavor = x.3.f\n\tdesc = gm_arch_site_ur_found\n}\n")
        self.events("x.2 = {\n\ttype = country_event\n\tflavor = x.2.f\n}\n", name="te_debug_x.txt")
        self.assertEqual(list(self.flagged()), ["x.3.f"])
        self.assertTrue(EXEMPT_KEYS.match("gm_arch_site_ur_found"))

    def test_a_reviewed_key_is_exempt(self):
        self.loc(f'x.1.f:0 "A cross of gold, a crown of thorns." # REVIEWED 2026-11-12 ({CHECK}): a real quotation')
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")
        result = audit(self.root)
        self.assertEqual([f.exemption["rationale"] for f in result.flags], ["a real quotation"])
        self.assertEqual((result.failing, result.stale_tags), (0, []))

    def test_another_checks_tag_is_not_ours(self):
        self.loc('x.1.f:0 "The priest spoke." # REVIEWED 2026-11-12 (loc_style): something else')
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")
        result = audit(self.root)
        self.assertEqual((result.failing, len(result.stale_tags)), (1, 0))

    def test_a_tag_that_suppresses_nothing_is_stale(self):
        tag = f"# REVIEWED 2026-11-12 ({CHECK}): was a priest once"
        self.loc(f'x.1.f:0 "The elder spoke." {tag}',          # no listed word any more
                 f'x.1.g:0 "The priest spoke." {tag}',          # gated now
                 f'orphan:0 "The priest spoke." {tag}')         # no event shows it
        self.events(f"x.1 = {{\n\ttype = country_event\n\ttrigger = {{ {CHRISTIAN} }}\n"
                    "\tflavor = x.1.f\n\tdesc = x.1.g\n}\n")
        result = audit(self.root)
        self.assertEqual(sorted(t.key for t in result.stale_tags), ["orphan", "x.1.f", "x.1.g"])
        self.assertEqual(result.failing, 3)

    def test_a_tag_on_an_overridden_copy_is_stale(self):
        tag = f"# REVIEWED 2026-11-12 ({CHECK}): reviewed"
        self.loc(f'x.1.f:0 "The priest spoke." {tag}', name="te_a_l_english.yml")
        self.loc('x.1.f:0 "The priest spoke again."', name="te_b_l_english.yml")
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")
        result = audit(self.root)
        self.assertEqual([(t.file, t.key) for t in result.stale_tags],
                         [("localization/english/te_a_l_english.yml", "x.1.f")])
        self.assertEqual(result.failing, 2)  # the winning copy is flagged and untagged

    def test_unused_loc_is_not_read(self):
        self.loc('x.1.f:0 "The elder spoke."')
        self.loc('x.1.f:0 "The priest spoke."', name="te_unused_l_english.yml")
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")
        self.assertEqual(self.flagged(), {})

    def test_a_vocabulary_can_be_passed_in(self):
        self.loc('x.1.f:0 "The elder spoke."')
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")
        result = audit(self.root, vocabulary=(Term("test", ("hindu",), (r"elders?",)),))
        self.assertEqual([f.key for f in result.flags], ["x.1.f"])

    def test_no_loc_raises(self):
        self.events("x.1 = {\n\ttype = country_event\n}\n")
        with self.assertRaises(FileNotFoundError):
            audit(self.root)


class CliTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.loc('x.1.f:0 "The priest spoke."')
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n")

    def run_main(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = main([*argv, "--mod-path", self.root])
        return code, out.getvalue()

    def test_strict_exit_codes_and_report(self):
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1)
        self.assertIn("- `x.1.f` (`localization/english/te_events_l_english.yml:2`): \"priest\"", out)
        self.assertIn("`x.1` flavor (`events/x_events.txt:4`): no religion gate", out)
        self.assertRegex(out, r"(?m)^FLAG  localization/english/te_events_l_english\.yml:2: x\.1\.f: ")
        self.assertEqual(self.run_main()[0], 0)
        self.loc(f'x.1.f:0 "The priest spoke." # REVIEWED 2026-11-12 ({CHECK}): meant')
        self.assertEqual(self.run_main("--strict")[0], 0)

    def test_strict_names_a_stale_tag(self):
        self.loc(f'x.1.f:0 "The elder spoke." # REVIEWED 2026-11-12 ({CHECK}): meant')
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"(?m)^STALE localization/english/te_events_l_english\.yml:2: x\.1\.f: ")

    def test_explain_lists_the_places_and_gates(self):
        self.events("x.1 = {\n\ttype = country_event\n\tflavor = x.1.f\n}\n"
                    f"x.2 = {{\n\ttype = country_event\n\ttrigger = {{ {HINDU} }}\n\tflavor = x.1.f\n}}\n")
        code, out = self.run_main("--explain", "x.1.f")
        self.assertEqual(code, 0)
        self.assertIn('x.1.f: "priest"', out)
        self.assertIn("x.1 flavor (events/x_events.txt:4): any state religion", out)
        self.assertIn("x.2 flavor (events/x_events.txt:9): state religion one of: hindu", out)
        self.assertIn("not a key", self.run_main("--explain", "no_such_key")[1])

    def test_regenerate_writes_the_report(self):
        with mock.patch("path_constants.mod_path", self.root):
            summary = regenerate(None)
        self.assertEqual((summary["unreviewed"], summary["total_flags"], summary["events_read"]), (1, 1, 1))
        with open(os.path.join(self.root, REPORT_PATH), encoding="utf-8") as fh:
            self.assertIn("- `x.1.f` (", fh.read())


class RepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from path_constants import mod_path
        cls.result = audit(mod_path)

    def test_runs_over_the_mod(self):
        self.assertGreater(self.result.events_read, 900)
        self.assertGreater(self.result.keys_read, 8000)
        self.assertGreater(self.result.religions, 20)  # vanilla's and the mod's custom ones

    def test_the_mod_has_no_failing_flag(self):
        # CI runs it --strict: every flag is fixed or carries its tagged
        # REVIEWED comment, and no tag is stale.
        self.assertEqual([f.key for f in self.result.flags if not f.exemption], [])
        self.assertEqual(self.result.stale_tags, [])

    def test_the_gated_ladders_are_read_as_gated(self):
        """The patterns the guide points to: a faith's rung under its gate."""
        admits = {}
        for site in self.result.sites:
            admits.setdefault(site.key, []).append(site.admits)
        faiths = Faiths(load_religions(ROOT))
        christian = faiths.named(("heritage_christian",))
        for key in ("society_technology_events.4.f", "amendment_petition_events.13.f",
                    "religious_revival_events.2.f_christian"):
            self.assertTrue(admits[key] and all(a <= christian for a in admits[key]), key)
        self.assertEqual(admits["religious_revival_events.1.d_dharmic"], [frozenset({"hindu"})])
        self.assertGreater(self.result.gated_uses, 30)
        flagged = {f.key for f in self.result.flags}
        self.assertFalse(flagged & {"society_technology_events.4.f", "religious_revival_events.1.d_dharmic"})

    def test_every_exemption_gives_a_reason(self):
        for flag in self.result.flags:
            self.assertGreater(len(flag.exemption["rationale"]), 20, flag.key)

    def test_post_load_roster(self):
        from scripts.analysis.check_post_load_rosters import extract_rosters
        self.assertIn("faith_scene_audit", extract_rosters(str(ROOT / "mod_state_server.py"))["POST_LOAD_AUDITS"])

    def test_ci_runs_it_strict(self):
        import audit_registry  # CI runs the registry's audits (scripts/run_audits.py)
        entry = audit_registry.get("faith_scene_audit")
        self.assertEqual(entry.command, "python3 faith_scene_audit.py --strict")
        self.assertEqual(entry.tags, (CHECK,))

    def test_the_patterns_compile_and_do_not_overlap_by_accident(self):
        seen = {}
        for term in VOCABULARY:
            for word in term.words:
                re.compile(word)
                self.assertNotIn(word, seen, f"{word} is listed under {seen.get(word)} and {term.faith}")
                seen[word] = term.faith


if __name__ == "__main__":
    unittest.main()
