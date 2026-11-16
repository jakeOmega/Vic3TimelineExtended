"""AI goods stances for the mod's own goods (#1822).

A goods stance tells the AI it wants a good in high supply, wants to export it, wants to import it or does not want it;
a good no strategy names gets no push at all when the AI scores buildings, production methods and trade. Five of the
mod's goods had none. The engine says nothing about a good that lacks one, so:

- every good the mod adds is named by a stance in one of the mod's strategy files, or is on EXEMPT with the reason;
- every stance is one of the four values the game executable holds, and gates on technologies that exist;
- every input of the mod's four later construction tiers has a stance (vanilla's default strategy's or the mod's)
  whose gate the country has passed by the time it can use the tier, or is on CONSTRUCTION_INPUTS_UNSTANCED;
- the three export stances sit in the administrative strategies named in
  common/ai_strategies/te_ai_export_stance_strategies.txt.

docs/systems/mod_systems/ai.md § AI Coverage of the Mod's Content.
"""
import json
import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
GOODS = ROOT / "common/goods/timeline_extended_extra_goods.txt"
STRATEGY_FILES = sorted((ROOT / "common/ai_strategies").glob("*.txt"))
DEFAULT = ROOT / "common/ai_strategies/edited_default_strategy.txt"
EXPORTS = ROOT / "common/ai_strategies/te_ai_export_stance_strategies.txt"
SYSTEM_DOC = ROOT / "docs/systems/mod_systems/ai.md"

# The stance values among the 1.15.1 executable's strings. Vanilla's files use the first three.
STANCES = {"wants_high_supply", "wants_export", "does_not_want", "wants_import"}

# A good the mod adds that is meant to have no stance, and why.
EXEMPT = {
    "grid_power": "a fixed-price settlement good (tradeable = no): Grid Transfer Stations buy and sell it at base "
                  "price, so no stance could move it",
}

# Vanilla goods the mod REPLACEs. Vanilla's strategies decide their stances (aeroplanes and tanks in the default
# strategy, fertilizer in the agricultural and industrial ones); transportation is a local good vanilla gives none.
REPLACED_VANILLA_GOODS = {"transportation", "aeroplanes", "fertilizer", "tanks"}

# Vanilla 1.15.1's default strategy: the goods it names that the mod's later construction tiers use, and the
# technology each is gated on (game/common/ai_strategies/00_default_strategy.txt, goods_stances).
VANILLA_DEFAULT_GATES = {
    "electricity": {"electrical_generation"},
    "copper": {"electrical_generation"},
    "engines": {"railways"},
}

# Inputs of the later construction tiers that keep no default stance: vanilla's own construction tiers use each of
# them (or, for transportation, a local good) and vanilla's default strategy names none; its industrial
# strategies want steel and tools.
CONSTRUCTION_INPUTS_UNSTANCED = {"steel", "glass", "explosives", "tools", "transportation"}

LATER_CONSTRUCTION_TIERS = (
    "pm_reinforced_concrete_buildings",
    "pm_advanced_construction",
    "pm_nanomaterial_buildings",
    "pm_self_replicating_construction",
)

EXPORT_STANCES = {
    "ai_strategy_agricultural_expansion": {"tourism"},
    "ai_strategy_plantation_economy": {"tourism"},
    "ai_strategy_industrial_expansion": {"consumer_appliances"},
}


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        if isinstance(part, dict):
            for key, (op, value) in part.items():
                yield key, op, value


def parse(path):
    parser = ParadoxFileParser()
    return parser.parse_object(parser.tokenize("{" + path.read_text(encoding="utf-8-sig") + "}"))[0]


def field(block, key):
    return next((value for k, _, value in entries(block) if k == key), None)


def bare(name):
    return name.split(":")[-1]


def stances_by_strategy():
    """{strategy: {good: (stance, trigger block)}} over the mod's strategy files."""
    out = {}
    for path in STRATEGY_FILES:
        for name, _, block in entries(parse(path)):
            for key, _, value in entries(block):
                if key != "goods_stances":
                    continue
                for good, _, entry in entries(value):
                    out.setdefault(bare(name), {})[good] = (field(entry, "stance"), field(entry, "trigger"))
    return out


def technologies_in(block):
    found = set()
    for key, _, value in entries(block):
        if key == "has_technology_researched":
            found.add(value)
        elif isinstance(value, (dict, list)):
            found |= technologies_in(value)
    return found


def required_technologies(trigger):
    """The technologies a trigger needs: its top-level has_technology_researched lines (an OR or a NOT needs none)."""
    return {value for key, _, value in entries(trigger) if key == "has_technology_researched"} if trigger else set()


def all_technologies():
    """({technology: its unlocking_technologies}, {technology: its era number}) over vanilla's snapshot and the mod."""
    techs, eras = {}, {}

    def take(name, block):
        techs[name] = list(field(block, "unlocking_technologies") or [])
        eras[name] = int(field(block, "era").split("_")[1])

    for name, entry in json.loads((ROOT / "vanilla_parsed/common/technologies.json").read_text()).items():
        take(name, entry[1])
    for path in sorted((ROOT / "common/technology/technologies").glob("*.txt")):
        for name, _, block in entries(parse(path)):
            if name.startswith("INJECT:") and bare(name) in techs:
                continue
            take(bare(name), block)
    return techs, eras


def with_ancestors(tech, techs):
    seen, todo = set(), [tech]
    while todo:
        current = todo.pop()
        if current not in seen:
            seen.add(current)
            todo.extend(techs.get(current, ()))
    return seen


def method_block(name):
    for path in sorted((ROOT / "common/production_methods").glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig")
        if not re.search(r"(?m)^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text):
            continue
        for key, _, block in entries(parse(path)):
            if bare(key) == name:
                return block
    return None


def input_goods(block):
    found = set()
    for key, _, value in entries(block):
        m = re.fullmatch(r"goods_input_(.+)_add", key)
        if m:
            found.add(m.group(1))
        elif isinstance(value, (dict, list)):
            found |= input_goods(value)
    return found


class GoodsStanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stances = stances_by_strategy()
        cls.named = {good for goods in cls.stances.values() for good in goods}
        cls.goods = [name for name, _, _ in entries(parse(GOODS))]
        cls.techs, cls.eras = all_technologies()

    def test_every_mod_good_has_a_stance_or_a_stated_exemption(self):
        new_goods = [g for g in self.goods if ":" not in g]
        self.assertGreaterEqual(len(new_goods), 13)
        missing = [g for g in new_goods if g not in self.named and g not in EXEMPT]
        self.assertEqual(missing, [], "a good no strategy names gets no AI push: add a stance or an EXEMPT entry")
        self.assertEqual([g for g in EXEMPT if g in self.named], [], "exempt goods that now have a stance")
        self.assertEqual([g for g in EXEMPT if g not in new_goods], [], "exempt goods the mod no longer defines")

    def test_replaced_vanilla_goods_are_the_ones_listed(self):
        replaced = {bare(g) for g in self.goods if ":" in g}
        self.assertEqual(replaced, REPLACED_VANILLA_GOODS)

    def test_every_stance_is_a_known_value_with_real_technologies(self):
        checked = 0
        for strategy, goods in self.stances.items():
            for good, (stance, trigger) in goods.items():
                with self.subTest(strategy=strategy, good=good):
                    self.assertIn(stance, STANCES)
                    for tech in technologies_in(trigger) if trigger else ():
                        self.assertIn(tech, self.techs)
                    checked += 1
        self.assertGreaterEqual(checked, 15)

    def test_the_default_strategy_gates_each_mod_stance_on_a_technology(self):
        # "construction" is the one ungated stance: every country builds from day one.
        for good, (stance, trigger) in self.stances["ai_strategy_default"].items():
            if good == "construction":
                continue
            with self.subTest(good=good):
                self.assertTrue(required_technologies(trigger), "gate it on the technology that brings the good")

    def test_later_construction_tiers_inputs_are_wanted_by_the_time_the_tier_unlocks(self):
        default = self.stances["ai_strategy_default"]
        for tier in LATER_CONSTRUCTION_TIERS:
            block = method_block(tier)
            self.assertIsNotNone(block, tier)
            unlocking = list(field(block, "unlocking_technologies") or [])
            self.assertEqual(len(unlocking), 1, tier)
            held = with_ancestors(unlocking[0], self.techs)
            inputs = input_goods(block)
            self.assertGreaterEqual(len(inputs), 8, tier)
            for good in sorted(inputs - CONSTRUCTION_INPUTS_UNSTANCED):
                with self.subTest(tier=tier, good=good):
                    if good in VANILLA_DEFAULT_GATES:
                        # Vanilla's gates sit four or more eras before the tier, in other branches of the tree.
                        for gate in VANILLA_DEFAULT_GATES[good]:
                            self.assertLess(self.eras[gate], self.eras[unlocking[0]])
                        continue
                    else:
                        self.assertIn(good, default, "an input of a later construction tier with no default stance")
                        stance, trigger = default[good]
                        self.assertEqual(stance, "wants_high_supply")
                        gates = required_technologies(trigger)
                    self.assertTrue(gates <= held, f"{good}'s gate {sorted(gates - held)} is not behind {unlocking[0]}")

    def test_unstanced_construction_inputs_are_still_inputs(self):
        used = set()
        for tier in LATER_CONSTRUCTION_TIERS:
            used |= input_goods(method_block(tier))
        self.assertEqual(CONSTRUCTION_INPUTS_UNSTANCED - used, set())
        self.assertEqual({g for g in CONSTRUCTION_INPUTS_UNSTANCED if g in self.stances["ai_strategy_default"]}, set())

    def test_motor_ships_hand_over_to_magnetic_drive_ships(self):
        default = self.stances["ai_strategy_default"]
        motor, magnetic = default["motor_ships"][1], default["magnetic_drive_ships"][1]
        successor = required_technologies(magnetic)
        self.assertEqual(successor, {"modern_material_science"})
        retired_on = technologies_in(field(motor, "NOT"))
        self.assertEqual(retired_on, successor, "motor ships retire on the technology that brings their successor")
        for trigger in (motor, magnetic):
            self.assertEqual(field(trigger, "has_port_country"), "yes")
            self.assertEqual(field(trigger, "country_rank"), "rank_value:major_power")

    def test_export_stances(self):
        text = EXPORTS.read_text(encoding="utf-8-sig")
        injected = re.findall(r"(?m)^INJECT:(ai_strategy_\w+)\s*=\s*\{", text)
        self.assertEqual(sorted(injected), sorted(EXPORT_STANCES))
        self.assertEqual(re.findall(r"(?m)^(?!INJECT:)[A-Z_]*:?ai_strategy_\w+\s*=\s*\{", text), [],
                         "only INJECTs: a REPLACE would drop vanilla's strategy")
        for strategy, goods in EXPORT_STANCES.items():
            with self.subTest(strategy=strategy):
                self.assertEqual(set(self.stances[strategy]), goods)
                for good in goods:
                    stance, trigger = self.stances[strategy][good]
                    self.assertEqual(stance, "wants_export")
                    self.assertTrue(required_technologies(trigger))

    def test_matches_the_game_files(self):
        try:
            from path_constants import base_game_path
            path = Path(base_game_path) / "game/common/ai_strategies/00_default_strategy.txt"
        except Exception:
            path = None
        if path is None or not path.is_file():
            self.skipTest("no Victoria 3 install")
        vanilla = {}
        for name, _, block in entries(parse(path)):
            if name == "ai_strategy_default":
                for good, _, entry in entries(field(block, "goods_stances")):
                    vanilla[good] = (field(entry, "stance"), field(entry, "trigger"))
        for good, gates in VANILLA_DEFAULT_GATES.items():
            with self.subTest(good=good):
                self.assertEqual(vanilla[good][0], "wants_high_supply")
                self.assertEqual(required_technologies(vanilla[good][1]), gates)
        # A key vanilla's block already holds keeps vanilla's value under an INJECT, so the mod must not restate one.
        clash = sorted(set(self.stances["ai_strategy_default"]) & set(vanilla))
        self.assertEqual(clash, [], "the default strategy's INJECT names a good vanilla's block already holds")
        for good in CONSTRUCTION_INPUTS_UNSTANCED:
            self.assertNotIn(good, vanilla)

    def test_the_system_doc_covers_it(self):
        doc = SYSTEM_DOC.read_text(encoding="utf-8")
        self.assertTrue("## AI Coverage of the Mod's Content" in doc, "ai.md lost its section")
        for good in ("consumer_appliances", "tech_metals", "motor_ships", "magnetic_drive_ships", "tourism",
                     "automobiles", "grid_power", "steamers"):
            with self.subTest(good=good):
                self.assertTrue(f"`{good}`" in doc, f"ai.md does not mention {good}")


if __name__ == "__main__":
    unittest.main()
