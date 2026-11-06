"""Every state region the mod names is a state on its map (#1407).

A vanilla patch that renames or removes a state region (1.15: KAUNAS, TARTARIA and GALICH renamed, CHUKOTKA merged
into KAMCHATKA) leaves every place the mod names the old key pointing at nothing. Script logs an invalid scope, an
`INJECT:STATE_X` on a key vanilla no longer defines creates a stray state or does nothing, and a config, region list
or loc key keyed on it quietly drops out. The #1402 migration found its stale names by hand.

The map is the mod's `map_data/state_regions/` (land and seas), which test_state_regions_vanilla_sync holds to
vanilla's states key for key. The scan is structural, since a bare `STATE_` token is as often a GUI loc key
(`STATE_TAX_CAPACITY_DESC`):
- script, GUI and loc text: a `s:STATE_X` scope link (comments stripped) and a database directive on a state
  (`INJECT:STATE_X`, `REPLACE:`, `TRY_INJECT:`, `TRY_REPLACE:`, `INJECT_OR_CREATE:`, `REPLACE_OR_CREATE:`);
- geographic regions' `state_regions = { }` and strategic regions' `states = { }` lists;
- loc and the translation memories: `HUB_NAME_STATE_X_<hub>` splices and the power bloc name keys
  (`te_pb_name_league_STATE_X`, `te_pb_name_pact_STATE_X`);
- the configs keyed on states: `deposits_config.json`, `state_trait_config.json`, the generators' CSV tables and the
  Demographics analysis tables;
- the generators' and analysis tools' Python, as quoted `"STATE_X"` literals.

    python3 test_state_references.py
"""
import csv
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STATE = r"STATE_[A-Z0-9_]*[A-Z0-9]"
DIRECTIVES = ("INJECT", "REPLACE", "TRY_INJECT", "TRY_REPLACE", "INJECT_OR_CREATE", "REPLACE_OR_CREATE")
SCOPE_RE = re.compile(rf"(?<![\w:])s:({STATE})\b")
DIRECTIVE_RE = re.compile(rf"(?<![\w:])(?:{'|'.join(DIRECTIVES)}):({STATE})\b")
HUB_RE = re.compile(rf"\bHUB_NAME_({STATE})_(?:city|port|mine|farm|wood)\b")
BLOC_KEY_RE = re.compile(rf"\bte_pb_name_(?:league|pact)_({STATE})\b")
LIST_RE = {"geographic_regions": re.compile(r"\bstate_regions\s*=\s*\{([^}]*)\}"),
           "strategic_regions": re.compile(r"\bstates\s*=\s*\{([^}]*)\}")}
PY_LITERAL_RE = re.compile(rf"""["']({STATE})["']""")
# Quoted STATE_ names in the tools' Python that are not states: placeholders and other constants.
NOT_STATES = {"STATE_X", "STATE_GOODS", "STATE_REGION", "STATE_TRAITS"}


def map_states(root=ROOT):
    """Every state region in the mod's map, land and seas."""
    out = set()
    for path in (root / "map_data" / "state_regions").glob("*.txt"):
        out |= set(re.findall(rf"(?m)^﻿?({STATE})\s*=\s*\{{", path.read_text(encoding="utf-8-sig")))
    return out


def strip_comments(text):
    """Script text less its `#` comments; a `#` inside a quoted string (GUI and loc formatting) stays."""
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def script_refs(text):
    """(state, kind) for every scope link and directive in a script or GUI file's text."""
    text = strip_comments(text)
    return ([(m.group(1), "s:") for m in SCOPE_RE.finditer(text)]
            + [(m.group(1), "directive") for m in DIRECTIVE_RE.finditer(text)])


def list_refs(text, kind):
    return [(s, kind) for block in LIST_RE[kind].findall(strip_comments(text)) for s in re.findall(STATE, block)]


def loc_refs(text):
    """(state, kind) in loc or translation-memory text: scope links, hub-name splices, bloc name keys."""
    return ([(m.group(1), "s:") for m in SCOPE_RE.finditer(text)]
            + [(m.group(1), "HUB_NAME") for m in HUB_RE.finditer(text)]
            + [(m.group(1), "bloc name key") for m in BLOC_KEY_RE.finditer(text)])


def tracked(*patterns):
    out = subprocess.run(["git", "ls-files", "--", *patterns], cwd=ROOT, capture_output=True, text=True, check=True)
    return [ROOT / p for p in out.stdout.split()]


def read(path):
    return path.read_text(encoding="utf-8-sig")


def all_refs():
    """{(relative path, state, kind)} for every reference the scan finds."""
    refs = set()

    def add(path, found):
        refs.update((str(path.relative_to(ROOT)), s, k) for s, k in found)

    for path in tracked("common/*.txt", "events/*.txt", "gui/*.gui", "map_data/*.txt"):
        if "map_data/state_regions/" in str(path):
            add(path, [(m.group(1), "directive") for m in DIRECTIVE_RE.finditer(strip_comments(read(path)))])
            continue
        text = read(path)
        add(path, script_refs(text))
        for kind in LIST_RE:
            if f"common/{kind}/" in str(path):
                add(path, list_refs(text, kind))
    for path in tracked("localization/*.yml", "i18n/*.json"):
        add(path, loc_refs(read(path)))
    for name in ("deposits_config.json", "state_trait_config.json"):
        path = ROOT / name
        add(path, [(k.lstrip("+-"), "config key") for k in json.loads(read(path)) if re.fullmatch(STATE, k.lstrip("+-"))])
    for path in tracked("scripts/generators/data/*.csv"):
        with open(path, encoding="utf-8-sig", newline="") as f:
            add(path, [(cell, "csv cell") for row in csv.reader(f) for cell in row if re.fullmatch(STATE, cell)])
    for path in tracked("scripts/analysis/demographics_*.json"):
        add(path, [(s, "table") for s in re.findall(rf'"({STATE})"', read(path))])
    for path in tracked("scripts/*.py", "*.py"):
        if path.name.startswith("test_"):
            continue
        add(path, [(m.group(1), "python literal") for m in PY_LITERAL_RE.finditer(path.read_text(encoding="utf-8"))
                   if m.group(1) not in NOT_STATES])
    return refs


class Scanner(unittest.TestCase):
    """The scan finds a stale name in each form it reads."""

    def test_script_forms(self):
        text = ("INJECT:STATE_KAUNAS = { traits = { } }\nREPLACE_OR_CREATE:STATE_GALICH = { }\n"
                "if = { limit = { state_region = s:STATE_TARTARIA } }\n# s:STATE_IN_A_COMMENT\n"
                'text = "#b s:STATE_IN_QUOTES#!"\nmodifier:state_birth_rate_mult = 1\n')
        self.assertEqual(sorted(script_refs(text)), [("STATE_GALICH", "directive"), ("STATE_IN_QUOTES", "s:"),
                                                      ("STATE_KAUNAS", "directive"), ("STATE_TARTARIA", "s:")])

    def test_lists(self):
        text = "region_x = {\n\tstate_regions = { STATE_KAUNAS STATE_TULA } # STATE_COMMENT\n}\n"
        self.assertEqual(sorted(list_refs(text, "geographic_regions")),
                         [("STATE_KAUNAS", "geographic_regions"), ("STATE_TULA", "geographic_regions")])
        self.assertEqual(list_refs("region_y = {\n\tstates = { STATE_CHUKOTKA }\n}\n", "strategic_regions"),
                         [("STATE_CHUKOTKA", "strategic_regions")])

    def test_loc_forms(self):
        text = (' te_pb_name_league_STATE_KAUNAS: "League of $HUB_NAME_STATE_KAUNAS_city|q$"\n'
                ' x: "[GetPlayer.MakeScope.ScriptValue(\'v\')] s:STATE_GALICH"\n STATE_TAX_CAPACITY_DESC: "y"\n')
        self.assertEqual(sorted(loc_refs(text)), [("STATE_GALICH", "s:"), ("STATE_KAUNAS", "HUB_NAME"),
                                                   ("STATE_KAUNAS", "bloc name key")])

    def test_a_gui_loc_key_is_not_a_state(self):
        self.assertEqual(script_refs('text = "STATE_WORLD_MARKET_ACCESS"\n'), [])


class Committed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states = map_states()
        cls.refs = all_refs()

    def test_the_map_has_its_states(self):
        self.assertIn("STATE_TULA", self.states)
        self.assertIn("STATE_LITHUANIA", self.states)
        self.assertNotIn("STATE_KAUNAS", self.states)
        self.assertGreater(len(self.states), 700)

    def test_the_scan_reads_every_form(self):
        kinds = {k for _, _, k in self.refs}
        for kind in ("s:", "geographic_regions", "strategic_regions", "HUB_NAME", "bloc name key", "config key",
                     "csv cell", "table", "python literal"):
            self.assertIn(kind, kinds)

    def test_every_named_state_is_on_the_map(self):
        stale = sorted(f"{path}: {state} ({kind})" for path, state, kind in self.refs if state not in self.states)
        self.assertEqual(stale, [], "a state the map doesn't have: point it at the state vanilla renamed it to, or "
                                    "drop it if vanilla removed it")


if __name__ == "__main__":
    unittest.main()
