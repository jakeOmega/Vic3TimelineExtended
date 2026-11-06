"""`add_journal_entry` of an entry with activation triggers skips a country holding its inactive copy (#1416).

Every country holds an inactive copy of every country entry that has its own activation triggers
(`is_shown_when_inactive`, `possible`), from the game's start, shown or not, and `add_journal_entry` is refused while
it does ("<Country> already has a journal entry of type X", `journal_entry_manager.cpp`). The entry comes in through
its triggers, at the engine's own check. So on such an entry an add is only a net for a country that holds no record
(a save from before the entry, an entry that concluded, a country the engine left out), and it must skip a country
holding a copy: `NOT = { has_inactive_journal_entry = X }` (or a `NOR` naming it) among the conjuncts of a `limit`
around the add, read through the named triggers that limit calls. A deliberate exception carries
`# REVIEWED YYYY-MM-DD (add_journal_entry): rationale` on the add's line; a tag on a line that is not such an add
fails. The rule: `docs/guides/scripting_best_practices.md`, the `has_journal_entry` bullet.

Mod entries come from `common/journal_entries/` (a plain or `REPLACE:` definition replaces vanilla's, an `INJECT:`
adds its fields), vanilla's from the committed `vanilla_parsed/` snapshot. A contextless entry (`context = none`) is
not a country's, and is left out.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import Node, parse_text

ROOT = Path(__file__).resolve().parent
JE_DIR = ROOT / "common" / "journal_entries"
VANILLA_JE = ROOT / "vanilla_parsed" / "common" / "journal_entries.json"
SCAN_DIRS = ("common", "events")

ACTIVATION_FIELDS = ("is_shown_when_inactive", "possible")
TAG = "add_journal_entry"
_TAG_RE = re.compile(r"REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(" + TAG + r"\)\s*:\s*\S")
# Blocks around an add that keep its scope: their limits (if, else_if) are the add's guards, and the climb goes on
# past them. Numeric keys are random_list weights.
_KEEPS_SCOPE = frozenset(("if", "else_if", "else", "hidden_effect", "custom_tooltip", "show_as_tooltip",
                          "random_list", "random"))
# An iterator's limit is a guard on the scope it enters; the climb stops there.
_ITERATOR_RE = re.compile(r"^(?:every|random|ordered)_\w+$")


def _parse(path: Path) -> tuple[list[Node], dict[int, str]]:
    return parse_text(path.read_text(encoding="utf-8-sig"), path.relative_to(ROOT).as_posix())


def _child(node: Node, key: str) -> Node | None:
    return next((c for c in node.children if c.key == key), None)


# --- Which entries have activation triggers ---------------------------------------------------------------------


def _vanilla_entries() -> dict[str, dict]:
    """Vanilla entry name -> its body's fields (the last definition when the snapshot holds several)."""
    data = json.loads(VANILLA_JE.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for name, raw in data.items():
        defs = raw if raw and isinstance(raw[0], list) else [raw]
        bodies = [d[1] for d in defs if len(d) == 2 and isinstance(d[1], dict)]
        if bodies:
            out[name] = bodies[-1]
    return out


def _value(raw) -> str | None:
    """A vanilla snapshot field's scalar value (`['=', 'none']`), if it has one."""
    if isinstance(raw, list) and len(raw) == 2 and isinstance(raw[1], str):
        return raw[1]
    return None


def entry_activation(mod_nodes: list[Node], vanilla: dict[str, dict]) -> dict[str, tuple[frozenset[str], str | None]]:
    """Entry name -> (its activation fields, its `context` value), merging mod definitions over vanilla's."""
    replaced: dict[str, Node] = {}
    injected: dict[str, list[Node]] = {}
    for node in mod_nodes:
        mode, _, name = node.key.rpartition(":")
        if mode == "INJECT":
            injected.setdefault(name, []).append(node)
        elif mode in ("", "REPLACE"):
            replaced[name] = node
    out: dict[str, tuple[frozenset[str], str | None]] = {}
    for name in set(vanilla) | set(replaced) | set(injected):
        if name in replaced:
            fields = {c.key for c in replaced[name].children}
            ctx_node = _child(replaced[name], "context")
            context = ctx_node.value if ctx_node else None
        elif name in vanilla:
            fields = set(vanilla[name])
            context = _value(vanilla[name].get("context"))
        else:
            fields, context = set(), None
        for node in injected.get(name, []):
            fields |= {c.key for c in node.children}
            ctx_node = _child(node, "context")
            if ctx_node is not None:
                context = ctx_node.value
        out[name] = (frozenset(fields) & frozenset(ACTIVATION_FIELDS), context)
    return out


def needs_guard(name: str, entries: dict[str, tuple[frozenset[str], str | None]]) -> bool:
    """Does every country hold an inactive copy of this entry? An unknown or parameterised type counts, so a new
    one is looked at."""
    if name not in entries:
        return True
    fields, context = entries[name]
    return bool(fields) and context in (None, "country")


def load_entries() -> dict[str, tuple[frozenset[str], str | None]]:
    mod_nodes = [n for path in sorted(JE_DIR.glob("*.txt")) for n in _parse(path)[0] if n.children]
    return entry_activation(mod_nodes, _vanilla_entries())


# --- Whether an add skips an inactive copy ---------------------------------------------------------------------


def load_triggers() -> dict[str, Node]:
    triggers: dict[str, Node] = {}
    for path in sorted((ROOT / "common" / "scripted_triggers").glob("*.txt")):
        triggers.update((n.key, n) for n in _parse(path)[0] if n.children)
    return triggers


def _names_inactive(node: Node, je: str) -> bool:
    return node.key == "has_inactive_journal_entry" and node.value == je and not node.children


def skips_inactive(conjuncts: list[Node], je: str, triggers: dict[str, Node], seen: tuple[str, ...] = ()) -> bool:
    """Is `NOT has_inactive_journal_entry = je` one of these conjuncts (through AND, and named triggers called with
    `= yes`)? `NOT = { a b }` is NOT(a AND b), so a NOT counts only with the test as its one child (or one OR naming
    it); a NOR counts with it as any child."""
    for node in conjuncts:
        if node.key == "AND" and skips_inactive(node.children, je, triggers, seen):
            return True
        if node.key == "NOT" and len(node.children) == 1:
            only = node.children[0]
            if _names_inactive(only, je) or (only.key == "OR" and any(_names_inactive(c, je) for c in only.children)):
                return True
        if node.key == "NOR" and any(_names_inactive(c, je) for c in node.children):
            return True
        if node.key in triggers and node.value == "yes" and node.key not in seen:
            if skips_inactive(triggers[node.key].children, je, triggers, seen + (node.key,)):
                return True
    return False


def guard_limits(ancestors: list[Node]) -> list[Node]:
    """The `limit`s that must hold for the add to run in its own scope, innermost first."""
    limits: list[Node] = []
    for anc in reversed(ancestors):
        if anc.key in ("if", "else_if") or _ITERATOR_RE.match(anc.key):
            limit = _child(anc, "limit")
            if limit is not None:
                limits.append(limit)
            if anc.key in ("if", "else_if"):
                continue
            break
        if anc.key in _KEEPS_SCOPE or anc.key.isdigit():
            continue
        break
    return limits


def find_adds(nodes: list[Node], ancestors: list[Node] | None = None):
    """(add node, its type, its ancestors outermost first) for every `add_journal_entry = { type = X }`."""
    ancestors = ancestors or []
    for node in nodes:
        if node.key == TAG and node.children:
            type_node = _child(node, "type")
            yield node, (type_node.value if type_node else None), ancestors
        if node.children:
            yield from find_adds(node.children, ancestors + [node])


def audit_text(text: str, rel: str, entries, triggers) -> tuple[list[tuple[str, int, str]], list[tuple[str, int]]]:
    """(unguarded adds as (file, line, type), stale tags as (file, line)) in one file."""
    nodes, comments = parse_text(text, rel)
    flags, flagged_lines, add_lines = [], set(), set()
    for add, je, ancestors in find_adds(nodes):
        add_lines.add(add.line)
        if not needs_guard(je or "?", entries):
            continue
        if je and any(skips_inactive(limit.children, je, triggers) for limit in guard_limits(ancestors)):
            continue
        flagged_lines.add(add.line)
        if not _TAG_RE.search(comments.get(add.line, "")):
            flags.append((rel, add.line, je or "?"))
    stale = [(rel, line) for line, comment in sorted(comments.items())
             if _TAG_RE.search(comment) and line not in flagged_lines]
    return flags, stale


def audit_repo() -> tuple[list[tuple[str, int, str]], list[tuple[str, int]], int]:
    entries, triggers = load_entries(), load_triggers()
    flags, stale, adds = [], [], 0
    for top in SCAN_DIRS:
        for path in sorted((ROOT / top).rglob("*.txt")):
            text = path.read_text(encoding="utf-8-sig")
            if TAG not in text:
                continue
            rel = path.relative_to(ROOT).as_posix()
            adds += sum(1 for _ in find_adds(parse_text(text, rel)[0]))
            f, s = audit_text(text, rel, entries, triggers)
            flags += f
            stale += s
    return flags, stale, adds


# --- Tests ----------------------------------------------------------------------------------------------------

_ENTRIES = {
    "je_triggered": (frozenset({"is_shown_when_inactive", "possible"}), None),
    "je_possible_only": (frozenset({"possible"}), None),
    "je_by_effect": (frozenset(), None),
    "je_contextless": (frozenset({"is_shown_when_inactive"}), "none"),
}
_TRIGGERS_TEXT = """
my_net_due = {
	has_variable = x
	NOT = { has_inactive_journal_entry = je_triggered }
}
my_other = {
	has_variable = y
}
"""


class FixtureTest(unittest.TestCase):
    def setUp(self):
        self.triggers = {n.key: n for n in parse_text(_TRIGGERS_TEXT, "t.txt")[0]}

    def run_one(self, body: str, je: str = "je_triggered"):
        text = "eff = {\n" + body.replace("JE", je) + "\n}\n"
        return audit_text(text, "e.txt", _ENTRIES, self.triggers)

    def assertFlagged(self, body, je="je_triggered"):
        flags, stale = self.run_one(body, je)
        self.assertEqual(len(flags), 1, body)
        self.assertEqual(stale, [])

    def assertClean(self, body, je="je_triggered"):
        self.assertEqual(self.run_one(body, je), ([], []), body)

    def test_a_bare_add_is_flagged(self):
        self.assertFlagged("add_journal_entry = { type = JE }")
        self.assertFlagged("add_journal_entry = { type = JE }", "je_possible_only")

    def test_an_active_only_guard_is_flagged(self):
        self.assertFlagged("if = { limit = { NOT = { has_journal_entry = JE } } add_journal_entry = { type = JE } }")

    def test_an_inactive_guard_passes(self):
        self.assertClean("if = { limit = { NOT = { has_journal_entry = JE } NOT = { has_inactive_journal_entry = JE } }"
                         " add_journal_entry = { type = JE } }")
        self.assertClean("if = { limit = { NOR = { has_journal_entry = JE has_inactive_journal_entry = JE } } "
                         "add_journal_entry = { type = JE } }")
        self.assertClean("if = { limit = { NOT = { OR = { has_journal_entry = JE has_inactive_journal_entry = JE } } }"
                         " add_journal_entry = { type = JE } }")
        # An outer if's limit guards the inner add, as does an iterator's.
        self.assertClean("if = { limit = { NOT = { has_inactive_journal_entry = JE } } "
                         "if = { limit = { always = yes } hidden_effect = { add_journal_entry = { type = JE } } } }")
        self.assertClean("every_country = { limit = { NOT = { has_inactive_journal_entry = JE } } "
                         "add_journal_entry = { type = JE } }")

    def test_a_guard_through_a_named_trigger_passes(self):
        self.assertClean("if = { limit = { my_net_due = yes } add_journal_entry = { type = JE } }")
        self.assertFlagged("if = { limit = { my_other = yes } add_journal_entry = { type = JE } }")
        self.assertFlagged("if = { limit = { my_net_due = no } add_journal_entry = { type = JE } }")

    def test_a_guard_that_does_not_skip_the_copy_is_flagged(self):
        # NOT(a AND b): a country with only the inactive copy passes it.
        self.assertFlagged("if = { limit = { NOT = { has_journal_entry = JE has_inactive_journal_entry = JE } } "
                           "add_journal_entry = { type = JE } }")
        # Inside an OR, it does not have to hold.
        self.assertFlagged("if = { limit = { OR = { always = yes NOT = { has_inactive_journal_entry = JE } } } "
                           "add_journal_entry = { type = JE } }")
        # The if before an else_if is not its guard; nor is a guard on another entry, or past a scope change.
        self.assertFlagged("if = { limit = { NOT = { has_inactive_journal_entry = JE } } } "
                           "else_if = { limit = { always = yes } add_journal_entry = { type = JE } }")
        self.assertFlagged("if = { limit = { NOT = { has_inactive_journal_entry = je_other } } "
                           "add_journal_entry = { type = JE } }")
        self.assertFlagged("if = { limit = { NOT = { has_inactive_journal_entry = JE } } "
                           "capital = { owner = { add_journal_entry = { type = JE } } } }")

    def test_entries_without_triggers_or_context_are_left_alone(self):
        self.assertClean("add_journal_entry = { type = JE }", "je_by_effect")
        self.assertClean("add_journal_entry = { type = JE }", "je_contextless")

    def test_an_unknown_type_is_looked_at(self):
        self.assertFlagged("add_journal_entry = { type = JE }", "je_from_nowhere")
        self.assertFlagged("add_journal_entry = { type = je_$KIND$ }")

    def test_the_tag_suppresses_and_goes_stale(self):
        tag = "# REVIEWED 2026-11-06 (add_journal_entry): the re-entry after the entry concluded"
        self.assertEqual(self.run_one(f"add_journal_entry = {{ type = JE }} {tag}"), ([], []))
        # A tag on a guarded add, or on no add, is stale.
        _, stale = self.run_one("if = { limit = { NOT = { has_inactive_journal_entry = JE } } }\n"
                                f"add_journal_entry = {{ type = je_by_effect }} {tag}")
        self.assertEqual(len(stale), 1)
        # Another audit's tag is not this one's.
        flags, _ = self.run_one("add_journal_entry = { type = JE } # REVIEWED 2026-11-06: something else")
        self.assertEqual(len(flags), 1)


class MergeTest(unittest.TestCase):
    def test_mod_definitions_merge_over_vanilla(self):
        vanilla = {"je_v": {"possible": ["=", {}]}, "je_w": {"icon": ["=", "x"]},
                   "je_c": {"possible": ["=", {}], "context": ["=", "none"]}}
        mod = parse_text("REPLACE:je_v = { icon = x }\nINJECT:je_w = { possible = { always = yes } }\n"
                         "je_m = { is_shown_when_inactive = { always = yes } }\n", "m.txt")[0]
        entries = entry_activation(mod, vanilla)
        self.assertFalse(needs_guard("je_v", entries))  # the replacement dropped `possible`
        self.assertTrue(needs_guard("je_w", entries))  # the inject added it
        self.assertTrue(needs_guard("je_m", entries))
        self.assertFalse(needs_guard("je_c", entries))  # contextless


class RepoTest(unittest.TestCase):
    def test_entries_load(self):
        entries = load_entries()
        for name in ("je_banking_cycle", "je_colonial_empire", "je_grand_monuments", "je_nuclear_program",
                     "je_space_race_solar_colonization", "je_united_nations", "je_tax_code"):
            self.assertTrue(needs_guard(name, entries), name)
        # Vanilla's adds-by-effect, from the snapshot.
        for name in ("je_portugal_regeneration_public_works", "je_king_in_parliament"):
            self.assertIn(name, entries)
            self.assertFalse(needs_guard(name, entries), name)

    def test_every_add_skips_an_inactive_copy(self):
        flags, stale, adds = audit_repo()
        self.assertGreaterEqual(adds, 12)  # the scan found the mod's adds
        self.assertEqual(flags, [], "add_journal_entry over an inactive copy is refused with an error; guard it with "
                                    "NOT = { has_inactive_journal_entry = X } or tag it "
                                    "# REVIEWED YYYY-MM-DD (add_journal_entry): rationale")
        self.assertEqual(stale, [], "a (add_journal_entry) tag on a line with no unguarded add")


if __name__ == "__main__":
    unittest.main()
