"""Power bloc names: the AI's catch-all names stay player-only, and the AI keeps a wide pool.

An entry in common/power_bloc_names takes only a `trigger`; there is no weight.
The AI draws its bloc's name at random from every name whose trigger passes, so
a name that passes for every country crowds out the specific ones. The mod
re-declares vanilla's catch-all names as `REPLACE:` with `is_ai = no`, gives the
AI at least as many names of its own that any bloc can take, and gives every
identity at least one name the AI can always draw.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python test_power_bloc_names.py
"""

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAMES = ROOT / "common" / "power_bloc_names" / "extra_power_bloc_names.txt"
LOC = ROOT / "localization" / "english"

# Vanilla's names that pass for any country. A patch adding one must add it here
# and to the REPLACE block (docs/guides/vanilla_patch_runbook.md § 6b).
CATCH_ALLS = {
    "great_alliance", "grand_coalition", "council_of_nations", "universal_league",
    "steadfast_union", "glorious_union", "unity_league", "supreme_alliance",
    "coalition_of_states", "united_front", "joint_front",
}
IDENTITIES = {
    "identity_trade_league", "identity_sovereign_empire", "identity_ideological_union",
    "identity_military_treaty_organization", "identity_religious", "identity_cultural",
    "identity_diplomatic",
}


def entries(text: str) -> dict:
    """Top-level `[REPLACE:]key = { ... }` blocks -> (is_replace, whitespace-normalized body)."""
    text = re.sub(r"#[^\n]*", "", text)
    out = {}
    for m in re.finditer(r"(?m)^(REPLACE:)?([A-Za-z0-9_\-]+)\s*=\s*\{", text):
        depth, j = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        out[m.group(2)] = (bool(m.group(1)), " ".join(text[m.end():j - 1].split()))
    return out


def identity_only(body: str):
    m = re.fullmatch(r"trigger = \{ scope:selected_identity = identity:(\w+) \}", body)
    return m.group(1) if m else None


class PowerBlocNamesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = entries(NAMES.read_text(encoding="utf-8-sig"))

    def test_catch_alls_are_player_only(self):
        for key in sorted(CATCH_ALLS):
            with self.subTest(key=key):
                self.assertIn(key, self.mod, "catch-all not re-declared")
                replace, body = self.mod[key]
                self.assertTrue(replace, "must be a REPLACE: of vanilla's entry")
                self.assertRegex(body, r"^trigger = \{ is_ai = no\b", "is_ai = no must gate the whole trigger")

    def test_imperial_circle_open_to_ai_only_for_sovereign_empire(self):
        replace, body = self.mod["imperial_circle"]
        self.assertTrue(replace)
        self.assertIn("coa_monarchy_trigger = yes", body)
        self.assertIn("OR = { is_ai = no scope:selected_identity = identity:identity_sovereign_empire }", body)

    def test_ai_has_at_least_as_many_unconditional_names(self):
        unconditional = [k for k, (rep, body) in self.mod.items() if not rep and body == "trigger = { always = yes }"]
        self.assertGreaterEqual(len(unconditional), len(CATCH_ALLS), unconditional)

    def test_every_identity_has_an_ai_name(self):
        pool = {}
        for key, (_, body) in self.mod.items():
            pool.setdefault(identity_only(body), []).append(key)
        vanilla = Path(os.environ.get("VIC3_BASE_GAME", "/nonexistent")) / "game" / "common" / "power_bloc_names" / "00_power_bloc_names.txt"
        if vanilla.is_file():
            for key, (_, body) in entries(vanilla.read_text(encoding="utf-8-sig")).items():
                if key not in self.mod:
                    pool.setdefault(identity_only(body), []).append(key)
            wanted = IDENTITIES
        else:  # CI: only the identities whose names the mod supplies
            wanted = {"identity_military_treaty_organization", "identity_cultural", "identity_diplomatic"}
        for identity in sorted(wanted):
            with self.subTest(identity=identity):
                self.assertTrue(pool.get(identity), f"no name the AI can always draw for {identity}")

    def test_mod_names_have_loc(self):
        text = "\n".join(p.read_text(encoding="utf-8-sig") for p in sorted(LOC.rglob("*_l_english.yml")))
        for key, (replace, _) in sorted(self.mod.items()):
            if replace:
                continue
            with self.subTest(key=key):
                self.assertEqual(len(re.findall(rf"^ {re.escape(key)}:0? ?\"", text, re.M)), 1)


if __name__ == "__main__":
    unittest.main()
