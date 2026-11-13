"""The United Nations of Earth's four great-power gates list the great powers (#1436).

`une_formation_supermajority`, `une_formation_bloc_aligned`,
`une_formation_no_internal_rivalry` and the bloc-unanimity branch of
`une_formation_world_order` were `NOT = { any_country = { ... } }` tests,
which vanilla 1.15's `list_scopes` cannot list. They are now positive counts
over the great powers other than ROOT (`filter`, then `count = all` or a
`percent >=` share from te_formation_gating_values.txt). This test runs both
forms through a small evaluator of the triggers as written, over random
worlds, and fails if any world tells them apart: the rewrite must not change
who can form the union. It also pins the tooltip keys, which the engine
checks nowhere.

The evaluator knows `filter`, `count = all` and `percent` in the meaning
vanilla's tsar buttons give them (a count or share over the filtered scopes)
and treats a `trigger_if` whose limit fails as true. It refuses `filter` with
any other count, as the engine does at load ("Filter should only be used if a
percent or count = all is specified", PostValidate false): the first rewrite
used `count >= <value>` there, passed this test, and failed in game
(2026-11-12). `any_limit_audit` checks the same rule over the whole mod. The
pre-rewrite triggers are kept below as text so the comparison doesn't need git.
"""
import random
import tempfile
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/formable_gating_triggers.txt"
VALUES = ROOT / "common/script_values/te_formation_gating_values.txt"
GATES = ("une_formation_supermajority", "une_formation_bloc_aligned",
         "une_formation_no_internal_rivalry", "une_formation_world_order")

# The four gates as they stood before the rewrite (main, 2026-11-12).
OLD = """
une_formation_supermajority = {
	is_power_bloc_leader = yes
	NOT = {
		any_country = {
			country_rank >= rank_value:great_power
			NOT = { this = ROOT }
			NOT = { is_in_same_power_bloc = ROOT }
			count >= 2
		}
	}
}
une_formation_bloc_aligned = {
	NOT = {
		any_country = {
			country_rank >= rank_value:great_power
			NOT = { this = ROOT }
			NOT = { is_in_same_power_bloc = ROOT }
			NOT = { is_aligned_with_root = yes }
		}
	}
}
une_formation_no_internal_rivalry = {
	NOT = {
		any_country = {
			country_rank >= rank_value:great_power
			NOT = { this = ROOT }
			is_at_friction_with_root = yes
		}
	}
}
une_formation_world_order = {
	trigger_if = {
		limit = { has_game_rule = united_nations_enabled }
		custom_tooltip = {
			text = une_formation_un_supranational_tt
			un_tier_is_supranational = yes
		}
	}
	trigger_else = {
		custom_tooltip = {
			text = une_formation_bloc_unanimity_tt
			NOT = {
				any_country = {
					country_rank >= rank_value:great_power
					NOT = { this = ROOT }
					NOT = { is_in_same_power_bloc = ROOT }
				}
			}
		}
	}
}
"""

DISPLAY_KEYS = {"list_scopes", "show_trigger_per_scope", "text"}


def parse_text(text):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "old.txt"
        path.write_text(text, encoding="utf-8")
        return parse_file(path)


def parse_file(path, script_values=False):
    parser = ParadoxFileParser(script_values=script_values)
    parser.parse_file(str(path), False)
    return parser.data


def entries(block):
    """(key, op, value) for each statement, in order."""
    for key, items in block.items():
        pairs = items if isinstance(items, list) else [items]
        for op, value in pairs:
            yield key, op, value


class World:
    def __init__(self, rng):
        n = rng.randint(1, 9)
        self.countries = list(range(n))
        self.gp = {c: rng.random() < 0.6 for c in self.countries}
        self.bloc = {c: rng.random() < 0.6 for c in self.countries}  # in ROOT's bloc
        self.aligned = {c: rng.random() < 0.5 for c in self.countries}
        self.friction = {c: rng.random() < 0.3 for c in self.countries}
        self.root = 0
        self.bloc[0] = True
        self.leader = rng.random() < 0.8
        self.un_rule = rng.random() < 0.5
        self.supranational = rng.random() < 0.5


class Evaluator:
    def __init__(self, world, script_values):
        self.w = world
        self.sv = script_values

    def value(self, token):
        if isinstance(token, dict):
            body = token
        else:
            try:
                return float(token)
            except ValueError:
                pass
            _, body = self.sv[token]
        total = 0.0
        for key, _, val in entries(body):
            if key == "value":
                total = self.value(val)
            elif key == "subtract":
                total -= self.value(val)
            elif key == "add":
                total += self.value(val)
            elif key == "divide":
                divisor = self.value(val)
                assert divisor != 0, "script value divides by zero"
                total /= divisor
            elif key == "min":
                total = max(total, self.value(val))
            elif key == "every_country":
                limit = val["limit"][1]
                add = self.value(val["add"][1])
                total += sum(add for c in self.w.countries if self.block(limit, c))
            else:
                raise AssertionError(f"script value key {key} not modelled")
        return total

    def block(self, body, scope):
        """AND of the statements in `body`, in scope `scope`."""
        pending_else = None
        for key, op, val in entries(body):
            if key in DISPLAY_KEYS:
                continue
            if key == "trigger_if":
                if self.block(val["limit"][1], scope):
                    if not self.block({k: v for k, v in val.items() if k != "limit"}, scope):
                        return False
                    pending_else = None
                else:
                    pending_else = True
                continue
            if key == "trigger_else":
                if pending_else and not self.block(val, scope):
                    return False
                pending_else = None
                continue
            if not self.statement(key, op, val, scope):
                return False
        return True

    def statement(self, key, op, val, scope):
        w = self.w
        if key == "NOT":
            return not self.block(val, scope)
        if key == "OR":
            return any(self.block({k: v}, scope) for k, v in val.items())
        if key == "custom_tooltip":
            return self.block(val, scope)
        if key == "this":
            assert val == "ROOT"
            return scope == w.root
        if key == "country_rank":
            assert (op, val) == (">=", "rank_value:great_power")
            return w.gp[scope]
        if key == "is_in_same_power_bloc":
            return w.bloc[scope]
        if key == "is_aligned_with_root":
            return w.aligned[scope] == (val == "yes")
        if key == "is_at_friction_with_root":
            return w.friction[scope] == (val == "yes")
        if key == "is_power_bloc_leader":
            return w.leader
        if key == "has_game_rule":
            assert val == "united_nations_enabled"
            return w.un_rule
        if key == "un_tier_is_supranational":
            return w.supranational
        if key == "any_country":
            return self.any_country(val)
        raise AssertionError(f"trigger {key} not modelled")

    def any_country(self, body):
        filt = body.get("filter")
        count = body.get("count")
        percent = body.get("percent")
        if filt is not None:
            assert percent is not None or count == ("=", "all"), (
                "the engine takes `filter` only with `percent` or `count = all`")
        cond = {k: v for k, v in body.items() if k not in ("filter", "count", "percent")}
        pool = [c for c in self.w.countries if filt is None or self.block(filt[1], c)]
        hits = sum(1 for c in pool if self.block(cond, c))
        if percent is not None:
            op, n = percent
            assert op == ">=", op
            assert pool, "a share of no scopes"
            return hits / len(pool) >= self.value(n)
        if count is None:
            return hits >= 1
        op, n = count
        if n == "all":
            assert op == "="
            return hits == len(pool)
        assert op == ">=", op
        return hits >= self.value(n)


class UneGatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new = parse_file(TRIGGERS)
        cls.old = parse_text(OLD)
        cls.sv = parse_file(VALUES, script_values=True)

    def test_rewrite_is_equivalent(self):
        rng = random.Random(1436)
        for _ in range(4000):
            world = World(rng)
            for gate in GATES:
                old = Evaluator(world, self.sv).block(self.old[gate][1], world.root)
                new = Evaluator(world, self.sv).block(self.new[gate][1], world.root)
                self.assertEqual(old, new, f"{gate} differs: gp={world.gp} bloc={world.bloc} "
                                 f"aligned={world.aligned} friction={world.friction}")

    def test_every_count_lists_its_scopes(self):
        def counts(body):
            for key, _, val in entries(body):
                if key == "any_country" and "filter" in val:
                    yield val
                if isinstance(val, dict):
                    yield from counts(val)
        for gate in GATES:
            found = list(counts(self.new[gate][1]))
            self.assertTrue(found, f"{gate} has no filtered count")
            for body in found:
                self.assertEqual(tuple(body.get("list_scopes", ())), ("=", "yes"), gate)
                self.assertEqual(tuple(body.get("show_trigger_per_scope", ())), ("=", "yes"), gate)


if __name__ == "__main__":
    unittest.main()
