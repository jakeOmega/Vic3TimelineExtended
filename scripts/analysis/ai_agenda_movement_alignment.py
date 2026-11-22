#!/usr/bin/env python3
"""How far each political movement's wishes agree with each AI political agenda's interest groups.

    .venv/bin/python scripts/analysis/ai_agenda_movement_alignment.py            # the mod's four movements
    .venv/bin/python scripts/analysis/ai_agenda_movement_alignment.py --calibrate # against vanilla's own lists
    .venv/bin/python scripts/analysis/ai_agenda_movement_alignment.py --ideologies # the mod's leader ideologies
    .venv/bin/python scripts/analysis/ai_agenda_movement_alignment.py movement_feminist ideology_corporate

Read-only, no game needed. It is the method behind the movement lists the mod INJECTs into the political agendas
(common/ai_strategies/te_ai_movement_strategies.txt; docs/systems/mod_systems/ai.md § AI Coverage of the Mod's
Content, whose table these figures fill).

THE SCORE. A movement wants what its ideology's law stances say (strongly approve +2, approve +1, disapprove -1,
strongly disapprove -2; neutral 0). An agenda favors some interest groups (`pro_interest_groups`) and opposes others
(`anti_interest_groups`). For every law the movement's ideology has a view on, multiply that view by the view of
each base ideology of each favored group, and sum; subtract the same sum over the opposed groups. Positive: the
agenda's friends want what the movement wants and its opponents don't. It is a count of agreements, not a
probability, and it grows with the number of laws an ideology has views on, so compare scores of one movement across
agendas rather than across movements.

WHAT IT READS. Ideologies and interest groups from vanilla's snapshot (vanilla_parsed/common/*.json) with the mod's
files over them (a REPLACE or a new entry replaces; an INJECT's blocks are read after vanilla's, so its stances
win). Movements from the snapshot and the mod's common/political_movements. The five common agendas' interest-group
and movement lists are vanilla 1.15.1's, held in AGENDAS below because the snapshot has no AI strategies;
--calibrate re-reads them from the game where it is installed and says if they have changed.

--calibrate counts, over every movement on a vanilla agenda's pro or anti list, how often the score's sign agrees
with the side vanilla put it on (90 of 98 on 2026-11-15) and lists the misses.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paradox_file_parser import ParadoxFileParser  # noqa: E402

STANCE = {"strongly_approve": 2, "approve": 1, "neutral": 0, "disapprove": -1, "strongly_disapprove": -2}
MOD_MOVEMENTS = ("movement_civil_rights", "movement_anti_war", "movement_transhumanist", "movement_environmental")

# Vanilla 1.15.1, game/common/ai_strategies/03_political_strategies.txt.
AGENDAS = {
    "conservative": {
        "pro_ig": ["ig_rural_folk", "ig_devout", "ig_landowners", "ig_armed_forces", "ig_petty_bourgeoisie"],
        "anti_ig": ["ig_trade_unions"],
        "pro_movements": ["movement_royalist_constitutional", "movement_royalist_absolutist",
                          "movement_religious_majority", "movement_cultural_majority", "movement_utilitarian",
                          "movement_corporatist", "movement_modernizer"],
        "anti_movements": ["movement_socialist", "movement_labor", "movement_communist", "movement_anarchist",
                           "movement_nihilist", "movement_feminist", "movement_radical", "movement_german_national",
                           "movement_italian_national", "movement_yugoslav_national"],
    },
    "reactionary": {
        "pro_ig": ["ig_devout", "ig_landowners"],
        "anti_ig": ["ig_intelligentsia", "ig_trade_unions", "ig_industrialists"],
        "pro_movements": ["movement_royalist_constitutional", "movement_royalist_absolutist",
                          "movement_religious_majority", "movement_cultural_majority", "movement_reactionary",
                          "movement_legitimist", "movement_pro_slavery"],
        "anti_movements": ["movement_socialist", "movement_labor", "movement_communist", "movement_anarchist",
                           "movement_nihilist", "movement_radical", "movement_liberal", "movement_german_national",
                           "movement_italian_national", "movement_modernizer", "movement_feminist",
                           "movement_positivist", "movement_cultural_minority", "movement_religious_minority",
                           "movement_land_reform"],
    },
    "progressive": {
        "pro_ig": ["ig_intelligentsia", "ig_industrialists", "ig_petty_bourgeoisie"],
        "anti_ig": ["ig_landowners", "ig_rural_folk"],
        "pro_movements": ["movement_liberal", "movement_modernizer", "movement_anti_slavery", "movement_land_reform",
                          "movement_positivist", "movement_utilitarian", "movement_feminist", "movement_radical",
                          "movement_german_national", "movement_italian_national", "movement_yugoslav_national"],
        "anti_movements": ["movement_socialist", "movement_communist", "movement_anarchist", "movement_nihilist",
                           "movement_fascist", "movement_reactionary", "movement_royalist_absolutist",
                           "movement_pro_slavery"],
    },
    "egalitarian": {
        "pro_ig": ["ig_trade_unions"],
        "anti_ig": ["ig_landowners", "ig_industrialists", "ig_petty_bourgeoisie"],
        "pro_movements": ["movement_radical", "movement_labor", "movement_socialist", "movement_nihilist",
                          "movement_feminist", "movement_anti_slavery", "movement_land_reform"],
        "anti_movements": ["movement_royalist_constitutional", "movement_royalist_absolutist",
                           "movement_religious_majority", "movement_cultural_majority", "movement_corporatist",
                           "movement_reactionary", "movement_fascist", "movement_legitimist", "movement_pro_slavery",
                           "movement_liberal", "movement_orleanist", "movement_bonapartist",
                           "movement_german_national", "movement_italian_national", "movement_yugoslav_national"],
    },
    "nationalist": {
        "pro_ig": ["ig_armed_forces", "ig_petty_bourgeoisie"],
        "anti_ig": ["ig_rural_folk", "ig_trade_unions"],
        "pro_movements": ["movement_fascist", "movement_corporatist", "movement_positivist", "movement_modernizer",
                          "movement_bonapartist", "movement_cultural_majority", "movement_religious_majority",
                          "movement_german_national", "movement_italian_national", "movement_yugoslav_national"],
        "anti_movements": ["movement_radical", "movement_labor", "movement_socialist", "movement_communist",
                           "movement_nihilist", "movement_feminist", "movement_cultural_minority",
                           "movement_religious_minority"],
    },
}


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def parse(path: Path):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]


def vanilla(name: str) -> dict:
    return json.loads((ROOT / f"vanilla_parsed/common/{name}.json").read_text(encoding="utf-8"))


def mod_entries(subdir: str):
    for path in sorted((ROOT / "common" / subdir).rglob("*.txt")):
        for key, _, value in entries(parse(path)):
            yield key, value


class Data:
    def __init__(self):
        # ideology -> its blocks, in the order the engine would read them
        self.ideologies = {name: [entry[1]] for name, entry in vanilla("ideologies").items()}
        for key, block in mod_entries("ideologies"):
            name = key.split(":")[-1]
            if key.startswith("INJECT:") and name in self.ideologies:
                self.ideologies[name].append(block)
            else:
                self.ideologies[name] = [block]
        self.leader_ideologies = [key for key, block in mod_entries("ideologies")
                                  if ":" not in key and field(block, "character_ideology") == "yes"]
        self.interest_groups = {name: entry[1] for name, entry in vanilla("interest_groups").items()}
        for key, block in mod_entries("interest_groups"):
            if not key.startswith("INJECT:"):
                self.interest_groups[key.split(":")[-1]] = block
        self.movements = {name: entry[1] for name, entry in vanilla("political_movements").items()}
        for key, block in mod_entries("political_movements"):
            if not key.startswith("INJECT:"):
                self.movements[key.split(":")[-1]] = block

    def stances(self, ideology: str) -> dict[str, int]:
        out = {}
        for block in self.ideologies.get(ideology, ()):
            for key, _, group in entries(block):
                if key.startswith("lawgroup_"):
                    for law, _, stance in entries(group):
                        if isinstance(stance, str) and stance in STANCE:
                            out[law] = STANCE[stance]
        return out

    def group_agreement(self, interest_group: str, wants: dict[str, int]) -> int:
        total = 0
        for ideology in field(self.interest_groups[interest_group], "ideologies") or ():
            theirs = self.stances(ideology)
            total += sum(view * theirs[law] for law, view in wants.items() if law in theirs)
        return total

    def ideology_of(self, name: str) -> str:
        """A movement's ideology, or the name itself when it is an ideology."""
        return field(self.movements[name], "ideology") if name in self.movements else name

    def score(self, name: str, agenda: str) -> int:
        wants = self.stances(self.ideology_of(name))
        lists = AGENDAS[agenda]
        return (sum(self.group_agreement(ig, wants) for ig in lists["pro_ig"])
                - sum(self.group_agreement(ig, wants) for ig in lists["anti_ig"]))


def table(data: Data, names) -> str:
    lines = ["%-34s" % "" + "".join("%14s" % agenda for agenda in AGENDAS)]
    for name in names:
        lines.append("%-34s" % name + "".join("%+14d" % data.score(name, agenda) for agenda in AGENDAS))
    return "\n".join(lines)


def calibrate(data: Data) -> tuple[int, int, list]:
    agree, total, misses = 0, 0, []
    for agenda, lists in AGENDAS.items():
        for side, sign in (("pro_movements", 1), ("anti_movements", -1)):
            for movement in dict.fromkeys(lists[side]):
                if movement not in data.movements or not data.stances(data.ideology_of(movement)):
                    continue
                total += 1
                score = data.score(movement, agenda)
                if score * sign > 0:
                    agree += 1
                else:
                    misses.append((agenda, side, movement, score))
    return agree, total, misses


def game_agendas():
    """AGENDAS as the installed game has them, or None without a game."""
    try:
        from path_constants import base_game_path
        path = Path(base_game_path) / "game/common/ai_strategies/03_political_strategies.txt"
    except Exception:
        return None
    if not path.is_file():
        return None
    blocks = {key: value for key, _, value in entries(parse(path))}
    out = {}
    for agenda in AGENDAS:
        block = blocks[f"ai_strategy_{agenda}_agenda"]
        # dict.fromkeys: the game's egalitarian anti list names movement_legitimist twice.
        out[agenda] = {ours: list(dict.fromkeys(field(block, theirs) or ()))
                       for ours, theirs in (("pro_ig", "pro_interest_groups"), ("anti_ig", "anti_interest_groups"),
                                            ("pro_movements", "pro_movements"), ("anti_movements", "anti_movements"))}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("names", nargs="*", help="movements or ideologies to score (default: the mod's four movements)")
    ap.add_argument("--calibrate", action="store_true", help="compare the score's sign with vanilla's own lists")
    ap.add_argument("--ideologies", action="store_true", help="score the mod's leader ideologies")
    args = ap.parse_args(argv)
    data = Data()
    names = list(args.names) or (data.leader_ideologies if args.ideologies else list(MOD_MOVEMENTS))
    unknown = [n for n in names if n not in data.movements and n not in data.ideologies]
    if unknown:
        print("unknown movement or ideology: " + ", ".join(unknown), file=sys.stderr)
        return 2
    print(table(data, names))
    if args.calibrate:
        installed = game_agendas()
        if installed is None:
            print("\n(no game install: vanilla's lists are the 1.15.1 copy in this script)")
        elif installed != AGENDAS:
            print("\nWARNING: the installed game's agenda lists differ from the copy in this script; update AGENDAS.")
        agree, total, misses = calibrate(data)
        print(f"\nvanilla's own lists: the score's sign agrees with vanilla's side in {agree} of {total} cases; misses:")
        for agenda, side, movement, score in misses:
            print(f"  {agenda:13s} {side:15s} {movement:32s} {score:+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
