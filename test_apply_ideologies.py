"""apply_ideologies.py: INJECT only new blocks, REPLACE to touch a vanilla one.

The generator writes common/ideologies/modified.txt from
ideology_modifications.py and vanilla's raw ideology files. An ideology whose
modifications only add lawgroup blocks vanilla lacks is an INJECT of those
blocks. One that touches a block vanilla has, to change a stance or to add a
law, is a REPLACE carrying vanilla's whole entry. An INJECT of a block vanilla
already has is not merged: the engine keeps both blocks and the ideology
tooltip lists the law group twice (read in game 2026-10-04).

The committed-file checks need no game install: vanilla comes from the
vanilla_parsed/ snapshot. They catch a modified.txt left stale after an edit
to ideology_modifications.py, which only regenerates on a machine with the
game.
"""

import os
import re
import tempfile
import unittest

import apply_ideologies
import ideology_lawgroup_audit
import ideology_modifications

REPO = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(REPO, "common", "ideologies", "modified.txt")
REGENERATE = (
    "regenerate common/ideologies/modified.txt with apply_ideologies.py (or a mod "
    "state server reload) on a machine with the game"
)

VANILLA_ENTRY = (
    "{\n"
    '\ticon = "gfx/x.dds"\n'
    "\tlawgroup_alpha = {\n"
    "\t\tlaw_a = approve\n"
    "\t\tlaw_b = disapprove\n"
    "\t}\n"
    "\tcountry_trigger = {\n"
    "\t\texists = c:AAA\n"
    "\t}\n"
    "}\n"
)
NO_BLOCKS_ENTRY = '{\n\ticon = "gfx/y.dds"\n}\n'


class ModifyEntriesTests(unittest.TestCase):
    def _run(self, mods, entries=None):
        entries = entries or {key: VANILLA_ENTRY for key in mods}
        return apply_ideologies.modify_entries(entries, mods)

    def test_new_block_only_is_an_inject(self):
        result, _ = self._run({"ideology_x": {"lawgroup_beta": [("law_c", "approve"), ("law_d", "neutral")]}})
        kw, body, reasons = result["ideology_x"]
        self.assertEqual((kw, reasons), ("INJECT", []))
        self.assertIn("\tlawgroup_beta = {\n\t\tlaw_c = approve\n\t\tlaw_d = neutral\n\t}", body)

    def test_new_law_in_a_vanilla_block_is_a_replace(self):
        result, _ = self._run({"ideology_x": {"lawgroup_alpha": [("law_new", "strongly_approve")]}})
        kw, body, reasons = result["ideology_x"]
        self.assertEqual((kw, reasons), ("REPLACE", ["lawgroup_alpha"]))
        self.assertIn("\tlawgroup_alpha = {\n\t\tlaw_new = strongly_approve\n\t\tlaw_a = approve\n", body)
        self.assertIn("country_trigger", body)

    def test_changed_vanilla_stance_is_a_replace(self):
        result, _ = self._run({"ideology_x": {"lawgroup_alpha": [("law_b", "approve")]}})
        kw, body, _ = result["ideology_x"]
        self.assertEqual(kw, "REPLACE")
        self.assertIn("\t\tlaw_b = approve\n", body)
        self.assertNotIn("law_b = disapprove", body)

    def test_new_block_on_an_ideology_with_no_lawgroup_block_is_kept(self):
        mods = {"ideology_y": {"lawgroup_beta": [("law_c", "approve")]}}
        result, _ = self._run(mods, {"ideology_y": NO_BLOCKS_ENTRY})
        self.assertIn("\tlawgroup_beta = {\n\t\tlaw_c = approve\n\t}\n}\n", result["ideology_y"][1])

    def test_unmatched_key_is_reported(self):
        _, unmatched = self._run({"ideology_missing": {"lawgroup_alpha": []}}, {"ideology_x": VANILLA_ENTRY})
        self.assertEqual(unmatched, ["ideology_missing"])

    def test_write_to_file(self):
        mods = {
            "ideology_x": {"lawgroup_beta": [("law_c", "approve")]},
            "ideology_y": {"lawgroup_alpha": [("law_new", "approve")]},
        }
        result, _ = self._run(mods)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "modified.txt")
            orig = apply_ideologies.modifications
            apply_ideologies.modifications = mods  # write_to_file extracts INJECT blocks by these keys
            try:
                apply_ideologies.write_to_file(out, result)
            finally:
                apply_ideologies.modifications = orig
            with open(out, encoding="utf-8-sig") as fh:
                text = fh.read()
        self.assertIn("INJECT:ideology_x = {\n\tlawgroup_beta = {\n\t\tlaw_c = approve\n\t}\n}\n", text)
        self.assertIn("# Forced REPLACE due to existing section(s): lawgroup_alpha\nREPLACE:ideology_y = {", text)


def _committed_entries():
    with open(GENERATED, encoding="utf-8-sig") as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"(?m)^(REPLACE|INJECT):(\w+) = ", text):
        body = text[m.end():text.index("\n}\n", m.end()) + 3]
        out[m.group(2)] = (m.group(1), body)
    return out


class CommittedFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vanilla = ideology_lawgroup_audit.load_vanilla(REPO)
        cls.vanilla_ideologies = {
            k: ideology_lawgroup_audit._unwrap(v) for k, v in cls.vanilla["Ideologies"].items()
        }
        cls.entries = _committed_entries()
        cls.merged = ideology_lawgroup_audit.load_state(REPO, cls.vanilla).get_data("Ideologies")

    def test_injects_name_only_blocks_vanilla_lacks(self):
        # An injected block vanilla already has shows twice in the tooltip.
        for ideology, (kw, body) in self.entries.items():
            if kw != "INJECT":
                continue
            vanilla = self.vanilla_ideologies.get(ideology, {})
            for group in re.findall(r"(?m)^\t(\w+) = \{", body):
                with self.subTest(ideology=ideology, group=group):
                    self.assertNotIn(group, vanilla, REGENERATE)

    def test_replaces_touch_a_vanilla_block(self):
        mods = ideology_modifications.modifications
        for ideology, (kw, _body) in self.entries.items():
            if kw != "REPLACE":
                continue
            vanilla = self.vanilla_ideologies.get(ideology, {})
            with self.subTest(ideology=ideology):
                self.assertTrue(
                    any(group in vanilla for group in mods[ideology]),
                    "a REPLACE that touches no vanilla block should be an INJECT",
                )

    def test_every_modification_is_in_effect(self):
        # Stale modified.txt: ideology_modifications.py was edited and the
        # generator not re-run.
        for ideology, groups in ideology_modifications.modifications.items():
            body = ideology_lawgroup_audit._unwrap(self.merged.get(ideology))
            for group, lines in groups.items():
                block = ideology_lawgroup_audit._unwrap(body.get(group)) if isinstance(body, dict) else None
                for law, stance in dict(lines).items():
                    with self.subTest(ideology=ideology, group=group, law=law):
                        self.assertIsInstance(block, dict, REGENERATE)
                        self.assertEqual(ideology_lawgroup_audit._unwrap(block.get(law)), stance, REGENERATE)

    def test_every_generated_entry_has_a_modification(self):
        self.assertEqual(set(self.entries) - set(ideology_modifications.modifications), set())


if __name__ == "__main__":
    unittest.main()
