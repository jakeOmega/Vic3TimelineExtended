# Covert Warfare — Four New Operation Types (Slice 6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four covert operations — regime change (code 9, severe), nuclear programme sabotage (10, severe), space programme espionage (11, mild) and cultivate assets (12, mild, network-only) — through every hand-kept per-type site, with a registry test that makes those sites checkable.

**Architecture:** Every operation type is listed by hand in about fifteen places (diplomatic action, sync row, tier trigger, pact-identity OR, detection-event branch, defender-event trigger, two custom-loc blocks, stand-down handler, two widget blocks, loc, lens icon). Task 1 turns that list into `test_covert_op_registry.py`, one table (`OPS`) checked against every site in both directions, green on today's nine types. Each new operation then gets one vertical task: add its `OPS` row (the registry test goes red and names every missing site), build the sites plus the operation's own behaviour, go green, commit. Cultivate assets additionally hooks the network tick (×1.5 growth), the Tradecraft pass (always at the preparatory rate) and the priority gate (pinned at 1).

**Tech Stack:** Paradox Clausewitz script (Victoria 3), `.gui`, YAML loc, Python `unittest` structural tests.

**Spec:** `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md` § Slice 6 (and § Slices and build order, § Verification). The slice-5 plan's "Engine rules" (`docs/superpowers/plans/2026-09-22-covert-tradecraft.md`) still hold; the ones this slice leans on are restated below.

## Global Constraints

- Branch `covert-new-ops` off `origin/main` (already created, upstream unset) in the **main checkout**, not a sparse worktree: Tasks 2–5 copy `.dds` files under `gfx/`. One PR, `gh pr create --base main`; push with `git push -u origin covert-new-ops`.
- Operation codes, verbatim from the spec: **9 regime change, 10 nuclear programme sabotage, 11 space programme espionage, 12 cultivate assets.** Short type names (container tag `iw_op_<type>`, `$TYPE$` parameter): `regime_change`, `nuclear_sabotage`, `space_espionage`, `cultivate_assets`. Action keys: `covert_<type>_action`.
- Tiers, verbatim: regime change and nuclear sabotage **severe**; space espionage and cultivate assets **mild**. Defence axes: regime change **ideological**, nuclear sabotage **military**, space espionage **economic**, cultivate assets **ideological**.
- Modifier values, verbatim: `covert_regime_change` = `country_coup_resistance_add = -1`, `country_legitimacy_base_add = -5`, `political_movement_radicalism_add = 0.05`; `covert_nuclear_sabotage` = `country_nuclear_program_progress_mult = -0.25`; `covert_space_espionage` = `country_space_race_progress_mult = 0.10`, `country_space_race_risk_mult = -0.10`; `covert_space_espionage_detected` = `country_authority_add = -3` (same shape as the two existing `_detected` markers). Constants: `covert_regime_change_coup_push = 5`, `covert_net_cultivate_mult = 1.5`, plus `covert_cultivate_ai_net_ceiling = 50` (the spec's "one below 50").
- Unlock rule from slice 5, verbatim: Seasoned (`covert_tradecraft_unlocks_severe_ops`) gates **launching** regime change and nuclear sabotage. **Existing operations are never gated** — the trigger goes in `possible`, never in `requirement_to_maintain`.
- Brace-based `.txt`/`.gui` use tabs; run `python3 scripts/format_paradox_tabs.py <files>` on every touched `.txt`/`.gui`. Every touched `.txt`/`.gui` keeps its UTF-8 BOM (all covert files have one): `head -c3 <f> | xxd -p` → `efbbbf`.
- Loc: `je_iw_*` keys in `localization/english/te_journal_entries_l_english.yml`, `*_pact_desc` in `te_diplomacy_l_english.yml`, `te_debug_covert.*` in `te_events_l_english.yml`, everything else in `te_miscellaneous_l_english.yml`. Run `python3 organize_loc.py` **only in Task 7** (keys added earlier are not all referenced until later tasks, and organize_loc would move unreferenced keys into `te_unused_l_english.yml`). Afterwards `git diff --stat localization/` must show **nothing new in `te_unused_l_english.yml`**.
- Vic3 loc formatting: `#b X#!`, `#v`, `#R`, `#G`, `#bold`, `#lore` — never `[b]…[/b]`.
- `docs/systems/journal_entry_systems.md` is CRLF: edit with `Edit` only; afterwards `grep -c $'\r$' docs/systems/journal_entry_systems.md` must equal `wc -l < docs/systems/journal_entry_systems.md`.
- Never `git commit -a`; stage by path. The tree carries unrelated `common/buy_packages/00_buy_packages.txt` and `docs/engine/*` churn that must never be staged.
- Commit trailer (both lines, every commit):
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc`
- Always use absolute paths or `cd /home/jakef/src/Vic3TimelineExtended && …` in shell commands.

### Engine rules this plan relies on

1. **`add_modifier`'s `multiplier` is re-evaluated against ROOT on later ticks**, so every apply site goes through `covert_op_add_scaled_modifier` (via `covert_op_apply_target_effect` / `covert_op_apply_self_effect`), which picks one of six constant script values by phase × priority. New operations use those two helpers and nothing else for their modifiers.
2. **`change_variable` does not reliably resolve a script-value operand.** Any write whose operand is a script value uses `set_variable = { value = { value = var:x add = <sv> } }`. `change_variable = { add = 1 }` with a literal is fine.
3. **Network lookups do their work inside the `random_in_list`**, never through a saved scope afterwards (slice 4's lookup rule): loops leave stale saved scopes, and tooltip render passes leave them unset.
4. **`covert_warfare.2` is fired only from `covert_warfare.1`'s `after`, straight after `covert_op_burn`** has written `iw_last_exposed_type` on the target (checked: `git grep 'covert_warfare\.2'`). So a trigger branch on `var:iw_last_exposed_type = 12` is true exactly for a just-burned cultivate-assets operation.
5. **Script values used as `add_progress` operands:** vanilla passes a variable read (`value = owner.var:temp_wargoal_impact`, `common/on_actions/00_code_on_actions.txt:6502`), so the field takes a script value; a named constant is the same class of operand. The console harness checks it in game.
6. **`.gui` booleans:** `And`, `And3`, `Not` exist in vanilla markup (`gui/military_panel_formations.gui:1217` uses `And3(Not(…), …)`).

### Decisions this plan makes where the spec is silent, wrong or inconsistent

- **Regime change needs a rivalry in `possible`, as the spec's text says — but not "like destabilization".** Destabilization's `possible` does *not* require a rivalry (only "not cordial"; the rivalry is only in its AI `will_propose`, despite its header comment). The explicit instruction wins: rivalry in `possible` and in `requirement_to_maintain`.
- **No `has_dlc_feature = ep2_content` gate on the coup push.** Coups are base game: `ip4_coup.1` fires from `coup_monthly_events` in `common/on_actions/00_on_actions_monthly.txt` with no DLC condition, and the progress bar has none either. Only vanilla's `orchestrate_coup` *diplomatic action* is ep2-gated. `je:je_ip4_coup ?= { … }` already makes the push a no-op when no coup is running, so a DLC gate would only withhold the push from players who do get coups.
- **`sr_target_ahead_of_root` becomes `covert_target_ahead_in_space = { TARGET = … }`** in `covert_warfare_triggers.txt`: parameterized so the console harness can test a candidate country with `TARGET = PREV`, built from one `{ TARGET MILESTONE }` helper over the eight milestones (`suborbital orbital moon_landing probe moon_base mars_landing interstellar_probe solar_colonization`; the last is set in `je_space_race.txt:1167`).
- **`nuclear_program_is_proliferating`** (in `nuke_triggers.txt`) also excludes a paused programme and one under a disarmament treaty — the idiom the programme's own display values use (`extra_script_values.txt` `nuclear_program_display_months_to_next`). A nuclear power building its stockpile qualifies, as the spec wants.
- **The "nearing completion" AI bonus reads `var:nuclear_weapon_program_progress >= 75` inline** (guarded): there is no `nuclear_program_nearing_completion` trigger; the spec's name pointed at the inline test in `je_nuclear_program.txt`.
- **Cultivate assets is pinned at priority 1** (user decision, 2026-09-23). Its stepper is hidden on its row and `covert_possible_priority_up` refuses it, so the AI — which steps through that same trigger — keeps it at 1 as well. Its row replaces the three phase lines and three priority lines (which promise effects it doesn't have) with one line saying what it does.
- **Cultivate assets' "usual covert gates"** are the full peacetime set the espionage actions use: per-type cap, a free slot, no duplicate, valid target, no truce, no intelligence-sharing pact, funding ≥ 1 — plus not our own subject. `requirement_to_maintain`: funding ≥ 1, target still valid, no truce.
- **Lens icons** (user decision, 2026-09-23): each action gets a copy of the nearest existing covert icon — regime change ← destabilization, nuclear sabotage ← infrastructure sabotage, space espionage ← industrial espionage, cultivate assets ← influence campaign. The engine auto-loads `gfx/interface/icons/lens_toolbar_icons/<action>.dds` for any action without `show_in_lens = no`; a missing one is a `VFSOpen` error every session (#324 cleaned exactly that).
- **Pre-existing bug fixed in Task 1:** `covert_warfare.2`'s trigger lists `has_modifier = covert_infrastructure_sabotage`, which is applied to *states* (`random_scope_state` in `covert_ops_apply_all_phase_effects`), never to the country, so a burned infrastructure-sabotage operation never tells the defender. The country-scope modifier that type leaves is `covert_infra_sabotage_morale`. The registry test pins "each type's defender-event marker is the modifier it applies to the target country", which is what surfaces this. One line.
- **`country_covert_defense_military_add_desc`** gains nuclear sabotage and the missing military espionage; the economic and ideological descriptions gain their new operations.
- **Console harness** gets its own event `te_debug_covert.4` rather than more options on `.2` (already ten) or `.3`.
- **Known behaviour, documented not changed:** the AI will rarely launch the two severe operations. `possible` binds the AI, so it needs Seasoned (60) Tradecraft; slice 5's own table puts one moderate operation at 10 % detection at a long-run average of 57.

### Balance at the numbers the spec gives (priority included)

The spec's "×2 fully operational" predates slice 3. The real multiplier is phase × priority: 1 / 1.35 / 1.6 establishing and 2 / 2.7 / 3.2 fully operational (`covert_op_mult_p{2,3}_pri{1,2,3}`).

| operation | at ×1 | at ×2 (full, pri 1) | at ×3.2 (full, pri 3) |
|---|---|---|---|
| regime change: coup resistance | −1 | −2 | −3.2 |
| regime change: legitimacy | −5 | −10 | −16 |
| regime change: movement radicalism | +5 % | +10 % | +16 % |
| nuclear sabotage: programme progress | ×0.75 | ×0.5 | ×0.2 (never ≤ 0: the JE multiplies by `1 + mult`) |
| space espionage: milestone progress / risk | +10 % / −10 % | +20 % / −20 % | +32 % / −32 % |

**Coups.** `je_ip4_coup_progress_bar` starts at 10, completes at 120, and moves **weekly** by `commander_coup_strength − country_coup_resistance` (`00_ip4_victoria_progress_bars.txt`); the entry times out after 730 days. `country_coup_resistance = legitimacy / 10 + (1 + country_coup_resistance_add) × (1 + mult)` (`ip4_je_values.txt:856`). So each point of resistance the operation removes is about **+4.3 progress a month**, and −10 legitimacy removes one more point. Against a mid-legitimacy (50) government, resistance 6:

| regime change | resistance | extra progress / month (resistance) | + push | total |
|---|---|---|---|---|
| none | 6 | 0 | 0 | 0 |
| establishing, pri 1 | 4.5 | +6.5 | 0 | +6.5 |
| fully operational, pri 1 | 3 | +13 | +5 | +18 |
| fully operational, pri 3 | 1.2 | +20.8 | +5 | +25.8 |

A coup that would stall (strength = resistance) finishes in about six months once the operation is fully operational. Lower resistance also makes coups *start* more often, since `ip4_coup.1` fires when a disloyal commander's strength reaches 0.9 × resistance. Resistance can go negative at low legitimacy (vanilla does not clamp it). The +5 push is the smaller part of the effect; the resistance channel does most of the work. These are the spec's numbers; the PR states this table so the user can tune them.

## Review Focus

1. **A regime-change or nuclear-sabotage operation must keep running when Tradecraft falls below Seasoned.** The unlock trigger belongs in `possible` only. Pinned by `test_severe_gate_is_launch_only` (Tasks 2 and 3).
2. **Cultivate assets must never act on its target or on its operator, and must never rise above priority 1, including under the AI.** Pinned by the registry's `test_markers_are_what_the_operation_leaves_on_its_target` (marker `None` ⇒ absent from the apply pass) and `test_cultivate_assets_is_pinned_at_priority_1` (Task 5).
3. **A burned cultivate-assets operation must still be announced to the defender**, although it leaves no modifier. Pinned by the registry's `test_defender_event_hears_every_type` (Task 5).
4. **Old-save networks have no `iw_net_cultivating`** and must not error or read as cultivating. Pinned by `test_cultivate_multiplier_is_guarded_and_zeroed` (Task 5).
5. **Nuclear sabotage at full strength must not drive programme progress to zero or below.** Pinned by `test_nuclear_sabotage_never_stops_progress` (Task 3), which multiplies the modifier by the largest phase × priority constant.

---

## File map

| File | Change |
|---|---|
| `test_covert_op_registry.py` | **New.** `OPS` table + one test per per-type site |
| `test_covert_new_ops.py` | **New.** Slice-6 behaviour tests (gates, modifiers, coup push, cultivate hooks, harness) |
| `test_covert_detection_roll.py`, `test_covert_exposure_tiers.py`, `test_covert_stand_down.py` | Import `CODES` / `TIER_CODES` / `TIERS` / `TYPES` from the registry instead of keeping copies |
| `common/diplomatic_actions/covert_operations.txt` | Four new actions |
| `common/scripted_effects/covert_warfare_effects.txt` | Four sync rows; apply blocks (regime change, nuclear, space); cultivate hooks in `covert_nets_sync` and `covert_tradecraft_monthly`; header comments |
| `common/scripted_triggers/covert_warfare_triggers.txt` | Pact OR; tier codes; space and network predicates; cultivate priority pin |
| `common/scripted_triggers/nuke_triggers.txt` | `nuclear_program_is_proliferating` |
| `common/script_values/covert_warfare_script_values.txt` | Three Section-1 constants; `covert_net_tick_gain` × cultivate |
| `events/covert_warfare_events.txt` | Four `after` branches; `covert_warfare.2` trigger (four new lines + infra fix) |
| `common/customizable_localization/covert_warfare_custom_loc.txt` | Codes 9–12 in both type-name blocks |
| `common/scripted_guis/covert_warfare_sguis.txt` | Four stand-down handlers |
| `gui/journal_entry_widgets/covert_operations_widget.gui` | Four row lines + four stand-down buttons; cultivate row: no stepper, no phase/priority lines, one detail line |
| `common/static_modifiers/extra_modifiers.txt` | `covert_regime_change`, `covert_nuclear_sabotage`, `covert_space_espionage`, `covert_space_espionage_detected` |
| `gfx/interface/icons/lens_toolbar_icons/covert_{regime_change,nuclear_sabotage,space_espionage,cultivate_assets}_action.dds` | Copies of existing icons |
| `localization/english/te_{miscellaneous,journal_entries,diplomacy,modifiers,events}_l_english.yml` | New keys; three covert-defence descriptions |
| `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt` | Harness `te_debug_covert.4` |
| `docs/systems/mod_systems.md`, `docs/systems/journal_entry_systems.md` (CRLF), `README.md`, spec § Slice 6 | Docs |

Test commands used throughout:
- `python3 -m unittest test_covert_op_registry test_covert_new_ops -v`
- existing covert suites (must stay green): `python3 -m unittest test_covert_detection_roll test_covert_exposure_tiers test_covert_networks test_covert_priority test_covert_stand_down test_covert_tradecraft`

---

### Task 1: The covert operation registry test (nine types) + the defender-event marker fix

**Files:**
- Create: `test_covert_op_registry.py`
- Modify: `events/covert_warfare_events.txt` (`covert_warfare.2` trigger)
- Modify: `test_covert_detection_roll.py`, `test_covert_exposure_tiers.py`, `test_covert_stand_down.py`

**Interfaces:**
- Produces: `test_covert_op_registry.OPS` — tuple of `(type, code, axis, tier, marker)`; `TYPES` (tuple of type names in code order), `CODES` (`{type: code}`), `TIERS` (`{type: tier}`), `TIER_CODES` (`{tier: {codes}}`). Tasks 2–5 each append one `OPS` row; nothing else in this file changes per type.

- [ ] **Step 1: Write the registry test**

Create `test_covert_op_registry.py`:

```python
"""The covert operation registry: every operation type in one table, pinned
against every site that lists operation types by hand.

Adding an operation type touches about fifteen hand-kept places — see
docs/systems/mod_systems.md § Covert Warfare System, "Adding an operation
type". OPS is the single list. Each test checks one site against it in both
directions (no type missing, no stale extra), so a half-added type fails here,
naming the site, instead of in a play test. The widget's stand-down buttons
are pinned by test_covert_stand_down.py, which reads TYPES from here.

The other covert test files import CODES / TIERS / TIER_CODES / TYPES from
this module rather than keeping their own copies.

Run: python3 -m unittest test_covert_op_registry -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
SGUIS = ROOT / "common/scripted_guis/covert_warfare_sguis.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
LOC_DIR = ROOT / "localization/english"
LENS_ICONS = ROOT / "gfx/interface/icons/lens_toolbar_icons"

# (short type, code, covert-defence axis, exposure tier, target marker)
#
# The code is what iw_type_code / iw_burned_type_code / iw_last_exposed_type
# carry. The marker is the country-scope modifier the operation leaves on its
# target, which covert_warfare.2 keys on to tell the defender about a burn;
# None for an operation that leaves nothing on its target, whose burn is keyed
# on iw_last_exposed_type instead.
OPS = (
    ("election_interference", 0, "ideological", "moderate", "covert_election_interference"),
    ("financial_subversion", 1, "economic", "moderate", "covert_financial_subversion"),
    ("infrastructure_sabotage", 2, "military", "war", "covert_infra_sabotage_morale"),
    ("comms_disruption", 3, "military", "war", "covert_comms_disruption"),
    ("industrial_espionage", 4, "economic", "mild", "covert_industrial_espionage_detected"),
    ("military_espionage", 5, "military", "mild", "covert_military_espionage_detected"),
    ("influence_campaign", 6, "ideological", "moderate", "covert_influence_campaign"),
    ("ideological_subversion", 7, "ideological", "severe", "covert_ideological_subversion_resist"),
    ("destabilization", 8, "ideological", "severe", "covert_destabilization_resist"),
)

TIER_NAMES = ("mild", "moderate", "severe", "war")
TYPES = tuple(op[0] for op in OPS)
CODES = {op[0]: op[1] for op in OPS}
TIERS = {op[0]: op[3] for op in OPS}
TIER_CODES = {tier: {op[1] for op in OPS if op[3] == tier} for tier in TIER_NAMES}

# Keys every covert action needs, as covert_<type><suffix>. The engine derives
# the _action_* ones from the diplomatic action key.
ACTION_LOC_SUFFIXES = (
    "_action",
    "_action_desc",
    "_action_action_propose_name",
    "_action_action_break_name",
    "_action_action_notification_name",
    "_action_action_notification_break_name",
    "_action_action_notification_desc",
    "_action_action_notification_break_desc",
    "_action_pact_desc",
)


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _event(n):
    body = _text(EVENTS)
    start = body.index("\ncovert_warfare.%d = {" % n)
    end = body.find("\ncovert_warfare.", start + 1)
    return body[start: end if end != -1 else len(body)]


def _loc():
    """Every live loc key -> its text. te_unused is organize_loc's output for
    keys nothing references, so a key found only there counts as missing."""
    out = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        if path.name.startswith("te_unused"):
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^ ([A-Za-z0-9_.]+):\d* (.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


class TableTests(unittest.TestCase):
    def test_codes_are_contiguous_from_zero(self):
        self.assertEqual(sorted(CODES.values()), list(range(len(OPS))))

    def test_types_are_unique(self):
        self.assertEqual(len(set(TYPES)), len(OPS))


class SyncRowTests(unittest.TestCase):
    def test_sync_all_has_exactly_one_row_per_type(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_sync_all = {")
        rows = set(re.findall(
            r"covert_op_sync = \{ TYPE = (\w+) ACTION = (\w+) DEFENSE_MOD = (\w+) CODE = (\d+) \}",
            block,
        ))
        expected = {
            (t, "covert_%s_action" % t, "country_covert_defense_%s_add" % axis, str(code))
            for t, code, axis, _, _ in OPS
        }
        self.assertEqual(rows, expected)


class DiplomaticActionTests(unittest.TestCase):
    def test_one_action_per_type_and_no_other(self):
        found = set(re.findall(r"(?m)^(covert_\w+_action) = \{", _text(ACTIONS)))
        self.assertEqual(found, {"covert_%s_action" % t for t in TYPES})

    def test_each_action_is_wired_to_its_own_type(self):
        body = _text(ACTIONS)
        for t, code, axis, _, _ in OPS:
            with self.subTest(type=t):
                block = _top_level_block(body, "covert_%s_action = {" % t)
                self.assertIn(
                    "covert_op_start = { TYPE = %s DEFENSE_MOD = country_covert_defense_%s_add CODE = %d }"
                    % (t, axis, code),
                    block,
                )
                self.assertIn("is_hostile = yes", block)
                self.assertIn("manual_break_effect = { covert_op_end = { TYPE = %s } }" % t, block)
                self.assertIn("auto_break_effect = { covert_op_end = { TYPE = %s } }" % t, block)
                self.assertIn("covert_ops_type_below_cap = { TYPE = covert_%s_action }" % t, block)
                self.assertIn(
                    "NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_%s_action } }" % t,
                    block,
                )
                self.assertIn("var:iw_funding_level >= 1", block)

    def test_every_tooltip_the_actions_name_exists(self):
        loc = _loc()
        for key in sorted(set(re.findall(r"text = (\w+)", _text(ACTIONS)))):
            with self.subTest(key=key):
                self.assertIn(key, loc)


class PactIdentityTests(unittest.TestCase):
    def test_is_covert_operation_pact_lists_every_action(self):
        block = _top_level_block(_text(TRIGGERS), "is_covert_operation_pact = {")
        found = set(re.findall(r"is_diplomatic_action_type = (\w+)", block))
        self.assertEqual(found, {"covert_%s_action" % t for t in TYPES})


class TierTableTests(unittest.TestCase):
    def test_tier_triggers_partition_the_codes(self):
        body = _text(TRIGGERS)
        seen = []
        for tier in TIER_NAMES:
            block = _top_level_block(body, "covert_code_tier_%s = {" % tier)
            codes = {int(c) for c in re.findall(r"var:\$VAR\$ = (\d+)", block)}
            self.assertEqual(codes, TIER_CODES[tier], "covert_code_tier_%s" % tier)
            seen.extend(codes)
        self.assertEqual(sorted(seen), sorted(CODES.values()))


class DetectionEventTests(unittest.TestCase):
    def test_after_burns_every_code_as_its_own_type(self):
        ev = _event(1)
        after = ev[ev.index("after = {"):]
        self.assertEqual(
            sorted(int(c) for c in re.findall(r"var:iw_burned_type_code = (\d+)", after)),
            sorted(CODES.values()),
        )
        for t, code, _, _, _ in OPS:
            with self.subTest(type=t):
                self.assertRegex(
                    after,
                    r"limit = \{ var:iw_burned_type_code = %d \}\s*"
                    r"covert_op_burn = \{ TYPE = %s ACTION = covert_%s_action "
                    r"TARGET = scope:detected_by_country CODE = %d \}" % (code, t, t, code),
                )

    def test_defender_event_hears_every_type(self):
        ev = _event(2)
        trigger = ev[ev.index("trigger = {"): ev.index("immediate = {")]
        self.assertEqual(
            set(re.findall(r"has_modifier = (\w+)", trigger)),
            {op[4] for op in OPS if op[4]},
        )
        for t, code, _, _, marker in OPS:
            if marker is None:
                with self.subTest(type=t):
                    self.assertIn("has_variable = iw_last_exposed_type", trigger)
                    self.assertIn("var:iw_last_exposed_type = %d" % code, trigger)

    def test_markers_are_what_the_operation_leaves_on_its_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for t, _, _, _, marker in OPS:
            with self.subTest(type=t):
                if marker is None:
                    # No effect at all: not on the target, not on the operator.
                    self.assertNotIn("iw_op_%s" % t, block)
                    self.assertNotIn("TYPE = %s " % t, block)
                else:
                    self.assertIn(
                        "covert_op_apply_target_effect = { TYPE = %s MODIFIER = %s }" % (t, marker),
                        block,
                    )


class CustomLocTests(unittest.TestCase):
    def test_both_type_name_blocks_name_every_code(self):
        body = _text(CUSTOM_LOC)
        for entry, var in (
            ("covert_last_exposed_type_name", "iw_last_exposed_type"),
            ("covert_burned_type_name", "iw_burned_type_code"),
        ):
            with self.subTest(entry=entry):
                block = _top_level_block(body, "%s = {" % entry)
                pairs = re.findall(
                    r"trigger = \{ var:%s = (\d+) \}\s*localization_key = iw_op_name_(\w+)" % var,
                    block,
                )
                self.assertEqual(
                    {(int(c), t) for c, t in pairs},
                    {(code, t) for t, code, _, _, _ in OPS},
                )
                self.assertIn("localization_key = iw_op_name_unknown", block)


class StandDownHandlerTests(unittest.TestCase):
    def test_one_handler_per_type(self):
        body = _text(SGUIS)
        self.assertEqual(
            set(re.findall(r"(?m)^covert_stand_down_(\w+)_sgui = \{", body)),
            set(TYPES),
        )
        for t in TYPES:
            with self.subTest(type=t):
                block = _top_level_block(body, "covert_stand_down_%s_sgui = {" % t)
                self.assertIn("covert_possible_stand_down = { TYPE = %s }" % t, block)
                self.assertIn(
                    "covert_effect_stand_down = { TYPE = %s ACTION = covert_%s_action }" % (t, t),
                    block,
                )


class WidgetTests(unittest.TestCase):
    def test_each_type_has_its_row_line(self):
        rows = re.findall(
            r"visible = \"\[ScriptContainer\.HasTag\('iw_op_(\w+)'\)\]\"\s*"
            r"text = \"je_iw_op_row_\1\"",
            _text(WIDGET),
        )
        self.assertEqual(sorted(rows), sorted(TYPES))


class LocTests(unittest.TestCase):
    def test_every_type_has_its_loc(self):
        loc = _loc()
        for t in TYPES:
            keys = ["iw_op_name_%s" % t, "je_iw_op_row_%s" % t]
            keys += ["covert_%s%s" % (t, s) for s in ACTION_LOC_SUFFIXES]
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(key, loc)

    def test_every_action_description_shows_its_own_tier(self):
        loc = _loc()
        for t, _, _, tier, _ in OPS:
            with self.subTest(type=t):
                self.assertIn("$iw_exposure_tier_%s_note$" % tier, loc["covert_%s_action_desc" % t])


class LensIconTests(unittest.TestCase):
    @unittest.skipUnless(LENS_ICONS.is_dir(), "gfx/ not checked out (sparse worktree)")
    def test_every_action_has_a_lens_icon(self):
        for t in TYPES:
            with self.subTest(type=t):
                self.assertTrue((LENS_ICONS / ("covert_%s_action.dds" % t)).is_file())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it — exactly one test fails, on the pre-existing bug**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry -v`
Expected: every test passes except `test_defender_event_hears_every_type`, whose set difference shows `covert_infrastructure_sabotage` present and `covert_infra_sabotage_morale` missing. If anything else fails, stop: the registry disagrees with the code on `main`, and that must be understood before continuing.

- [ ] **Step 3: Fix the defender-event trigger**

In `events/covert_warfare_events.txt`, `covert_warfare.2`'s `trigger`, replace

```
		# Only fire when someone has run an operation on us — covers all 9 op types (#158)
		OR = {
			has_modifier = covert_election_interference
			has_modifier = covert_financial_subversion
			has_modifier = covert_infrastructure_sabotage
```

with

```
		# Only fire when someone has run an operation on us (#158). One line per
		# operation type: the country-scope modifier that type leaves on its
		# target (infrastructure sabotage's own modifier sits on a state, so its
		# line is the country-scope morale one). Pinned by test_covert_op_registry.
		OR = {
			has_modifier = covert_election_interference
			has_modifier = covert_financial_subversion
			has_modifier = covert_infra_sabotage_morale
```

- [ ] **Step 4: Point the older covert tests at the registry**

`test_covert_detection_roll.py`: delete the whole `CODES = { … }` literal and the three comment lines above it (`# Operation type code mapping, per …` through `# against the same numbers rather than hand-copied per test.`). Directly after the line `from paradox_file_parser import ParadoxFileParser`, add

```python
from test_covert_op_registry import CODES  # the single copy of the type codes
```

and change `for code in range(9):` to `for code in CODES.values():`. In the module docstring change "the nine\ncovert_op_start calls" to "every\ncovert_op_start call".

`test_covert_exposure_tiers.py`: delete the `CODES`, `TIER_CODES` and `ACTION_TIER` literals and the comment "Slice 1's codes, repeated here so this file stands alone."; directly after the line `from paradox_file_parser import ParadoxFileParser` add

```python
from test_covert_op_registry import CODES, TIER_CODES, TIERS as ACTION_TIER
```

and replace the comment in `test_tier_triggers_partition_every_operation_code`
`# Slice 6 adds three operation types. Each new code must land in` / `# exactly one tier, and no code may be forgotten.` with `# Each operation code (test_covert_op_registry.OPS) must land in` / `# exactly one tier, and no code may be forgotten.`

`test_covert_stand_down.py`: delete the `TYPES = ( … )` literal and add `from test_covert_op_registry import TYPES` directly after `from pathlib import Path` (one blank line between, as a first-party import), and in the docstring change "Each row carries nine stand-down instances" to "Each row carries one stand-down instance per operation type".

Run `ruff check test_covert_op_registry.py test_covert_detection_roll.py test_covert_exposure_tiers.py test_covert_stand_down.py` and fix any import-order finding it reports (ruff config: `ruff.toml`).

- [ ] **Step 5: Run everything covert**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry test_covert_detection_roll test_covert_exposure_tiers test_covert_networks test_covert_priority test_covert_stand_down test_covert_tradecraft`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd /home/jakef/src/Vic3TimelineExtended
python3 scripts/format_paradox_tabs.py events/covert_warfare_events.txt
git add test_covert_op_registry.py test_covert_detection_roll.py test_covert_exposure_tiers.py test_covert_stand_down.py events/covert_warfare_events.txt docs/superpowers/plans/2026-09-23-covert-new-operations.md
git commit -m "test(covert): one registry of operation types, pinned against every per-type site

Adding a covert operation type touches about fifteen hand-kept lists. OPS in
test_covert_op_registry.py is now the single table; each test checks one site
against it in both directions. The detection-roll, exposure-tier and
stand-down tests read their codes and types from it.

The registry surfaced a pre-existing bug: covert_warfare.2 keyed infrastructure
sabotage on covert_infrastructure_sabotage, a state modifier, so a burned
sabotage operation never told the defender. It now keys on the country-scope
covert_infra_sabotage_morale.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

---

### Task 2: Regime change (code 9, severe) — plus the shared slice-6 constants and gate tooltips

**Files:**
- Create: `test_covert_new_ops.py`
- Modify: `test_covert_op_registry.py` (one `OPS` row)
- Modify: `common/script_values/covert_warfare_script_values.txt` (Section 1)
- Modify: `common/static_modifiers/extra_modifiers.txt`
- Modify: `common/diplomatic_actions/covert_operations.txt` (append)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_ops_sync_all`, `covert_ops_apply_all_phase_effects`)
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (`is_covert_operation_pact`, `covert_code_tier_severe`)
- Modify: `events/covert_warfare_events.txt` (`covert_warfare.1` `after`, `covert_warfare.2` `trigger`)
- Modify: `common/customizable_localization/covert_warfare_custom_loc.txt`
- Modify: `common/scripted_guis/covert_warfare_sguis.txt`
- Modify: `gui/journal_entry_widgets/covert_operations_widget.gui`
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_journal_entries_l_english.yml`, `te_diplomacy_l_english.yml`
- Create: `gfx/interface/icons/lens_toolbar_icons/covert_regime_change_action.dds`

**Interfaces:**
- Consumes: `test_covert_op_registry.OPS` (Task 1); `covert_tradecraft_unlocks_severe_ops` (slice 5); `covert_op_apply_target_effect` / `covert_op_is_fully_operational` (existing).
- Produces: constants `covert_regime_change_coup_push`, `covert_net_cultivate_mult`, `covert_cultivate_ai_net_ceiling` (Section 1); loc keys `iw_requires_rivalry_tt`, `iw_target_not_our_subject_tt`, `iw_severe_ops_need_tradecraft_tt` (Tasks 3 and 5 reuse them); `test_covert_new_ops.py` helpers `_text`, `_top_level_block`, `_loc` and its path constants (later tasks add classes to it).

- [ ] **Step 1: Add the registry row (red)**

In `test_covert_op_registry.py`, append to `OPS`:

```python
    ("regime_change", 9, "ideological", "severe", "covert_regime_change"),
```

Run: `python3 -m unittest test_covert_op_registry`
Expected: FAIL in `test_sync_all_has_exactly_one_row_per_type`, `test_one_action_per_type_and_no_other`, `test_each_action_is_wired_to_its_own_type`, `test_is_covert_operation_pact_lists_every_action`, `test_tier_triggers_partition_the_codes`, `test_after_burns_every_code_as_its_own_type`, `test_defender_event_hears_every_type`, `test_markers_are_what_the_operation_leaves_on_its_target`, `test_both_type_name_blocks_name_every_code`, `test_one_handler_per_type`, `test_each_type_has_its_row_line`, `test_every_type_has_its_loc`, `test_every_action_description_shows_its_own_tier`, `test_every_action_has_a_lens_icon` — the fifteen sites this task fills.

- [ ] **Step 2: Write the behaviour tests (red)**

Create `test_covert_new_ops.py`:

```python
"""Structural tests for covert warfare slice 6: four new operation types.

The per-type plumbing (sync rows, tier table, detection branches, widget,
loc, icons) is pinned by test_covert_op_registry.py. This file pins what each
new operation does: its gates, its modifiers, regime change's coup push,
cultivate assets' network and Tradecraft hooks and its fixed priority, and
the console harness.

Run: python3 -m unittest test_covert_new_ops -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
STATIC = ROOT / "common/static_modifiers/extra_modifiers.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_covert_events.txt"
LOC_DIR = ROOT / "localization/english"


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry (see test_covert_op_registry)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _loc():
    out = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        if path.name.startswith("te_unused"):
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^ ([A-Za-z0-9_.]+):\d* (.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def _section(block, header):
    """The `header = { ... }` sub-block of an action, by brace counting."""
    start = block.index(header)
    depth = 0
    for i in range(start, len(block)):
        if block[i] == "{":
            depth += 1
        elif block[i] == "}":
            depth -= 1
            if depth == 0:
                return block[start: i + 1]
    raise AssertionError("unbalanced %s" % header)


def _requirements(block):
    """Every requirement_to_maintain body of an action, concatenated. The
    leading tab keeps "pact = {" from matching inside has_diplomatic_pact."""
    pact = _section(block, "\tpact = {")
    parts = []
    at = 0
    while True:
        at = pact.find("requirement_to_maintain = {", at)
        if at == -1:
            return "".join(parts)
        parts.append(_section(pact[at:], "requirement_to_maintain = {"))
        at += 1


class ConstantTests(unittest.TestCase):
    def test_slice_6_constants(self):
        body = _text(VALUES)
        for name, value in (
            ("covert_regime_change_coup_push", "5"),
            ("covert_net_cultivate_mult", "1.5"),
            ("covert_cultivate_ai_net_ceiling", "50"),
        ):
            self.assertRegex(body, r"(?m)^%s = %s$" % (name, re.escape(value)))

    def test_shared_gate_tooltips_exist(self):
        loc = _loc()
        for key in ("iw_requires_rivalry_tt", "iw_target_not_our_subject_tt",
                    "iw_severe_ops_need_tradecraft_tt"):
            self.assertIn(key, loc)
        self.assertIn("covert_tradecraft_tier_3_floor", loc["iw_severe_ops_need_tradecraft_tt"])


class RegimeChangeTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_regime_change_action = {")

    def test_launch_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("has_diplomatic_pact = { who = scope:target_country type = rivalry }", possible)
        self.assertIn("NOT = { scope:target_country = { is_subject_of = ROOT } }", possible)
        self.assertIn("covert_tradecraft_unlocks_severe_ops = yes", possible)

    def test_severe_gate_is_launch_only(self):
        # Existing operations are never gated: a falling score must not end one.
        reqs = _requirements(self.block)
        self.assertNotIn("covert_tradecraft", reqs)
        self.assertIn("has_diplomatic_pact = { who = scope:target_country type = rivalry }", reqs)

    def test_ai_wants_a_hostile_rival(self):
        will = _section(self.block, "will_propose = {")
        self.assertIn("type = rivalry", will)
        self.assertIn("attitude = antagonistic", will)
        self.assertIn("attitude = domineering", will)

    def test_modifier_values(self):
        block = _top_level_block(_text(STATIC), "covert_regime_change = {")
        self.assertIn("country_coup_resistance_add = -1", block)
        self.assertIn("country_legitimacy_base_add = -5", block)
        self.assertIn("political_movement_radicalism_add = 0.05", block)

    def test_coup_push_is_fully_operational_null_safe_and_not_dlc_gated(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        start = block.index("has_tag = iw_op_regime_change")
        branch = block[start: block.index("covert_refresh_priority_cost = yes", start)]
        self.assertIn("covert_op_is_fully_operational = yes", branch)
        self.assertIn("je:je_ip4_coup ?= {", branch)
        self.assertIn(
            "add_progress = { value = covert_regime_change_coup_push name = je_ip4_coup_progress_bar }",
            branch,
        )
        self.assertNotIn("has_dlc_feature", block)

    def test_script_only_coup_resistance_is_named_in_the_description(self):
        # country_coup_resistance_add is script_only: the modifier tooltip
        # never lists it, so the description has to.
        self.assertIn("coup", _loc()["covert_regime_change_desc"].lower())


if __name__ == "__main__":
    unittest.main()
```

Run: `python3 -m unittest test_covert_new_ops`
Expected: FAIL (`ValueError: substring not found` in `setUp`, missing constants and loc).

- [ ] **Step 3: Section-1 constants**

In `common/script_values/covert_warfare_script_values.txt`, directly after the line `covert_tradecraft_net_gain_per_tier = 0.15` (the last Section-1 constant, just before `# SECTION 2: INTELLIGENCE CAPACITY`'s banner), insert:

```
# ---- New operations (slice 6) ----
# Regime change: once fully operational, a monthly push on any coup already
# under way in the target (je_ip4_coup's bar runs 10 -> 120 and moves weekly
# by commander strength minus coup resistance). Vanilla's coup events nudge it
# by 15; this is a steady third of that. Most of the operation's pull on a
# coup comes through coup resistance, not this push (plan table:
# docs/superpowers/plans/2026-09-23-covert-new-operations.md).
covert_regime_change_coup_push = 5
# Cultivate assets: a network with one running against its target grows this
# much faster. Stacks with the extra-operation factor and with Tradecraft.
# Alone against a target: strength 50 in ~17 months (25 for any other
# operation), 75 in ~28 (42).
covert_net_cultivate_mult = 1.5
# The AI proposes cultivate assets only where its network is weaker than this.
covert_cultivate_ai_net_ceiling = 50
```

- [ ] **Step 4: Static modifier**

In `common/static_modifiers/extra_modifiers.txt`, directly after the block

```
covert_military_espionage_detected = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds
	country_authority_add = -3
}
```

insert (keep one blank line before and after):

```
# Applied to TARGET while a regime-change operation runs (covert slice 6),
# scaled by phase x priority. country_coup_resistance_add is script_only, so
# it does not render in the modifier tooltip; covert_regime_change_desc names
# it instead.
covert_regime_change = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	country_coup_resistance_add = -1
	country_legitimacy_base_add = -5
	political_movement_radicalism_add = 0.05
}
```

- [ ] **Step 5: The diplomatic action**

Append to the end of `common/diplomatic_actions/covert_operations.txt` (after destabilization's closing `}`; one blank line between):

```
# ---- PEACETIME: Regime Change (slice 6) ----
# Bankroll the colonels: erode a rival government's legitimacy and its
# resistance to a coup, radicalise its movements, and once fully operational
# push any coup already under way. Severe tier. Needs a Seasoned agency to
# launch; a running operation is never ended by the score falling.
covert_regime_change_action = {
	groups = {
		general
	}
	requires_approval = no
	show_confirmation_box = yes
	show_effect_in_tooltip = yes
	is_hostile = yes
	should_notify_third_parties = no

	accept_effect = {
		custom_tooltip = {
			text = covert_regime_change_extra_tt
		}
		custom_tooltip = {
			text = covert_op_phase_warning_tt
		}
		custom_tooltip = {
			text = covert_op_detection_warning_tt
		}
		covert_op_start = { TYPE = regime_change DEFENSE_MOD = country_covert_defense_ideological_add CODE = 9 }
	}

	potential = {
		has_game_rule = covert_warfare_enabled
	}

	possible = {
		custom_tooltip = {
			text = covert_op_capacity_regime_change_tt
			covert_ops_type_below_cap = { TYPE = covert_regime_change_action }
		}
		custom_tooltip = {
			text = iw_has_available_slot_tt
			covert_operations_available_slots >= 1
		}
		custom_tooltip = {
			text = iw_no_duplicate_target_tt
			NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_regime_change_action } }
		}
		custom_tooltip = {
			text = iw_target_not_decentralized_tt
			scope:target_country = { covert_action_valid_target = yes }
		}
		custom_tooltip = {
			text = iw_no_truce_tt
			NOT = { has_truce_with = scope:target_country }
		}
		# Allowed during war: no has_war guard
		custom_tooltip = {
			text = iw_no_intel_sharing_tt
			NOT = {
				any_scope_treaty = {
					binds = scope:target_country
					any_scope_article = { has_type = intelligence_sharing_pact }
				}
			}
		}
		custom_tooltip = {
			text = iw_requires_rivalry_tt
			has_diplomatic_pact = { who = scope:target_country type = rivalry }
		}
		custom_tooltip = {
			text = iw_target_not_our_subject_tt
			NOT = { scope:target_country = { is_subject_of = ROOT } }
		}
		custom_tooltip = {
			text = iw_severe_ops_need_tradecraft_tt
			covert_tradecraft_unlocks_severe_ops = yes
		}
		custom_tooltip = {
			text = iw_funding_not_zero_tt
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
		}
	}

	pact = {
		cost = 0
		is_two_sided_pact = no
		show_in_outliner = yes

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_funding_not_zero_tt
					has_variable = iw_funding_level
					var:iw_funding_level >= 1
				}
			}
		}

		# The Tradecraft gate is launch-only: a running operation survives the
		# agency's score falling below Seasoned.
		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_requires_rivalry_tt
					has_diplomatic_pact = { who = scope:target_country type = rivalry }
				}
			}
		}

		# Allowed during war: do not auto-break when war starts

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_no_truce_tt
					NOT = { has_truce_with = scope:target_country }
				}
			}
		}
		manual_break_effect = { covert_op_end = { TYPE = regime_change } }
		auto_break_effect = { covert_op_end = { TYPE = regime_change } }
	}

	ai = {
		evaluation_chance = {
			value = 0.02
			if = {
				limit = { ruler_is_aggressive = yes }
				add = 0.03
			}
			if = {
				limit = { ruler_is_cautious = yes }
				multiply = 0.25
			}
		}

		will_propose = {
			has_diplomatic_pact = { who = scope:target_country type = rivalry }
			OR = {
				has_attitude = { who = scope:target_country attitude = antagonistic }
				has_attitude = { who = scope:target_country attitude = domineering }
			}
			covert_operations_available_slots >= 1
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
			in_default = no
			country_rank >= rank_value:major_power
		}

		propose_score = {
			value = 5
			if = {
				limit = { country_rank >= rank_value:great_power }
				add = 5
			}
			if = {
				limit = { ruler_is_aggressive = yes }
				add = 8
			}
		}
	}
}
```

- [ ] **Step 6: Plumbing — sync row, pact identity, tier, detection branches, defender trigger**

`common/scripted_effects/covert_warfare_effects.txt`, `covert_ops_sync_all`: after the `CODE = 8` destabilization row insert

```
	covert_op_sync = { TYPE = regime_change ACTION = covert_regime_change_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 9 }
```

`common/scripted_triggers/covert_warfare_triggers.txt`, `is_covert_operation_pact`: after `is_diplomatic_action_type = covert_destabilization_action` insert

```
		is_diplomatic_action_type = covert_regime_change_action
```

Same file, `covert_code_tier_severe`: after `var:$VAR$ = 8` insert

```
		var:$VAR$ = 9
```

`events/covert_warfare_events.txt`, `covert_warfare.1` `after`: after the `var:iw_burned_type_code = 8` branch (the one ending `CODE = 8 }` then `}`) insert

```
			else_if = {
				limit = { var:iw_burned_type_code = 9 }
				covert_op_burn = { TYPE = regime_change ACTION = covert_regime_change_action TARGET = scope:detected_by_country CODE = 9 }
			}
```

Same file, `covert_warfare.2` `trigger`: after `has_modifier = covert_military_espionage_detected` insert

```
			has_modifier = covert_regime_change
```

- [ ] **Step 7: Plumbing — custom loc, stand-down handler, widget**

`common/customizable_localization/covert_warfare_custom_loc.txt`: in `covert_last_exposed_type_name`, after the `var:iw_last_exposed_type = 8` text block and before the fallback `text = { localization_key = iw_op_name_unknown }`, insert

```
	text = {
		trigger = { var:iw_last_exposed_type = 9 }
		localization_key = iw_op_name_regime_change
	}
```

and in `covert_burned_type_name`, at the same place, insert

```
	text = {
		trigger = { var:iw_burned_type_code = 9 }
		localization_key = iw_op_name_regime_change
	}
```

`common/scripted_guis/covert_warfare_sguis.txt`: after the closing `}` of `covert_stand_down_destabilization_sgui` (before `# ---- PRIORITY: the row stepper`), insert (blank line before):

```
covert_stand_down_regime_change_sgui = {
	scope = country
	saved_scopes = { iw_tgt }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_stand_down = { TYPE = regime_change }
	}

	effect = {
		covert_effect_stand_down = { TYPE = regime_change ACTION = covert_regime_change_action }
	}

	ai_is_valid = {
		always = no
	}
}
```

`gui/journal_entry_widgets/covert_operations_widget.gui`: after the row line block

```
		widget_je_covert_operation_text = {
			visible = "[ScriptContainer.HasTag('iw_op_destabilization')]"
			text = "je_iw_op_row_destabilization"
		}
```

insert

```
		widget_je_covert_operation_text = {
			visible = "[ScriptContainer.HasTag('iw_op_regime_change')]"
			text = "je_iw_op_row_regime_change"
		}
```

and after the destabilization stand-down instance (the `covert_op_stand_down_button` block naming `covert_stand_down_destabilization_sgui`) insert

```
		covert_op_stand_down_button = {
			blockoverride "sd_context" {
				datacontext = "[GetScriptedGui('covert_stand_down_regime_change_sgui')]"
			}
			blockoverride "sd_visible" {
				visible = "[ScriptContainer.HasTag('iw_op_regime_change')]"
			}
		}
```

- [ ] **Step 8: The effect**

`common/scripted_effects/covert_warfare_effects.txt`, `covert_ops_apply_all_phase_effects`: after the destabilization `every_in_list = { … }` block and before `# The applied-priority snapshot just moved: recharge upkeep from it.`, insert

```
		# ---- Regime Change (slice 6): country modifier on TARGET; once fully
		#      operational, a monthly push on any coup already under way there.
		#      Coups are base game (only vanilla's orchestrate_coup action is
		#      DLC-gated), and ?= makes the push a no-op when none is running.
		covert_op_apply_target_effect = { TYPE = regime_change MODIFIER = covert_regime_change }
		every_in_list = {
			variable = iw_ops
			limit = {
				has_tag = iw_op_regime_change
				covert_op_is_fully_operational = yes
			}
			var:iw_target ?= {
				je:je_ip4_coup ?= {
					add_progress = { value = covert_regime_change_coup_push name = je_ip4_coup_progress_bar }
				}
			}
		}
```

- [ ] **Step 9: Loc**

`localization/english/te_miscellaneous_l_english.yml` — add beside the other `covert_*` / `iw_*` keys (organize_loc re-sorts later; leading space, `:0`):

```yaml
 covert_regime_change_action:0 "Covert: Regime Change"
 covert_regime_change_action_desc:0 "Bankroll a rival's disaffected officers and opposition. Erodes the target government's [concept_legitimacy] and its resistance to a coup, and radicalises its [Concept('concept_political_movement', 'political movements')]; once fully operational, any coup already under way there is pushed forward every month. Requires a [concept_rivalry] and an agency of at least #bold Seasoned#! Tradecraft.$iw_exposure_tier_severe_note$"
 covert_regime_change_action_action_propose_name:0 "Launch Regime Change"
 covert_regime_change_action_action_break_name:0 "Cancel Regime Change"
 covert_regime_change_action_action_notification_name:0 "Regime Change Launched"
 covert_regime_change_action_action_notification_break_name:0 "Regime Change Cancelled"
 covert_regime_change_action_action_notification_desc:0 "[INITIATOR_COUNTRY.GetName] has launched a regime-change operation."
 covert_regime_change_action_action_notification_break_desc:0 "[INITIATOR_COUNTRY.GetName] has discontinued their regime-change operation."
 covert_regime_change_extra_tt:0 "Erodes the target's [concept_legitimacy] and coup resistance and radicalises its [Concept('concept_political_movement', 'political movements')]; once fully operational, pushes any coup under way there forward every month."
 covert_op_capacity_regime_change_tt:0 "No regime change slots available — reduce active regime change operations or increase covert capacity."
 iw_op_name_regime_change:0 "Regime Change"
 covert_regime_change:0 "Foreign-Backed Regime Change"
 covert_regime_change_desc:0 "Foreign money is reaching our officers and our opposition. Our government's [concept_legitimacy] is eroding, and a coup against it is easier to mount: this also lowers our coup resistance, which is not listed among the effects above — by 1 at the operation's base strength, and by up to 3.2 at its strongest."
 iw_requires_rivalry_tt:0 "Must have declared a [concept_rivalry] with them"
 iw_target_not_our_subject_tt:0 "Cannot target our own subjects"
 iw_severe_ops_need_tradecraft_tt:0 "Needs an agency of at least #bold Seasoned#! Tradecraft (#v [GetPlayer.MakeScope.ScriptValue('covert_tradecraft_tier_3_floor')|0]#!)"
```

`localization/english/te_journal_entries_l_english.yml`, beside the other `je_iw_op_row_*` keys:

```yaml
 je_iw_op_row_regime_change:0 "• #R Regime Change#! vs [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]"
```

`localization/english/te_diplomacy_l_english.yml`, beside the other `covert_*_action_pact_desc` keys:

```yaml
 covert_regime_change_action_pact_desc:0 "We are bankrolling a change of government in [SCOPE.GetRootScope.GetDiplomaticPact.GetSecondCountry.GetName]."
```

`localization/english/te_modifiers_l_english.yml`: change `country_covert_defense_ideological_add_desc` to

```yaml
 country_covert_defense_ideological_add_desc:0 "Additional defense against ideological [concept_covert_operations] such as election interference, influence campaigns, ideological subversion, destabilization and regime change."
```

- [ ] **Step 10: Icon**

```bash
cd /home/jakef/src/Vic3TimelineExtended
cp gfx/interface/icons/lens_toolbar_icons/covert_destabilization_action.dds gfx/interface/icons/lens_toolbar_icons/covert_regime_change_action.dds
```

- [ ] **Step 11: Green, format, BOM**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry test_covert_new_ops test_covert_detection_roll test_covert_exposure_tiers test_covert_stand_down`
Expected: all pass.

```bash
cd /home/jakef/src/Vic3TimelineExtended
F="common/script_values/covert_warfare_script_values.txt common/static_modifiers/extra_modifiers.txt common/diplomatic_actions/covert_operations.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui"
python3 scripts/format_paradox_tabs.py $(echo "$F")
for f in $(echo "$F"); do printf '%s ' $f; head -c3 $f | xxd -p; done
```

(`$(echo "$F")` word-splits in both zsh and bash; a bare `$F` does not in zsh.) Expected: every file prints `efbbbf`.

- [ ] **Step 12: Commit**

```bash
cd /home/jakef/src/Vic3TimelineExtended
git add test_covert_op_registry.py test_covert_new_ops.py $(echo "$F") localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml localization/english/te_diplomacy_l_english.yml localization/english/te_modifiers_l_english.yml gfx/interface/icons/lens_toolbar_icons/covert_regime_change_action.dds
git commit -m "feat(covert): regime change operation (slice 6, code 9)

A severe-tier operation against a rival: erodes legitimacy (-5) and coup
resistance (-1), radicalises movements (+5%), all scaled by phase x
priority, and once fully operational pushes any coup already under way by 5
a month. Launching needs a rivalry, a non-subject target and a Seasoned
agency; a running operation survives the score falling. No DLC gate: coups
are base game, and je:je_ip4_coup ?= makes the push a no-op without one.

Also adds the slice's Section-1 constants and shared gate tooltips.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

(Define `F` again in the same shell as the `git add` if the steps run in separate shells.)

---

### Task 3: Nuclear programme sabotage (code 10, severe)

**Files:**
- Modify: `test_covert_op_registry.py` (one `OPS` row), `test_covert_new_ops.py` (one class)
- Modify: `common/scripted_triggers/nuke_triggers.txt`
- Modify: `common/static_modifiers/extra_modifiers.txt`
- Modify: `common/diplomatic_actions/covert_operations.txt` (append)
- Modify: `common/scripted_effects/covert_warfare_effects.txt`, `common/scripted_triggers/covert_warfare_triggers.txt`, `events/covert_warfare_events.txt`, `common/customizable_localization/covert_warfare_custom_loc.txt`, `common/scripted_guis/covert_warfare_sguis.txt`, `gui/journal_entry_widgets/covert_operations_widget.gui`
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_journal_entries_l_english.yml`, `te_diplomacy_l_english.yml`, `te_modifiers_l_english.yml`
- Create: `gfx/interface/icons/lens_toolbar_icons/covert_nuclear_sabotage_action.dds`

**Interfaces:**
- Consumes: `iw_severe_ops_need_tradecraft_tt` (Task 2), `covert_tradecraft_unlocks_severe_ops` (slice 5), `covert_op_mult_p3_pri3` (slice 3).
- Produces: scripted trigger `nuclear_program_is_proliferating` (country scope; Task 6's harness uses it).

- [ ] **Step 1: Registry row (red)**

Append to `OPS` in `test_covert_op_registry.py`:

```python
    ("nuclear_sabotage", 10, "military", "severe", "covert_nuclear_sabotage"),
```

Run: `python3 -m unittest test_covert_op_registry` — Expected: the same fifteen site tests fail as in Task 2 Step 1, now for `nuclear_sabotage`.

- [ ] **Step 2: Behaviour tests (red)**

Add to `test_covert_new_ops.py`, before `if __name__ == "__main__":`:

```python
class NuclearSabotageTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_nuclear_sabotage_action = {")

    def test_proliferating_trigger(self):
        block = _top_level_block(_text(NUKE_TRIGGERS), "nuclear_program_is_proliferating = {")
        self.assertIn("has_variable = nuclear_weapon_program_progress", block)
        self.assertIn("has_variable = nuclear_weapons_program_funding", block)
        self.assertIn("var:nuclear_weapons_program_funding >= 1", block)
        self.assertIn("modifier:country_nuclear_program_pause_bool = yes", block)
        self.assertIn("modifier:country_nuclear_disarmament_bool = yes", block)

    def test_launch_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("scope:target_country = { nuclear_program_is_proliferating = yes }", possible)
        self.assertIn("covert_tradecraft_unlocks_severe_ops = yes", possible)

    def test_severe_gate_is_launch_only(self):
        reqs = _requirements(self.block)
        self.assertNotIn("covert_tradecraft", reqs)
        self.assertIn("nuclear_program_is_proliferating = yes", reqs)

    def test_ai_values_a_programme_near_completion(self):
        score = _section(self.block, "propose_score = {")
        self.assertIn("var:nuclear_weapon_program_progress >= 75", score)
        self.assertIn("has_variable = nuclear_weapon_program_progress", score)

    def test_nuclear_sabotage_never_stops_progress(self):
        # je_nuclear_program multiplies progress by (1 + mult); at the largest
        # phase x priority multiplier the operation must leave it positive.
        static = _top_level_block(_text(STATIC), "covert_nuclear_sabotage = {")
        mult = float(re.search(r"country_nuclear_program_progress_mult = (-?[\d.]+)", static).group(1))
        self.assertEqual(mult, -0.25)
        values = _text(VALUES)
        pri3 = float(re.search(r"(?m)^covert_op_priority_3_effect_mult = ([\d.]+)$", values).group(1))
        full = float(re.search(r"(?m)^covert_op_phase_full_mult = ([\d.]+)$", values).group(1))
        self.assertGreater(1 + mult * pri3 * full, 0)
```

Run: `python3 -m unittest test_covert_new_ops` — Expected: FAIL in `NuclearSabotageTests`.

- [ ] **Step 3: The proliferation trigger**

In `common/scripted_triggers/nuke_triggers.txt`, directly after the closing `}` of `nuclear_program_possible_decrease_funding` (and before the `# Country scope: True if scope:country has existential war goals…` comment), insert (blank line before and after):

```
# Country scope: is this country's nuclear weapons programme funded and
# running? A nuclear power building its stockpile qualifies too. The gate on
# covert_nuclear_sabotage_action (covert slice 6), whose modifier slows exactly
# this progress. Same test the programme's own display values use
# (nuclear_program_display_months_to_next, extra_script_values.txt).
nuclear_program_is_proliferating = {
	has_variable = nuclear_weapon_program_progress
	has_variable = nuclear_weapons_program_funding
	var:nuclear_weapons_program_funding >= 1
	NOT = { modifier:country_nuclear_program_pause_bool = yes }
	NOT = { modifier:country_nuclear_disarmament_bool = yes }
}
```

- [ ] **Step 4: Static modifier**

In `common/static_modifiers/extra_modifiers.txt`, directly after the `covert_regime_change` block (Task 2), insert (blank line before):

```
# Applied to TARGET while a nuclear-programme sabotage operation runs (covert
# slice 6), scaled by phase x priority. je_nuclear_program multiplies progress
# by (1 + this): x0.75 at base strength, x0.2 at the strongest operation
# (fully operational, priority 3), never zero.
covert_nuclear_sabotage = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds
	country_nuclear_program_progress_mult = -0.25
}
```

- [ ] **Step 5: The diplomatic action**

Append to `common/diplomatic_actions/covert_operations.txt` (blank line before):

```
# ---- PEACETIME: Nuclear Programme Sabotage (slice 6) ----
# Infiltrate a foreign nuclear weapons programme and slow it: faulty parts,
# failed centrifuges, missing scientists. Severe tier. Needs a Seasoned agency
# to launch; lapses when the target's programme stops.
covert_nuclear_sabotage_action = {
	groups = {
		general
	}
	requires_approval = no
	show_confirmation_box = yes
	show_effect_in_tooltip = yes
	is_hostile = yes
	should_notify_third_parties = no

	accept_effect = {
		custom_tooltip = {
			text = covert_nuclear_sabotage_extra_tt
		}
		custom_tooltip = {
			text = covert_op_phase_warning_tt
		}
		custom_tooltip = {
			text = covert_op_detection_warning_tt
		}
		covert_op_start = { TYPE = nuclear_sabotage DEFENSE_MOD = country_covert_defense_military_add CODE = 10 }
	}

	potential = {
		has_game_rule = covert_warfare_enabled
	}

	possible = {
		custom_tooltip = {
			text = covert_op_capacity_nuclear_sabotage_tt
			covert_ops_type_below_cap = { TYPE = covert_nuclear_sabotage_action }
		}
		custom_tooltip = {
			text = iw_has_available_slot_tt
			covert_operations_available_slots >= 1
		}
		custom_tooltip = {
			text = iw_no_duplicate_target_tt
			NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_nuclear_sabotage_action } }
		}
		custom_tooltip = {
			text = iw_target_not_decentralized_tt
			scope:target_country = { covert_action_valid_target = yes }
		}
		custom_tooltip = {
			text = iw_no_truce_tt
			NOT = { has_truce_with = scope:target_country }
		}
		# Allowed during war: no has_war guard
		custom_tooltip = {
			text = iw_no_intel_sharing_tt
			NOT = {
				any_scope_treaty = {
					binds = scope:target_country
					any_scope_article = { has_type = intelligence_sharing_pact }
				}
			}
		}
		custom_tooltip = {
			text = iw_target_nuclear_programme_tt
			scope:target_country = { nuclear_program_is_proliferating = yes }
		}
		custom_tooltip = {
			text = iw_severe_ops_need_tradecraft_tt
			covert_tradecraft_unlocks_severe_ops = yes
		}
		custom_tooltip = {
			text = iw_funding_not_zero_tt
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
		}
	}

	pact = {
		cost = 0
		is_two_sided_pact = no
		show_in_outliner = yes

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_funding_not_zero_tt
					has_variable = iw_funding_level
					var:iw_funding_level >= 1
				}
			}
		}

		# The Tradecraft gate is launch-only: a running operation survives the
		# agency's score falling below Seasoned.
		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_target_nuclear_programme_tt
					scope:target_country = { nuclear_program_is_proliferating = yes }
				}
			}
		}

		# Allowed during war: do not auto-break when war starts

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_no_truce_tt
					NOT = { has_truce_with = scope:target_country }
				}
			}
		}
		manual_break_effect = { covert_op_end = { TYPE = nuclear_sabotage } }
		auto_break_effect = { covert_op_end = { TYPE = nuclear_sabotage } }
	}

	ai = {
		evaluation_chance = {
			value = 0.02
			if = {
				limit = { ruler_is_aggressive = yes }
				add = 0.03
			}
			if = {
				limit = { ruler_is_cautious = yes }
				multiply = 0.25
			}
		}

		will_propose = {
			scope:target_country = { nuclear_program_is_proliferating = yes }
			OR = {
				has_modifier = nuclear_power
				country_rank >= rank_value:great_power
			}
			OR = {
				has_diplomatic_pact = { who = scope:target_country type = rivalry }
				has_attitude = { who = scope:target_country attitude = antagonistic }
			}
			covert_operations_available_slots >= 1
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
			in_default = no
		}

		propose_score = {
			value = 5
			if = {
				limit = {
					scope:target_country = {
						has_variable = nuclear_weapon_program_progress
						var:nuclear_weapon_program_progress >= 75
					}
				}
				add = 10
			}
			if = {
				limit = { country_rank >= rank_value:great_power }
				add = 5
			}
		}
	}
}
```

- [ ] **Step 6: Plumbing (same sites as Task 2, code 10)**

`covert_warfare_effects.txt` `covert_ops_sync_all`, after the `CODE = 9` row:

```
	covert_op_sync = { TYPE = nuclear_sabotage ACTION = covert_nuclear_sabotage_action DEFENSE_MOD = country_covert_defense_military_add CODE = 10 }
```

`covert_warfare_triggers.txt` `is_covert_operation_pact`, after the regime-change line:

```
		is_diplomatic_action_type = covert_nuclear_sabotage_action
```

`covert_code_tier_severe`, after `var:$VAR$ = 9`:

```
		var:$VAR$ = 10
```

`covert_warfare.1` `after`, after the code-9 branch:

```
			else_if = {
				limit = { var:iw_burned_type_code = 10 }
				covert_op_burn = { TYPE = nuclear_sabotage ACTION = covert_nuclear_sabotage_action TARGET = scope:detected_by_country CODE = 10 }
			}
```

`covert_warfare.2` `trigger`, after `has_modifier = covert_regime_change`:

```
			has_modifier = covert_nuclear_sabotage
```

`covert_last_exposed_type_name`, after the code-9 text block:

```
	text = {
		trigger = { var:iw_last_exposed_type = 10 }
		localization_key = iw_op_name_nuclear_sabotage
	}
```

`covert_burned_type_name`, after the code-9 text block:

```
	text = {
		trigger = { var:iw_burned_type_code = 10 }
		localization_key = iw_op_name_nuclear_sabotage
	}
```

`covert_warfare_sguis.txt`, after `covert_stand_down_regime_change_sgui` (blank line before):

```
covert_stand_down_nuclear_sabotage_sgui = {
	scope = country
	saved_scopes = { iw_tgt }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_stand_down = { TYPE = nuclear_sabotage }
	}

	effect = {
		covert_effect_stand_down = { TYPE = nuclear_sabotage ACTION = covert_nuclear_sabotage_action }
	}

	ai_is_valid = {
		always = no
	}
}
```

Widget, after the regime-change row line:

```
		widget_je_covert_operation_text = {
			visible = "[ScriptContainer.HasTag('iw_op_nuclear_sabotage')]"
			text = "je_iw_op_row_nuclear_sabotage"
		}
```

Widget, after the regime-change stand-down instance:

```
		covert_op_stand_down_button = {
			blockoverride "sd_context" {
				datacontext = "[GetScriptedGui('covert_stand_down_nuclear_sabotage_sgui')]"
			}
			blockoverride "sd_visible" {
				visible = "[ScriptContainer.HasTag('iw_op_nuclear_sabotage')]"
			}
		}
```

- [ ] **Step 7: The effect**

`covert_ops_apply_all_phase_effects`, after the regime-change block (Task 2) and before the `covert_refresh_priority_cost = yes` recharge comment:

```
		# ---- Nuclear Programme Sabotage (slice 6): country modifier on TARGET ----
		covert_op_apply_target_effect = { TYPE = nuclear_sabotage MODIFIER = covert_nuclear_sabotage }
```

- [ ] **Step 8: Loc**

`te_miscellaneous_l_english.yml`:

```yaml
 covert_nuclear_sabotage_action:0 "Covert: Nuclear Programme Sabotage"
 covert_nuclear_sabotage_action_desc:0 "Infiltrate a foreign nuclear weapons programme and quietly sabotage it — faulty parts, failed centrifuges, scientists who stop coming to work — slowing its progress towards the bomb, or towards its next warhead. Requires the target to be running a funded programme and an agency of at least #bold Seasoned#! Tradecraft.$iw_exposure_tier_severe_note$"
 covert_nuclear_sabotage_action_action_propose_name:0 "Launch Nuclear Sabotage"
 covert_nuclear_sabotage_action_action_break_name:0 "Cancel Nuclear Sabotage"
 covert_nuclear_sabotage_action_action_notification_name:0 "Nuclear Sabotage Launched"
 covert_nuclear_sabotage_action_action_notification_break_name:0 "Nuclear Sabotage Cancelled"
 covert_nuclear_sabotage_action_action_notification_desc:0 "[INITIATOR_COUNTRY.GetName] has launched a nuclear-programme sabotage operation."
 covert_nuclear_sabotage_action_action_notification_break_desc:0 "[INITIATOR_COUNTRY.GetName] has discontinued their nuclear-programme sabotage operation."
 covert_nuclear_sabotage_extra_tt:0 "Slows the target's nuclear weapons programme."
 covert_op_capacity_nuclear_sabotage_tt:0 "No nuclear sabotage slots available — reduce active nuclear sabotage operations or increase covert capacity."
 iw_op_name_nuclear_sabotage:0 "Nuclear Programme Sabotage"
 iw_target_nuclear_programme_tt:0 "Target must be running a funded nuclear weapons programme"
 covert_nuclear_sabotage:0 "Nuclear Programme Sabotage"
 covert_nuclear_sabotage_desc:0 "Centrifuges fail, parts arrive faulty and scientists disappear. Our nuclear weapons programme is progressing more slowly than it should."
```

`te_journal_entries_l_english.yml`:

```yaml
 je_iw_op_row_nuclear_sabotage:0 "• #R Nuclear Sabotage#! vs [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]"
```

`te_diplomacy_l_english.yml`:

```yaml
 covert_nuclear_sabotage_action_pact_desc:0 "We are sabotaging the nuclear weapons programme of [SCOPE.GetRootScope.GetDiplomaticPact.GetSecondCountry.GetName]."
```

`te_modifiers_l_english.yml`: change `country_covert_defense_military_add_desc` to (military espionage was missing too):

```yaml
 country_covert_defense_military_add_desc:0 "Additional defense against military [concept_covert_operations] such as military espionage, communications disruption, [concept_infrastructure] sabotage and nuclear programme sabotage."
```

- [ ] **Step 9: Icon**

```bash
cd /home/jakef/src/Vic3TimelineExtended
cp gfx/interface/icons/lens_toolbar_icons/covert_infrastructure_sabotage_action.dds gfx/interface/icons/lens_toolbar_icons/covert_nuclear_sabotage_action.dds
```

- [ ] **Step 10: Green, format, BOM, commit**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry test_covert_new_ops test_covert_detection_roll test_covert_exposure_tiers test_covert_stand_down` — Expected: all pass.

```bash
cd /home/jakef/src/Vic3TimelineExtended
F="common/scripted_triggers/nuke_triggers.txt common/static_modifiers/extra_modifiers.txt common/diplomatic_actions/covert_operations.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui"
python3 scripts/format_paradox_tabs.py $(echo "$F")
for f in $(echo "$F"); do printf '%s ' $f; head -c3 $f | xxd -p; done
git add test_covert_op_registry.py test_covert_new_ops.py $(echo "$F") localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml localization/english/te_diplomacy_l_english.yml localization/english/te_modifiers_l_english.yml gfx/interface/icons/lens_toolbar_icons/covert_nuclear_sabotage_action.dds
git commit -m "feat(covert): nuclear programme sabotage operation (slice 6, code 10)

A severe-tier operation against a country whose nuclear weapons programme is
funded and running (new trigger nuclear_program_is_proliferating, which a
stockpiling nuclear power also meets): programme progress x(1 - 0.25 x phase
x priority), from x0.75 down to x0.2, never zero. Launching needs a Seasoned
agency; the operation lapses when the programme stops, not when the score
falls. The AI values a target at 75% or more.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

---

### Task 4: Space programme espionage (code 11, mild)

**Files:**
- Modify: `test_covert_op_registry.py`, `test_covert_new_ops.py`
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (new predicates + plumbing)
- Modify: `common/static_modifiers/extra_modifiers.txt`
- Modify: `common/diplomatic_actions/covert_operations.txt` (append)
- Modify: `common/scripted_effects/covert_warfare_effects.txt`, `events/covert_warfare_events.txt`, `common/customizable_localization/covert_warfare_custom_loc.txt`, `common/scripted_guis/covert_warfare_sguis.txt`, `gui/journal_entry_widgets/covert_operations_widget.gui`
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_journal_entries_l_english.yml`, `te_diplomacy_l_english.yml`, `te_modifiers_l_english.yml`
- Create: `gfx/interface/icons/lens_toolbar_icons/covert_space_espionage_action.dds`

**Interfaces:**
- Consumes: `sr_is_pursuing_milestone` (`space_race_triggers.txt`), `covert_op_apply_self_effect` / `covert_op_apply_target_effect`.
- Produces: scripted trigger `covert_target_ahead_in_space = { TARGET = <country> }` (scope: the operator; Task 6's harness calls it with `TARGET = PREV`).

- [ ] **Step 1: Registry row (red)**

Append to `OPS`:

```python
    ("space_espionage", 11, "economic", "mild", "covert_space_espionage_detected"),
```

Run: `python3 -m unittest test_covert_op_registry` — Expected: the fifteen site tests fail for `space_espionage`.

- [ ] **Step 2: Behaviour tests (red)**

Add to `test_covert_new_ops.py`:

```python
MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base",
              "mars_landing", "interstellar_probe", "solar_colonization")


class SpaceEspionageTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_space_espionage_action = {")

    def test_ahead_in_space_covers_every_milestone(self):
        body = _text(TRIGGERS)
        block = _top_level_block(body, "covert_target_ahead_in_space = {")
        for m in MILESTONES:
            self.assertIn("covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = %s }" % m, block)
        helper = _top_level_block(body, "covert_target_ahead_in_space_on = {")
        self.assertIn("$TARGET$ = { has_variable = sr_completed_$MILESTONE$ }", helper)
        self.assertIn("NOT = { has_variable = sr_completed_$MILESTONE$ }", helper)

    def test_gates_use_the_space_gap(self):
        gate = "covert_target_ahead_in_space = { TARGET = scope:target_country }"
        self.assertIn(gate, _section(self.block, "possible = {"))
        self.assertIn(gate, _requirements(self.block))
        will = _section(self.block, "will_propose = {")
        self.assertIn(gate, will)
        self.assertIn("sr_is_pursuing_milestone = yes", will)

    def test_modifiers(self):
        static = _text(STATIC)
        own = _top_level_block(static, "covert_space_espionage = {")
        self.assertIn("country_space_race_progress_mult = 0.10", own)
        self.assertIn("country_space_race_risk_mult = -0.10", own)
        marker = _top_level_block(static, "covert_space_espionage_detected = {")
        self.assertIn("country_authority_add = -3", marker)

    def test_self_effect_from_the_strongest_operation(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        self.assertIn("covert_op_apply_self_effect = { TYPE = space_espionage MODIFIER = covert_space_espionage }", block)
```

Run: `python3 -m unittest test_covert_new_ops` — Expected: FAIL in `SpaceEspionageTests`.

- [ ] **Step 3: The space-gap predicates**

Append to the end of `common/scripted_triggers/covert_warfare_triggers.txt` (blank line before):

```
# ============================================================================
# NEW OPERATIONS (slice 6)
# ============================================================================

# True when $TARGET$ has completed at least one space race milestone this
# country has not. Milestone completion is public (world-first modifiers
# announce it), so this is not the progress omniscience the space race design
# forbids. The gate on covert_space_espionage_action — the space-race
# analogue of industrial espionage's tech-gap gate.
# Parameters: $TARGET$ = the country that may be ahead (scope:target_country
#             from an action; PREV from the console harness)
# Scope: country (the operator)
covert_target_ahead_in_space = {
	OR = {
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = suborbital }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = orbital }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = moon_landing }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = probe }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = moon_base }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = mars_landing }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = interstellar_probe }
		covert_target_ahead_in_space_on = { TARGET = $TARGET$ MILESTONE = solar_colonization }
	}
}

# One milestone of the above.
# Parameters: $TARGET$ as above; $MILESTONE$ = suborbital | orbital |
#             moon_landing | probe | moon_base | mars_landing |
#             interstellar_probe | solar_colonization
# Scope: country (the operator)
covert_target_ahead_in_space_on = {
	$TARGET$ = { has_variable = sr_completed_$MILESTONE$ }
	NOT = { has_variable = sr_completed_$MILESTONE$ }
}
```

- [ ] **Step 4: Static modifiers**

In `extra_modifiers.txt`, after the `covert_nuclear_sabotage` block (Task 3), insert (blank line before):

```
# Applied to SELF while a space-programme espionage operation runs (covert
# slice 6), from the strongest such operation (phase x priority).
covert_space_espionage = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	country_space_race_progress_mult = 0.10
	country_space_race_risk_mult = -0.10
}

# Applied to TARGET while a space-programme espionage operation runs against
# it, so covert_warfare.2 can tell the defender when one is burned. Same shape
# as the industrial and military espionage markers.
covert_space_espionage_detected = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_negative.dds
	country_authority_add = -3
}
```

- [ ] **Step 5: The diplomatic action**

Append to `covert_operations.txt` (blank line before):

```
# ---- PEACETIME: Space Programme Espionage (slice 6) ----
# Steal the rocket plans of a space programme that is ahead of ours: our
# milestones progress faster and fail less often. Mild tier. Requires the
# target to have completed a milestone we have not.
# Effect phases through preparatory → establishing → fully operational.
covert_space_espionage_action = {
	groups = {
		general
	}
	requires_approval = no
	show_confirmation_box = yes
	show_effect_in_tooltip = yes
	is_hostile = yes
	should_notify_third_parties = no

	accept_effect = {
		custom_tooltip = {
			text = covert_space_espionage_extra_tt
		}
		custom_tooltip = {
			text = covert_op_phase_warning_tt
		}
		custom_tooltip = {
			text = covert_op_detection_warning_tt
		}
		covert_op_start = { TYPE = space_espionage DEFENSE_MOD = country_covert_defense_economic_add CODE = 11 }
	}

	potential = {
		has_game_rule = covert_warfare_enabled
	}

	possible = {
		custom_tooltip = {
			text = covert_op_capacity_space_espionage_tt
			covert_ops_type_below_cap = { TYPE = covert_space_espionage_action }
		}
		custom_tooltip = {
			text = iw_has_available_slot_tt
			covert_operations_available_slots >= 1
		}
		custom_tooltip = {
			text = iw_no_duplicate_target_tt
			NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_space_espionage_action } }
		}
		custom_tooltip = {
			text = iw_target_not_decentralized_tt
			scope:target_country = { covert_action_valid_target = yes }
		}
		custom_tooltip = {
			text = iw_no_truce_tt
			NOT = { has_truce_with = scope:target_country }
		}
		# Allowed during war: no has_war guard
		custom_tooltip = {
			text = iw_no_intel_sharing_tt
			NOT = {
				any_scope_treaty = {
					binds = scope:target_country
					any_scope_article = { has_type = intelligence_sharing_pact }
				}
			}
		}
		custom_tooltip = {
			text = iw_target_ahead_in_space_tt
			covert_target_ahead_in_space = { TARGET = scope:target_country }
		}
		custom_tooltip = {
			text = iw_funding_not_zero_tt
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
		}
	}

	pact = {
		cost = 0
		is_two_sided_pact = no
		show_in_outliner = yes

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_funding_not_zero_tt
					has_variable = iw_funding_level
					var:iw_funding_level >= 1
				}
			}
		}

		# Stealing plans from a programme we have caught up with is pointless.
		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_target_ahead_in_space_tt
					covert_target_ahead_in_space = { TARGET = scope:target_country }
				}
			}
		}

		# Allowed during war: do not auto-break when war starts

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_no_truce_tt
					NOT = { has_truce_with = scope:target_country }
				}
			}
		}
		manual_break_effect = { covert_op_end = { TYPE = space_espionage } }
		auto_break_effect = { covert_op_end = { TYPE = space_espionage } }
	}

	ai = {
		evaluation_chance = {
			value = 0.03
			if = {
				limit = { ruler_is_aggressive = yes }
				add = 0.02
			}
			if = {
				limit = { ruler_is_cautious = yes }
				multiply = 0.5
			}
		}

		will_propose = {
			covert_operations_available_slots >= 1
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
			in_default = no
			# Only spy on a programme that is ahead, while we run one ourselves
			covert_target_ahead_in_space = { TARGET = scope:target_country }
			sr_is_pursuing_milestone = yes
		}

		propose_score = {
			value = 10
			if = {
				limit = { country_rank >= rank_value:great_power }
				add = 5
			}
		}
	}
}
```

- [ ] **Step 6: Plumbing (code 11)**

`covert_ops_sync_all`, after the `CODE = 10` row:

```
	covert_op_sync = { TYPE = space_espionage ACTION = covert_space_espionage_action DEFENSE_MOD = country_covert_defense_economic_add CODE = 11 }
```

`is_covert_operation_pact`, after the nuclear-sabotage line:

```
		is_diplomatic_action_type = covert_space_espionage_action
```

`covert_code_tier_mild`, after `var:$VAR$ = 5`:

```
		var:$VAR$ = 11
```

`covert_warfare.1` `after`, after the code-10 branch:

```
			else_if = {
				limit = { var:iw_burned_type_code = 11 }
				covert_op_burn = { TYPE = space_espionage ACTION = covert_space_espionage_action TARGET = scope:detected_by_country CODE = 11 }
			}
```

`covert_warfare.2` `trigger`, after `has_modifier = covert_nuclear_sabotage`:

```
			has_modifier = covert_space_espionage_detected
```

`covert_last_exposed_type_name`, after the code-10 text block:

```
	text = {
		trigger = { var:iw_last_exposed_type = 11 }
		localization_key = iw_op_name_space_espionage
	}
```

`covert_burned_type_name`, after the code-10 text block:

```
	text = {
		trigger = { var:iw_burned_type_code = 11 }
		localization_key = iw_op_name_space_espionage
	}
```

`covert_warfare_sguis.txt`, after `covert_stand_down_nuclear_sabotage_sgui` (blank line before):

```
covert_stand_down_space_espionage_sgui = {
	scope = country
	saved_scopes = { iw_tgt }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_stand_down = { TYPE = space_espionage }
	}

	effect = {
		covert_effect_stand_down = { TYPE = space_espionage ACTION = covert_space_espionage_action }
	}

	ai_is_valid = {
		always = no
	}
}
```

Widget, after the nuclear-sabotage row line:

```
		widget_je_covert_operation_text = {
			visible = "[ScriptContainer.HasTag('iw_op_space_espionage')]"
			text = "je_iw_op_row_space_espionage"
		}
```

Widget, after the nuclear-sabotage stand-down instance:

```
		covert_op_stand_down_button = {
			blockoverride "sd_context" {
				datacontext = "[GetScriptedGui('covert_stand_down_space_espionage_sgui')]"
			}
			blockoverride "sd_visible" {
				visible = "[ScriptContainer.HasTag('iw_op_space_espionage')]"
			}
		}
```

- [ ] **Step 7: The effect**

`covert_ops_apply_all_phase_effects`, after the nuclear-sabotage line (Task 3):

```
		# ---- Space Programme Espionage (slice 6): self modifier from the
		#      strongest operation; marker on TARGET so covert_warfare.2 can
		#      notify them ----
		covert_op_apply_self_effect = { TYPE = space_espionage MODIFIER = covert_space_espionage }
		covert_op_apply_target_effect = { TYPE = space_espionage MODIFIER = covert_space_espionage_detected }
```

- [ ] **Step 8: Loc**

`te_miscellaneous_l_english.yml`:

```yaml
 covert_space_espionage_action:0 "Covert: Space Programme Espionage"
 covert_space_espionage_action_desc:0 "Steal the designs of a foreign space programme that is ahead of ours. Our space race milestones progress faster and are less likely to fail. Requires the target to have completed a milestone we have not.$iw_exposure_tier_mild_note$"
 covert_space_espionage_action_action_propose_name:0 "Launch Space Espionage"
 covert_space_espionage_action_action_break_name:0 "Cancel Space Espionage"
 covert_space_espionage_action_action_notification_name:0 "Space Espionage Launched"
 covert_space_espionage_action_action_notification_break_name:0 "Space Espionage Cancelled"
 covert_space_espionage_action_action_notification_desc:0 "[INITIATOR_COUNTRY.GetName] has launched a space-programme espionage operation."
 covert_space_espionage_action_action_notification_break_desc:0 "[INITIATOR_COUNTRY.GetName] has discontinued their space-programme espionage operation."
 covert_space_espionage_extra_tt:0 "Speeds our space race milestones and lowers their risk of failure."
 covert_op_capacity_space_espionage_tt:0 "No space espionage slots available — reduce active space espionage operations or increase covert capacity."
 iw_op_name_space_espionage:0 "Space Programme Espionage"
 iw_target_ahead_in_space_tt:0 "Target must have completed a space race milestone we have not"
 covert_space_espionage:0 "Stolen Rocket Plans"
 covert_space_espionage_desc:0 "Our intelligence services are passing us the designs of a foreign space programme: our milestones progress faster and fail less often."
 covert_space_espionage_detected:0 "Foreign Space Espionage"
 covert_space_espionage_detected_desc:0 "Counterintelligence has uncovered foreign agents inside our space programme, and plugging the leak consumes administrative focus."
```

`te_journal_entries_l_english.yml`:

```yaml
 je_iw_op_row_space_espionage:0 "• #G Space Espionage#! vs [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]"
```

`te_diplomacy_l_english.yml`:

```yaml
 covert_space_espionage_action_pact_desc:0 "We are stealing space programme designs from [SCOPE.GetRootScope.GetDiplomaticPact.GetSecondCountry.GetName]."
```

`te_modifiers_l_english.yml`: change `country_covert_defense_economic_add_desc` to

```yaml
 country_covert_defense_economic_add_desc:0 "Additional defense against economic [concept_covert_operations] such as financial subversion, industrial espionage and space programme espionage."
```

- [ ] **Step 9: Icon**

```bash
cd /home/jakef/src/Vic3TimelineExtended
cp gfx/interface/icons/lens_toolbar_icons/covert_industrial_espionage_action.dds gfx/interface/icons/lens_toolbar_icons/covert_space_espionage_action.dds
```

- [ ] **Step 10: Green, format, BOM, commit**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry test_covert_new_ops test_covert_detection_roll test_covert_exposure_tiers test_covert_stand_down` — Expected: all pass.

```bash
cd /home/jakef/src/Vic3TimelineExtended
F="common/static_modifiers/extra_modifiers.txt common/diplomatic_actions/covert_operations.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui"
python3 scripts/format_paradox_tabs.py $(echo "$F")
for f in $(echo "$F"); do printf '%s ' $f; head -c3 $f | xxd -p; done
git add test_covert_op_registry.py test_covert_new_ops.py $(echo "$F") localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml localization/english/te_diplomacy_l_english.yml localization/english/te_modifiers_l_english.yml gfx/interface/icons/lens_toolbar_icons/covert_space_espionage_action.dds
git commit -m "feat(covert): space programme espionage operation (slice 6, code 11)

A mild-tier operation against a country that has completed a space race
milestone we have not (covert_target_ahead_in_space, over all eight
milestones; completion is public): our milestones progress +10% and fail
-10% less, scaled by phase x priority from the strongest such operation. The
target carries the usual espionage marker so a burn still reaches it. Lapses
once we catch up.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

---

### Task 5: Cultivate assets (code 12, mild, network-only)

**Files:**
- Modify: `test_covert_op_registry.py`, `test_covert_new_ops.py`
- Modify: `common/scripted_triggers/covert_warfare_triggers.txt` (network predicate, priority pin, plumbing)
- Modify: `common/script_values/covert_warfare_script_values.txt` (`covert_net_tick_gain`)
- Modify: `common/scripted_effects/covert_warfare_effects.txt` (`covert_nets_sync`, `covert_tradecraft_monthly`, sync row, apply-pass comment, header comment)
- Modify: `common/diplomatic_actions/covert_operations.txt` (append)
- Modify: `events/covert_warfare_events.txt`, `common/customizable_localization/covert_warfare_custom_loc.txt`, `common/scripted_guis/covert_warfare_sguis.txt`, `gui/journal_entry_widgets/covert_operations_widget.gui`
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `te_journal_entries_l_english.yml`, `te_diplomacy_l_english.yml`, `te_modifiers_l_english.yml`
- Create: `gfx/interface/icons/lens_toolbar_icons/covert_cultivate_assets_action.dds`

**Interfaces:**
- Consumes: `covert_net_cultivate_mult`, `covert_cultivate_ai_net_ceiling` (Task 2); `iw_target_not_our_subject_tt` (Task 2); `covert_nets_sync`, `covert_net_tick_gain`, `covert_tradecraft_monthly`, `covert_possible_priority_up` (slices 3–5).
- Produces: network variable `iw_net_cultivating` (0/1, written each monthly pass); scripted trigger `covert_net_weaker_than = { TARGET STRENGTH }`.

- [ ] **Step 1: Registry row (red)**

Append to `OPS` (marker `None`: it leaves nothing on its target):

```python
    ("cultivate_assets", 12, "ideological", "mild", None),
```

Run: `python3 -m unittest test_covert_op_registry` — Expected: the site tests fail for `cultivate_assets` (`test_markers_are_what_the_operation_leaves_on_its_target` already passes — it asserts absence).

- [ ] **Step 2: Behaviour tests (red)**

Add to `test_covert_new_ops.py`:

```python
class CultivateAssetsTests(unittest.TestCase):
    def setUp(self):
        self.block = _top_level_block(_text(ACTIONS), "covert_cultivate_assets_action = {")

    def test_no_modifiers_of_its_own(self):
        self.assertNotIn("\ncovert_cultivate_assets = {", _text(STATIC))

    def test_gates(self):
        possible = _section(self.block, "possible = {")
        self.assertIn("NOT = { scope:target_country = { is_subject_of = ROOT } }", possible)
        self.assertNotIn("type = rivalry", possible)
        self.assertNotIn("covert_tradecraft", possible)
        self.assertIn("covert_action_valid_target = yes", _requirements(self.block))

    def test_ai_builds_thin_networks(self):
        will = _section(self.block, "will_propose = {")
        self.assertIn(
            "covert_net_weaker_than = { TARGET = scope:target_country STRENGTH = covert_cultivate_ai_net_ceiling }",
            will,
        )
        pred = _top_level_block(_text(TRIGGERS), "covert_net_weaker_than = {")
        self.assertIn("has_variable_list = iw_nets", pred)
        self.assertIn("var:iw_net_strength >= $STRENGTH$", pred)

    def test_cultivate_multiplier_is_guarded_and_zeroed(self):
        gain = _top_level_block(_text(VALUES), "covert_net_tick_gain = {")
        self.assertIn("has_variable = iw_net_cultivating", gain)
        self.assertIn("multiply = covert_net_cultivate_mult", gain)
        sync = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        count = sync[sync.index("# ---- 2. Count ----"): sync.index("# ---- 3. Tick ----")]
        self.assertIn("set_variable = { name = iw_net_cultivating value = 0 }", count)
        self.assertIn("has_tag = iw_op_cultivate_assets", count)
        self.assertIn("set_variable = { name = iw_net_cultivating value = 1 }", count)

    def test_tradecraft_counts_it_at_the_preparatory_rate(self):
        # The full-rate branch's limit must exclude it (comments may sit between).
        block = _top_level_block(_text(EFFECTS), "covert_tradecraft_monthly = {")
        self.assertRegex(
            block,
            r"covert_op_is_established = yes(?:\s*#[^\n]*)*\s*NOT = \{ has_tag = iw_op_cultivate_assets \}",
        )

    def test_cultivate_assets_is_pinned_at_priority_1(self):
        # The stepper and the AI both step through covert_possible_priority_up.
        block = _top_level_block(_text(TRIGGERS), "covert_possible_priority_up = {")
        self.assertIn("scope:iw_op ?= { NOT = { has_tag = iw_op_cultivate_assets } }", block)
        gui = _text(WIDGET)
        stepper = gui[gui.index("type covert_op_priority_stepper = flowcontainer {"):]
        stepper = stepper[: stepper.index("textbox = {")]
        self.assertIn("Not( ScriptContainer.HasTag('iw_op_cultivate_assets') )", stepper)

    def test_its_row_says_what_it_does_instead_of_phase_and_priority(self):
        gui = _text(WIDGET)
        for key in ("je_iw_op_row_phase_prep", "je_iw_op_row_phase_est", "je_iw_op_row_phase_full",
                    "je_iw_op_row_priority_1", "je_iw_op_row_priority_2", "je_iw_op_row_priority_3"):
            line = gui[: gui.index('text = "%s"' % key)].rsplit("visible = ", 1)[1]
            self.assertIn("Not( ScriptContainer.HasTag('iw_op_cultivate_assets') )", line, key)
        self.assertIn(
            "visible = \"[ScriptContainer.HasTag('iw_op_cultivate_assets')]\"\n\t\t\ttext = \"je_iw_op_row_cultivate_detail\"",
            gui,
        )
        self.assertIn("covert_net_cultivate_mult", _loc()["je_iw_op_row_cultivate_detail"])
```

Run: `python3 -m unittest test_covert_new_ops` — Expected: FAIL in `CultivateAssetsTests`.

- [ ] **Step 3: Network hooks**

`common/script_values/covert_warfare_script_values.txt`, `covert_net_tick_gain`: after the Tradecraft `if = { … multiply = var:iw_net_tc_mult }` block and before the closing `}`, insert

```
	# Cultivate assets (slice 6): flagged onto the network by covert_nets_sync
	# step 2 when one runs against its target. A network from before slice 6
	# has no flag until its first pass; missing reads as x1.
	if = {
		limit = {
			has_variable = iw_net_cultivating
			var:iw_net_cultivating = 1
		}
		multiply = covert_net_cultivate_mult
	}
```

`common/scripted_effects/covert_warfare_effects.txt`, `covert_nets_sync`, step 2. Replace

```
		# ---- 2. Count ----
		every_in_list = {
			variable = iw_nets
			set_variable = { name = iw_net_ops value = 0 }
		}
```

with

```
		# ---- 2. Count ----
		every_in_list = {
			variable = iw_nets
			set_variable = { name = iw_net_ops value = 0 }
			set_variable = { name = iw_net_cultivating value = 0 }
		}
```

and directly after the counting `if = { limit = { has_variable_list = iw_ops } every_in_list = { … change_variable = { name = iw_net_ops add = 1 } … } }` block (still before `# ---- 3. Tick ----`), insert

```
		# Cultivate assets (slice 6): flag the network it feeds, for
		# covert_net_tick_gain's x covert_net_cultivate_mult. It is also counted
		# above as an operation like any other.
		if = {
			limit = { has_variable_list = iw_ops }
			every_in_list = {
				variable = iw_ops
				limit = { has_tag = iw_op_cultivate_assets }
				var:iw_target ?= {
					save_scope_as = iw_net_cultivate_tgt
					scope:iw_net_operator = {
						random_in_list = {
							variable = iw_nets
							limit = { var:iw_target ?= scope:iw_net_cultivate_tgt }
							set_variable = { name = iw_net_cultivating value = 1 }
						}
					}
				}
			}
		}
```

In the file's header comment, in the NETWORK container's `vars` list, after the `iw_net_tc_mult` line add

```
#           iw_net_cultivating      1 while a cultivate-assets operation runs against the target (slice 6)
```

and in the `covert_nets_sync` comment's step list change `#   2. Count operations per network (zero every count, then walk iw_ops once).` to `#   2. Count operations per network (zero every count, then walk iw_ops once),\n#      and flag networks a cultivate-assets operation feeds (slice 6).` — as two comment lines.

- [ ] **Step 4: Tradecraft at the preparatory rate**

`covert_tradecraft_monthly`: replace

```
			if = {
				limit = { covert_op_is_established = yes }
				scope:iw_tc_operator = { change_variable = { name = iw_tradecraft_ops add = 1 } }
			}
```

with

```
			if = {
				limit = {
					covert_op_is_established = yes
					# Cultivate assets (slice 6) always counts at the
					# preparatory fraction: cheap and near-riskless, it must
					# not be a way to farm experience.
					NOT = { has_tag = iw_op_cultivate_assets }
				}
				scope:iw_tc_operator = { change_variable = { name = iw_tradecraft_ops add = 1 } }
			}
```

In the comment above `covert_tradecraft_monthly`, change `#   2. Weigh the running operations into iw_tradecraft_ops: 1 for each at` / `#      establishing or better, covert_tradecraft_prep_gain_fraction for each` / `#      still preparatory; the total capped at covert_tradecraft_ops_counted.` to

```
#   2. Weigh the running operations into iw_tradecraft_ops: 1 for each at
#      establishing or better, covert_tradecraft_prep_gain_fraction for each
#      still preparatory and for every cultivate-assets operation (slice 6);
#      the total capped at covert_tradecraft_ops_counted.
```

- [ ] **Step 5: Priority pinned at 1**

`common/scripted_triggers/covert_warfare_triggers.txt`, `covert_possible_priority_up`: after the `iw_priority_not_max_tt` custom_tooltip and before the Tradecraft-gate comment, insert

```
	# Cultivate assets (slice 6) has no effect for priority to multiply, so it
	# stays at 1: raising it would only cost upkeep and detection. The AI
	# steps through this same trigger, so it cannot raise it either.
	custom_tooltip = {
		text = iw_priority_cultivate_fixed_tt
		scope:iw_op ?= { NOT = { has_tag = iw_op_cultivate_assets } }
	}
```

`gui/journal_entry_widgets/covert_operations_widget.gui`, type `covert_op_priority_stepper`: replace its `visible` line

```
		visible = "[GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
```

with

```
		### Hidden on a cultivate-assets row: its priority is fixed at 1
		### (covert_possible_priority_up), and the row says so instead.
		visible = "[And( GetScriptedGui('covert_ops_priority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), Not( ScriptContainer.HasTag('iw_op_cultivate_assets') ) )]"
```

- [ ] **Step 6: The cultivate row's own line in place of phase and priority**

In the operation row, change each of the three phase lines and the three priority lines from `visible = "[And( A, B )]"` to `visible = "[And3( A, B, Not( ScriptContainer.HasTag('iw_op_cultivate_assets') ) )]"`. Concretely, the phase-1 line becomes

```
		widget_je_covert_operation_detail = {
			visible = "[And3( GetScriptedGui('covert_ops_phase_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ), EqualTo_CFixedPoint(ScriptContainer.GetVariableValue('iw_phase'), '(CFixedPoint)1'), Not( ScriptContainer.HasTag('iw_op_cultivate_assets') ) )]"
			text = "je_iw_op_row_phase_prep"
		}
```

and the same edit applies to `(CFixedPoint)2` / `je_iw_op_row_phase_est`, `(CFixedPoint)3` / `je_iw_op_row_phase_full`, and to the three priority lines (`covert_ops_priority_ready_sgui`, `iw_priority`, `je_iw_op_row_priority_1..3`). Then, directly before `# ---- Priority: a stepper, then what the current level means ----`, insert

```
		# ---- Cultivate assets (slice 6): no phase effect and no priority to
		#      show; one line saying what it does instead ----
		widget_je_covert_operation_detail = {
			visible = "[ScriptContainer.HasTag('iw_op_cultivate_assets')]"
			text = "je_iw_op_row_cultivate_detail"
		}
```

- [ ] **Step 7: The network predicate and the diplomatic action**

Append to `covert_warfare_triggers.txt` (after `covert_target_ahead_in_space_on`, blank line before):

```
# True unless this country already has a network of at least $STRENGTH$
# against $TARGET$. For the AI's cultivate-assets proposal: build where the
# network is thin, not where it is already strong.
# Parameters: $TARGET$ = country (a scope: reference), $STRENGTH$ = 0-100
# Scope: country (the operator)
covert_net_weaker_than = {
	NOT = {
		AND = {
			has_variable_list = iw_nets
			any_in_list = {
				variable = iw_nets
				var:iw_target ?= $TARGET$
				var:iw_net_strength >= $STRENGTH$
			}
		}
	}
}
```

Append to `covert_operations.txt` (blank line before):

```
# ---- PEACETIME: Cultivate Assets (slice 6) ----
# Dinners, favours and a slow list of names. No effect on the target at all:
# its only product is our network there, which grows x covert_net_cultivate_mult
# while it runs. Mild tier; priority fixed at 1; counts towards Tradecraft
# only at the preparatory rate.
covert_cultivate_assets_action = {
	groups = {
		general
	}
	requires_approval = no
	show_confirmation_box = yes
	show_effect_in_tooltip = yes
	is_hostile = yes
	should_notify_third_parties = no

	accept_effect = {
		custom_tooltip = {
			text = covert_cultivate_assets_extra_tt
		}
		custom_tooltip = {
			text = covert_op_detection_warning_tt
		}
		covert_op_start = { TYPE = cultivate_assets DEFENSE_MOD = country_covert_defense_ideological_add CODE = 12 }
	}

	potential = {
		has_game_rule = covert_warfare_enabled
	}

	possible = {
		custom_tooltip = {
			text = covert_op_capacity_cultivate_assets_tt
			covert_ops_type_below_cap = { TYPE = covert_cultivate_assets_action }
		}
		custom_tooltip = {
			text = iw_has_available_slot_tt
			covert_operations_available_slots >= 1
		}
		custom_tooltip = {
			text = iw_no_duplicate_target_tt
			NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_cultivate_assets_action } }
		}
		custom_tooltip = {
			text = iw_target_not_decentralized_tt
			scope:target_country = { covert_action_valid_target = yes }
		}
		custom_tooltip = {
			text = iw_no_truce_tt
			NOT = { has_truce_with = scope:target_country }
		}
		# Allowed during war: no has_war guard
		custom_tooltip = {
			text = iw_no_intel_sharing_tt
			NOT = {
				any_scope_treaty = {
					binds = scope:target_country
					any_scope_article = { has_type = intelligence_sharing_pact }
				}
			}
		}
		custom_tooltip = {
			text = iw_target_not_our_subject_tt
			NOT = { scope:target_country = { is_subject_of = ROOT } }
		}
		custom_tooltip = {
			text = iw_funding_not_zero_tt
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
		}
	}

	pact = {
		cost = 0
		is_two_sided_pact = no
		show_in_outliner = yes

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_funding_not_zero_tt
					has_variable = iw_funding_level
					var:iw_funding_level >= 1
				}
			}
		}

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_target_not_decentralized_tt
					scope:target_country = { covert_action_valid_target = yes }
				}
			}
		}

		# Allowed during war: do not auto-break when war starts

		requirement_to_maintain = {
			trigger = {
				custom_tooltip = {
					text = iw_no_truce_tt
					NOT = { has_truce_with = scope:target_country }
				}
			}
		}
		manual_break_effect = { covert_op_end = { TYPE = cultivate_assets } }
		auto_break_effect = { covert_op_end = { TYPE = cultivate_assets } }
	}

	ai = {
		evaluation_chance = {
			value = 0.05
		}

		will_propose = {
			OR = {
				has_diplomatic_pact = { who = scope:target_country type = rivalry }
				has_attitude = { who = scope:target_country attitude = antagonistic }
			}
			covert_net_weaker_than = { TARGET = scope:target_country STRENGTH = covert_cultivate_ai_net_ceiling }
			covert_operations_available_slots >= 1
			has_variable = iw_funding_level
			var:iw_funding_level >= 1
			in_default = no
		}

		propose_score = {
			value = 5
			# Feed the network another operation there already benefits from.
			if = {
				limit = {
					has_variable_list = iw_ops
					any_in_list = {
						variable = iw_ops
						var:iw_target ?= scope:target_country
					}
				}
				add = 5
			}
		}
	}
}
```

(The accept tooltip omits `covert_op_phase_warning_tt` on purpose: that line warns the effect is delayed, and this operation has none.)

- [ ] **Step 8: Plumbing (code 12)**

`covert_ops_sync_all`, after the `CODE = 11` row:

```
	covert_op_sync = { TYPE = cultivate_assets ACTION = covert_cultivate_assets_action DEFENSE_MOD = country_covert_defense_ideological_add CODE = 12 }
```

`is_covert_operation_pact`, after the space-espionage line:

```
		is_diplomatic_action_type = covert_cultivate_assets_action
```

`covert_code_tier_mild`, after `var:$VAR$ = 11`:

```
		var:$VAR$ = 12
```

`covert_warfare.1` `after`, after the code-11 branch:

```
			else_if = {
				limit = { var:iw_burned_type_code = 12 }
				covert_op_burn = { TYPE = cultivate_assets ACTION = covert_cultivate_assets_action TARGET = scope:detected_by_country CODE = 12 }
			}
```

`covert_warfare.2` `trigger`, after `has_modifier = covert_space_espionage_detected`:

```
			# Cultivate assets (slice 6) leaves nothing on its target, so its
			# burn is keyed on the record covert_op_burn has just written
			# (covert_warfare.2 fires only from there).
			AND = {
				has_variable = iw_last_exposed_type
				var:iw_last_exposed_type = 12
			}
```

`covert_last_exposed_type_name`, after the code-11 text block:

```
	text = {
		trigger = { var:iw_last_exposed_type = 12 }
		localization_key = iw_op_name_cultivate_assets
	}
```

`covert_burned_type_name`, after the code-11 text block:

```
	text = {
		trigger = { var:iw_burned_type_code = 12 }
		localization_key = iw_op_name_cultivate_assets
	}
```

`covert_warfare_sguis.txt`, after `covert_stand_down_space_espionage_sgui` (blank line before):

```
covert_stand_down_cultivate_assets_sgui = {
	scope = country
	saved_scopes = { iw_tgt }

	is_shown = {
		always = yes
	}

	is_valid = {
		covert_possible_stand_down = { TYPE = cultivate_assets }
	}

	effect = {
		covert_effect_stand_down = { TYPE = cultivate_assets ACTION = covert_cultivate_assets_action }
	}

	ai_is_valid = {
		always = no
	}
}
```

Widget, after the space-espionage row line:

```
		widget_je_covert_operation_text = {
			visible = "[ScriptContainer.HasTag('iw_op_cultivate_assets')]"
			text = "je_iw_op_row_cultivate_assets"
		}
```

Widget, after the space-espionage stand-down instance:

```
		covert_op_stand_down_button = {
			blockoverride "sd_context" {
				datacontext = "[GetScriptedGui('covert_stand_down_cultivate_assets_sgui')]"
			}
			blockoverride "sd_visible" {
				visible = "[ScriptContainer.HasTag('iw_op_cultivate_assets')]"
			}
		}
```

`covert_ops_apply_all_phase_effects`, after the space-espionage lines (Task 4), a comment only (it must not name the tag or `TYPE = cultivate_assets`; the registry asserts their absence):

```
		# Cultivate assets (slice 6) is deliberately absent: it acts on
		# nothing but the network (covert_nets_sync / covert_net_tick_gain).
```

- [ ] **Step 9: Loc**

`te_miscellaneous_l_english.yml`:

```yaml
 covert_cultivate_assets_action:0 "Covert: Cultivate Assets"
 covert_cultivate_assets_action_desc:0 "Dinners, favours and a slow list of names. Does nothing to the target at all: it only builds our network there, #G x[GetPlayer.MakeScope.ScriptValue('covert_net_cultivate_mult')|1]#! as fast as any other operation would. Its priority is fixed at 1, and it teaches our agency only as much as a preparatory operation does.$iw_exposure_tier_mild_note$"
 covert_cultivate_assets_action_action_propose_name:0 "Start Cultivating Assets"
 covert_cultivate_assets_action_action_break_name:0 "Stop Cultivating Assets"
 covert_cultivate_assets_action_action_notification_name:0 "Asset Cultivation Begun"
 covert_cultivate_assets_action_action_notification_break_name:0 "Asset Cultivation Ended"
 covert_cultivate_assets_action_action_notification_desc:0 "[INITIATOR_COUNTRY.GetName] has begun cultivating intelligence assets."
 covert_cultivate_assets_action_action_notification_break_desc:0 "[INITIATOR_COUNTRY.GetName] has stopped cultivating intelligence assets."
 covert_cultivate_assets_extra_tt:0 "No effect on the target: grows our network there faster than any other operation."
 covert_op_capacity_cultivate_assets_tt:0 "No asset cultivation slots available — reduce active asset cultivation operations or increase covert capacity."
 iw_op_name_cultivate_assets:0 "Asset Cultivation"
 iw_priority_cultivate_fixed_tt:0 "Cultivating assets has nothing for priority to multiply: it stays at priority #v 1#!"
```

`te_journal_entries_l_english.yml`:

```yaml
 je_iw_op_row_cultivate_assets:0 "• #G Cultivating Assets#! in [ScriptContainer.MakeScope.Var('iw_target_capital').GetState.GetCountry.GetName]"
 je_iw_op_row_cultivate_detail:0 "#G Recruiting sources#! - no effect on the target; our network there grows #G x[JournalEntry.GetCountry.MakeScope.ScriptValue('covert_net_cultivate_mult')|1]#! faster. Priority stays at 1."
```

`te_diplomacy_l_english.yml`:

```yaml
 covert_cultivate_assets_action_pact_desc:0 "We are cultivating intelligence assets in [SCOPE.GetRootScope.GetDiplomaticPact.GetSecondCountry.GetName]."
```

`te_modifiers_l_english.yml`: change `country_covert_defense_ideological_add_desc` (last set in Task 2) to

```yaml
 country_covert_defense_ideological_add_desc:0 "Additional defense against ideological [concept_covert_operations] such as election interference, influence campaigns, ideological subversion, destabilization, regime change and the cultivation of assets."
```

- [ ] **Step 10: Icon**

```bash
cd /home/jakef/src/Vic3TimelineExtended
cp gfx/interface/icons/lens_toolbar_icons/covert_influence_campaign_action.dds gfx/interface/icons/lens_toolbar_icons/covert_cultivate_assets_action.dds
```

- [ ] **Step 11: Green (all covert suites), format, BOM, commit**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_op_registry test_covert_new_ops test_covert_detection_roll test_covert_exposure_tiers test_covert_networks test_covert_priority test_covert_stand_down test_covert_tradecraft` — Expected: all pass. (`test_covert_networks` and `test_covert_tradecraft` pin the network tick and Tradecraft pass this task edited; if one fails, read its assertion before touching it — adjust the test only where it pinned text this task deliberately changed.)

```bash
cd /home/jakef/src/Vic3TimelineExtended
F="common/script_values/covert_warfare_script_values.txt common/diplomatic_actions/covert_operations.txt common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt events/covert_warfare_events.txt common/customizable_localization/covert_warfare_custom_loc.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui"
python3 scripts/format_paradox_tabs.py $(echo "$F")
for f in $(echo "$F"); do printf '%s ' $f; head -c3 $f | xxd -p; done
git add test_covert_op_registry.py test_covert_new_ops.py $(echo "$F") localization/english/te_miscellaneous_l_english.yml localization/english/te_journal_entries_l_english.yml localization/english/te_diplomacy_l_english.yml localization/english/te_modifiers_l_english.yml gfx/interface/icons/lens_toolbar_icons/covert_cultivate_assets_action.dds
git commit -m "feat(covert): cultivate assets, a network-only operation (slice 6, code 12)

No effect on the target or the operator. While it runs, the target's
network grows x1.5 (flagged per network in covert_nets_sync, read by
covert_net_tick_gain; a pre-slice-6 network reads x1). It counts towards
Tradecraft only at the preparatory rate, whatever its phase, so it cannot
be farmed; its priority is fixed at 1 (covert_possible_priority_up refuses
it, which binds the AI too), and its widget row shows one line saying so
in place of the phase and priority lines. A burn is still announced to the
defender through iw_last_exposed_type. Mild tier.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

---

### Task 6: Console harness `te_debug_covert.4`

**Files:**
- Modify: `common/scripted_effects/te_debug_covert_effects.txt`, `events/te_debug_covert_events.txt`
- Modify: `localization/english/te_events_l_english.yml`
- Modify: `test_covert_new_ops.py`

**Interfaces:**
- Consumes: `te_debug_covert_plant_op`, `te_debug_covert_set_funding`, `te_debug_covert_set_tradecraft` (existing); `nuclear_program_is_proliferating` (Task 3); `covert_target_ahead_in_space` (Task 4).

- [ ] **Step 1: Harness tests (red)**

Add to `test_covert_new_ops.py`:

```python
class DebugHarnessTests(unittest.TestCase):
    def test_seed_plants_all_four_new_codes(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_seed_new_ops = {")
        self.assertEqual({int(c) for c in re.findall(r"CODE = (\d+)", block)}, {9, 10, 11, 12})
        self.assertIn("type = rivalry", block)
        self.assertIn("nuclear_program_is_proliferating = yes", block)
        self.assertIn("covert_target_ahead_in_space = { TARGET = PREV }", block)

    def test_event_is_console_only_and_localised(self):
        body = _text(DEBUG_EVENTS)
        opener = re.search(r"(?m)^te_debug_covert\.4 = \{.*$", body).group(0)
        self.assertIn("REVIEWED", opener)
        ev = body[body.index("te_debug_covert.4 = {"):]
        self.assertIn("event_image", ev)
        loc = _loc()
        for suffix in ("t", "d", "f", "a", "b"):
            self.assertIn("te_debug_covert.4.%s" % suffix, loc)
```

Run: `python3 -m unittest test_covert_new_ops.DebugHarnessTests` — Expected: FAIL.

- [ ] **Step 2: The seed effect**

Append to `common/scripted_effects/te_debug_covert_effects.txt` (blank line before):

```
# Slice 6's four operations, each planted fully operational (month 14) so
# their effects land at the next monthly pulse. Each needs a target that meets
# its requirement_to_maintain, or the pact lapses at the next check:
#   regime change + cultivate assets  one valid target; a rivalry is declared
#                                      on it first (regime change needs one)
#   nuclear sabotage                   a country whose programme is funded and
#                                      running, if there is one
#   space espionage                    a country ahead of us in the space race,
#                                      if there is one
# Funding is floored at 2, like te_debug_covert_seed_phases. Also sets
# Tradecraft to Seasoned (65), so both severe operations can be launched by
# hand from the diplomacy panel too.
# Scope: country
te_debug_covert_seed_new_ops = {
	if = {
		limit = {
			OR = {
				NOT = { has_variable = iw_funding_level }
				var:iw_funding_level < 1
			}
		}
		te_debug_covert_set_funding = { LEVEL = 2 }
	}
	te_debug_covert_set_tradecraft = { VALUE = 65 }
	random_country = {
		limit = {
			NOT = { this = ROOT }
			covert_action_valid_target = yes
			NOT = { is_subject_of = ROOT }
		}
		save_scope_as = te_debug_covert_target
	}
	if = {
		limit = { exists = scope:te_debug_covert_target }
		if = {
			limit = { NOT = { has_diplomatic_pact = { who = scope:te_debug_covert_target type = rivalry } } }
			create_diplomatic_pact = {
				country = scope:te_debug_covert_target
				type = rivalry
			}
		}
		te_debug_covert_plant_op = {
			TYPE = regime_change
			ACTION = covert_regime_change_action
			DEFENSE_MOD = country_covert_defense_ideological_add
			CODE = 9
			MONTHS = 14
		}
		te_debug_covert_plant_op = {
			TYPE = cultivate_assets
			ACTION = covert_cultivate_assets_action
			DEFENSE_MOD = country_covert_defense_ideological_add
			CODE = 12
			MONTHS = 14
		}
	}
	random_country = {
		limit = {
			NOT = { this = ROOT }
			covert_action_valid_target = yes
			nuclear_program_is_proliferating = yes
		}
		save_scope_as = te_debug_covert_nuke_target
	}
	if = {
		limit = { exists = scope:te_debug_covert_nuke_target }
		scope:te_debug_covert_nuke_target = { save_scope_as = te_debug_covert_target }
		te_debug_covert_plant_op = {
			TYPE = nuclear_sabotage
			ACTION = covert_nuclear_sabotage_action
			DEFENSE_MOD = country_covert_defense_military_add
			CODE = 10
			MONTHS = 14
		}
	}
	random_country = {
		limit = {
			NOT = { this = ROOT }
			covert_action_valid_target = yes
			ROOT = { covert_target_ahead_in_space = { TARGET = PREV } }
		}
		save_scope_as = te_debug_covert_space_target
	}
	if = {
		limit = { exists = scope:te_debug_covert_space_target }
		scope:te_debug_covert_space_target = { save_scope_as = te_debug_covert_target }
		te_debug_covert_plant_op = {
			TYPE = space_espionage
			ACTION = covert_space_espionage_action
			DEFENSE_MOD = country_covert_defense_economic_add
			CODE = 11
			MONTHS = 14
		}
	}
}
```

Also update `te_debug_covert_plant_op`'s header comment line `#             $CODE$ = operation type code 0-8, matching the branches of` to `0-12`.

- [ ] **Step 3: The event**

Append to `events/te_debug_covert_events.txt` (blank line before):

```
te_debug_covert.4 = { # REVIEWED 2026-09-23: console-only test event (`event te_debug_covert.4`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { texture = "gfx/event_pictures/espionage_dead_drop.dds" }

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

	icon = "gfx/interface/icons/event_icons/event_default.dds"

	title = te_debug_covert.4.t
	desc = te_debug_covert.4.d
	flavor = te_debug_covert.4.f

	# ---- Slice 6: plant the four new operations, fully operational, against
	#      targets that meet their conditions (nuclear sabotage and space
	#      espionage only if such a target exists). Tradecraft goes to 65.
	option = {
		name = te_debug_covert.4.a
		default_option = yes
		te_debug_covert_seed_new_ops = yes
	}

	# ---- Tradecraft to Seasoned (65) only: the two severe operations become
	#      launchable from the diplomacy panel.
	option = {
		name = te_debug_covert.4.b
		te_debug_covert_set_tradecraft = { VALUE = 65 }
	}
}
```

- [ ] **Step 4: Loc**

`localization/english/te_events_l_english.yml`, beside the other `te_debug_covert.3.*` keys:

```yaml
 te_debug_covert.4.t:0 "Covert Test Console: New Operations"
 te_debug_covert.4.d:0 "Console-only shortcuts for the four slice-6 operations. None of these can happen in normal play.\n\nPlanting declares a rivalry with one valid country and runs regime change and asset cultivation against it; nuclear sabotage goes against a country whose programme is running and space espionage against one ahead of us in the space race, each only if such a country exists. All four start fully operational, so their effects land at the next monthly pulse. Tradecraft is set to Seasoned (65)."
 te_debug_covert.4.f:0 "Test harness. Check debug.log after the next monthly pulse."
 te_debug_covert.4.a:0 "Plant the four new operations"
 te_debug_covert.4.b:0 "Set Tradecraft to Seasoned (65)"
```

- [ ] **Step 5: Green, format, BOM, commit**

Run: `cd /home/jakef/src/Vic3TimelineExtended && python3 -m unittest test_covert_new_ops test_covert_detection_roll test_covert_exposure_tiers` — Expected: all pass (`test_covert_exposure_tiers.DebugHarnessTests` reads only `te_debug_covert_seed_phases`, untouched).

```bash
cd /home/jakef/src/Vic3TimelineExtended
F="common/scripted_effects/te_debug_covert_effects.txt events/te_debug_covert_events.txt"
python3 scripts/format_paradox_tabs.py $(echo "$F")
for f in $(echo "$F"); do printf '%s ' $f; head -c3 $f | xxd -p; done
git add test_covert_new_ops.py $(echo "$F") localization/english/te_events_l_english.yml
git commit -m "test(covert): console harness for the slice-6 operations (te_debug_covert.4)

Plants all four new operations fully operational against targets that meet
their conditions (a rivalry is declared for regime change), and sets
Tradecraft to Seasoned.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
```

---

### Task 7: Loc housekeeping, docs, and the whole-mod checks

**Files:**
- Modify: `localization/english/*.yml` (organize_loc output)
- Modify: comments in `common/scripted_effects/covert_warfare_effects.txt`, `common/scripted_triggers/covert_warfare_triggers.txt`, `common/scripted_guis/covert_warfare_sguis.txt`, `gui/journal_entry_widgets/covert_operations_widget.gui`
- Modify: `docs/systems/mod_systems.md`, `docs/systems/journal_entry_systems.md` (CRLF), `README.md`, `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md`

- [ ] **Step 1: organize_loc, and nothing new unused**

```bash
cd /home/jakef/src/Vic3TimelineExtended
python3 organize_loc.py
git diff --stat localization/
git diff localization/english/te_unused_l_english.yml | grep '^+ ' || echo "nothing added to te_unused"
```

Expected: `nothing added to te_unused`. If a new key landed there, organize_loc cannot see where it is used: find the reference (`git grep -n <key>`), and fix the reference or the key — never hand-move it back (memory: te_unused is an organize_loc output). Re-run `python3 -m unittest test_covert_op_registry test_covert_new_ops` (they read live loc).

- [ ] **Step 2: Stale counts in code comments**

- `covert_warfare_effects.txt`: the four `$CODE$ = operation type code 0-8` comment lines (`covert_op_create`, `covert_op_start`, `covert_op_burn`, `covert_op_sync`) → `0-12`; `# Reconcile all 9 operation types, then recompute the upkeep weights.` → `# Reconcile every operation type, then recompute the upkeep weights.`; `# Master effect: apply ALL 9 operation types' phase-based effects.` → `# Master effect: apply every operation type's phase-based effects (cultivate assets has none).`
- `covert_warfare_triggers.txt`: `# Check if a diplomatic pact is a covert operation pact (any of the 9 types).` → `# Check if a diplomatic pact is a covert operation pact (any type; the list is pinned by test_covert_op_registry).`
- `covert_warfare_sguis.txt`: `(covert_stand_down_<type>_sgui, nine of them)` → `(covert_stand_down_<type>_sgui, one per operation type)`; `why there are nine rather than one` → `why there is one per type rather than one`.
- `covert_operations_widget.gui`: `### the nine covert_stand_down_<type>_sgui entries` → `### the covert_stand_down_<type>_sgui entries, one per type,`; `Nine instances per row` → `One instance per operation type per row`; `identical for all nine` → `identical for every type`.

Check nothing else still says nine: `grep -n -i 'nine\|0-8\|all 9\|ALL 9\|9 types' common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui events/covert_warfare_events.txt common/scripted_effects/te_debug_covert_effects.txt` — expected: no covert-count hits.

- [ ] **Step 3: `docs/systems/mod_systems.md` § Covert Warfare System**

- Key Files table: `9 diplomatic actions (7 peacetime, 2 wartime)` → `13 diplomatic actions (11 peacetime, 2 wartime)`; sguis row `nine per-type stand-down handlers` → `thirteen per-type stand-down handlers`; triggers row add `the slice-6 target predicates (covert_target_ahead_in_space, covert_net_weaker_than)`; add a row for `common/scripted_triggers/nuke_triggers.txt` → `nuclear_program_is_proliferating (nuclear sabotage's gate)`; debug-harness row `.1` / `.2` / `.3` → add `/ .4 (slice-6 operations)`.
- Game-rules table (the `covert_warfare_rule` row): `all 9 covert diplomatic actions` → `all 13 covert diplomatic actions`.
- Tier-table bullet: today's split becomes mild = {4 industrial espionage, 5 military espionage, 11 space programme espionage, 12 cultivate assets}; severe = {7 ideological subversion, 8 destabilization, 9 regime change, 10 nuclear programme sabotage}.
- "Adding an operation type" bullet: add the lens icon (`gfx/interface/icons/lens_toolbar_icons/covert_<type>_action.dds`, auto-loaded; a missing one is a `VFSOpen` error), the three `country_covert_defense_*_add_desc` strings, and the `covert_warfare.2` marker (the country-scope modifier the type leaves on its target, or an `iw_last_exposed_type` branch if it leaves none); and state that **`test_covert_op_registry.py` is the executable form of this list** — add the type's `OPS` row first and the failures name every missing site.
- Stand-down bullet: `the widget's nine covert_stand_down_<type>_sgui handlers` → `thirteen`.
- Tradecraft unlocks bullet: `for slice 6's regime change and nuclear programme sabotage; nothing reads it yet` → `read by regime change's and nuclear programme sabotage's possible — launching only; a running one survives the score falling`.
- Cancellation Conditions: `All 7 peacetime ops` → `All 11 peacetime ops`, and add: regime change also lapses when the rivalry ends; nuclear sabotage when the target's programme stops (`nuclear_program_is_proliferating`); space espionage when the target is no longer ahead; cultivate assets when the target becomes decentralized.
- AI Behavior: one bullet per new operation (guards and scores from Tasks 2–5), plus: **the AI will rarely launch the two severe operations** — they need Seasoned Tradecraft, and one moderate operation at 10 % detection averages 57.
- Known Behaviours: add "`covert_warfare.2` keyed infrastructure sabotage on its state modifier until slice 6, so its burns never reached the defender; it now keys on `covert_infra_sabotage_morale`."
- New subsection after `### Tradecraft — agency experience (2026-09, covert slice 5)`:

```markdown
### New operations (2026-09, covert slice 6)
- **Regime change** (`covert_regime_change_action`, code 9, severe, ideological defence): needs a rivalry (launch and maintain), a non-subject target and **Seasoned** Tradecraft (launch only). Target modifier `covert_regime_change`: coup resistance −1 (script-only — named in the modifier's description, not listed in its tooltip), legitimacy −5, movement radicalism +5 %, all × phase × priority (up to ×3.2). Once fully operational, `je:je_ip4_coup ?= { add_progress = { value = covert_regime_change_coup_push … } }` (+5 a month) — no DLC gate: coups are base game. The coup bar moves weekly by commander strength − coup resistance, so each point of resistance removed is ~+4.3 progress a month; against a legitimacy-50 government a fully operational priority-1 operation adds ~+18 a month (table: `docs/superpowers/plans/2026-09-23-covert-new-operations.md`).
- **Nuclear programme sabotage** (`covert_nuclear_sabotage_action`, code 10, severe, military defence): target must satisfy `nuclear_program_is_proliferating` (funded, running, not paused or disarming — a stockpiling nuclear power qualifies); **Seasoned** to launch. Target modifier `covert_nuclear_sabotage`: `country_nuclear_program_progress_mult −0.25` × phase × priority — progress ×0.75 … ×0.2, never zero.
- **Space programme espionage** (`covert_space_espionage_action`, code 11, mild, economic defence): target must have completed a milestone we have not (`covert_target_ahead_in_space`, over all eight; milestone completion is public). Self modifier `covert_space_espionage` (+10 % milestone progress, −10 % risk, × phase × priority, from the strongest such operation); target marker `covert_space_espionage_detected` (authority −3, like the other espionage markers).
- **Cultivate assets** (`covert_cultivate_assets_action`, code 12, mild, ideological defence): **no effect on the target or the operator**. `covert_nets_sync` flags the network it feeds (`iw_net_cultivating`), and `covert_net_tick_gain` multiplies that network's growth by `covert_net_cultivate_mult` (1.5; stacks with the extra-operation factor and Tradecraft) — alone against a target, strength 50 in ~17 months and 75 in ~28 (25 and 42 for any other operation). Always counts towards Tradecraft at the preparatory fraction. **Priority is fixed at 1**: `covert_possible_priority_up` refuses it (binding the AI too) and its widget row hides the stepper and the phase and priority lines behind one line of its own. A burn still reaches the defender: `covert_warfare.2` has an `iw_last_exposed_type = 12` branch. The AI proposes it against a rival or an antagonised country where its network is below `covert_cultivate_ai_net_ceiling` (50), more keenly where it already runs another operation.
- **Console:** `event te_debug_covert.4` — plant all four (fully operational; rivalry declared for regime change; nuclear and space only if a qualifying target exists) and set Tradecraft to Seasoned.
```

- [ ] **Step 4: `docs/systems/journal_entry_systems.md` (CRLF) and `README.md`**

In `journal_entry_systems.md` § Covert Warfare, with `Edit` only:
- Area 7 (**Operation rows**): append `A cultivate-assets row (2026-09, covert slice 6) has no stepper and no phase or priority lines: its priority is fixed at 1 and it has no effect, so it shows one line, je_iw_op_row_cultivate_detail, instead.`
- **Debug Harness**: append `` `event te_debug_covert.4` plants the four slice-6 operations fully operational and sets Tradecraft to Seasoned. ``

Then: `grep -c $'\r$' docs/systems/journal_entry_systems.md` and `wc -l < docs/systems/journal_entry_systems.md` — expected: equal.

`README.md`, the `covert_warfare_rule` row: `9 covert diplomatic actions` → `13 covert diplomatic actions`.

- [ ] **Step 5: Spec "as built"**

Append to § Slice 6 of `docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md`:

```markdown
**As built (plan `docs/superpowers/plans/2026-09-23-covert-new-operations.md`).**
Departures from the text above: the per-type list is now executable —
`test_covert_op_registry.py` holds one `OPS` table and checks every site
against it, and it caught `covert_warfare.2` keying infrastructure sabotage on
a state modifier (fixed); regime change's rivalry gate is new (destabilization
never had one in `possible`); the coup push has no DLC gate (coups are base
game; `je:je_ip4_coup ?=` covers the no-coup case); `sr_target_ahead_of_root`
is `covert_target_ahead_in_space = { TARGET }` in `covert_warfare_triggers.txt`;
`nuclear_program_is_proliferating` also excludes paused and disarming
programmes; cultivate assets is pinned at priority 1 (user decision
2026-09-23) and its row replaces the phase and priority lines with one line;
the four lens icons are copies of existing covert icons (user decision
2026-09-23). The spec's "×2 fully operational" figures predate priority: the
real range is ×1 to ×3.2 (plan § Balance).
```

- [ ] **Step 6: Whole-mod checks**

```bash
cd /home/jakef/src/Vic3TimelineExtended
git diff --name-only origin/main -- '*.txt' '*.gui' | xargs python3 scripts/format_paradox_tabs.py --check
ruff check .
python3 scripts/analysis/check_localization_files.py
python3 scripts/analysis/check_post_load_rosters.py
python3 scripts/analysis/check_dds_dimensions.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image treaty_leverage_side; do python3 ${a}_audit.py --strict >/dev/null 2>&1 && echo "ok $a" || echo "FAIL $a"; done
python3 kill_character_audit.py --check >/dev/null && echo ok kill_character
python3 attitude_key_audit.py >/dev/null && echo ok attitude_key
python3 -m unittest discover -s . -p 'test_*.py' 2>&1 | tail -3
```

(These are the CI steps from `.github/workflows/ci.yml`; the audits live at the repo root.) Expected: every line `ok`, ruff clean, unittest `OK`. For any `FAIL`, re-run that one command without the redirect to read it. This is the main checkout, so running the full discovery (which fires a real `POST /reload`) is allowed.

Then reload the server and read its warnings:

```bash
curl -s -X POST 'http://localhost:8950/reload?mod_only=true&audits_only=true' | .venv/bin/python -c "import json,sys; r=json.load(sys.stdin); print(json.dumps(r.get('warnings'), indent=1)[:4000]); print('parse_failures', r.get('parse_failures'))"
```

Expected: no warning that names a covert key, `covert_*` modifier, `iw_*`/`je_iw_*` loc key or `te_debug_covert.4`; `parse_failures` empty. The 17 pre-existing `common/messages` loc gaps are not this slice's. Check `docs/engine/modifier_visibility_report.md`, `loc_coverage_report.md` and `modifier_multiplier_var_report.md` for the four new modifiers. Restore the regenerated `docs/engine/*` files before committing (`git checkout -- docs/engine/` only for files this slice did not intend to change; never stage them).

- [ ] **Step 7: Commit, push, PR**

```bash
cd /home/jakef/src/Vic3TimelineExtended
git add localization/english/ common/scripted_effects/covert_warfare_effects.txt common/scripted_triggers/covert_warfare_triggers.txt common/scripted_guis/covert_warfare_sguis.txt gui/journal_entry_widgets/covert_operations_widget.gui docs/systems/mod_systems.md docs/systems/journal_entry_systems.md README.md docs/superpowers/specs/2026-09-22-covert-warfare-expansion-design.md
git status --short   # confirm no buy_packages or docs/engine churn is staged
git commit -m "docs(covert): slice 6 — four new operations; organize loc

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01CViHM7Avi99HyFXdbugbSc"
git push -u origin covert-new-ops
```

Write the PR body to `/tmp/claude-1000/-home-jakef-src-Vic3TimelineExtended/b0c75c2f-529d-4d66-bffa-48bb22b3ff4d/scratchpad/pr-body.md` first (summary per operation; the Balance tables from this plan; the registry test and the infra-sabotage fix; the spec departures; the in-game checks from § In-game verification below, unticked; ending with the `🤖 Generated with [Claude Code](https://claude.com/claude-code)` line and the session URL), then `gh pr create --base main --title "feat(covert): four new operation types (slice 6)" --body-file <that file>`.

---

## In-game verification (for the PR's checklist; needs the game)

1. `event te_debug_covert.4` → option a. Four rows appear (fewer if no proliferating or space-leading country exists); the cultivate row shows its single detail line and no stepper; every row has a working **Stand down**.
2. Next monthly pulse: the regime-change target carries `covert_regime_change` (legitimacy −10 at ×2); the nuclear target `covert_nuclear_sabotage`; we carry `covert_space_espionage`; the cultivate target's network row grows faster than an ordinary one would.
3. A coup in the regime-change target: its progress bar gains +5 a month on top of its weekly drift (confirms `add_progress` takes the named constant).
4. `event te_debug_covert.2` → force detection on the cultivate-assets operation: the defender gets `covert_warfare.2`; the attacker's event names "Asset Cultivation" and "routine espionage".
5. Tradecraft below 60 (`event te_debug_covert.3` → option a sets 45): the running regime-change operation survives; launching a new one shows the Seasoned gate crossed out.
6. `debug.log` via the `log-triage` skill: no `VFSOpen` for the four lens icons, no errors naming a covert key.
