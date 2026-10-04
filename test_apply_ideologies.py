"""apply_ideologies.py: INJECT for additions, REPLACE only to change vanilla.

The generator writes common/ideologies/modified.txt from
ideology_modifications.py and vanilla's raw ideology files. An ideology whose
modifications only add (a block vanilla lacks, or laws a vanilla block doesn't
name) is an INJECT holding just the additions; one that changes a stance
vanilla sets is a REPLACE carrying vanilla's whole entry. An INJECT that
restated a vanilla stance would lean on unread engine behaviour, and a REPLACE
freezes vanilla's text until the next regeneration, so both directions matter.

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
import ideology_modifications
import ideology_lawgroup_audit

REPO = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(REPO, "common", "ideologies", "modified.txt")

VANILLA_ENTRY = (
    "{\n"
    '\ticon = "gfx/x.dds"\n'
    "\tlawgroup_alpha = { # vanilla comment\n"
    "\t\tlaw_a = approve\n"
    "\t\tlaw_b = disapprove\n"
    "\t}\n"
    "\tcountry_trigger = {\n"
    "\t\texists = c:AAA\n"
    "\t}\n"
    "}\n"
)


class PlanTests(unittest.TestCase):
    def test_new_block_is_injected_whole(self):
        inject, changed = apply_ideologies._plan(
            VANILLA_ENTRY, {"lawgroup_beta": [("law_c", "approve"), ("law_d", "neutral")]}
        )
        self.assertEqual(changed, [])
        self.assertEqual(inject, [("lawgroup_beta", [("law_c", "approve"), ("law_d", "neutral")])])

    def test_new_law_in_a_vanilla_block_is_injected_alone(self):
        inject, changed = apply_ideologies._plan(
            VANILLA_ENTRY, {"lawgroup_alpha": [("law_a", "approve"), ("law_new", "strongly_approve")]}
        )
        self.assertEqual(changed, [])
        self.assertEqual(inject, [("lawgroup_alpha", [("law_new", "strongly_approve")])])

    def test_changed_vanilla_stance_forces_replace(self):
        inject, changed = apply_ideologies._plan(
            VANILLA_ENTRY, {"lawgroup_alpha": [("law_b", "approve"), ("law_new", "approve")]}
        )
        self.assertEqual(changed, ["lawgroup_alpha: law_b"])

    def test_modify_entries_writes_inject_and_replace(self):
        entries = {"ideology_x": VANILLA_ENTRY, "ideology_y": VANILLA_ENTRY, "ideology_z": VANILLA_ENTRY}
        mods = {
            "ideology_x": {"lawgroup_alpha": [("law_new", "approve")]},
            "ideology_y": {"lawgroup_alpha": [("law_a", "neutral")]},
            "ideology_z": {"lawgroup_alpha": [("law_a", "approve")]},  # restates vanilla only
            "ideology_missing": {"lawgroup_alpha": [("law_a", "approve")]},
        }
        result, unmatched = apply_ideologies.modify_entries(entries, mods)
        self.assertEqual(unmatched, ["ideology_missing"])
        self.assertEqual(set(result), {"ideology_x", "ideology_y"})
        kw, body, _ = result["ideology_x"]
        self.assertEqual(kw, "INJECT")
        self.assertEqual(body, "{\n\tlawgroup_alpha = {\n\t\tlaw_new = approve\n\t}\n}\n")
        kw, body, reasons = result["ideology_y"]
        self.assertEqual(kw, "REPLACE")
        self.assertEqual(reasons, ["lawgroup_alpha: law_a"])
        self.assertIn("\t\tlaw_a = neutral\n", body)
        self.assertIn("country_trigger", body)

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "modified.txt")
            apply_ideologies.write_to_file(out, result)
            with open(out, encoding="utf-8-sig") as fh:
                text = fh.read()
        self.assertIn("INJECT:ideology_x = {\n\tlawgroup_alpha = {\n\t\tlaw_new = approve\n\t}\n}\n", text)
        self.assertIn("# REPLACE: changes vanilla stances in lawgroup_alpha (law_a)\nREPLACE:ideology_y = {", text)


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

    def _vanilla_block(self, ideology, group):
        block = self.vanilla_ideologies.get(ideology, {}).get(group)
        if block is None:
            return None
        return {law: ideology_lawgroup_audit._unwrap(v) for law, v in ideology_lawgroup_audit._unwrap(block).items()}

    def test_injects_carry_only_laws_vanilla_does_not_state(self):
        for ideology, (kw, body) in self.entries.items():
            if kw != "INJECT":
                continue
            for group, inner in re.findall(r"(?m)^\t(\w+) = \{\n((?:\t\t.*\n)*)\t\}", body):
                vanilla = self._vanilla_block(ideology, group) or {}
                for law in re.findall(r"(?m)^\t\t([\w\-]+) = ", inner):
                    with self.subTest(ideology=ideology, group=group, law=law):
                        self.assertNotIn(law, vanilla)

    def test_replaces_change_a_vanilla_stance(self):
        mods = ideology_modifications.modifications
        for ideology, (kw, _body) in self.entries.items():
            if kw != "REPLACE":
                continue
            changes = [
                law
                for group, lines in mods[ideology].items()
                for law, stance in lines
                if (self._vanilla_block(ideology, group) or {}).get(law, stance) != stance
            ]
            with self.subTest(ideology=ideology):
                self.assertTrue(changes, "a REPLACE that changes no vanilla stance should be an INJECT")

    def test_every_modification_is_in_effect(self):
        # Stale modified.txt: ideology_modifications.py was edited and the
        # generator not re-run.
        for ideology, groups in ideology_modifications.modifications.items():
            body = ideology_lawgroup_audit._unwrap(self.merged.get(ideology))
            for group, lines in groups.items():
                block = ideology_lawgroup_audit._unwrap(body.get(group)) if isinstance(body, dict) else None
                for law, stance in dict(lines).items():
                    with self.subTest(ideology=ideology, group=group, law=law):
                        self.assertIsInstance(block, dict)
                        self.assertEqual(ideology_lawgroup_audit._unwrap(block.get(law)), stance)

    def test_every_generated_entry_has_a_modification(self):
        self.assertEqual(set(self.entries) - set(ideology_modifications.modifications), set())


if __name__ == "__main__":
    unittest.main()
