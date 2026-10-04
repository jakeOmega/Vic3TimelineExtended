"""Unit tests for ideology_lawgroup_audit.

A law an ideology's lawgroup block leaves out is implicitly neutral, unless it
is a variant (`parent = law_x`), which takes its parent's stance. The mod's
rule: an ideology the mod defines, or a block the mod adds to a vanilla
ideology, names every law in its group; a block vanilla already had names the
laws the mod adds to the group.

Each test builds a throwaway mod tree (ideologies, laws, optionally an
ideology_modifications.py) over a vanilla data set parsed from text, and runs
the real audit, whose ModState merges INJECT blocks into vanilla's.
"""
from __future__ import annotations

import os
import tempfile
import textwrap
import unittest

from ideology_lawgroup_audit import audit, check, render_report, scan_modifications
from paradox_file_parser import ParadoxFileParser

# Vanilla: one group of three laws (one a variant), one of two.
_VANILLA_LAWS = """
law_v_one = { group = lawgroup_alpha }
law_v_two = { group = lawgroup_alpha }
law_v_variant = { group = lawgroup_alpha parent = law_v_one }
law_b_one = { group = lawgroup_beta }
law_b_two = { group = lawgroup_beta }
"""
# The mod adds one law to each vanilla group.
_MOD_LAWS = """
law_m_alpha = { group = lawgroup_alpha }
law_m_beta = { group = lawgroup_beta }
"""
_VANILLA_IDEOLOGIES = """
ideology_vanilla = {
	lawgroup_alpha = {
		law_v_one = approve
	}
}
ideology_untouched = {
	lawgroup_alpha = {
		law_v_one = approve
		law_m_alpha = neutral
	}
}
"""


def _parse(text: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text))
        path = fh.name
    try:
        parser = ParadoxFileParser()
        parser.parse_file(path)
        return parser.data
    finally:
        os.unlink(path)


class _Tree:
    def __init__(self, ideologies: str = "", modifications: str | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self._write("common/laws/test_laws.txt", _MOD_LAWS)
        self._write("common/ideologies/test_ideologies.txt", ideologies)
        if modifications is not None:
            self._write("ideology_modifications.py", modifications)
        self.vanilla = {"Ideologies": _parse(_VANILLA_IDEOLOGIES), "Laws": _parse(_VANILLA_LAWS)}

    def _write(self, rel: str, text: str):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(textwrap.dedent(text))

    def run(self):
        return audit(mod_path=self.root, vanilla_data=self.vanilla)

    def close(self):
        self._tmp.cleanup()


class IdeologyLawgroupTests(unittest.TestCase):
    def setUp(self):
        self.trees = []

    def tearDown(self):
        for t in self.trees:
            t.close()

    def _run(self, ideologies="", modifications=None):
        tree = _Tree(ideologies, modifications)
        self.trees.append(tree)
        return tree.run()

    def _flags(self, result):
        return {(f.kind, f.ideology, f.lawgroup, tuple(f.laws)) for f in result.flags if not f.exemption}

    def test_vanilla_block_needs_only_the_mods_laws(self):
        # ideology_vanilla leaves out law_v_two (vanilla's gap) and law_m_alpha.
        r = self._run()
        self.assertEqual(
            self._flags(r),
            {("missing_law", "ideology_vanilla", "lawgroup_alpha", ("law_m_alpha",))},
        )
        self.assertEqual(r.vanilla_gaps, 2)  # law_v_two, twice

    def test_inject_of_the_new_law_satisfies_a_vanilla_block(self):
        r = self._run("INJECT:ideology_vanilla = {\n\tlawgroup_alpha = {\n\t\tlaw_m_alpha = disapprove\n\t}\n}\n")
        self.assertEqual(self._flags(r), set())

    def test_block_the_mod_adds_to_a_vanilla_ideology_names_every_law(self):
        text = (
            "INJECT:ideology_vanilla = {\n"
            "\tlawgroup_alpha = {\n\t\tlaw_m_alpha = disapprove\n\t}\n"
            "\tlawgroup_beta = {\n\t\tlaw_m_beta = approve\n\t}\n"
            "}\n"
        )
        r = self._run(text)
        self.assertEqual(
            self._flags(r),
            {("missing_law", "ideology_vanilla", "lawgroup_beta", ("law_b_one", "law_b_two"))},
        )

    def test_mod_ideology_names_every_law_but_variants(self):
        text = textwrap.dedent("""\
            ideology_mod = {
            	lawgroup_alpha = {
            		law_v_one = approve
            		law_m_alpha = neutral
            	}
            }
            """)
        r = self._run(text)
        self.assertEqual(
            self._flags(r),
            {
                ("missing_law", "ideology_mod", "lawgroup_alpha", ("law_v_two",)),
                ("missing_law", "ideology_vanilla", "lawgroup_alpha", ("law_m_alpha",)),
            },
        )

    def test_stance_on_a_variant_is_flagged(self):
        text = "INJECT:ideology_vanilla = {\n\tlawgroup_alpha = {\n\t\tlaw_m_alpha = neutral\n\t\tlaw_v_variant = approve\n\t}\n}\n"
        r = self._run(text)
        self.assertEqual(
            self._flags(r),
            {("variant_stance", "ideology_vanilla", "lawgroup_alpha", ("law_v_variant",))},
        )

    def test_unknown_law_wrong_group_bad_stance_and_unknown_group(self):
        text = textwrap.dedent("""\
            ideology_mod = {
            	lawgroup_alpha = {
            		law_v_one = approve
            		law_v_two = approve
            		law_m_alpha = maybe
            		law_b_one = approve
            		law_nonexistent = approve
            	}
            	lawgroup_gamma = {
            		law_v_one = approve
            	}
            }
            INJECT:ideology_vanilla = { lawgroup_alpha = { law_m_alpha = neutral } }
            """)
        r = self._run(text)
        kinds = {(f.kind, tuple(f.laws)) for f in r.flags}
        self.assertEqual(
            kinds,
            {
                ("bad_stance", ("law_m_alpha",)),
                ("wrong_group", ("law_b_one",)),
                ("unknown_law", ("law_nonexistent",)),
                ("unknown_lawgroup", ()),
            },
        )

    def test_carrier_laws_are_never_required(self):
        laws = {
            "law_a": ("=", {"group": ("=", "lawgroup_x")}),
            "law_carrier": ("=", {"group": ("=", "lawgroup_x")}),
        }
        ideologies = {"ideology_mod": ("=", {"lawgroup_x": ("=", {"law_a": ("=", "approve")})})}
        r = check(ideologies, laws, {}, set(), {}, {}, carriers={"law_carrier"})
        self.assertEqual(r.flags, [])
        r = check(ideologies, laws, {}, set(), {}, {})
        self.assertEqual([f.laws for f in r.flags], [["law_carrier"]])

    def test_reviewed_comment_on_the_block_line_exempts(self):
        text = textwrap.dedent("""\
            ideology_mod = {
            	lawgroup_alpha = { # REVIEWED 2026-10-04 (ideology_lawgroup): only Alpha One matters to them
            		law_v_one = approve
            		law_m_alpha = neutral
            	}
            }
            INJECT:ideology_vanilla = { lawgroup_alpha = { law_m_alpha = neutral } }
            """)
        r = self._run(text)
        self.assertEqual(self._flags(r), set())
        self.assertEqual([f.exemption["date"] for f in r.flags], ["2026-10-04"])
        self.assertIn("Reviewed Exemptions", render_report(r))

    def test_reviewed_comment_in_ideology_modifications_exempts_a_generated_block(self):
        mods = textwrap.dedent('''\
            modifications = {
                "ideology_vanilla": {
                    "lawgroup_alpha": [("law_v_one", "approve")],  # REVIEWED 2026-10-04 (ideology_lawgroup): test
                },
            }
            ''')
        r = self._run("", mods)
        self.assertEqual(self._flags(r), set())
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].file, "ideology_modifications.py")

    def test_scan_modifications_reads_ideology_and_block_lines(self):
        mods = textwrap.dedent('''\
            x = [("law_a", "approve")]
            modifications = {
                "ideology_one": {  # REVIEWED 2026-10-04 (ideology_lawgroup): whole ideology
                    "lawgroup_a": x,
                    "lawgroup_b": [
                        ("law_b", "approve"),
                    ],
                },
            }
            ''')
        src = scan_modifications(mods)
        self.assertEqual(set(src), {"ideology_one"})
        self.assertEqual(src["ideology_one"].openers[0][1], 3)
        self.assertIn("REVIEWED", src["ideology_one"].openers[0][2])
        self.assertEqual(sorted(src["ideology_one"].blocks), ["lawgroup_a", "lawgroup_b"])


    def test_untagged_review_does_not_exempt(self):
        text = textwrap.dedent("""\
            ideology_mod = {
            	lawgroup_alpha = { # REVIEWED 2026-10-04: plain form
            		law_v_one = approve
            	}
            }
            INJECT:ideology_vanilla = { lawgroup_alpha = { law_m_alpha = neutral } }
            """)
        r = self._run(text)
        self.assertEqual({f.kind for f in r.flags if not f.exemption}, {"missing_law"})

    def test_tag_that_suppresses_nothing_is_stale(self):
        text = textwrap.dedent("""\
            ideology_mod = {
            	lawgroup_alpha = { # REVIEWED 2026-10-04 (ideology_lawgroup): no longer needed
            		law_v_one = approve
            		law_v_two = approve
            		law_m_alpha = neutral
            	}
            }
            INJECT:ideology_vanilla = { lawgroup_alpha = { law_m_alpha = neutral } }
            """)
        r = self._run(text)
        self.assertEqual([(f.kind, f.line) for f in r.flags], [("stale_review", 2)])


class LiveTreeTest(unittest.TestCase):
    def test_the_mod_has_no_unreviewed_flags(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        r = audit(mod_path=repo)
        self.assertGreater(r.ideologies_checked, 100)
        self.assertEqual(
            [f"{f.kind}: {f.ideology} {f.lawgroup} {f.laws}" for f in r.flags if not f.exemption], []
        )


if __name__ == "__main__":
    unittest.main()
