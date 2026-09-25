"""Tests for silent_variable_audit (the nuclear_incident.40 "costs money and does
nothing" class)."""

import os
import tempfile
import unittest

import silent_variable_audit as sva

LOC_HEADER = "﻿l_english:\n"


def _event(eid: str, options: list[str], hidden: bool = False) -> str:
    head = "\thidden = yes\n" if hidden else f"\ttitle = {eid}.t\n"
    body = "".join(f"\toption = {{\n\t\tname = {eid}.{chr(97 + i)}\n{o}\t}}\n"
                   for i, o in enumerate(options))
    return f"{eid} = {{\n\ttype = country_event\n{head}{body}}}\n"


class SilentVariableAuditTests(unittest.TestCase):
    def _mod(self, files: dict[str, str], loc: str = "") -> str:
        td = tempfile.mkdtemp()
        for rel, content in files.items():
            p = os.path.join(td, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)
        p = os.path.join(td, "localization", "english", "t_l_english.yml")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(LOC_HEADER + loc)
        return td

    SHOWN = " je_tt:0 \"Reliability: [JournalEntry.GetCountry.MakeScope.Var('rel').GetValue]\"\n"
    WRITE = "\t\tchange_variable = { name = rel add = 3 }\n"

    def _flags(self, mod: str, unreviewed_only: bool = True):
        return {(f.event_id, f.option) for f in sva.audit(mod).flags
                if not (unreviewed_only and f.exemption)}

    def test_displayed_variable_written_silently_is_flagged(self):
        mod = self._mod({"events/e.txt": _event("my.1", [self.WRITE, ""])}, self.SHOWN)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})

    def test_flag_points_at_the_option_line(self):
        mod = self._mod({"events/e.txt": _event("my.1", ["", self.WRITE])}, self.SHOWN)
        (flag,) = sva.audit(mod).flags
        self.assertEqual(flag.option, "my.1.b")
        with open(flag.file, encoding="utf-8-sig") as fh:
            self.assertIn("option = {", fh.read().split("\n")[flag.line - 1])

    def test_undisplayed_variable_is_ignored(self):
        mod = self._mod({"events/e.txt": _event("my.1", [self.WRITE])})
        self.assertEqual(self._flags(mod), set())

    def test_custom_tooltip_wrapper_covers_the_write(self):
        opt = "\t\tcustom_tooltip = {\n\t\t\ttext = rel_up\n\t" + self.WRITE + "\t\t}\n"
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, self.SHOWN)
        self.assertEqual(self._flags(mod), set())

    def test_sibling_custom_tooltip_line_covers_the_block(self):
        opt = "\t\tcustom_tooltip = rel_up\n" + self.WRITE
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, self.SHOWN)
        self.assertEqual(self._flags(mod), set())

    def test_tooltip_in_a_sibling_branch_does_not_cover(self):
        opt = ("\t\tif = {\n\t\t\tlimit = { always = yes }\n\t\t\tcustom_tooltip = other\n\t\t}\n"
               + self.WRITE)
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, self.SHOWN)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})

    def test_hidden_effect_is_not_silent(self):
        opt = "\t\thidden_effect = {\n\t" + self.WRITE + "\t\t}\n"
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, self.SHOWN)
        self.assertEqual(self._flags(mod), set())

    def test_script_value_chain_makes_a_variable_displayed(self):
        loc = " je_tt:0 \"[JournalEntry.GetCountry.MakeScope.ScriptValue('rel_display')|0]\"\n"
        svs = ("rel_display = { value = rel_or_default }\n"
               "rel_or_default = {\n\tvalue = 60\n\tif = {\n\t\tlimit = { has_variable = rel }\n"
               "\t\tvalue = var:rel\n\t}\n}\n")
        mod = self._mod({"events/e.txt": _event("my.1", [self.WRITE]),
                         "common/script_values/v.txt": svs}, loc)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})

    def test_write_inside_a_scripted_effect_with_parameters(self):
        effects = "bump = {\n\tchange_variable = { name = $VAR$ add = $AMOUNT$ }\n}\n"
        opt = "\t\tbump = { VAR = rel AMOUNT = 3 }\n"
        mod = self._mod({"events/e.txt": _event("my.1", [opt]),
                         "common/scripted_effects/s.txt": effects}, self.SHOWN)
        (flag,) = sva.audit(mod).flags
        self.assertEqual([(w.variable, w.via) for w in flag.writes], [("rel", "bump")])

    def test_scripted_effect_with_its_own_tooltip_is_covered(self):
        effects = "bump = {\n\tcustom_tooltip = rel_up\n\tchange_variable = { name = rel add = 3 }\n}\n"
        mod = self._mod({"events/e.txt": _event("my.1", ["\t\tbump = yes\n"]),
                         "common/scripted_effects/s.txt": effects}, self.SHOWN)
        self.assertEqual(self._flags(mod), set())

    def test_global_variable_needs_a_global_read(self):
        opt = "\t\tset_global_variable = { name = host value = ROOT }\n"
        scope_only = " x:0 \"[GetPlayer.MakeScope.Var('host').GetValue]\"\n"
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, scope_only)
        self.assertEqual(self._flags(mod), set())
        global_read = " x:0 \"[GetGlobalVariable('host').GetCountry.GetName]\"\n"
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, global_read)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})

    def test_hidden_events_and_console_harnesses_are_skipped(self):
        mod = self._mod({"events/e.txt": _event("my.1", [self.WRITE], hidden=True),
                         "events/te_debug_x.txt": _event("te_debug_x.1", [self.WRITE])},
                        self.SHOWN)
        self.assertEqual(self._flags(mod), set())

    def test_tag_suppresses_and_a_tag_on_a_clean_option_is_stale(self):
        tag = "\t\t# REVIEWED 2026-09-25 (silent_variable): the JE says so\n"
        mod = self._mod({"events/e.txt": _event("my.1", [tag + self.WRITE, tag])}, self.SHOWN)
        res = sva.audit(mod)
        self.assertEqual([(f.option, bool(f.exemption)) for f in res.flags], [("my.1.a", True)])
        self.assertEqual([s.option for s in res.stale_tags], ["my.1.b"])
        self.assertEqual(res.failing, 1)

    def test_untagged_reviewed_comment_does_not_suppress(self):
        opt = "\t\t# REVIEWED 2026-09-25: read by other audits\n" + self.WRITE
        mod = self._mod({"events/e.txt": _event("my.1", [opt])}, self.SHOWN)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})

    def test_braces_in_comments_do_not_split_options(self):
        opt = "\t\t# a stray } in a comment\n" + self.WRITE
        mod = self._mod({"events/e.txt": _event("my.1", [opt, ""])}, self.SHOWN)
        self.assertEqual(self._flags(mod), {("my.1", "my.1.a")})


if __name__ == "__main__":
    unittest.main()
