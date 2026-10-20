# Event Magnitude Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an audit + scaled-effect library so mod events stop using hardcoded values that go invisible at late-game scale; convert the existing 8 prestige events to validate the workflow end-to-end.

**Architecture:** New `event_magnitude_audit.py` module (registry + regex-based event scanner + suppression parser) wired into `mod_state_server.py` as a new endpoint and a post-load report writer. Companion library of tiered script values + `_mult`-based static modifiers in the existing mod data files. Inline `# REVIEWED YYYY-MM-DD: <rationale>` comments serve as exemptions.

**Tech Stack:** Python 3 + unittest (existing convention at repo root), Paradox script (`.txt`), `mod_state_server.py` (HTTP service).

**Source spec:** `/home/jakef/.claude/plans/i-just-got-the-purring-micali.md`

---

## File Structure

- New: `event_magnitude_audit.py` (~250 lines: registry, regex scanner, suppression parser, report writer)
- New: `test_event_magnitude_audit.py` (unittest at repo root, follows `test_event_balance.py` style)
- Modify: `mod_state_server.py` (add endpoint, wire into `_run_post_load_generators`)
- Modify: `common/script_values/extra_script_values.txt` (append tiered scaler script values)
- Modify: `common/static_modifiers/extra_modifiers.txt` (append `_mult`-based generic prestige/bureaucracy modifiers)
- Modify: 8 events in `events/*.txt` (located via first audit run; convert each prestige hit)
- New (auto-generated): `docs/engine/event_magnitude_report.md`
- Modify: `docs/audits/open_issues.md` (append trading-principle inflation + deferred categories)
- Modify: `docs/guides/scripting_best_practices.md` (new subsection)
- Modify: `CLAUDE.md` (one-line pointer)

---

### Task 1: Verify registry assumptions against engine docs

This is a verification step before writing any code. Confirms that the modifier-type names in the spec actually exist in the engine, and that the script-value sources work.

**Files:** none (verification only)

- [ ] **Step 1: Verify mod_state_server is running**

```bash
curl -s http://localhost:8950/status | head -5
```
Expected: status 200 with snapshot timestamps. If not running, start with `.venv/bin/python mod_state_server.py` (~60-110s startup).

- [ ] **Step 2: Verify each modifier type exists**

```bash
for m in country_prestige_add country_bureaucracy_add country_construction_add country_expenses_add country_government_dividends_add country_minting_add country_prestige_mult country_bureaucracy_mult; do
  echo -n "$m: "
  curl -s "http://localhost:8950/engine-docs/modifiers/$m" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name','MISSING'), '|', d.get('origin','?'))" 2>/dev/null || echo "MISSING"
done
```
Expected: every name except potentially `country_minting_add` resolves with `origin = vanilla`. Drop any that come back MISSING from the registry.

- [ ] **Step 3: Verify script-value sources for scalers**

```bash
curl -s "http://localhost:8950/search?q=country_prestige" | head -40
```
Look for `country_prestige` appearing as a script-value source (vanilla scripted_values typically reference it directly as `value = country_prestige`). If the search returns vanilla-side script values that use this pattern, we're good. If not, the scaler will need a `var:` cache populated on monthly pulse — note this in the script-value file's comment.

- [ ] **Step 4: Findings (recorded 2026-05-04)**

- `country_prestige_add` ✓ FOUND vanilla; `country_prestige_mult` ✓; `value = prestige` ✓ (mod & vanilla precedent).
- `country_bureaucracy_add` ✓; `country_bureaucracy_mult` ✓ (use mult path, no script value needed).
- `add_treasury` ✓ effect; `value = gold_reserves` ✓ (vanilla uses it as treasury proxy).
- `country_construction_add` ✓ exists, but NO mult counterpart and bare-name `construction` token unverified — DROP from v1 registry.
- `country_expenses_add` ✓ exists, NO mult counterpart, no script-value source verified — DROP from v1.
- `country_minting_add` ✓ exists, has `country_minting_mult` ✓ but value→percent conversion ≠ 1:1 — DROP from v1, revisit later.
- `country_government_dividends_add` ✗ MISSING — doesn't exist; treasury flows from dividends are routed through `country_government_dividends_efficiency_add` (a percent modifier already, no scaling needed).

**v1 registry reduced to:** `country_prestige_add`, `country_bureaucracy_add`, `add_treasury`. The architecture is one-line-extensible so the dropped four come back once script-value sources or correct fix paths are confirmed.

---

### Task 2: Create audit module skeleton with registry

**Files:**
- Create: `event_magnitude_audit.py`
- Create: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write the first failing test (registry lookup)**

```python
# test_event_magnitude_audit.py
"""Unit tests for event_magnitude_audit. Run: python3 test_event_magnitude_audit.py"""
import unittest

from event_magnitude_audit import (
    FAST_SCALING_MODIFIERS,
    DIRECT_EFFECTS,
    ResourceMeta,
)


class RegistryTests(unittest.TestCase):
    def test_registry_has_prestige(self):
        self.assertIn("country_prestige_add", FAST_SCALING_MODIFIERS)
        meta = FAST_SCALING_MODIFIERS["country_prestige_add"]
        self.assertEqual(meta.resource, "prestige")

    def test_registry_has_add_treasury_direct(self):
        self.assertIn("add_treasury", DIRECT_EFFECTS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /home/jakef/src/Vic3TimelineExtended && python3 test_event_magnitude_audit.py
```
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Implement the registry**

```python
# event_magnitude_audit.py
"""Detects hardcoded delta values in events for fast-scaling resources.

Adding a new fast-scaling resource: one line in FAST_SCALING_MODIFIERS or
DIRECT_EFFECTS. Suppress a flagged value by adding a same-line comment:

    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated; intentionally large
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceMeta:
    resource: str         # display name: "prestige", "treasury (instant)", etc.
    fix_hint: str         # short suggestion for the report's fix column


# Modifier-type keys checked inside static modifiers referenced via
# add_modifier { name = X multiplier = N }, AND inline modifier-type keys
# inside add_modifier { country_prestige_add = N } blocks.
FAST_SCALING_MODIFIERS: dict[str, ResourceMeta] = {
    "country_prestige_add": ResourceMeta(
        resource="prestige",
        fix_hint="use prestige_loss_<tier>/prestige_gain_<tier> static modifier (mult-based) or multiplier=sv_prestige_event_<tier>",
    ),
    "country_bureaucracy_add": ResourceMeta(
        resource="bureaucracy",
        fix_hint="use bureaucracy_loss_<tier>/bureaucracy_gain_<tier> static modifier (mult-based) or multiplier=sv_bureaucracy_event_<tier>",
    ),
    "country_construction_add": ResourceMeta(
        resource="construction",
        fix_hint="use multiplier=sv_construction_event_<tier>",
    ),
    "country_expenses_add": ResourceMeta(
        resource="treasury (weekly flow)",
        fix_hint="use multiplier=sv_treasury_flow_event_<tier>",
    ),
    "country_government_dividends_add": ResourceMeta(
        resource="treasury (weekly flow)",
        fix_hint="use multiplier=sv_treasury_flow_event_<tier>",
    ),
    "country_minting_add": ResourceMeta(
        resource="treasury (weekly flow)",
        fix_hint="use multiplier=sv_treasury_flow_event_<tier>",
    ),
}

# Direct effects (not modifier types). Keys are effect names that take a
# numeric value as their right-hand side.
DIRECT_EFFECTS: dict[str, ResourceMeta] = {
    "add_treasury": ResourceMeta(
        resource="treasury (instant)",
        fix_hint="use add_treasury = sv_treasury_event_<tier>",
    ),
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd /home/jakef/src/Vic3TimelineExtended && python3 test_event_magnitude_audit.py
```
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: scaffold registry of fast-scaling modifier types

Adds the resource registry that the audit walker will consult. Inline
form, tiered-script-value form, and direct-effect form all share the
same FAST_SCALING_MODIFIERS / DIRECT_EFFECTS lookup.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Implement enclosing-event-id resolution

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing tests**

Add to `test_event_magnitude_audit.py`:

```python
from event_magnitude_audit import find_event_id_at_line


class EventIdResolutionTests(unittest.TestCase):
    def test_simple(self):
        text = (
            "namespace = test_events\n"
            "\n"
            "test_events.1 = {\n"
            "  type = country_event\n"
            "  immediate = {\n"
            "    add_treasury = -100\n"  # line 6
            "  }\n"
            "}\n"
        )
        self.assertEqual(find_event_id_at_line(text, line_no=6), "test_events.1")

    def test_multiple_events_in_file(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = -100 }\n"
            "}\n"
            "test_events.2 = {\n"
            "  immediate = { add_treasury = -200 }\n"  # line 5
            "}\n"
        )
        self.assertEqual(find_event_id_at_line(text, line_no=5), "test_events.2")

    def test_inject_replace_prefixes(self):
        text = (
            "REPLACE:foo.5 = {\n"
            "  immediate = { add_treasury = -1 }\n"  # line 2
            "}\n"
            "INJECT:bar.7 = {\n"
            "  immediate = { add_treasury = -2 }\n"  # line 5
            "}\n"
        )
        self.assertEqual(find_event_id_at_line(text, line_no=2), "foo.5")
        self.assertEqual(find_event_id_at_line(text, line_no=5), "bar.7")

    def test_no_event_returns_none(self):
        text = "namespace = test_events\n# just a comment\n"
        self.assertIsNone(find_event_id_at_line(text, line_no=2))
```

- [ ] **Step 2: Run tests to verify they fail**

Expected: `ImportError: cannot import name 'find_event_id_at_line'`

- [ ] **Step 3: Implement the resolver**

Add to `event_magnitude_audit.py`:

```python
import re

# Matches event header lines like:
#   foo_events.123 = {
#   REPLACE:foo_events.123 = {
#   INJECT:foo_events.123 = {
# Captures the bare event id (without the REPLACE:/INJECT: prefix).
_EVENT_HEADER_RE = re.compile(
    r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_]\w*\.\w+)\s*=\s*\{"
)


def find_event_id_at_line(text: str, line_no: int) -> str | None:
    """Walk upward from `line_no` (1-indexed) to find the most recent event
    header. Returns the event id, or None if no header is above the line.

    Bare-bones implementation: doesn't track brace depth, so a value inside
    a deeply-nested `event { }` block in a non-event file would resolve to
    the most recent event-shaped header. For events/*.txt that's correct.
    """
    lines = text.splitlines()
    if not (1 <= line_no <= len(lines)):
        return None
    for i in range(line_no - 1, -1, -1):
        m = _EVENT_HEADER_RE.match(lines[i].lstrip())
        if m:
            return m.group(1)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 test_event_magnitude_audit.py
```
Expected: all tests pass (registry tests + 4 new resolver tests).

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: enclosing-event-id resolver

Awk-style upward scan of event-file text to attribute a flagged line to
the event it belongs to. Handles REPLACE: and INJECT: prefixes used by
the mod's vanilla-extension pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Implement suppression-comment parser

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing tests**

```python
from event_magnitude_audit import parse_reviewed_comment


class SuppressionCommentTests(unittest.TestCase):
    def test_full_form(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated; intentionally large"
        result = parse_reviewed_comment(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-04")
        self.assertEqual(result["rationale"], "tech-gated; intentionally large")

    def test_missing_date_rejected(self):
        line = "    multiplier = 2000  # REVIEWED: no date here"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_missing_rationale_rejected(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_no_comment_at_all(self):
        line = "    multiplier = 2000"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_unrelated_comment(self):
        line = "    multiplier = 2000  # just a regular comment"
        self.assertIsNone(parse_reviewed_comment(line))
```

- [ ] **Step 2: Run tests, expect ImportError**

```bash
python3 test_event_magnitude_audit.py
```

- [ ] **Step 3: Implement the parser**

Add to `event_magnitude_audit.py`:

```python
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)


def parse_reviewed_comment(line: str) -> dict | None:
    """Look for `# REVIEWED YYYY-MM-DD: rationale` on the given line.
    Returns {date, rationale} or None.
    """
    m = _REVIEWED_RE.search(line)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}
```

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: inline REVIEWED comment parser

Suppression mechanism for the audit. Format requires both a YYYY-MM-DD
date and a rationale to discourage drive-by exemptions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Implement direct-effect scanner (`add_treasury = N`)

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing tests**

```python
from event_magnitude_audit import scan_direct_effects, AuditFlag


class DirectEffectScannerTests(unittest.TestCase):
    def test_flags_literal(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="events/foo.txt")
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.event_id, "test_events.1")
        self.assertEqual(f.effect, "add_treasury")
        self.assertEqual(f.value, "-10000")
        self.assertEqual(f.resource, "treasury (instant)")
        self.assertIsNone(f.exemption)

    def test_skips_script_value(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = sv_treasury_event_small }\n"
            "}\n"
        )
        self.assertEqual(scan_direct_effects(text, file_path="x.txt"), [])

    def test_reviewed_becomes_exemption(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000  # REVIEWED 2026-05-04: vanilla precedent\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["rationale"], "vanilla precedent")
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement**

Add to `event_magnitude_audit.py`:

```python
@dataclass
class AuditFlag:
    file: str
    line: int
    event_id: str | None
    kind: str          # "direct_effect" | "modifier_named" | "modifier_inline"
    effect: str        # the matched key, e.g. "add_treasury" or "country_prestige_add"
    value: str         # the literal matched (for reporting)
    resource: str      # display name from ResourceMeta
    fix_hint: str      # display hint from ResourceMeta
    exemption: dict | None = None  # {date, rationale} when REVIEWED


def _is_literal_number(token: str) -> bool:
    """True for things like `100`, `-20`, `0.5`, `-3.14`."""
    try:
        float(token)
        return True
    except ValueError:
        return False


def scan_direct_effects(text: str, file_path: str) -> list[AuditFlag]:
    """Find `<direct_effect> = <literal>` lines for effects in DIRECT_EFFECTS."""
    lines = text.splitlines()
    flags = []
    for i, line in enumerate(lines, start=1):
        for effect, meta in DIRECT_EFFECTS.items():
            # Match: optional indent, effect = value [comment]
            # Value is the first whitespace-delimited token after `=`.
            m = re.match(
                rf"^\s*{re.escape(effect)}\s*=\s*(\S+)",
                line,
            )
            if not m:
                continue
            value = m.group(1).rstrip("}").rstrip()
            if not _is_literal_number(value):
                continue
            exemption = parse_reviewed_comment(line)
            flags.append(AuditFlag(
                file=file_path,
                line=i,
                event_id=find_event_id_at_line(text, i),
                kind="direct_effect",
                effect=effect,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=exemption,
            ))
    return flags
```

- [ ] **Step 4: Run tests, expect pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: scan direct effects (add_treasury)

First scanner. Catches the `add_treasury = <literal>` form. Identifier
RHS values (script values) are skipped via _is_literal_number.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Implement inline modifier-type scanner (`country_prestige_add = N`)

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing tests**

```python
from event_magnitude_audit import scan_inline_modifier_types


class InlineModifierScannerTests(unittest.TestCase):
    def test_flags_inline_prestige(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      country_prestige_add = 100\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_inline_modifier_types(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")
        self.assertEqual(flags[0].value, "100")

    def test_skips_mult_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_prestige_mult = 0.05 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])

    def test_skips_unrelated_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_authority_add = 100 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement**

Add to `event_magnitude_audit.py`:

```python
def scan_inline_modifier_types(text: str, file_path: str) -> list[AuditFlag]:
    """Find `<fast-scaling-modifier-type> = <literal>` lines anywhere in the
    file. The naive approach catches both inline `add_modifier { K = V }` form
    AND any same-key occurrences in static-modifier *definitions* in non-event
    files — but this scanner is only called on events/*.txt where definitions
    don't live, so collisions are not a concern.
    """
    lines = text.splitlines()
    flags = []
    for i, line in enumerate(lines, start=1):
        for key, meta in FAST_SCALING_MODIFIERS.items():
            m = re.match(
                rf"^\s*{re.escape(key)}\s*=\s*(\S+)",
                line,
            )
            if not m:
                continue
            value = m.group(1).rstrip("}").rstrip()
            if not _is_literal_number(value):
                continue
            exemption = parse_reviewed_comment(line)
            flags.append(AuditFlag(
                file=file_path,
                line=i,
                event_id=find_event_id_at_line(text, i),
                kind="modifier_inline",
                effect=key,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=exemption,
            ))
    return flags
```

- [ ] **Step 4: Run tests, expect pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: scan inline modifier-type form

Catches `add_modifier { country_prestige_add = N }` syntax (no static
modifier name). The scanner uses the same registry lookup so adding a
new fast-scaling modifier type covers all three forms uniformly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Implement named-static-modifier scanner (the big one — multi-line)

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

This catches `add_modifier = { name = X multiplier = N }` where X is a static modifier defined elsewhere whose body contains a fast-scaling field. Requires a `ModState`-like lookup of the static modifier's body to know which fields it has.

- [ ] **Step 1: Write failing tests using a fake static-modifier lookup**

```python
from event_magnitude_audit import scan_named_modifiers


def _fake_static_modifier_lookup(name: str) -> dict | None:
    """Return {field_name: value, ...} for the given static modifier."""
    return {
        "prestige_loss_X": {"country_prestige_add": "1"},
        "boring_modifier": {"country_authority_add": "10"},
        "mult_modifier": {"country_prestige_mult": "-0.05"},
    }.get(name)


class NamedModifierScannerTests(unittest.TestCase):
    def test_flags_prestige_via_named_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      name = prestige_loss_X\n"
            "      multiplier = -20\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")
        self.assertEqual(flags[0].value, "-20")
        # line should point at the multiplier line (the actionable value)
        self.assertEqual(flags[0].line, 5)

    def test_skips_mult_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = mult_modifier multiplier = -0.1 }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup), [])

    def test_skips_when_multiplier_is_script_value(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      name = prestige_loss_X\n"
            "      multiplier = sv_prestige_event_small\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup), [])

    def test_skips_unknown_static_modifier(self):
        # If the static modifier isn't in the lookup, we can't know if it's
        # fast-scaling — skip rather than false-flag.
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = unknown_modifier multiplier = -20 }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup), [])

    def test_skips_named_modifier_without_multiplier(self):
        # `add_modifier { name = X }` with no multiplier means default 1 —
        # no literal to scale, nothing to flag.
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = prestige_loss_X }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup), [])
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement**

Add to `event_magnitude_audit.py`:

```python
from typing import Callable

# Multi-line block matcher. Captures everything between `add_modifier = {`
# and the matching `}` — using a non-greedy match. Won't handle nested {},
# but `add_modifier` blocks in practice never contain nested braces.
_ADD_MODIFIER_BLOCK_RE = re.compile(
    r"add_modifier\s*=\s*\{(?P<body>[^{}]*?)\}",
    re.DOTALL,
)
_NAME_RE = re.compile(r"^\s*name\s*=\s*(?P<name>\S+)", re.MULTILINE)
_MULTIPLIER_RE = re.compile(r"^\s*multiplier\s*=\s*(?P<value>\S+)", re.MULTILINE)


def scan_named_modifiers(
    text: str,
    file_path: str,
    lookup: Callable[[str], dict | None],
) -> list[AuditFlag]:
    """Find `add_modifier = { name = X multiplier = N }` blocks where X
    contains a fast-scaling field and N is a literal."""
    flags: list[AuditFlag] = []
    lines = text.splitlines()
    line_starts = _build_line_index(text)

    for block_match in _ADD_MODIFIER_BLOCK_RE.finditer(text):
        body = block_match.group("body")
        name_m = _NAME_RE.search(body)
        mult_m = _MULTIPLIER_RE.search(body)
        if not name_m or not mult_m:
            continue
        name = name_m.group("name").rstrip(",")
        value = mult_m.group("value").rstrip(",")
        if not _is_literal_number(value):
            continue
        modifier_body = lookup(name)
        if not modifier_body:
            continue

        # Determine which line the `multiplier =` appears on
        mult_offset = block_match.start() + mult_m.start()
        mult_line = _offset_to_line(line_starts, mult_offset)
        line_text = lines[mult_line - 1] if 0 < mult_line <= len(lines) else ""
        exemption = parse_reviewed_comment(line_text)

        # Emit a flag for every fast-scaling field the static modifier carries
        for field in modifier_body.keys():
            meta = FAST_SCALING_MODIFIERS.get(field)
            if not meta:
                continue
            flags.append(AuditFlag(
                file=file_path,
                line=mult_line,
                event_id=find_event_id_at_line(text, mult_line),
                kind="modifier_named",
                effect=field,
                value=value,
                resource=meta.resource,
                fix_hint=meta.fix_hint,
                exemption=exemption,
            ))
    return flags


def _build_line_index(text: str) -> list[int]:
    """Return list of byte offsets where each line starts (1-indexed)."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _offset_to_line(starts: list[int], offset: int) -> int:
    # Binary search would be faster but linear is fine for event-file sizes
    line = 0
    for i, start in enumerate(starts):
        if start > offset:
            break
        line = i + 1
    return line
```

- [ ] **Step 4: Run tests, expect pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: scan named-static-modifier form

The dominant form in mod events: add_modifier { name=X multiplier=N }.
Looks up X's body via injected callable so tests can stub without a
ModState, and the production caller wires it to ms.get_data.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Implement top-level `audit()` entrypoint

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing test**

```python
from event_magnitude_audit import audit, AuditResult


class _StubModState:
    """Minimal ModState fake for audit()."""
    def __init__(self, static_modifiers: dict, mod_path: str):
        self._sm = static_modifiers
        self.mod_path = mod_path

    def get_data(self, key):
        if key == "StaticModifiers":
            return self._sm
        return {}


class AuditEntrypointTests(unittest.TestCase):
    def test_end_to_end_on_tempdir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "events"))
            event_file = os.path.join(tmp, "events", "test_events.txt")
            with open(event_file, "w") as f:
                f.write(
                    "test_events.1 = {\n"
                    "  immediate = {\n"
                    "    add_modifier = { name = prestige_loss_X multiplier = -20 }\n"
                    "    add_treasury = -10000\n"
                    "    add_treasury = -50000  # REVIEWED 2026-05-04: era-tagged\n"
                    "  }\n"
                    "}\n"
                )
            ms = _StubModState(
                static_modifiers={
                    "prestige_loss_X": _eq({"country_prestige_add": _eq("1")}),
                },
                mod_path=tmp,
            )
            result = audit(ms)
            unrev = [f for f in result.flags if not f.exemption]
            exemp = [f for f in result.flags if f.exemption]
            # 1 named-modifier flag (prestige) + 1 unreviewed direct effect
            self.assertEqual(len(unrev), 2)
            # 1 reviewed direct effect
            self.assertEqual(len(exemp), 1)
            self.assertEqual(result.coverage["files_audited"], 1)
```

(`_eq` helper is already imported from where? Add it inline:)

```python
def _eq(value):
    return ("=", value)
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement**

Add to `event_magnitude_audit.py`:

```python
import os


@dataclass
class AuditResult:
    flags: list[AuditFlag]
    coverage: dict


def _make_static_modifier_lookup(ms) -> Callable[[str], dict | None]:
    """Build a name→{field: value} lookup from ModState's parsed StaticModifiers.
    The parser stores each modifier as ('=', {field: ('=', value), ...}).
    """
    raw = ms.get_data("StaticModifiers") or {}

    def lookup(name: str) -> dict | None:
        entry = raw.get(name)
        if not entry:
            return None
        # Unwrap ('=', body)
        body = entry[1] if isinstance(entry, tuple) and len(entry) == 2 else entry
        if not isinstance(body, dict):
            return None
        # Unwrap each field's ('=', value)
        return {
            k: (v[1] if isinstance(v, tuple) and len(v) == 2 else v)
            for k, v in body.items()
        }

    return lookup


def audit(ms) -> AuditResult:
    """Walk every events/*.txt file, return all magnitude flags."""
    lookup = _make_static_modifier_lookup(ms)
    events_dir = os.path.join(ms.mod_path, "events")
    flags: list[AuditFlag] = []
    files_audited = 0
    if not os.path.isdir(events_dir):
        return AuditResult(flags=[], coverage={"files_audited": 0})
    for fname in sorted(os.listdir(events_dir)):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(events_dir, fname)
        with open(fpath, encoding="utf-8-sig") as f:
            text = f.read()
        rel = os.path.join("events", fname)
        flags.extend(scan_direct_effects(text, file_path=rel))
        flags.extend(scan_inline_modifier_types(text, file_path=rel))
        flags.extend(scan_named_modifiers(text, file_path=rel, lookup=lookup))
        files_audited += 1
    return AuditResult(flags=flags, coverage={"files_audited": files_audited})
```

- [ ] **Step 4: Run tests, expect pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: audit() entrypoint

Walks events/*.txt and concatenates the three scanner outputs. Builds
the static-modifier lookup from ModState's parsed dict, unwrapping the
parser's ('=', value) tuple form.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Implement markdown report writer

**Files:**
- Modify: `event_magnitude_audit.py`
- Modify: `test_event_magnitude_audit.py`

- [ ] **Step 1: Write failing test**

```python
from event_magnitude_audit import render_report


class ReportRenderTests(unittest.TestCase):
    def test_basic_render(self):
        flags = [
            AuditFlag(file="events/foo.txt", line=10, event_id="foo.1",
                      kind="direct_effect", effect="add_treasury", value="-10000",
                      resource="treasury (instant)", fix_hint="use add_treasury = sv_treasury_event_<tier>"),
            AuditFlag(file="events/bar.txt", line=42, event_id="bar.7",
                      kind="modifier_named", effect="country_prestige_add", value="-20",
                      resource="prestige", fix_hint="use prestige_loss_<tier>",
                      exemption={"date": "2026-05-04", "rationale": "tech-gated"}),
        ]
        result = AuditResult(flags=flags, coverage={"files_audited": 2})
        md = render_report(result)
        self.assertIn("## Unreviewed Flags", md)
        self.assertIn("foo.1", md)
        self.assertIn("treasury (instant)", md)
        self.assertIn("## Reviewed Exemptions", md)
        self.assertIn("bar.7", md)
        self.assertIn("tech-gated", md)
        self.assertIn("## Coverage", md)
        self.assertIn("files_audited: 2", md)
```

- [ ] **Step 2: Run, expect ImportError**

- [ ] **Step 3: Implement**

```python
def render_report(result: AuditResult) -> str:
    """Render a markdown report. Top section is the actionable inbox."""
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = ["# Event magnitude audit report",
           "",
           "Auto-generated by `event_magnitude_audit.py` on every full",
           "`POST /reload` of the mod state server. Do not hand-edit.",
           "",
           "Suppress a flag by adding a same-line comment in the format:",
           "`# REVIEWED YYYY-MM-DD: rationale`",
           ""]

    out.append("## Unreviewed Flags")
    out.append("")
    if not unrev:
        out.append("_None._")
    else:
        # Group by resource
        by_resource: dict[str, list[AuditFlag]] = {}
        for f in unrev:
            by_resource.setdefault(f.resource, []).append(f)
        for resource in sorted(by_resource):
            out.append(f"### {resource} ({len(by_resource[resource])})")
            out.append("")
            for f in by_resource[resource]:
                out.append(
                    f"- `{f.file}:{f.line}` — event `{f.event_id or '?'}` — "
                    f"`{f.effect} = {f.value}` — fix: {f.fix_hint}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `{f.event_id or '?'}` — "
                f"`{f.effect} = {f.value}` — {f['exemption']['date']}: "
                f"{f['exemption']['rationale']}"
            )
    out.append("")

    out.append("## Coverage")
    out.append("")
    for k, v in result.coverage.items():
        out.append(f"- {k}: {v}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")

    return "\n".join(out) + "\n"
```

Note: there's a bug in the exemption rendering — `f['exemption']` should be `f.exemption`. Fix in implementation:

```python
            for f in exemp:
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.event_id or '?'}` — "
                    f"`{f.effect} = {f.value}` — {f.exemption['date']}: "
                    f"{f.exemption['rationale']}"
                )
```

- [ ] **Step 4: Run tests, expect pass**

- [ ] **Step 5: Commit**

```bash
git add event_magnitude_audit.py test_event_magnitude_audit.py
git commit -m "$(cat <<'EOF'
event_magnitude_audit: markdown report renderer

Two-section report: actionable Unreviewed Flags grouped by resource,
followed by compact Reviewed Exemptions. Same shape as the existing
engine_coverage_report.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 10: Wire audit into mod_state_server.py

**Files:**
- Modify: `mod_state_server.py`

- [ ] **Step 1: Add the endpoint and the post-load hook**

Find the section in `mod_state_server.py` where existing audit endpoints are registered (search for `/validate/engine-coverage` to locate the surrounding code). Add a new endpoint handler:

```python
# Near top of file, with other audit-module imports
import event_magnitude_audit


# In the request-routing section, near /validate/engine-coverage:
def _event_magnitude_audit_handler(self, parsed_query: dict):
    """GET /event-magnitude-audit — see event_magnitude_audit.py for details."""
    result = event_magnitude_audit.audit(ms)
    flags = result.flags
    show_reviewed = parsed_query.get("show_reviewed", ["false"])[0].lower() in ("true", "1", "yes")
    resource_filter = parsed_query.get("resource", [None])[0]
    event_filter = parsed_query.get("event_id", [None])[0]
    if not show_reviewed:
        flags = [f for f in flags if not f.exemption]
    if resource_filter:
        flags = [f for f in flags if resource_filter in f.resource]
    if event_filter:
        flags = [f for f in flags if f.event_id == event_filter]
    fmt = parsed_query.get("format", ["json"])[0]
    if fmt == "text":
        body = event_magnitude_audit.render_report(
            event_magnitude_audit.AuditResult(flags=flags, coverage=result.coverage)
        )
        return body, "text/markdown"
    payload = {
        "flags": [
            {
                "file": f.file, "line": f.line, "event_id": f.event_id,
                "kind": f.kind, "effect": f.effect, "value": f.value,
                "resource": f.resource, "fix_hint": f.fix_hint,
                "exemption": f.exemption,
            }
            for f in flags
        ],
        "coverage": result.coverage,
    }
    return json.dumps(payload, indent=2), "application/json"
```

(Adapt the routing pattern to whatever style `mod_state_server.py` uses — match the existing handlers' shape.)

- [ ] **Step 2: Hook into _run_post_load_generators**

Find `_run_post_load_generators` (or equivalent) in `mod_state_server.py`. Add at the end of its execution:

```python
try:
    result = event_magnitude_audit.audit(ms)
    report = event_magnitude_audit.render_report(result)
    out_path = os.path.join(mod_path, "docs", "event_magnitude_report.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    logger.info(f"[post-load] event_magnitude_report ok ({len(result.flags)} flags)")
except Exception as exc:
    logger.warning(f"[post-load] event_magnitude_report failed: {exc}")
```

- [ ] **Step 3: Restart the server and test**

```bash
# stop existing server (it auto-runs under VS Code)
pkill -f mod_state_server.py
.venv/bin/python mod_state_server.py &
# wait for ready
until curl -sf http://localhost:8950/status > /dev/null; do sleep 5; done
curl -s "http://localhost:8950/event-magnitude-audit?resource=prestige" | head -50
```
Expected: JSON response with at least 8 prestige flags (the existing problematic events).

- [ ] **Step 4: Confirm report regenerates on reload**

```bash
ls -la docs/engine/event_magnitude_report.md
# Touch nothing. Just trigger a reload.
curl -X POST http://localhost:8950/reload
ls -la docs/engine/event_magnitude_report.md
```
Expected: mtime advances. File contains "## Unreviewed Flags" and ~8 prestige entries.

- [ ] **Step 5: Commit**

```bash
git add mod_state_server.py docs/engine/event_magnitude_report.md
git commit -m "$(cat <<'EOF'
mod_state_server: wire event_magnitude_audit endpoint + report

Adds /event-magnitude-audit (JSON, with ?resource= ?event_id=
?show_reviewed= ?format=text filters) and runs the audit on every full
/reload to regenerate docs/engine/event_magnitude_report.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 11: Add tiered script values for fast-scaling resources

**Files:**
- Modify: `common/script_values/extra_script_values.txt`

- [ ] **Step 1: Verify script-value source pattern works in this engine**

Search for an existing vanilla script value that references `country_prestige` or similar as a value source:

```bash
grep -r "value = country_prestige" /home/jakef/src/vic3/game/common/script_values/ 2>/dev/null | head -5
grep -r "value = country_prestige" /home/jakef/src/Vic3TimelineExtended/common/script_values/ 2>/dev/null | head -5
```
Expected: at least one hit confirming the pattern is engine-supported. If zero hits, fall back to the `var:` cache approach (skipped in this plan; document and ask for guidance).

- [ ] **Step 2: Append script values to the mod file**

Append at end of `common/script_values/extra_script_values.txt`:

```
# === Tiered scaler script values for events ============================
# Used by add_modifier { multiplier = sv_<resource>_event_<tier> } so the
# resulting modifier scales with the country's current resource value
# instead of being a hardcoded delta that goes invisible at late-game scale.
#
# See docs/engine/event_magnitude_report.md for the audit that flags missing usage.
# Tiers: tiny=0.5%, small=2%, medium=5%, large=15%, huge=30%

sv_prestige_event_tiny   = { value = country_prestige  multiply = 0.005 }
sv_prestige_event_small  = { value = country_prestige  multiply = 0.02  }
sv_prestige_event_medium = { value = country_prestige  multiply = 0.05  }
sv_prestige_event_large  = { value = country_prestige  multiply = 0.15  }
sv_prestige_event_huge   = { value = country_prestige  multiply = 0.30  }

sv_treasury_event_tiny   = { value = country_treasury  multiply = 0.005 }
sv_treasury_event_small  = { value = country_treasury  multiply = 0.02  }
sv_treasury_event_medium = { value = country_treasury  multiply = 0.05  }
sv_treasury_event_large  = { value = country_treasury  multiply = 0.15  }
sv_treasury_event_huge   = { value = country_treasury  multiply = 0.30  }

# Construction is a per-week-capacity number; same scale ladder.
sv_construction_event_tiny   = { value = country_construction  multiply = 0.005 }
sv_construction_event_small  = { value = country_construction  multiply = 0.02  }
sv_construction_event_medium = { value = country_construction  multiply = 0.05  }
sv_construction_event_large  = { value = country_construction  multiply = 0.15  }

# Bureaucracy is a capacity; small values matter so use a denser ladder.
sv_bureaucracy_event_tiny   = { value = country_bureaucracy  multiply = 0.005 }
sv_bureaucracy_event_small  = { value = country_bureaucracy  multiply = 0.02  }
sv_bureaucracy_event_medium = { value = country_bureaucracy  multiply = 0.05  }

# Weekly-flow scalers: use country_weekly_net_income / country_weekly_minting
# as the underlying source. Verify exact source names during implementation
# via /search?q=country_weekly_net_income — fall back to country_treasury/52
# if the live-flow source isn't available.
sv_treasury_flow_event_tiny   = { value = country_weekly_net_income  multiply = 0.01 }
sv_treasury_flow_event_small  = { value = country_weekly_net_income  multiply = 0.05 }
sv_treasury_flow_event_medium = { value = country_weekly_net_income  multiply = 0.15 }
```

- [ ] **Step 3: Reload mod_state_server and verify no parse errors**

```bash
curl -X POST http://localhost:8950/reload
curl -s "http://localhost:8950/script-values" | grep -c sv_prestige_event
```
Expected: 5 (matches the five prestige tiers).

Then check `debug.log` for any `script_parse_error` related to the new script values:
```bash
curl -s "http://localhost:8950/logs/debug?summary=false&dedupe=true&q=sv_prestige_event" | head -20
```
Expected: empty / no errors.

- [ ] **Step 4: Commit**

```bash
git add common/script_values/extra_script_values.txt
git commit -m "$(cat <<'EOF'
script_values: tiered scaler script values for event effects

Adds sv_<resource>_event_<tier> for prestige, treasury, construction,
bureaucracy, and treasury-flow. Used by add_modifier multiplier= to
scale event effects with the country's current resource value instead
of hardcoding deltas that go invisible at late-game scale.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 12: Add `_mult`-based generic prestige/bureaucracy static modifiers

**Files:**
- Modify: `common/static_modifiers/extra_modifiers.txt`

- [ ] **Step 1: Append static modifiers**

Append:

```
# === Generic mult-based scaled prestige/bureaucracy modifiers =========
# Pair with add_modifier = { name = prestige_loss_<tier> } in events,
# no multiplier needed — the _mult is naturally proportional to current
# value so it stays meaningful at any game scale.
#
# Tiers: tiny=0.5%, small=2%, medium=5%, large=15%, huge=30%

prestige_loss_tiny    = { country_prestige_mult = -0.005 }
prestige_loss_small   = { country_prestige_mult = -0.02  }
prestige_loss_medium  = { country_prestige_mult = -0.05  }
prestige_loss_large   = { country_prestige_mult = -0.15  }
prestige_loss_huge    = { country_prestige_mult = -0.30  }

prestige_gain_tiny    = { country_prestige_mult =  0.005 }
prestige_gain_small   = { country_prestige_mult =  0.02  }
prestige_gain_medium  = { country_prestige_mult =  0.05  }
prestige_gain_large   = { country_prestige_mult =  0.15  }
prestige_gain_huge    = { country_prestige_mult =  0.30  }

bureaucracy_loss_tiny    = { country_bureaucracy_mult = -0.005 }
bureaucracy_loss_small   = { country_bureaucracy_mult = -0.02  }
bureaucracy_loss_medium  = { country_bureaucracy_mult = -0.05  }

bureaucracy_gain_tiny    = { country_bureaucracy_mult =  0.005 }
bureaucracy_gain_small   = { country_bureaucracy_mult =  0.02  }
bureaucracy_gain_medium  = { country_bureaucracy_mult =  0.05  }
```

- [ ] **Step 2: Tab-normalize and reload**

```bash
python3 scripts/format_paradox_tabs.py common/static_modifiers/extra_modifiers.txt
curl -X POST http://localhost:8950/reload
curl -s "http://localhost:8950/raw/StaticModifier/prestige_loss_small"
```
Expected: returns the `country_prestige_mult = -0.02` body.

- [ ] **Step 3: Commit**

```bash
git add common/static_modifiers/extra_modifiers.txt
git commit -m "$(cat <<'EOF'
static_modifiers: add prestige_<gain|loss>_<tier> and bureaucracy_<...> generics

These _mult-based modifiers are naturally proportional to current
prestige/bureaucracy, so events using `add_modifier { name = X }`
(no multiplier) stay meaningful at any game scale.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 13: Convert the 8 existing prestige events

**Files:**
- Modify: `events/*.txt` (specific files identified by audit run)

- [ ] **Step 1: List the offenders**

```bash
curl -s "http://localhost:8950/event-magnitude-audit?resource=prestige" | python3 -m json.tool | head -80
```
Record the list of `event_id` + `file:line` entries.

- [ ] **Step 2: Convert each one**

For each flagged event:
- If the static modifier carries ONLY `country_prestige_add`: replace `add_modifier = { name = X multiplier = -20 }` with `add_modifier = { name = prestige_loss_small }` (pick tier by old absolute value: -5..-25 → small, -25..-100 → medium, ≤ -100 → large).
- If the static modifier has multiple fields: replace `multiplier = -20` with `multiplier = sv_prestige_event_small` (same tier rule).
- For `add_treasury` direct effects: replace `add_treasury = -10000` with `add_treasury = sv_treasury_event_small`.

Keep one event in flight at a time, deploy + reload between each, sanity-check `error.log` and `debug.log` are clean.

- [ ] **Step 3: Re-run audit, confirm cleanup**

```bash
curl -X POST http://localhost:8950/reload
curl -s "http://localhost:8950/event-magnitude-audit?resource=prestige" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['flags']),'flags')"
```
Expected: 0 flags (or only flags marked `# REVIEWED`).

- [ ] **Step 4: Commit**

```bash
git add events/
git commit -m "$(cat <<'EOF'
events: convert hardcoded prestige hits to scaled modifiers

Replaces 8 events' hardcoded `add_modifier { multiplier = -N }` over
prestige-bearing static modifiers with mult-based prestige_loss_<tier>
generics (or sv_prestige_event_<tier> where the static modifier has
multiple fields).

Resolves the international_relations_events.106 UX bug where -20
prestige was 0.012% of late-game prestige and entirely invisible.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 14: Update documentation

**Files:**
- Modify: `docs/audits/open_issues.md`
- Modify: `docs/guides/scripting_best_practices.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Append to docs/audits/open_issues.md**

Read the current file first to match its style, then append two new entries:

```markdown
## Trading-principle influence inflation

Late-game trading powers in a power-bloc that has the trading principle
accumulate effectively unbounded influence per Trade Center, breaking
influence as a finite diplomatic-budget resource. A late-game trading
hegemon can sign every available treaty article without budget pressure,
which collapses the diplomatic strategy layer.

Reproducible: build a trading-principle bloc as a high-rank country,
take many Trade Centers, observe weekly influence gain.

Possible fixes: cap the per-TC bonus, scale it down with rank, or move
the principle's influence bonus to a one-time threshold rather than
per-Trade-Center.

## Deferred event-tooling categories

The 2026-05-04 magnitude-audit work covered category #1 of a four-part
event-quality plan. Still TODO:

- **Category #2 — pulse-event narrative drift.** Flavor events fired
  from on_yearly/monthly_pulse narrate game actions the player didn't
  take (e.g., un_events.txt veto flavor that fires regardless of the
  player using a veto). Tooling: scan event localization for
  action-implying tokens, cross-reference event triggers for matching
  game-state checks, flag drift.
- **Category #3 — event-chain invisibility.** Backfires/sequels don't
  surface their precursor to the player. Tooling: build event-chain
  graph, for events with predecessors check whether the description
  references the prior choice; otherwise prepend a contextual reminder.
- **Category #4 — orphan event-bug detection.** Events meant to fire
  mechanically but never wired anywhere. Tooling: list events that
  appear in no `trigger_event` call and no `random_events` pool, then
  cross-reference against event titles/descriptions to identify which
  ones are mechanically required vs intentionally pulse-only.
```

- [ ] **Step 2: Append to docs/guides/scripting_best_practices.md**

Add a new subsection (locate the right place by reading the table of contents). Suggested content:

```markdown
### Fast-scaling resources require scaled effects

Hardcoded delta values for fast-scaling resources go invisible at
late-game scale. Late-1900s prestige can hit 100k+; treasury can hit
billions. A `multiplier = -20` on a prestige-bearing static modifier is
0.012% of 163,028 prestige — invisible.

The fast-scaling resources tracked by the magnitude audit (see
`event_magnitude_audit.py`):

- `country_prestige_add`
- `country_bureaucracy_add`
- `country_construction_add`
- `country_expenses_add`, `country_government_dividends_add`,
  `country_minting_add` (treasury-equivalent weekly flows)
- `add_treasury` (direct effect, instant)

For each, prefer one of:

1. The `_mult`-based generic static modifier:
   `add_modifier = { name = prestige_loss_small }` (no multiplier
   needed — the modifier is naturally % of current value).
2. The script-value scaler:
   `add_modifier = { name = my_modifier multiplier = sv_prestige_event_small }`
   (use when the static modifier has multiple fields that should scale
   together).

Slow-scaling resources (authority, influence) and non-scaling ones
(infamy, SoL, country rank, legitimacy) are NOT in scope — their
usage doesn't grow over the game, so hardcoded values remain meaningful.

**Suppressing a flag.** If a hardcoded value is intentional (tech-gated
to a specific era, vanilla precedent, etc.), add an inline comment on
the value line:

    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated to nuclear era

The audit captures the date and rationale. The
`docs/engine/event_magnitude_report.md` distinguishes unreviewed flags
(actionable) from reviewed exemptions.
```

- [ ] **Step 3: Append one line to CLAUDE.md**

Locate the "Validation rules that bite if ignored" section and append:

```markdown
- **Fast-scaling resources require scaled effects.** Events that hardcode prestige/treasury/bureaucracy/construction deltas go invisible at late-game scale (e.g. -20 prestige is 0.012% of 163k). The `event_magnitude_audit` (`/event-magnitude-audit` endpoint, `docs/engine/event_magnitude_report.md`) flags these. See `docs/guides/scripting_best_practices.md` § "Fast-scaling resources require scaled effects".
```

- [ ] **Step 4: Commit**

```bash
git add docs/audits/open_issues.md docs/guides/scripting_best_practices.md CLAUDE.md
git commit -m "$(cat <<'EOF'
docs: event magnitude audit, deferred tooling categories, trading-principle issue

Adds the new fast-scaling-resources rule + REVIEWED-comment convention
to scripting_best_practices.md and CLAUDE.md, and parks the
trading-principle influence inflation issue + deferred event-tooling
categories #2-#4 in open_issues.md so they don't get lost.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 15: End-to-end verification (manual playtest)

**Files:** none

- [ ] **Step 1: Deploy mod**

```bash
./scripts/deploy.sh --apply
```

- [ ] **Step 2: Launch a 1981 save (or any late-game save)**

Boot the game with the mod loaded, load a save where prestige > 50000, and trigger one of the converted prestige events (e.g., manually fire `international_relations_events.106` via console: `event international_relations_events.106`).

- [ ] **Step 3: Verify prestige drop is visible**

Expected: prestige drops by ~2% (≈3000 at 150k prestige, vs the old -20). The change is visible in the country tooltip.

- [ ] **Step 4: Check logs for parse errors**

```bash
curl -s "http://localhost:8950/logs/debug?dedupe=true&since=last-launch" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for e in d.get('entries', []):
    if any(k in e.get('message','') for k in ['sv_prestige_event','prestige_loss_','prestige_gain_','sv_treasury_event','sv_bureaucracy_event','sv_construction_event']):
        print(e['category'], '|', e['message'][:200])
"
```
Expected: empty (no parse errors against new script values or static modifiers).

If errors appear: investigate immediately, do not mark this task complete.

- [ ] **Step 5: Final audit run**

```bash
curl -s "http://localhost:8950/event-magnitude-audit" | python3 -c "
import json, sys
d = json.load(sys.stdin)
flags = d['flags']
unrev = [f for f in flags if not f.get('exemption')]
print(f'unreviewed flags: {len(unrev)}')
for f in unrev[:10]:
    print(f' - {f[\"resource\"]} | {f[\"file\"]}:{f[\"line\"]} | {f[\"event_id\"]}')
"
```
Expected: any remaining unreviewed flags are non-prestige (treasury, construction, etc.) and represent next-batch follow-up work — fine to leave for a future session, but record the count in the final commit message.

---

## Self-Review Checks

After implementing all tasks, verify against the spec:

1. **Spec coverage:** does every section of `/home/jakef/.claude/plans/i-just-got-the-purring-micali.md` map to a task above?
   - Resource registry → Task 2 ✓
   - Audit walker → Tasks 3-8 ✓
   - Endpoint + report → Task 10 ✓ + Task 9 (renderer)
   - Scaled-effect library → Tasks 11-12 ✓
   - Convert 8 prestige events → Task 13 ✓
   - Doc updates → Task 14 ✓
   - Tests (14 unit tests) → covered across Tasks 2-9 ✓
   - End-to-end verification → Task 15 ✓

2. **Type consistency:** `AuditFlag`, `AuditResult`, `ResourceMeta` — defined once in Task 2 (ResourceMeta), Task 5 (AuditFlag), Task 8 (AuditResult); referenced consistently after.

3. **Placeholder scan:** no TBDs. Implementation steps include exact code blocks. Suppression-format regex is concrete. Exact event-id resolution is concrete. Where there's verification needed (Task 1), it produces concrete decisions before code is written.

If any task references a function/type defined later, that's a bug — go fix the ordering.
