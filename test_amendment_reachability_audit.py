"""Unit tests for amendment_reachability_audit.

No control in the law panel adds an amendment: script does, with
`add_amendment`, or an interest group sponsors one in an enactment
negotiation. The mod's rule is that every amendment it defines has a scripted
way in. The audit flags `unreachable` (no add, no sponsor), `sponsor_only`
(no add, sponsor possible), `dead_adds_only` (every add in an orphaned event
or an uncalled scripted effect), `unknown_allowed_law` and `unknown_type`.

Each test builds a throwaway mod tree (amendments, laws, events, scripted
effects, a journal entry) and runs the real audit on it. With no
vanilla_parsed/ snapshot in the tree, laws and amendments are the mod's own.
"""
from __future__ import annotations

import os
import tempfile
import textwrap
import unittest

from amendment_reachability_audit import audit, render_report

_LAWS = """
law_alpha = { group = lawgroup_test }
law_beta = { group = lawgroup_test }
"""


def _amendment(name: str, sponsor: str = "always = no", allowed: str = "law_alpha", opener_comment: str = "") -> str:
    return textwrap.dedent(f"""\
        {name} = {{{(' ' + opener_comment) if opener_comment else ''}
        	parent = law_alpha
        	allowed_laws = {{
        		{allowed}
        	}}
        	would_sponsor = {{ {sponsor} }}
        }}
        """)


class _Tree:
    def __init__(self, amendments: str, files: dict | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self._write("common/amendments/test_amendments.txt", amendments)
        self._write("common/laws/test_laws.txt", _LAWS)
        for rel, text in (files or {}).items():
            self._write(rel, text)

    def _write(self, rel: str, text: str):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig") as fh:
            fh.write(textwrap.dedent(text))

    def run(self):
        return audit(mod_path=self.root)

    def close(self):
        self._tmp.cleanup()


def _event(event_id: str, amendment: str, self_firing: bool = False) -> str:
    return textwrap.dedent(f"""\
        {event_id} = {{
        	type = country_event
        	{'mean_time_to_happen = { months = 120 }' if self_firing else ''}
        	option = {{
        		currently_enacting_law = {{
        			add_amendment = {{ type = {amendment} sponsor = ROOT.ig:ig_test cooldown = 0 }}
        		}}
        	}}
        }}
        """)


class AmendmentReachabilityTests(unittest.TestCase):
    def setUp(self):
        self.trees = []

    def tearDown(self):
        for t in self.trees:
            t.close()

    def _run(self, amendments, files=None):
        tree = _Tree(amendments, files)
        self.trees.append(tree)
        return tree.run()

    def _kinds(self, result):
        return {(f.kind, f.subject) for f in result.flags if not f.exemption}

    def test_no_add_and_no_sponsor_is_unreachable(self):
        r = self._run(_amendment("amendment_dead"))
        self.assertEqual(self._kinds(r), {("unreachable", "amendment_dead")})

    def test_missing_would_sponsor_counts_as_no_sponsor(self):
        text = "amendment_bare = {\n\tparent = law_alpha\n\tallowed_laws = { law_alpha }\n}\n"
        r = self._run(text)
        self.assertEqual(self._kinds(r), {("unreachable", "amendment_bare")})

    def test_sponsor_without_add_is_sponsor_only(self):
        r = self._run(_amendment("amendment_lobbied", sponsor="is_interest_group_type = ig_test"))
        self.assertEqual(self._kinds(r), {("sponsor_only", "amendment_lobbied")})

    def test_add_from_a_dispatched_event_is_reachable(self):
        files = {
            "events/test_events.txt": "namespace = test_events\n" + _event("test_events.1", "amendment_live"),
            "common/on_actions/test_on_actions.txt": (
                "on_monthly_pulse_country = { events = { test_events.1 } }\n"
            ),
        }
        r = self._run(_amendment("amendment_live"), files)
        self.assertEqual(self._kinds(r), set())
        self.assertIn("amendment_live", r.by_add)

    def test_add_only_from_an_orphaned_event_is_dead(self):
        files = {"events/test_events.txt": "namespace = test_events\n" + _event("test_events.1", "amendment_stranded")}
        r = self._run(_amendment("amendment_stranded"), files)
        self.assertEqual(self._kinds(r), {("dead_adds_only", "amendment_stranded")})

    def test_event_with_mean_time_to_happen_fires_on_its_own(self):
        files = {
            "events/test_events.txt": "namespace = test_events\n"
            + _event("test_events.1", "amendment_pulsed", self_firing=True),
        }
        r = self._run(_amendment("amendment_pulsed"), files)
        self.assertEqual(self._kinds(r), set())

    def test_templated_type_resolves_through_call_sites(self):
        files = {
            "common/scripted_effects/test_effects.txt": textwrap.dedent("""\
                te_test_attach = {
                	active_law:lawgroup_test = {
                		add_amendment = { type = amendment_$WHICH$ sponsor = ROOT.ig:ig_test cooldown = 0 }
                	}
                }
                te_test_wrapper = {
                	te_test_attach = { WHICH = $INNER$ }
                }
                """),
            "common/journal_entries/test_je.txt": textwrap.dedent("""\
                je_test = {
                	immediate = {
                		te_test_attach = { WHICH = first }
                		te_test_wrapper = { INNER = second }
                	}
                }
                """),
        }
        amendments = _amendment("amendment_first") + _amendment("amendment_second") + _amendment("amendment_third")
        r = self._run(amendments, files)
        self.assertEqual(self._kinds(r), {("unreachable", "amendment_third")})

    def test_add_in_an_uncalled_scripted_effect_is_dead(self):
        files = {
            "common/scripted_effects/test_effects.txt": textwrap.dedent("""\
                te_test_never_called = {
                	active_law:lawgroup_test = {
                		add_amendment = { type = amendment_shelved sponsor = ROOT.ig:ig_test cooldown = 0 }
                	}
                }
                """),
        }
        r = self._run(_amendment("amendment_shelved"), files)
        self.assertEqual(self._kinds(r), {("dead_adds_only", "amendment_shelved")})

    def test_commented_out_add_does_not_count(self):
        files = {
            "common/history/test_history.txt": textwrap.dedent("""\
                COUNTRIES = {
                	c:AAA = {
                		# add_amendment = { type = amendment_ghost sponsor = ig:ig_test }
                	}
                }
                """),
        }
        r = self._run(_amendment("amendment_ghost"), files)
        self.assertEqual(self._kinds(r), {("unreachable", "amendment_ghost")})

    def test_unknown_type_is_flagged(self):
        files = {
            "common/history/test_history.txt": textwrap.dedent("""\
                COUNTRIES = {
                	c:AAA = {
                		active_law:lawgroup_test ?= {
                			add_amendment = { type = amendment_typo sponsor = PREV.ig:ig_test }
                			add_amendment = { type = amendment_real sponsor = PREV.ig:ig_test }
                		}
                	}
                }
                """),
        }
        r = self._run(_amendment("amendment_real"), files)
        kinds = {f.kind for f in r.flags}
        self.assertEqual(kinds, {"unknown_type"})
        self.assertIn("amendment_typo", r.flags[0].detail)

    def test_unknown_allowed_law_is_flagged(self):
        files = {"common/history/test_history.txt": "x = { add_amendment = { type = amendment_odd } }\n"}
        r = self._run(_amendment("amendment_odd", allowed="law_alpha\n\t\tlaw_gamma"), files)
        flags = [(f.kind, f.detail) for f in r.flags]
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0][0], "unknown_allowed_law")
        self.assertIn("law_gamma", flags[0][1])

    def test_reviewed_comment_on_opener_exempts(self):
        text = _amendment("amendment_kept", opener_comment="# REVIEWED 2026-10-04 (amendment_reachability): attached by a console command")
        r = self._run(text)
        self.assertEqual(self._kinds(r), set())
        self.assertEqual(len(r.flags), 1)
        self.assertEqual(r.flags[0].exemption["date"], "2026-10-04")
        self.assertIn("Reviewed Exemptions", render_report(r))

    def test_reviewed_comment_on_add_line_exempts_unknown_type(self):
        files = {
            "common/history/test_history.txt": (
                "x = {\n\tadd_amendment = { type = amendment_later } # REVIEWED 2026-10-04 (amendment_reachability): lands next PR\n}\n"
            ),
        }
        r = self._run("", files)
        self.assertEqual(self._kinds(r), set())
        self.assertEqual([f.kind for f in r.flags], ["unknown_type"])


    def test_untagged_or_foreign_review_does_not_exempt(self):
        text = _amendment("amendment_a", opener_comment="# REVIEWED 2026-10-04: plain form")
        text += _amendment("amendment_b", opener_comment="# REVIEWED 2026-10-04 (empty_block): other audit")
        r = self._run(text)
        self.assertEqual(self._kinds(r), {("unreachable", "amendment_a"), ("unreachable", "amendment_b")})

    def test_tag_that_suppresses_nothing_is_stale(self):
        files = {
            "events/test_events.txt": "namespace = test_events\n" + _event("test_events.1", "amendment_live", True),
        }
        text = _amendment("amendment_live", opener_comment="# REVIEWED 2026-10-04 (amendment_reachability): old")
        r = self._run(text, files)
        self.assertEqual([f.kind for f in r.flags], ["stale_review"])
        self.assertIsNone(r.flags[0].exemption)


class LiveTreeTest(unittest.TestCase):
    def test_the_mod_has_no_unreviewed_flags(self):
        repo = os.path.dirname(os.path.abspath(__file__))
        r = audit(mod_path=repo)
        self.assertGreater(r.amendments_checked, 100)
        self.assertEqual([f"{f.kind}: {f.subject}" for f in r.flags if not f.exemption], [])


if __name__ == "__main__":
    unittest.main()
