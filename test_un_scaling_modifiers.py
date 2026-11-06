# -*- coding: utf-8 -*-
"""The United Nations' scaling modifiers, declared on je_united_nations.

Since 1.15 the entry declares each modifier that follows a number, or a state a
variable records, in `scaling_modifiers_while_active`, and the engine re-reads
its value from the owning country about every four days (design:
docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.11). These
tests pin each declaration (once, an inline block, the exact value with its
"off" gate, which must read 0 wherever the old code removed the modifier), the
variables each value reads and every site that writes them, and that the
refresh and re-add code the declarations replaced is gone.
test_journal_entry_shape.py checks the tree-wide rule that nothing adds,
removes or tests a declared key.
"""

import os
import re
import unittest

from je_multiplier_scope_audit import parse_text

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


JE = _path("common", "journal_entries", "je_united_nations.txt")
UN_VALUES = _path("common", "script_values", "un_script_values.txt")
LADDER = _path("common", "scripted_effects", "un_ladder_effects.txt")
DEBUG = _path("common", "scripted_effects", "te_debug_un_effects.txt")
DUES_EFFECTS = _path("common", "scripted_effects", "un_dues_effects.txt")
DUES_TRIGGERS = _path("common", "scripted_triggers", "un_dues_triggers.txt")


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    """The file without comments."""
    return re.sub(r"#[^\n]*", "", _raw(path))


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _serialize(node):
    """A node as one line: ``key=value`` for a leaf, ``key{...}`` for a block."""
    if node.value is not None and not node.children:
        return f"{node.key}={node.value}"
    return node.key + "{" + " ".join(_serialize(c) for c in node.children) + "}"


def _entry():
    nodes, _ = parse_text(_raw(JE), "common/journal_entries/je_united_nations.txt")
    return next(n for n in nodes if n.key == "je_united_nations")


def _child(node, key):
    return next((c for c in node.children if c.key == key), None)


def _declarations():
    """modifier -> [the value node] for every scaling_modifiers_while_active block on the entry."""
    out = {}
    for block in (c for c in _entry().children if c.key == "scaling_modifiers_while_active"):
        out.setdefault(_child(block, "modifier").value, []).append(_child(block, "value"))
    return out


def _gated(limit, add):
    """``value = { value = 0 if = { limit = { <limit> } add = <add> } }``, serialized."""
    return "value{value=0 if{limit{" + limit + "} add=" + add + "}}"


# modifier -> its value block, serialized (_serialize). Every value is an inline
# block, as in all of vanilla's uses (08_tsarpoints.txt, 00_communism.txt).
EXPECTED = {
    # Membership benefits: from the Contested tier, to a member that draws them.
    "un_membership_benefits_modifier": _gated(
        "un_tier_at_least_contested=yes un_member_draws_benefits=yes", "un_membership_benefits_multiplier"),
    # Dues: this month's cache while the member pays its own.
    "un_dues_modifier": _gated("un_dues_in_force=yes", "var:un_dues_cached"),
}


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in sorted(files):
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


def _writes(variable, ops=("set_variable", "remove_variable", "change_variable")):
    """(file, top-level definition) of every write of ``variable`` in common/ and events/, by op."""
    out = {op: [] for op in ops}
    pattern = re.compile(r"\b(" + "|".join(ops) + r")\s*=\s*(?:\{\s*name\s*=\s*)?" + re.escape(variable) + r"\b")
    top = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)
    for path in _script_files():
        text = _read(path)
        if variable not in text:
            continue
        tops = [(m.start(), m.group(1)) for m in top.finditer(text)]
        for m in pattern.finditer(text):
            owner = max((t for t in tops if t[0] <= m.start()), default=(0, "?"))[1]
            out[m.group(1)].append((os.path.relpath(path, REPO), owner))
    return out


class DeclarationTests(unittest.TestCase):
    def test_the_entry_declares_exactly_these_once_each(self):
        declared = _declarations()
        self.assertEqual(set(declared), set(EXPECTED))
        for modifier, values in declared.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(len(values), 1)

    def test_each_value_is_its_block(self):
        declared = _declarations()
        for modifier, expected in EXPECTED.items():
            with self.subTest(modifier=modifier):
                value = declared[modifier][0]
                self.assertIsNone(value.value, "an inline value block, never a bare name")
                self.assertEqual(_serialize(value), expected)


class MembershipBenefitsTests(unittest.TestCase):
    def test_the_strength_reads_the_country_without_a_wrapper(self):
        body = _block(_read(UN_VALUES), "un_membership_benefits_multiplier")
        self.assertIn("has_global_variable = un_authority", body)
        self.assertIn("add = modifier:country_un_institutional_alignment", body)
        self.assertNotIn("owner", body)

    def test_the_old_wrapper_is_left_uncalled_for_old_saves(self):
        raw = _raw(UN_VALUES)
        at = raw.index("\nun_membership_benefits_multiplier_for_je = {")
        self.assertIn("PENDING REMOVAL", raw[raw.rindex("\n\n", 0, at):at])
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for f in files:
                    if f.endswith(".txt") and f != "un_script_values.txt":
                        with self.subTest(file=f):
                            self.assertNotIn("un_membership_benefits_multiplier_for_je",
                                             _read(os.path.join(dirpath, f)))


class DuesTests(unittest.TestCase):
    def test_in_force_is_the_old_gate(self):
        body = [line.strip() for line in _block(_read(DUES_TRIGGERS), "un_dues_in_force").splitlines()
                if line.strip()]
        self.assertEqual(body, ["has_variable = un_dues_cached", "un_dues_self_assessed = yes",
                                "NOT = { un_dues_is_withholding = yes }", "un_dues_assessed = yes"])

    def test_the_cache_is_set_by_the_refresh_and_the_resume_and_removed_by_one_helper(self):
        writes = _writes("un_dues_cached")
        self.assertEqual(sorted(set(owner for _, owner in writes["set_variable"])),
                         ["un_dues_country_monthly_update", "un_dues_resume"])
        self.assertEqual(writes["remove_variable"],
                         [("common/scripted_effects/un_dues_effects.txt", "un_dues_stop_paying")])
        self.assertEqual(writes["change_variable"], [])

    def test_every_way_out_stops_paying(self):
        effects = _read(DUES_EFFECTS)
        monthly = _block(effects, "un_dues_country_monthly_update")
        self.assertEqual(monthly.count("un_dues_stop_paying = yes"), 2, "withholding, and not assessed")
        for name in ("un_dues_withhold", "un_dues_clear"):
            with self.subTest(effect=name):
                self.assertIn("un_dues_stop_paying = yes", _block(effects, name))
        self.assertIn("un_dues_stop_paying = yes", _block(_read(LADDER), "un_membership_end_effect"))
        je = _read(JE)
        self.assertRegex(je, r"limit = \{ NOT = \{ un_dues_self_assessed = yes \} \}\s*un_dues_stop_paying = yes")


if __name__ == "__main__":
    unittest.main()
