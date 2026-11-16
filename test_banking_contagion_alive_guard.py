"""`is_market_reachable_for_trade` crashes the game on a country with no states (#1871).

A country that loses its last state at war stays in the game, with no capital
and no market, and `every_country` still reaches it. On such a country the
engine's `is_market_reachable_for_trade` falls back to a land search from the
capital, starts it from the null State and writes 16 MB past a stack buffer: a
crash to desktop (game 1.15.1, RVA 0xd63d38, the October 1913 observer run of
2026-11-16). The banking contagion, `banking_cycle_spread_contagion`, asked it
of every country with a running cycle and no `is_country_alive` guard.

So every use of the trigger in the mod's script must sit behind
`is_country_alive = yes` for the country in scope: an earlier condition of the
same limit or trigger block (or of an AND-like block around it), or the limit
of an `if` / `trigger_if` around it, with no scope change in between. A guard
beside the use in an `OR`, `NOT`, `NOR` or `NAND` does not count: an `OR` goes
on to its next child when the guard fails. `exists = capital` is not a guard,
because a stateless country's capital can still resolve to the state it lost
(scripting_best_practices.md § "Guard Scope References in Triggers").

The contagion's own guards are pinned too: the target guard as the first line
of its `every_country` limit, the origin guard around the spread, and the
crash roll behind the same test of the origin.
"""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGER = "is_market_reachable_for_trade"
OPERATORS = {"=", "?=", "<", ">", "<=", ">=", "!=", "=="}

# Blocks whose children are all required (an AND): an earlier
# `is_country_alive = yes` among them guards everything after it.
AND_LIKE = {
    "AND", "limit", "trigger", "hidden_trigger", "custom_tooltip", "possible",
    "is_shown", "is_valid", "visible", "potential", "allow", "can_ratify",
    "trigger_if", "trigger_else_if",
}
# Same scope, but a sibling guard here does not run first and stop the rest.
PASS_THROUGH = {"OR", "NOT", "NOR", "NAND"}
# Effect blocks of the same scope whose `limit` child guards their body.
CONDITIONAL = {"if", "else_if", "trigger_if", "trigger_else_if"}
# Same-scope effect wrappers to climb through. Anything else (an iterator, a
# `scope:`, a link like `market` or `capital`) ends the climb: a guard above it
# tested another object.
SAME_SCOPE_EFFECTS = {"hidden_effect", "custom_tooltip", "if", "else_if"}


def parse_body(source):
    """The script as ordered (key, op, value) triples; a block's value is a list."""
    tokens = ParadoxFileParser().tokenize(source)
    pos = 0

    def body():
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                return result
            if key == "{":  # an anonymous block, as in a list of lists
                result.append((None, None, body()))
                continue
            if pos >= len(tokens) or tokens[pos] not in OPERATORS:
                result.append((key, None, None))
                continue
            op, value = tokens[pos], tokens[pos + 1]
            pos += 2
            result.append((key, op, body() if value == "{" else value.strip('"')))
        return result

    return body()


def is_alive_guard(entry):
    key, op, value = entry
    return key == "is_country_alive" and op == "=" and value == "yes"


def find_uses(body, path=()):
    """Yield the ancestor chain of each use of TRIGGER: a tuple of (block, index)
    pairs from the outermost block in, where index is the child's position."""
    for index, (key, _, value) in enumerate(body):
        here = (*path, (body, index))
        if key == TRIGGER:
            yield here
        if isinstance(value, list):
            yield from find_uses(value, here)


def guarded(chain, top_level_and_like):
    """Whether the use at the end of ``chain`` sits behind `is_country_alive = yes`."""
    # Walk outward. At each level, `body` is the block holding the child at
    # `index`; its own key is the key of the entry one level further out.
    for depth in range(len(chain) - 1, -1, -1):
        body, index = chain[depth]
        if depth == 0:
            return False  # the file's top level holds entities, not conditions
        outer_body, outer_index = chain[depth - 1]
        key = outer_body[outer_index][0]
        if key in AND_LIKE and any(is_alive_guard(e) for e in body[:index]):
            return True
        if key in CONDITIONAL and body[index][0] != "limit":
            limit = next((v for k, _, v in body if k == "limit" and isinstance(v, list)), [])
            if any(is_alive_guard(e) for e in limit):
                return True
        if key in AND_LIKE or key in PASS_THROUGH or key in SAME_SCOPE_EFFECTS:
            continue
        # The entity itself, one level below the file's top: an effect, event,
        # trigger or article. Its body is not an AND unless it is a scripted trigger.
        if depth == 1:
            return top_level_and_like and key is not None and any(
                is_alive_guard(e) for e in body[:index])
        return False
    return False


def unguarded_uses(source, scripted_trigger_file=False):
    """Each unguarded use as ``entity name``, for one file's text."""
    found = []
    for chain in find_uses(parse_body(source)):
        if not guarded(chain, scripted_trigger_file):
            top_body, top_index = chain[0]
            found.append(top_body[top_index][0])
    return found


def script_files():
    for folder in ("common", "events"):
        for path in sorted((ROOT / folder).rglob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            if TRIGGER in text:
                yield path, text


def entity(path, name):
    for key, _, value in parse_body((ROOT / path).read_text(encoding="utf-8-sig")):
        if key == name:
            return value
    raise AssertionError(f"{name} not found in {path}")


def child(body, key):
    return next(value for k, _, value in body if k == key)


class CheckerSelfTest(unittest.TestCase):
    """The checker on small cases, so a pass below means something."""

    def flags(self, source, scripted_trigger_file=False):
        return unguarded_uses(source, scripted_trigger_file)

    def test_first_line_guard_passes(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            is_country_alive = yes
            OR = { this.market = scope:o.market  is_market_reachable_for_trade = scope:o.market }
        } } }"""), [])

    def test_unguarded_use_fails(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            OR = { is_market_reachable_for_trade = scope:o.market }
        } } }"""), ["e"])

    def test_guard_after_the_use_fails(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            is_market_reachable_for_trade = scope:o.market
            is_country_alive = yes
        } } }"""), ["e"])

    def test_guard_inside_an_or_fails(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            OR = { is_country_alive = yes  is_market_reachable_for_trade = scope:o.market }
        } } }"""), ["e"])

    def test_guard_beyond_a_scope_change_fails(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            is_country_alive = yes
            scope:other = { is_market_reachable_for_trade = scope:o.market }
        } } }"""), ["e"])

    def test_exists_capital_is_not_a_guard(self):
        self.assertEqual(self.flags("""e = { every_country = { limit = {
            exists = capital
            is_market_reachable_for_trade = scope:o.market
        } } }"""), ["e"])

    def test_if_limit_guards_its_body(self):
        self.assertEqual(self.flags("""e = { if = { limit = { is_country_alive = yes }
            if = { limit = { is_market_reachable_for_trade = scope:o.market } x = yes }
        } }"""), [])

    def test_scripted_trigger_top_level_guard(self):
        self.assertEqual(self.flags(
            "t = { is_country_alive = yes  is_market_reachable_for_trade = scope:o.market }",
            scripted_trigger_file=True), [])
        self.assertEqual(self.flags(
            "t = { is_market_reachable_for_trade = scope:o.market }",
            scripted_trigger_file=True), ["t"])

    def test_comment_is_not_a_use(self):
        self.assertEqual(self.flags("e = { # is_market_reachable_for_trade = x\n}"), [])


class EveryUseIsGuarded(unittest.TestCase):
    def test_no_unguarded_use_in_mod_script(self):
        failures, uses = [], 0
        for path, text in script_files():
            rel = path.relative_to(ROOT).as_posix()
            uses += sum(1 for _ in find_uses(parse_body(text)))
            for name in unguarded_uses(text, rel.startswith("common/scripted_triggers/")):
                failures.append(f"{rel}: {name}")
        # Not vacuous: the banking contagion is a use today.
        self.assertGreaterEqual(uses, 1, f"no use of {TRIGGER} found; the scan is broken")
        self.assertEqual(failures, [], (
            f"{TRIGGER} without `is_country_alive = yes` before it in the same limit or "
            "trigger block. On a country with no states the trigger crashes the game "
            "(#1871): put `is_country_alive = yes` first in the limit."))

    def test_no_use_in_gui_files(self):
        # A .gui file cannot hold a trigger; a hit means the scan above misses one.
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            self.assertNotIn(TRIGGER, path.read_text(encoding="utf-8-sig"), path.name)


class ContagionGuards(unittest.TestCase):
    EFFECTS = "common/scripted_effects/banking_cycle_effects.txt"

    def test_target_guard_is_the_limits_first_line(self):
        spread = entity(self.EFFECTS, "banking_cycle_spread_contagion")
        guard = child(spread, "if")
        limit = child(child(child(guard, "custom_tooltip"), "every_country"), "limit")
        self.assertTrue(is_alive_guard(limit[0]), f"first line is {limit[0][:3:2]}")

    def test_origin_guard_wraps_the_spread(self):
        spread = entity(self.EFFECTS, "banking_cycle_spread_contagion")
        self.assertEqual([k for k, _, _ in spread], ["if"], "the spread's only line is its origin guard")
        limit = child(child(spread, "if"), "limit")
        origin = child(limit, "scope:banking_crash_origin_country")
        self.assertTrue(any(is_alive_guard(e) for e in origin))
        self.assertIn(("exists", "=", "market"), origin)

    def test_crash_roll_needs_a_live_origin(self):
        check = entity(self.EFFECTS, "banking_cycle_check_and_execute_crash")
        self.assertNotIn("random_list", [k for k, _, _ in check], "the roll sits behind the guard")

        def sets_crash(body):
            return any(
                (k == "set_variable" and ("name", "=", "crash") in v and ("value", "=", "1") in v)
                or sets_crash(v)
                for k, _, v in body if isinstance(v, list))

        rolls = [v for k, _, v in check if k == "if" and sets_crash(v)]
        self.assertEqual(len(rolls), 1, "one guarded block holds the roll that sets crash = 1")
        limit = child(rolls[0], "limit")
        self.assertTrue(any(is_alive_guard(e) for e in limit))
        self.assertIn(("exists", "=", "market"), limit)


if __name__ == "__main__":
    unittest.main()
