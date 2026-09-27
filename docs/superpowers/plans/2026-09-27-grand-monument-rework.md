# Grand Monuments as a Political Instrument — Implementation Plan (phase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Grand Monument in place into a political/legacy instrument: dedications with a kind, national totals on a Monuments journal entry instead of per-building effects, one doubling curve for every effect, contested monuments with Tear Down / Rededicate / Preserve, identity skins, vanity backlash, and flavour events with real choices.

**Architecture:** The building, its level ("grandeur") and the dedication PM ratchet stay. The PMs carry only staff; every effect is a modifier refreshed by a pulse. A monthly **state** pulse applies each monument's local modifiers (multiplier = the curve over its own level). A monthly **country** pulse (and a hidden country event, `monument_events.20`, fired by the on-actions whose ROOT is not the country) records what each monument honours, detects contests, decays the ledgers, sums grandeur by status, and applies the national modifiers to `je:je_grand_monuments`. Everything a monument must remember lives on its **state** (buildings hold no variables).

**Tech Stack:** Paradox Clausewitz script (Victoria 3), `.gui`, YAML localization, Python 3 `unittest` static tests.

**Spec:** `docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md` (read it first; its Decisions table is settled). Phase 2 (named landmarks, new art) is out of this plan.

## Global Constraints

- **Prefix:** every new variable, modifier, script value, scripted trigger/effect/GUI and loc key starts with `gm_`, except PM keys (`pm_monument_<key>`), event keys (`monument_events.N`), the JE (`je_grand_monuments`), the game rule (`grand_monuments_rule`, `setting_grand_monuments_*`), the concept (`concept_grandeur`), the notification (`notification_gm_*`) and the shared heritage triggers (`te_heritage_<language>`). `mon_` and `te_mon_` belong to the monetary system.
- **The doubling curve:** 8 steps; step *n* completes at *f*·(2ⁿ − 1). First step *f* = **5** for standing grandeur (prestige), each dedication's own total, each IG total, the teardown ledger and every local effect; *f* = **10** for regime grandeur (legitimacy) and cultural pull. Cultural pull is capped at **5** steps.
- **Per step** (the static modifier carries one step; the multiplier is the step count, fractional):
  - national: prestige `country_prestige_add = 25`; legitimacy `country_legitimacy_base_add = 2`; Leader `country_authority_add = 25`; Shrine `interest_group_ig_devout_pop_attraction_mult = 0.05`; War Memorial `country_war_support_casualties_mult = -0.03`; Opera `interest_group_ig_intelligentsia_pop_attraction_mult = 0.05`; Observatory `country_weekly_innovation_max_add = 3`; Exhibition `interest_group_ig_industrialists_pop_attraction_mult = 0.05`; IG approval `interest_group_ig_<ig>_approval_add = 1` (signed multiplier); teardown `country_legitimacy_base_add = 3`; cultural pull `1`.
  - local (state): Tourism Industry `building_tourism_industry_throughput_add = 0.25`; Crown/Republic/Revolution/Leader/Nation `state_loyalists_from_political_movements_mult = 0.10`; Shrine `state_conversion_mult = 0.10`; War Memorial `state_conscription_rate_add = 0.05`; Opera `building_art_academy_throughput_add = 0.10`; Gardens `state_pollution_generation_add = -5000`; Observatory `state_literacy_growth_add = 0.00025`; Exhibition `state_migration_pull_mult = 0.10`; Stadium `state_turmoil_effects_mult = -0.10`.
  - vanity: `country_legitimacy_base_add = -3` per unit of the vanity ledger, **linear** (not curved).
- **Ledger decay per month:** teardown ×0.96, IG ledgers ×0.97, vanity ×0.92; a ledger within ±0.05 of 0 snaps to 0. Ledgers are never removed, only zeroed (they back multipliers).
- **Rededication:** treasury cost = level × 5,000; rebuilt at `ceil(level / 2)`, at most 200.
- **Vanity:** each level finished in hard times radicalizes 5% of the state's pops (`add_radicals_in_state = { value = 0.05 }`) and adds 1 to the vanity ledger. Hard times = `in_default`, `has_famine`, or (with `finance_cycle_value` present) `banking_cycle_is_recession`.
- **No PM carries `country_modifiers`, `state_modifiers` or a goods output.** Each dedication PM carries only `unscaled` employment: 200 laborers + 50 clerks.
- **Where a multiplier modifier may be added:** state modifiers only from `on_monthly_pulse_state` (ROOT = the state); national (JE) modifiers only where ROOT is the country (the country pulse, `monument_events.20`, a scripted GUI effect, a country event option). `on_building_built` (ROOT = building), `on_law_activated` (ROOT = law), `on_new_ruler` (ROOT = character) and `on_state_owner_change` (ROOT = state) only set variables and fire `monument_events.20` on the owner. On the JE, write `multiplier = root.var:X` and `limit = { root.var:X … }`. A variable that backs a multiplier is never removed.
- **Game rule:** every check is `gm_system_enabled = yes` (`NOT = { has_game_rule = grand_monuments_disabled }`).
- **Identity:** skins read only the owner's state religion and primary cultures (`te_heritage_*`, `religion = rel:x`). A conquered shrine becomes heritage and is never contested.
- **Flavour events:** every option is positive; the only cost an option may carry is money.
- **Files:** Paradox `.txt` and `.gui` are tab-indented and start with a UTF-8 BOM; loc files start with a BOM and `l_english:`. Loc formatting is `#b X#!` / `#G X#!` / `#R X#!` / `#v X#!`, never `[b]`. Loc describes the mod's effects, not vanilla mechanics.
- **Loc placement:** every `gm_*` key goes in `localization/english/te_miscellaneous_l_english.yml` (Task 1 adds the routing rule first); `monument_events.N.*` and `te_debug_monuments.N.*` in `te_events_l_english.yml`; `je_*` in `te_journal_entries_l_english.yml`; `pm_*`/`pmg_*` in `te_production_methods_l_english.yml`; `building_*` in `te_buildings_l_english.yml`; `rule_*`/`setting_*` in `te_game_rules_l_english.yml`; `notification_*` in `te_notifications_l_english.yml`; `concept_*` in `te_concepts_l_english.yml`. Keep each file's key order (the files are sorted by key; insert in order).
- **Work** in the sparse worktree `~/src/vic3te-grand-monument` (branch `grand-monument-rework`). Never `POST /reload` to the main checkout's server (port 8950) from here, never `git commit -a`: stage by path.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh
  ```

### Decisions this plan makes that the spec left open (flag them in the PR body)

1. **Per-step values live in the static modifiers** (one step each; multiplier = the step count). `gm_step_*` script values mirror them for loc and the registry test pins each pair equal. The spec (§2.2) had unit modifiers with multiplier = steps × per-step; this form lets `modifier_visibility_audit` check the real magnitudes.
2. **`gm_raised_by`:** every dedicated regime, ruler or faith monument records the country that dedicated it, and fits only while that country owns it. Without it a conquered Crown monument in a monarchy would fit the conqueror's laws the next month and lift its own contest. A civil war's winner adopts the monuments the loser raised (`gm_repair_after_civil_war`, beside the other repairs in `te_civil_war_on_won`), so "the winner continues the nation" holds; the fit test then contests them only if the winner's laws differ.
3. **The JE stays valid while a ledger is still fading** after the last monument goes (activation still needs a monument). Otherwise tearing down the last monument would remove its own legitimacy reward with the JE.
4. **The War Memorial takes heritage skins only**, not faith skins.
5. **"Decide each in turn"** in the contested notice fires one state event per monument (`monument_events.17`: Tear Down / Rededicate / Preserve / Leave it for now), a proven UI path beside the JE row buttons, whose saved state scope (`AddScope('gm_state', State.MakeScope)`) has no vanilla precedent (gui gotcha #22). The notice itself (`.16`) goes to players only; the AI decides per monument, monthly (§4.6).
6. **Demolishing a contested monument from the building panel counts as tearing it down** (its grandeur goes to the same ledgers), so the panel is not a free way out of the standing penalty.
7. **Flavour event magnitudes** (spec §9 said "about a tenth of the first step"): IG approval +2 (+3 for Pilgrims' clergy option), prestige +10, legitimacy +3, authority +25, standard of living +1, literacy growth +0.0005, innovation +5/week, influence +10, turmoil effects −10%, Tourism Industry throughput +10%, ruler popularity +10, all for `normal_modifier_time` (5 years); costs 2% of yearly gross income, income 1%.

## Review Focus

These are the inputs the spec implies but no static test fully exercises, most likely first. Each has a pinning test in the owning task.

1. **An old save.** Pre-rework monuments have no records. The first pulse must record them from the current owner (a Shrine's faith = the state religion, a civic monument = To the Nation) and must not contest them. Pinned in Task 5 (`gm_country_refresh` runs `gm_state_first_sight` before `gm_check_contests`, Task 6) and Task 4 (first sight writes `gm_raised_by` = owner).
2. **A conquered Crown monument whose conqueror is also a monarchy** must stay contested. Pinned in Task 4 (every bound fit test requires `gm_state_raised_by_owner`) and Task 6 (`gm_state_changed_hands`).
3. **A civil war.** Rebel-held monuments are not contested during the war; after a rebel win the winner adopts them, and they are contested only if its laws differ. Pinned in Task 6 (`te_cw_role` guard, `gm_repair_after_civil_war`, `gm_cw_adopting`).
4. **A Leader monument whose honoree has died** (a dangling character variable) must read "does not fit", not error. Pinned in Task 4 (`var:gm_honoree ?= { … }`).
5. **Tearing down the last monument** must not drop the JE (and its fading legitimacy) at once. Pinned in Task 5 (JE `invalid` requires `gm_ledgers_idle`).

## File map

| File | Responsibility | Task |
|---|---|---|
| `organize_loc.py` | `gm_` routing rule | 1 |
| `common/scripted_triggers/te_heritage_triggers.txt` | 18 shared `te_heritage_<language>` triggers + `te_heritage_any` | 1 |
| `events/extra_law_events.txt` | `.25` calls the shared triggers | 1 |
| `common/game_rules/extra_game_rules.txt` | `grand_monuments_rule` | 1 |
| `common/scripted_triggers/monument_triggers.txt` | rule, gates, hard times, kinds, fits, statuses, IG alignment, skins | 1, 3, 4, 5, 7 |
| `test_grand_monument_registry.py` | the registry and every site it pins | 1–11 |
| `common/script_values/gm_values.txt` | curve, step mirrors, sums, displays, codes | 2, 4, 5, 6, 10 |
| `common/static_modifiers/gm_modifiers.txt` | national, IG, ledger, local and event modifiers | 2, 10 |
| `common/game_concepts/extra_concepts.txt` | `concept_grandeur` | 2 |
| `common/production_methods/grand_monument_pms.txt` | 13 staff-only PMs | 3 |
| `common/production_method_groups/grand_monument_pmgs.txt` | the group, four new PMs | 3 |
| `common/buildings/grand_monuments.txt` | `possible`, `ai_value` | 3 |
| `common/scripted_effects/gm_effects.txt` | records, local pulse, national refresh, contests, choices, dedication, skins, vanity | 4–8 |
| `common/on_actions/monument_events_on_actions.txt` | state/country pulses, hooks, flavour dispatch | 4, 5, 6, 10 |
| `common/journal_entries/je_grand_monuments.txt` | the JE | 5, 9 |
| `common/script_values/cultural_hegemony_script_values.txt` | cultural pull from the curve | 5 |
| `events/monument_events.txt` | `.1`, `.2`, `.3`–`.17`, `.20` | 5–8, 10 |
| `common/on_actions/te_civil_war_on_actions.txt` | `gm_repair_after_civil_war` | 6 |
| `common/scripted_effects/te_construction_market_build_effects.txt` | ladder 101–200 | 6 |
| `common/customizable_localization/gm_custom_loc.txt` | skin, dedication, status, IG and inscription names | 6, 7 |
| `common/messages/extra_messages.txt` | vanity notification | 8 |
| `common/scripted_guis/gm_sguis.txt` | JE row buttons, hard-times line | 9 |
| `gui/journal_entry_widgets/grand_monuments_widget.gui` | national lines, monument rows | 9 |
| `events/te_debug_monuments_events.txt` | console test event | 11 |
| `docs/systems/mod_systems.md`, `docs/player_guide/*`, PDF | docs | 12 |
| `localization/english/*.yml` | loc per task (placement above) | 1–12 |

## Test commands (used in every task)

```bash
cd ~/src/vic3te-grand-monument
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent \
       VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
python3 -m unittest test_grand_monument_registry -v
python3 scripts/format_paradox_tabs.py --check <changed .txt files>
python3 scripts/analysis/check_localization_files.py
```

Every task after Task 1 adds its test classes to `test_grand_monument_registry.py` **above** the final `if __name__ == "__main__":` block, so `python3 test_grand_monument_registry.py` runs them too.

---

### Task 1: Loc routing, the shared heritage triggers, the game rule

Language reform decides which classical language a country may revive from its primary cultures (and, for four languages, its state religion). The monuments' heritage skins use the same partition, so it moves into shared triggers that both call.

**Files:**
- Modify: `organize_loc.py` (`categorize_key`)
- Create: `common/scripted_triggers/te_heritage_triggers.txt`
- Modify: `events/extra_law_events.txt` (`extra_law_events.25`)
- Modify: `common/game_rules/extra_game_rules.txt` (append)
- Modify: `common/scripted_triggers/monument_triggers.txt` (append `gm_system_enabled`)
- Modify: `localization/english/te_game_rules_l_english.yml`
- Create: `test_grand_monument_registry.py`

**Interfaces:**
- Produces (triggers, country scope): `te_heritage_latin`, `te_heritage_hebrew`, `te_heritage_sanskrit`, `te_heritage_geez`, `te_heritage_slavonic`, `te_heritage_pali`, `te_heritage_avestan`, `te_heritage_arabic`, `te_heritage_chinese`, `te_heritage_greek`, `te_heritage_irish`, `te_heritage_coptic`, `te_heritage_nahuatl`, `te_heritage_norse`, `te_heritage_gothic`, `te_heritage_mayan`, `te_heritage_prussian`, `te_heritage_aramaic`, `te_heritage_any`.
- Produces (trigger, any scope): `gm_system_enabled`.
- Produces (game rule): `grand_monuments_rule`, settings `grand_monuments_enabled` (default), `grand_monuments_disabled`.
- Produces (Python, used by every later test class): `read`, `strip_comments`, `block`, `raw_block_at`, `number`, `squash`, `top_level_blocks`, `loc`, `loc_file_of`, and the tables `DEDICATIONS`, `IGS`, `HERITAGES`, `HERITAGE_AS_FAITH`, `HERITAGE_SKINS`, `FAITHS`, `REVIVAL_OPTION`.

- [ ] **Step 1: Write the failing test**

Create `test_grand_monument_registry.py`:

```python
"""The Grand Monument registry: every dedication, skin and IG alignment in one
table, pinned against every site that lists them by hand.

Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
Adding a dedication touches its PM and the ratchet, the PM group, its kind and
fit trigger, the IG alignment triggers, its local and national modifiers and
their step mirrors, the ceremony option, the skin rules, its flavour event and
the loc. Nothing in the engine checks that they agree. DEDICATIONS is the
single list; each test checks one site against it, so a half-added dedication
fails here, naming the site.

Run: python3 -m unittest test_grand_monument_registry -v
"""
import re
import unittest
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent

RULES = "common/game_rules/extra_game_rules.txt"
HERITAGE = "common/scripted_triggers/te_heritage_triggers.txt"
LAW_EVENTS = "events/extra_law_events.txt"
TRIGGERS = "common/scripted_triggers/monument_triggers.txt"
VALUES = "common/script_values/gm_values.txt"
MODIFIERS = "common/static_modifiers/gm_modifiers.txt"
CONCEPTS = "common/game_concepts/extra_concepts.txt"
PMS = "common/production_methods/grand_monument_pms.txt"
PMG = "common/production_method_groups/grand_monument_pmgs.txt"
BUILDING = "common/buildings/grand_monuments.txt"
EFFECTS = "common/scripted_effects/gm_effects.txt"
ON_ACTIONS = "common/on_actions/monument_events_on_actions.txt"
CIVIL_WAR_ON_ACTIONS = "common/on_actions/te_civil_war_on_actions.txt"
LADDER = "common/scripted_effects/te_construction_market_build_effects.txt"
EVENTS = "events/monument_events.txt"
JE = "common/journal_entries/je_grand_monuments.txt"
CULTURAL = "common/script_values/cultural_hegemony_script_values.txt"
CUSTOM_LOC = "common/customizable_localization/gm_custom_loc.txt"
MESSAGES = "common/messages/extra_messages.txt"
SGUIS = "common/scripted_guis/gm_sguis.txt"
WIDGET = "gui/journal_entry_widgets/grand_monuments_widget.gui"
DEBUG_EVENTS = "events/te_debug_monuments_events.txt"
MISC_LOC = "te_miscellaneous_l_english.yml"

Dedication = namedtuple(
    "Dedication",
    "key kind approve oppose local_field local_step national_field national_step event")

# approve / oppose are IG keys (without the ig_ prefix); "dynamic" is the
# Leader's: the ruler's own IG approves, the strongest IG outside the
# government opposes (spec §1).
DEDICATIONS = (
    Dedication("crown", "regime", "landowners", "intelligentsia",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 12),
    Dedication("republic", "regime", "intelligentsia", "landowners",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 13),
    Dedication("revolution", "regime", "trade_unions", "industrialists",
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 14),
    Dedication("leader", "ruler", "dynamic", "dynamic",
               "state_loyalists_from_political_movements_mult", 0.10,
               "country_authority_add", 25, 15),
    Dedication("religious", "faith", "devout", None,
               "state_conversion_mult", 0.10,
               "interest_group_ig_devout_pop_attraction_mult", 0.05, 4),
    Dedication("civic", "timeless", "petty_bourgeoisie", None,
               "state_loyalists_from_political_movements_mult", 0.10, None, None, 3),
    Dedication("war_memorial", "timeless", "armed_forces", None,
               "state_conscription_rate_add", 0.05,
               "country_war_support_casualties_mult", -0.03, 5),
    Dedication("artistic", "timeless", "intelligentsia", None,
               "building_art_academy_throughput_add", 0.10,
               "interest_group_ig_intelligentsia_pop_attraction_mult", 0.05, 6),
    Dedication("naturalist", "timeless", "rural_folk", None,
               "state_pollution_generation_add", -5000, None, None, 7),
    Dedication("scientific", "timeless", "intelligentsia", None,
               "state_literacy_growth_add", 0.00025,
               "country_weekly_innovation_max_add", 3, 8),
    Dedication("industrial", "timeless", "industrialists", None,
               "state_migration_pull_mult", 0.10,
               "interest_group_ig_industrialists_pop_attraction_mult", 0.05, 9),
    Dedication("athletic", "timeless", "trade_unions", None,
               "state_turmoil_effects_mult", -0.10, None, None, 10),
)
BY_KEY = {d.key: d for d in DEDICATIONS}
BOUND = tuple(d.key for d in DEDICATIONS if d.kind != "timeless")
TECH_GATES = {"artistic": "romanticism", "naturalist": "romanticism", "scientific": "empiricism",
              "industrial": "marketing_research", "athletic": "television_broadcasting"}
# Dedications that take heritage skins (spec §1.1; the War Memorial takes no
# faith skin, plan decision 4).
HERITAGE_SKINNED = ("crown", "republic", "revolution", "leader", "civic", "war_memorial")

IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners",
       "petty_bourgeoisie", "rural_folk", "trade_unions")

# The language-reform revival partition (extra_law_events.25), in its order.
HERITAGES = ("latin", "hebrew", "sanskrit", "geez", "slavonic", "pali", "avestan", "arabic",
             "chinese", "greek", "irish", "coptic", "nahuatl", "norse", "gothic", "mayan",
             "prussian", "aramaic")
# Pali and Coptic are keyed on the state religion; their heritage skin is the
# matching faith skin.
HERITAGE_AS_FAITH = {"pali": "theravada", "coptic": "oriental_orthodox"}
HERITAGE_SKINS = tuple(h for h in HERITAGES if h not in HERITAGE_AS_FAITH)
FAITHS = ("catholic", "protestant", "orthodox", "oriental_orthodox", "sunni", "shiite", "ibadi",
          "jewish", "mahayana", "gelugpa", "theravada", "confucian", "hindu", "shinto", "sikh",
          "animist")
SKINS = ("generic",) + tuple(f"faith_{f}" for f in FAITHS) + tuple(f"heritage_{h}" for h in HERITAGE_SKINS)

# extra_law_events.25 option comment ("# Revive <name>") -> heritage.
REVIVAL_OPTION = {
    "Latin": "latin", "Hebrew": "hebrew", "Sanskrit": "sanskrit", "Ge'ez": "geez",
    "Old Church Slavonic": "slavonic", "Pali": "pali", "Avestan": "avestan",
    "Classical Arabic": "arabic", "Literary Chinese": "chinese", "Classical Greek": "greek",
    "Classical Irish (Gaeilge)": "irish", "Coptic": "coptic", "Classical Nahuatl": "nahuatl",
    "Old Norse": "norse", "Gothic": "gothic", "Classic Mayan": "mayan",
    "Old Prussian": "prussian", "Aramaic": "aramaic",
}


# ---- helpers -------------------------------------------------------------------------

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _match_brace(text, open_end):
    depth, i = 1, open_end
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[open_end:i - 1]


def block(text, name):
    """Body of `name = {` in text (comments stripped), or None. A top-level
    definition (at the start of a line) wins over a nested use, so a scripted
    effect's body is found even when a call with parameters
    (`gm_add_local = { KEY = crown }`) comes first in the file."""
    text = strip_comments(text)
    m = (re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
         or re.search(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{", text))
    return _match_brace(text, m.end()) if m else None


def raw_block_at(text, pattern):
    """Body of the block whose opening line matches `pattern` (a regex ending in
    `\\{`), comments kept, or None."""
    m = re.search(pattern, text)
    return _match_brace(text, m.end()) if m else None


def number(body, key):
    """The first `key = <number>` in body, as a float, or None."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*(-?\d+(?:\.\d+)?)", body or "")
    return float(m.group(1)) if m else None


def squash(text):
    return " ".join((text or "").split())


def top_level_blocks(text):
    """(name, body) for every top-level `name = {` in text (comments stripped)."""
    text = strip_comments(text)
    for m in re.finditer(r"(?m)^([\w:.]+)\s*=\s*\{", text):
        yield m.group(1), _match_brace(text, m.end())


_LOC = None


def _load_loc():
    global _LOC
    if _LOC is None:
        _LOC = {}
        for path in sorted((ROOT / "localization/english").glob("*.yml")):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'\s*([\w.$\'-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    _LOC[m.group(1)] = (m.group(2), path.name)
    return _LOC


class _Loc(dict):
    """The loc table; a short repr, so a failed assertIn doesn't print 100k keys."""
    def __repr__(self):
        return f"<{len(self)} loc keys>"


def loc():
    return _Loc({k: v[0] for k, v in _load_loc().items()})


def loc_file_of(key):
    entry = _load_loc().get(key)
    return entry[1] if entry else None


# ---- Task 1: loc routing, shared heritage triggers, the game rule --------------------

class RoutingTests(unittest.TestCase):
    def test_gm_keys_route_to_miscellaneous(self):
        from organize_loc import categorize_key
        for key in ("gm_local_crown", "gm_local_crown_desc", "gm_national_prestige",
                    "gm_skin_faith_jewish", "gm_row_title", "gm_je_line_legitimacy",
                    "gm_step_local_scientific_religion_event_add"):
            self.assertEqual(categorize_key(key, set()), "MISCELLANEOUS", key)

    def test_every_gm_key_lives_in_miscellaneous(self):
        for key in loc():
            if key.startswith("gm_"):
                self.assertEqual(loc_file_of(key), MISC_LOC, key)


class HeritageTests(unittest.TestCase):
    def test_eighteen_triggers_and_any(self):
        text = read(HERITAGE)
        for h in HERITAGES:
            self.assertIsNotNone(block(text, f"te_heritage_{h}"), h)
        any_body = squash(block(text, "te_heritage_any"))
        for h in HERITAGES:
            self.assertIn(f"te_heritage_{h} = yes", any_body)

    def test_heritage_reads_own_identity_only(self):
        body = strip_comments(read(HERITAGE))
        self.assertNotRegex(body, r"\bscope:|\bvar:|\bprev\b", "reads only the country's own identity")
        self.assertNotIn("any_scope_pop", body)

    def test_revival_options_call_the_shared_triggers(self):
        text = read(LAW_EVENTS)
        event = raw_block_at(text, r"(?m)^extra_law_events\.25\s*=\s*\{")
        self.assertIsNotNone(event)
        for name, h in REVIVAL_OPTION.items():
            option = raw_block_at(event, r"option\s*=\s*\{\s*# Revive " + re.escape(name) + r"\s*\n")
            self.assertIsNotNone(option, name)
            trigger = squash(block(option, "trigger"))
            self.assertEqual(trigger, f"te_heritage_{h} = yes", name)
        calc = squash(block(event, "calc_true_if"))
        for h in HERITAGES:
            self.assertIn(f"te_heritage_{h} = yes", calc)
        self.assertNotIn("has_discrimination_trait", calc)
        generic = raw_block_at(event, r"option\s*=\s*\{\s*# Revive a classical or historical language")
        self.assertEqual(squash(block(generic, "trigger")), "te_heritage_any = no")


class RuleTests(unittest.TestCase):
    def test_rule_two_settings_default_enabled(self):
        body = block(read(RULES), "grand_monuments_rule")
        self.assertIsNotNone(body)
        self.assertIn("default = grand_monuments_enabled", squash(body))
        for setting in ("grand_monuments_enabled", "grand_monuments_disabled"):
            self.assertIn(f"flag = {setting}", squash(block(body, setting)))

    def test_rule_trigger_tests_the_disabled_setting(self):
        self.assertEqual(squash(block(read(TRIGGERS), "gm_system_enabled")),
                         "NOT = { has_game_rule = grand_monuments_disabled }")

    def test_rule_is_localized(self):
        L = loc()
        self.assertIn("rule_grand_monuments_rule", L)
        for setting in ("grand_monuments_enabled", "grand_monuments_disabled"):
            self.assertIn(f"setting_{setting}", L)
            self.assertIn(f"setting_{setting}_desc", L)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: FAIL/ERROR in `RoutingTests.test_gm_keys_route_to_miscellaneous` (keys route to CONCEPTS/MODIFIERS/RELIGION), `HeritageTests` (`FileNotFoundError`), `RuleTests`.

- [ ] **Step 3: Add the routing rule**

In `organize_loc.py`, `categorize_key`, insert directly after the `if key in technology_keys: return "TECHNOLOGIES"` lines:

```python
    # Grand Monuments (docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md).
    # Every loc-bearing key the system adds carries the gm_ prefix: modifiers
    # (some end in _add-like tokens), skin names ("gm_skin_faith_*", which would
    # otherwise match "religion"-style rules), JE lines and tooltips. Tested
    # before every substring rule so the whole family stays in one file.
    if key.startswith("gm_"):
        return "MISCELLANEOUS"
```

- [ ] **Step 4: Write the shared triggers**

Create `common/scripted_triggers/te_heritage_triggers.txt` (BOM, tabs):

```
# ============================================================================
# CLASSICAL HERITAGE — the classical or liturgical languages a country can
# claim as its own
# ============================================================================
# Country scope. One trigger per language that language reform can revive
# (amendment_langreform_revived_<language>, extra_law_events.25), keyed on a
# primary culture's language, and for Hebrew, Sanskrit, Pali and Coptic on the
# state religion. Shared by language reform (which revival it offers) and the
# Grand Monuments (which heritage skins a monument may take, spec
# docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md §1.1), so
# the two cannot drift apart. test_grand_monument_registry.py pins the list and
# that extra_law_events.25 calls these.

te_heritage_latin = {
	any_primary_culture = { has_discrimination_trait_group = language_group_romance }
}

te_heritage_hebrew = {
	OR = {
		country_has_state_religion = rel:jewish
		any_primary_culture = { has_discrimination_trait_group = language_group_semitic }
	}
}

te_heritage_sanskrit = {
	OR = {
		any_primary_culture = { has_discrimination_trait_group = language_group_indo_aryan }
		country_has_state_religion = rel:hindu
	}
}

te_heritage_geez = {
	any_primary_culture = {
		OR = {
			has_discrimination_trait = language_amharic
			has_discrimination_trait = language_tigrinya
		}
	}
}

te_heritage_slavonic = {
	any_primary_culture = { has_discrimination_trait_group = language_group_slavic }
}

te_heritage_pali = {
	country_has_state_religion = rel:theravada
}

te_heritage_avestan = {
	any_primary_culture = { has_discrimination_trait_group = language_group_iranic }
}

te_heritage_arabic = {
	any_primary_culture = { has_discrimination_trait = language_arabic }
}

te_heritage_chinese = {
	any_primary_culture = {
		OR = {
			has_discrimination_trait_group = language_group_sinitic
			has_discrimination_trait = language_japanese
			has_discrimination_trait = language_korean
		}
	}
}

te_heritage_greek = {
	any_primary_culture = { has_discrimination_trait_group = language_group_hellenic }
}

te_heritage_irish = {
	any_primary_culture = { has_discrimination_trait = language_gaelic }
}

te_heritage_coptic = {
	country_has_state_religion = rel:oriental_orthodox
}

te_heritage_nahuatl = {
	any_primary_culture = { has_discrimination_trait = language_nahuan }
}

te_heritage_norse = {
	any_primary_culture = { has_discrimination_trait = language_scandinavian }
}

te_heritage_gothic = {
	any_primary_culture = { has_discrimination_trait_group = language_group_germanic }
}

te_heritage_mayan = {
	any_primary_culture = { has_discrimination_trait = language_mayan }
}

te_heritage_prussian = {
	any_primary_culture = { has_discrimination_trait_group = language_group_baltic }
}

te_heritage_aramaic = {
	any_primary_culture = { has_discrimination_trait = language_aramaic }
}

# Country scope. True if any of the eighteen holds. The generic revival option
# offers itself only when none does.
te_heritage_any = {
	OR = {
		te_heritage_latin = yes
		te_heritage_hebrew = yes
		te_heritage_sanskrit = yes
		te_heritage_geez = yes
		te_heritage_slavonic = yes
		te_heritage_pali = yes
		te_heritage_avestan = yes
		te_heritage_arabic = yes
		te_heritage_chinese = yes
		te_heritage_greek = yes
		te_heritage_irish = yes
		te_heritage_coptic = yes
		te_heritage_nahuatl = yes
		te_heritage_norse = yes
		te_heritage_gothic = yes
		te_heritage_mayan = yes
		te_heritage_prussian = yes
		te_heritage_aramaic = yes
	}
}
```

- [ ] **Step 5: Point language reform at them**

In `events/extra_law_events.txt`, inside `extra_law_events.25` (starts near line 1844):

(a) Replace the body of the `calc_true_if = { … }` block (keep `amount >= 2` as its first line) with:

```
						amount >= 2
						te_heritage_latin = yes
						te_heritage_hebrew = yes
						te_heritage_sanskrit = yes
						te_heritage_geez = yes
						te_heritage_slavonic = yes
						te_heritage_pali = yes
						te_heritage_avestan = yes
						te_heritage_arabic = yes
						te_heritage_chinese = yes
						te_heritage_greek = yes
						te_heritage_irish = yes
						te_heritage_coptic = yes
						te_heritage_nahuatl = yes
						te_heritage_norse = yes
						te_heritage_gothic = yes
						te_heritage_mayan = yes
						te_heritage_prussian = yes
						te_heritage_aramaic = yes
```

(b) In each revival option, replace its whole `trigger = { … }` block with a one-line call. The option is found by its comment; nothing else in the option changes:

| Option comment | New trigger |
|---|---|
| `# Revive Latin` | `trigger = { te_heritage_latin = yes }` |
| `# Revive Hebrew` | `trigger = { te_heritage_hebrew = yes }` |
| `# Revive Sanskrit` | `trigger = { te_heritage_sanskrit = yes }` |
| `# Revive Ge'ez` | `trigger = { te_heritage_geez = yes }` |
| `# Revive Old Church Slavonic` | `trigger = { te_heritage_slavonic = yes }` |
| `# Revive Pali` | `trigger = { te_heritage_pali = yes }` |
| `# Revive Avestan` | `trigger = { te_heritage_avestan = yes }` |
| `# Revive Classical Arabic` | `trigger = { te_heritage_arabic = yes }` |
| `# Revive Literary Chinese` | `trigger = { te_heritage_chinese = yes }` |
| `# Revive Classical Greek` | `trigger = { te_heritage_greek = yes }` |
| `# Revive Classical Irish (Gaeilge)` | `trigger = { te_heritage_irish = yes }` |
| `# Revive Coptic` | `trigger = { te_heritage_coptic = yes }` |
| `# Revive Classical Nahuatl` | `trigger = { te_heritage_nahuatl = yes }` |
| `# Revive Old Norse` | `trigger = { te_heritage_norse = yes }` |
| `# Revive Gothic` | `trigger = { te_heritage_gothic = yes }` |
| `# Revive Classic Mayan` | `trigger = { te_heritage_mayan = yes }` |
| `# Revive Old Prussian` | `trigger = { te_heritage_prussian = yes }` |
| `# Revive Aramaic` | `trigger = { te_heritage_aramaic = yes }` |
| `# Revive a classical or historical language (generic)` | `trigger = { te_heritage_any = no }` |

Write each as three lines, tab-indented to the option's level:

```
		trigger = {
			te_heritage_latin = yes
		}
```

Leave the event's `desc` `triggered_desc` blocks alone: they choose description text, not which revival is offered.

- [ ] **Step 6: The game rule and its trigger**

Append to `common/game_rules/extra_game_rules.txt`:

```

# Grand Monuments (docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md
# §7). Disabled makes the building unbuildable and stops the pulses, the
# dedication ceremony and the Monuments journal entry. Every check is written
# NOT = { has_game_rule = grand_monuments_disabled } (gm_system_enabled), so a
# save started before the rule existed stays enabled.
grand_monuments_rule = {
	default = grand_monuments_enabled

	grand_monuments_enabled = {
		flag = grand_monuments_enabled
	}

	grand_monuments_disabled = {
		flag = grand_monuments_disabled
	}
}
```

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  The game rule (spec §7)
# ======================================================================
# Any scope. The Grand Monument system runs under this rule setting.
gm_system_enabled = {
	NOT = { has_game_rule = grand_monuments_disabled }
}
```

Add to `localization/english/te_game_rules_l_english.yml`, in key order:

```yaml
 rule_grand_monuments_rule:0 "Grand Monuments"
 setting_grand_monuments_enabled:0 "Grand Monuments Enabled"
 setting_grand_monuments_enabled_desc:0 "Countries may raise Grand Monuments to their crown, republic, revolution, leader, faith or nation. What a monument honours can fall with the regime that raised it, and the next government decides whether to pull it down, rededicate it or keep it as heritage."
 setting_grand_monuments_disabled:0 "Grand Monuments Disabled"
 setting_grand_monuments_disabled_desc:0 "The Grand Monument cannot be built, and no monument ceremony, contest or journal entry runs."
```

- [ ] **Step 7: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all tests OK (8 so far).
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_triggers/te_heritage_triggers.txt events/extra_law_events.txt common/game_rules/extra_game_rules.txt common/scripted_triggers/monument_triggers.txt && python3 scripts/analysis/check_localization_files.py && python3 -m unittest test_organize_loc`
Expected: all exit 0.

- [ ] **Step 8: Commit**

```bash
git add organize_loc.py common/scripted_triggers/te_heritage_triggers.txt events/extra_law_events.txt \
        common/game_rules/extra_game_rules.txt common/scripted_triggers/monument_triggers.txt \
        localization/english/te_game_rules_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): shared heritage triggers, the game rule, gm_ loc routing

Language reform's revival partition moves into eighteen te_heritage_<language>
triggers, which the monuments' heritage skins will share. grand_monuments_rule:
enabled / disabled. Every gm_ loc key routes to te_miscellaneous.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 2: The curve, the step values and the modifiers

**Files:**
- Create: `common/script_values/gm_values.txt`
- Create: `common/static_modifiers/gm_modifiers.txt`
- Modify: `common/game_concepts/extra_concepts.txt` (append `concept_grandeur`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `localization/english/te_concepts_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `CurveTests`, `ModifierTests`)

**Interfaces:**
- Consumes: nothing.
- Produces (script values, read `var:gm_curve_in` on the current scope): `gm_curve_steps_f5`, `gm_curve_steps_f10` (fractional steps, 0–8), `gm_curve_next_f5`, `gm_curve_next_f10` (grandeur at which the step being filled completes).
- Produces (constants): `gm_step_prestige`, `gm_step_legitimacy`, `gm_step_ig`, `gm_step_teardown`, `gm_step_vanity`, `gm_step_tourism`, `gm_step_culture`, `gm_step_local_<key>` (12), `gm_step_national_<key>` for leader, religious, war_memorial, artistic, scientific, industrial; `gm_event_cost` (country: −2% of yearly gross income), `gm_event_income` (country: +1%).
- Produces (static modifiers): `gm_national_prestige`, `gm_national_legitimacy`, `gm_national_<key>` (the six above), `gm_national_teardown`, `gm_national_vanity`, `gm_ig_approval_<ig>` (8), `gm_local_tourism`, `gm_local_<key>` (12).
- Produces (concept): `concept_grandeur`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`, above `if __name__ == "__main__":`:

```python
# ---- Task 2: the curve, the step values, the modifiers -------------------------------

NATIONAL = ("leader", "religious", "war_memorial", "artistic", "scientific", "industrial")


def curve_terms(f):
    """(start, size) of the eight steps of a curve with first step f."""
    return [(f * (2 ** k - 1), f * 2 ** k) for k in range(8)]


class CurveTests(unittest.TestCase):
    def _terms(self, name):
        body = squash(block(read(VALUES), name))
        self.assertIsNotNone(body, name)
        return re.findall(r"add = \{ value = var:gm_curve_in (?:subtract = (\d+) )?divide = (\d+) "
                          r"min = 0 max = 1 \}", body)

    def test_steps_double(self):
        for f in (5, 10):
            terms = [(int(s or 0), int(d)) for s, d in self._terms(f"gm_curve_steps_f{f}")]
            self.assertEqual(terms, curve_terms(f), f)

    def test_next_thresholds(self):
        for f in (5, 10):
            body = squash(block(read(VALUES), f"gm_curve_next_f{f}"))
            ends = [f * (2 ** n - 1) for n in range(1, 9)]
            self.assertTrue(body.startswith(f"value = {ends[-1]} "), f)
            for end in ends[:-1]:
                self.assertIn(f"if = {{ limit = {{ var:gm_curve_in < {end} }} value = {end} }}", body)


class ModifierTests(unittest.TestCase):
    def _mod(self, name):
        body = block(read(MODIFIERS), name)
        self.assertIsNotNone(body, name)
        return body

    def assert_pair(self, modifier, field, step_name, expected):
        self.assertAlmostEqual(number(self._mod(modifier), field), expected, msg=modifier)
        mirror = re.search(r"(?m)^" + step_name + r"\s*=\s*(-?\d+(?:\.\d+)?)\s*$",
                           strip_comments(read(VALUES)))
        self.assertIsNotNone(mirror, step_name)
        self.assertAlmostEqual(float(mirror.group(1)), expected, msg=step_name)

    def test_national_pairs(self):
        self.assert_pair("gm_national_prestige", "country_prestige_add", "gm_step_prestige", 25)
        self.assert_pair("gm_national_legitimacy", "country_legitimacy_base_add", "gm_step_legitimacy", 2)
        self.assert_pair("gm_national_teardown", "country_legitimacy_base_add", "gm_step_teardown", 3)
        self.assert_pair("gm_national_vanity", "country_legitimacy_base_add", "gm_step_vanity", -3)
        for key in NATIONAL:
            d = BY_KEY[key]
            self.assert_pair(f"gm_national_{key}", d.national_field, f"gm_step_national_{key}",
                             d.national_step)
        self.assertEqual({d.key for d in DEDICATIONS if d.national_field}, set(NATIONAL))

    def test_ig_pairs(self):
        for ig in IGS:
            self.assert_pair(f"gm_ig_approval_{ig}", f"interest_group_ig_{ig}_approval_add",
                             "gm_step_ig", 1)

    def test_local_pairs(self):
        self.assert_pair("gm_local_tourism", "building_tourism_industry_throughput_add",
                         "gm_step_tourism", 0.25)
        for d in DEDICATIONS:
            self.assert_pair(f"gm_local_{d.key}", d.local_field, f"gm_step_local_{d.key}", d.local_step)

    def test_culture_step(self):
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^gm_step_culture = 1\s*$")

    def test_each_modifier_has_one_field_and_an_icon(self):
        for name, body in top_level_blocks(read(MODIFIERS)):
            if not name.startswith(("gm_national_", "gm_ig_approval_", "gm_local_")):
                continue
            fields = [k for k in re.findall(r"(?m)^\s*(\w+)\s*=", body) if k != "icon"]
            self.assertEqual(len(fields), 1, name)
            self.assertIn("modifier_statue_", body, name)

    def test_modifiers_are_localized(self):
        L = loc()
        for name, _ in top_level_blocks(read(MODIFIERS)):
            self.assertIn(name, L, name)
            self.assertIn(f"{name}_desc", L, name)

    def test_concept(self):
        self.assertIsNotNone(block(read(CONCEPTS), "concept_grandeur"))
        L = loc()
        self.assertIn("concept_grandeur", L)
        self.assertIn("concept_grandeur_desc", L)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: `CurveTests`, `ModifierTests` ERROR (`FileNotFoundError` for `gm_values.txt`).

- [ ] **Step 3: Write the script values**

Create `common/script_values/gm_values.txt` (BOM, tabs):

```
# ============================================================================
# GRAND MONUMENTS — script values
# ============================================================================
# Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.

# ---- The doubling curve (§2.2) ---------------------------------------------
# Every effect a monument gives grows in steps of equal size, and each step
# costs twice the grandeur of the one before. With a first step of f, step n
# completes at f * (2^n - 1): for f = 5, at 5, 15, 35, 75, 155, 315, 635 and
# 1275. Inside a step the value grows linearly, so no level is wasted.
#
# Input: var:gm_curve_in on the current scope, which the caller sets first.
# Output: the fractional number of steps, 0-8. Each term is one step's share,
# clamped to 0-1 (min, then max: sequential clamps).
gm_curve_steps_f5 = {
	value = 0
	add = { value = var:gm_curve_in divide = 5 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 5 divide = 10 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 15 divide = 20 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 35 divide = 40 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 75 divide = 80 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 155 divide = 160 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 315 divide = 320 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 635 divide = 640 min = 0 max = 1 }
}

gm_curve_steps_f10 = {
	value = 0
	add = { value = var:gm_curve_in divide = 10 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 10 divide = 20 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 30 divide = 40 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 70 divide = 80 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 150 divide = 160 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 310 divide = 320 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 630 divide = 640 min = 0 max = 1 }
	add = { value = var:gm_curve_in subtract = 1270 divide = 1280 min = 0 max = 1 }
}

# The grandeur at which the step now being filled completes ("next step at"
# in the journal entry). Each later `if` overrides the earlier, so the result
# is the smallest step end above the input; the last end once the curve is
# complete.
gm_curve_next_f5 = {
	value = 1275
	if = { limit = { var:gm_curve_in < 635 } value = 635 }
	if = { limit = { var:gm_curve_in < 315 } value = 315 }
	if = { limit = { var:gm_curve_in < 155 } value = 155 }
	if = { limit = { var:gm_curve_in < 75 } value = 75 }
	if = { limit = { var:gm_curve_in < 35 } value = 35 }
	if = { limit = { var:gm_curve_in < 15 } value = 15 }
	if = { limit = { var:gm_curve_in < 5 } value = 5 }
}

gm_curve_next_f10 = {
	value = 2550
	if = { limit = { var:gm_curve_in < 1270 } value = 1270 }
	if = { limit = { var:gm_curve_in < 630 } value = 630 }
	if = { limit = { var:gm_curve_in < 310 } value = 310 }
	if = { limit = { var:gm_curve_in < 150 } value = 150 }
	if = { limit = { var:gm_curve_in < 70 } value = 70 }
	if = { limit = { var:gm_curve_in < 30 } value = 30 }
	if = { limit = { var:gm_curve_in < 10 } value = 10 }
}

# ---- Per-step values (§9) ------------------------------------------------------
# Mirrors of the static modifiers in gm_modifiers.txt, each of which carries
# exactly one step (the multiplier is the step count). Loc reads these; the
# registry test pins every pair equal.
gm_step_prestige = 25
gm_step_legitimacy = 2
gm_step_ig = 1
gm_step_teardown = 3
gm_step_vanity = -3
gm_step_tourism = 0.25
gm_step_culture = 1

gm_step_local_crown = 0.10
gm_step_local_republic = 0.10
gm_step_local_revolution = 0.10
gm_step_local_leader = 0.10
gm_step_local_religious = 0.10
gm_step_local_civic = 0.10
gm_step_local_war_memorial = 0.05
gm_step_local_artistic = 0.10
gm_step_local_naturalist = -5000
gm_step_local_scientific = 0.00025
gm_step_local_industrial = 0.10
gm_step_local_athletic = -0.10

gm_step_national_leader = 25
gm_step_national_religious = 0.05
gm_step_national_war_memorial = -0.03
gm_step_national_artistic = 0.05
gm_step_national_scientific = 3
gm_step_national_industrial = 0.05

# ---- Money (§6.1, plan decision 7) -------------------------------------------
# Country scope. What a flavour event's paid option costs, and what a
# money-in option brings.
gm_event_cost = {
	value = yearly_gross_income
	multiply = -0.02
}

gm_event_income = {
	value = yearly_gross_income
	multiply = 0.01
}
```

- [ ] **Step 4: Write the static modifiers**

Create `common/static_modifiers/gm_modifiers.txt` (BOM, tabs). Every modifier carries one step (Global Constraints):

```
# ============================================================================
# GRAND MONUMENTS — static modifiers
# ============================================================================
# Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
# Each carries ONE STEP of the doubling curve (§2.2); the multiplier is the
# step count. gm_values.txt mirrors every value as gm_step_*; change both.

# ---- National totals (§2.4): on je:je_grand_monuments ------------------------
# Refreshed by gm_apply_national_modifiers (gm_effects.txt), ROOT = country.
gm_national_prestige = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_prestige_add = 25
}

gm_national_legitimacy = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_legitimacy_base_add = 2
}

gm_national_leader = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_authority_add = 25
}

gm_national_religious = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_devout_pop_attraction_mult = 0.05
}

gm_national_war_memorial = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_war_support_casualties_mult = -0.03
}

gm_national_artistic = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_intelligentsia_pop_attraction_mult = 0.05
}

gm_national_scientific = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_weekly_innovation_max_add = 3
}

gm_national_industrial = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_industrialists_pop_attraction_mult = 0.05
}

# Tear Down's reward (§4.3), from the decaying teardown ledger through the curve.
gm_national_teardown = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_negative.dds
	country_legitimacy_base_add = 3
}

# Vanity backlash (§5): the multiplier is the vanity ledger itself, LINEAR.
gm_national_vanity = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_negative.dds
	country_legitimacy_base_add = -3
}

# ---- IG approval (§2.4): one per IG, signed multiplier -----------------------
gm_ig_approval_armed_forces = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_armed_forces_approval_add = 1
}

gm_ig_approval_devout = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_devout_approval_add = 1
}

gm_ig_approval_industrialists = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_industrialists_approval_add = 1
}

gm_ig_approval_intelligentsia = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_intelligentsia_approval_add = 1
}

gm_ig_approval_landowners = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_landowners_approval_add = 1
}

gm_ig_approval_petty_bourgeoisie = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_petty_bourgeoisie_approval_add = 1
}

gm_ig_approval_rural_folk = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_rural_folk_approval_add = 1
}

gm_ig_approval_trade_unions = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_trade_unions_approval_add = 1
}

# ---- Local (§2.5): on the monument's state, multiplier = its own steps -------
# Refreshed by gm_state_monthly (gm_effects.txt) from on_monthly_pulse_state.
gm_local_tourism = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	building_tourism_industry_throughput_add = 0.25
}

gm_local_crown = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_loyalists_from_political_movements_mult = 0.10
}

gm_local_republic = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_loyalists_from_political_movements_mult = 0.10
}

gm_local_revolution = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_loyalists_from_political_movements_mult = 0.10
}

gm_local_leader = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_loyalists_from_political_movements_mult = 0.10
}

gm_local_religious = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_conversion_mult = 0.10
}

gm_local_civic = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_loyalists_from_political_movements_mult = 0.10
}

gm_local_war_memorial = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_conscription_rate_add = 0.05
}

gm_local_artistic = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	building_art_academy_throughput_add = 0.10
}

gm_local_naturalist = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_pollution_generation_add = -5000
}

gm_local_scientific = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_literacy_growth_add = 0.00025
}

gm_local_industrial = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_migration_pull_mult = 0.10
}

gm_local_athletic = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_turmoil_effects_mult = -0.10
}
```

- [ ] **Step 5: The concept**

Append to `common/game_concepts/extra_concepts.txt`:

```

concept_grandeur = {
	texture = "gfx/interface/icons/building_icons/building_government_administration.dds"
}
```

Add to `localization/english/te_concepts_l_english.yml`, in key order:

```yaml
 concept_grandeur:0 "Grandeur"
 concept_grandeur_desc:0 "A $building_grand_monument$'s grandeur is its level. Everything a monument gives grows with grandeur in steps: the first step takes 5 grandeur, and each further step takes twice as much as the one before (complete at 5, 15, 35, 75, 155 and so on). Inside a step every level counts. Legitimacy and cultural pull take steps of 10 instead. National effects count your monuments' grandeur together; local effects count each monument's own."
```

- [ ] **Step 6: Loc for the modifiers**

Add to `localization/english/te_miscellaneous_l_english.yml`, in key order (every `gm_*` key goes here):

```yaml
 gm_ig_approval_armed_forces:0 "Grand Monuments"
 gm_ig_approval_armed_forces_desc:0 "How the $ig_armed_forces$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_devout:0 "Grand Monuments"
 gm_ig_approval_devout_desc:0 "How the $ig_devout$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_industrialists:0 "Grand Monuments"
 gm_ig_approval_industrialists_desc:0 "How the $ig_industrialists$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_intelligentsia:0 "Grand Monuments"
 gm_ig_approval_intelligentsia_desc:0 "How the $ig_intelligentsia$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_landowners:0 "Grand Monuments"
 gm_ig_approval_landowners_desc:0 "How the $ig_landowners$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_petty_bourgeoisie:0 "Grand Monuments"
 gm_ig_approval_petty_bourgeoisie_desc:0 "How the $ig_petty_bourgeoisie$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_rural_folk:0 "Grand Monuments"
 gm_ig_approval_rural_folk_desc:0 "How the $ig_rural_folk$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_ig_approval_trade_unions:0 "Grand Monuments"
 gm_ig_approval_trade_unions_desc:0 "How the $ig_trade_unions$ regard what our monuments honour. It grows with the [concept_grandeur] of the monuments they approve of, falls with those they oppose, and follows what we did with contested monuments."
 gm_local_artistic:0 "Grand Monument: Opera House"
 gm_local_artistic_desc:0 "A grand opera house in this state. Grows with its [concept_grandeur]."
 gm_local_athletic:0 "Grand Monument: Stadium"
 gm_local_athletic_desc:0 "A grand stadium in this state. Grows with its [concept_grandeur]."
 gm_local_civic:0 "Grand Monument: To the Nation"
 gm_local_civic_desc:0 "A monument to the nation in this state. Grows with its [concept_grandeur]."
 gm_local_crown:0 "Grand Monument: To the Crown"
 gm_local_crown_desc:0 "A monument to the Crown in this state. Grows with its [concept_grandeur]."
 gm_local_industrial:0 "Grand Monument: Exhibition Hall"
 gm_local_industrial_desc:0 "A great exhibition hall in this state. Grows with its [concept_grandeur]."
 gm_local_leader:0 "Grand Monument: To the Leader"
 gm_local_leader_desc:0 "A monument to the country's leader in this state. Grows with its [concept_grandeur]."
 gm_local_naturalist:0 "Grand Monument: Gardens"
 gm_local_naturalist_desc:0 "Botanical gardens in this state. Grows with their [concept_grandeur]."
 gm_local_religious:0 "Grand Monument: Shrine"
 gm_local_religious_desc:0 "A grand shrine in this state. Grows with its [concept_grandeur]."
 gm_local_republic:0 "Grand Monument: To the Republic"
 gm_local_republic_desc:0 "A monument to the republic in this state. Grows with its [concept_grandeur]."
 gm_local_revolution:0 "Grand Monument: To the Revolution"
 gm_local_revolution_desc:0 "A monument to the revolution in this state. Grows with its [concept_grandeur]."
 gm_local_scientific:0 "Grand Monument: Observatory"
 gm_local_scientific_desc:0 "A grand observatory in this state. Grows with its [concept_grandeur]."
 gm_local_tourism:0 "Grand Monument"
 gm_local_tourism_desc:0 "Visitors come to see this state's Grand Monument. Grows with its [concept_grandeur], whatever it honours."
 gm_local_war_memorial:0 "Grand Monument: War Memorial"
 gm_local_war_memorial_desc:0 "A war memorial in this state. Grows with its [concept_grandeur]."
 gm_national_artistic:0 "Grand Opera Houses"
 gm_national_artistic_desc:0 "From the [concept_grandeur] of our grand opera houses, counted together."
 gm_national_industrial:0 "Great Exhibition Halls"
 gm_national_industrial_desc:0 "From the [concept_grandeur] of our great exhibition halls, counted together."
 gm_national_leader:0 "Monuments to the Leader"
 gm_national_leader_desc:0 "From the [concept_grandeur] of our monuments to the leader who still rules, counted together."
 gm_national_legitimacy:0 "Monuments to the Regime"
 gm_national_legitimacy_desc:0 "From the [concept_grandeur] of our monuments to the Crown, the republic, the revolution or the leader, counted together while what they honour still stands."
 gm_national_prestige:0 "Grand Monuments"
 gm_national_prestige_desc:0 "From the [concept_grandeur] of every monument we own that is not contested, heritage included."
 gm_national_religious:0 "Grand Shrines"
 gm_national_religious_desc:0 "From the [concept_grandeur] of our grand shrines, counted together while our faith is the one they honour."
 gm_national_scientific:0 "Grand Observatories"
 gm_national_scientific_desc:0 "From the [concept_grandeur] of our grand observatories, counted together."
 gm_national_teardown:0 "The Old Order Torn Down"
 gm_national_teardown_desc:0 "We pulled down monuments to an order that has fallen. The new government's standing gained from it, and the gain fades over about five years."
 gm_national_vanity:0 "Palaces amid Hardship"
 gm_national_vanity_desc:0 "We finished monument levels while the country was in default, famine or recession. The resentment fades over about two years."
 gm_national_war_memorial:0 "War Memorials"
 gm_national_war_memorial_desc:0 "From the [concept_grandeur] of our war memorials, counted together."
```

- [ ] **Step 7: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all tests OK (17 so far).
Run: `python3 scripts/format_paradox_tabs.py --check common/script_values/gm_values.txt common/static_modifiers/gm_modifiers.txt common/game_concepts/extra_concepts.txt && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add common/script_values/gm_values.txt common/static_modifiers/gm_modifiers.txt \
        common/game_concepts/extra_concepts.txt localization/english/te_miscellaneous_l_english.yml \
        localization/english/te_concepts_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): the doubling curve, per-step values and the modifiers

One script value per first-step size turns grandeur into a step count (8
steps, each twice the last). Every static modifier carries one step; the
gm_step_* mirrors feed loc and are pinned equal to them.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 3: Staff-only dedications, four new PMs, the building

**Files:**
- Rewrite: `common/production_methods/grand_monument_pms.txt`
- Modify: `common/production_method_groups/grand_monument_pmgs.txt`
- Modify: `common/buildings/grand_monuments.txt`
- Modify: `common/scripted_triggers/monument_triggers.txt` (append gates and hard times)
- Modify: `localization/english/te_production_methods_l_english.yml`, `te_buildings_l_english.yml`, `te_miscellaneous_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `PMTests`, `BuildingTests`)

**Interfaces:**
- Consumes: `gm_system_enabled` (Task 1).
- Produces (PMs): `pm_monument_undedicated` (default), `pm_monument_<key>` for every `DEDICATIONS` key.
- Produces (triggers, country scope): `gm_country_hard_times`, `gm_government_is_revolutionary`, `gm_can_raise_leader_monument`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 3: staff-only dedications, the building ------------------------------------

class PMTests(unittest.TestCase):
    def test_group_lists_every_dedication(self):
        group = squash(block(read(PMG), "pmg_monument_dedication"))
        for d in DEDICATIONS:
            self.assertIn(f"pm_monument_{d.key}", group)
        self.assertIn("pm_monument_undedicated", group)

    def test_ratchet(self):
        text = read(PMS)
        undedicated = squash(block(text, "pm_monument_undedicated"))
        self.assertIn("is_default = yes", undedicated)
        self.assertIn("unlocking_production_methods = { pm_monument_undedicated }", undedicated)
        for d in DEDICATIONS:
            body = squash(block(text, f"pm_monument_{d.key}"))
            self.assertIn(f"unlocking_production_methods = {{ pm_monument_undedicated pm_monument_{d.key} }}",
                          body, d.key)
            self.assertIn("is_hidden_when_unavailable = yes", body, d.key)
            self.assertNotIn("replacement_if_valid", body, d.key)

    def test_staff_only(self):
        text = read(PMS)
        for name in ["pm_monument_undedicated"] + [f"pm_monument_{d.key}" for d in DEDICATIONS]:
            body = squash(block(text, name))
            for forbidden in ("country_modifiers", "state_modifiers", "goods_output", "goods_input",
                              "level_scaled", "workforce_scaled"):
                self.assertNotIn(forbidden, body, f"{name}: {forbidden}")
            self.assertIn("unscaled = { building_employment_laborers_add = 200 "
                          "building_employment_clerks_add = 50 }", body, name)

    def test_tech_gates(self):
        text = read(PMS)
        for d in DEDICATIONS:
            body = squash(block(text, f"pm_monument_{d.key}"))
            if d.key in TECH_GATES:
                self.assertIn(f"unlocking_technologies = {{ {TECH_GATES[d.key]} }}", body, d.key)
            else:
                self.assertNotIn("unlocking_technologies", body, d.key)

    def test_pms_localized(self):
        L = loc()
        for d in DEDICATIONS:
            self.assertIn(f"pm_monument_{d.key}", L)
            self.assertIn(f"pm_monument_{d.key}_desc", L)
        self.assertEqual(L["pm_monument_civic"], "To the Nation")


class BuildingTests(unittest.TestCase):
    def test_possible_reads_the_rule(self):
        possible = squash(block(read(BUILDING), "possible"))
        self.assertIn("text = gm_possible_rule_tt gm_system_enabled = yes", possible)
        self.assertIn("gm_possible_rule_tt", loc())

    def test_ai_avoids_hard_times_and_war(self):
        ai = squash(block(read(BUILDING), "ai_value"))
        self.assertIn("owner = { gm_country_hard_times = yes } } add = -100", ai)
        self.assertIn("owner = { is_at_war = yes } } add = -100", ai)
        self.assertIn("owner = { government_legitimacy < 40 } } add = 25", ai)

    def test_hard_times(self):
        body = squash(block(read(TRIGGERS), "gm_country_hard_times"))
        self.assertIn("in_default = yes", body)
        self.assertIn("has_famine = yes", body)
        self.assertIn("AND = { has_variable = finance_cycle_value banking_cycle_is_recession = yes }", body)

    def test_regime_gates(self):
        text = read(TRIGGERS)
        revolutionary = squash(block(text, "gm_government_is_revolutionary"))
        self.assertIn("law_type:law_single_party_state", revolutionary)
        self.assertIn("law_type:law_council_republic", revolutionary)
        leader = squash(block(text, "gm_can_raise_leader_monument"))
        self.assertIn("law_type:law_autocracy", leader)
        self.assertIn("law_type:law_single_party_state", leader)
        self.assertIn("monument_government_is_crowned = no", leader)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: `PMTests`, `BuildingTests` FAIL (new PMs missing; old PMs carry modifiers).

- [ ] **Step 3: Rewrite the PMs**

Replace the whole of `common/production_methods/grand_monument_pms.txt` (BOM, tabs):

```
#==================================================
# Grand Monument dedications
#==================================================
# Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
#
# THE RATCHET -- why every PM below lists itself in unlocking_production_methods.
#
# The engine has no "lock this PM once chosen" feature, so the lock is built
# out of unlocking_production_methods, which is an OR over its list:
#
#   pm_monument_undedicated  unlocks on { itself }
#   every dedication         unlocks on { pm_monument_undedicated, itself }
#
# Fresh build  -> Undedicated is active (is_default), so every dedication is
#                 available. After a pick -> only the chosen PM's own
#                 self-reference is satisfied. The choice is permanent;
#                 Rededicate (§4.3) rebuilds the monument.
#
# Every PM carries is_hidden_when_unavailable so the group shows one row.
# Do NOT add replacement_if_valid to any of these -- it would defeat the ratchet.
#
# STAFF ONLY. A dedication PM carries the caretaker staff and nothing else.
# Every effect a monument gives -- local and national -- is a modifier that a
# monthly pulse refreshes along the doubling curve (§2): gm_state_monthly for
# the state, gm_country_refresh for the nation, both in
# common/scripted_effects/gm_effects.txt. The registry test fails if a PM here
# carries country_modifiers, state_modifiers or goods.
#
# The dedication is set by the ceremony (monument_events.2) through
# activate_production_method; a pick made in the building panel is recorded by
# the first monthly pulse that sees it (gm_state_first_sight).

# Entry point and fallback: a monument whose meaning is not yet settled.
pm_monument_undedicated = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes
	is_default = yes

	unlocking_production_methods = {
		pm_monument_undedicated
	}

	building_modifiers = {
		# A caretaker staff, not a workforce that grows with the monument's height.
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Regime: to the Crown. Fits while the government is crowned.
pm_monument_crown = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_crown
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Regime: to the republic. Fits while the government is republican.
pm_monument_republic = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_republic
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Regime: to the revolution. Fits under a Single-Party State or a Council Republic.
pm_monument_revolution = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_revolution
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Ruler: to the leader. Fits while the honoured character still rules.
pm_monument_leader = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_leader
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Faith: a grand shrine to the state religion.
pm_monument_religious = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_religious
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: to the nation. The key is the old Civic Monument's, so monuments
# in older saves keep their dedication (§8).
pm_monument_civic = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_civic
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: a memorial to the fallen.
pm_monument_war_memorial = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_war_memorial
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: a grand opera house.
pm_monument_artistic = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_technologies = {
		romanticism
	}

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_artistic
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: botanical gardens.
pm_monument_naturalist = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_technologies = {
		romanticism
	}

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_naturalist
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: a grand observatory.
pm_monument_scientific = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_technologies = {
		empiricism
	}

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_scientific
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: a great exhibition hall.
pm_monument_industrial = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_technologies = {
		marketing_research
	}

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_industrial
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}

# Timeless: a grand stadium.
pm_monument_athletic = {
	texture = "gfx/interface/icons/production_method_icons/cat_star_gold_p0.dds"
	is_hidden_when_unavailable = yes

	unlocking_technologies = {
		television_broadcasting
	}

	unlocking_production_methods = {
		pm_monument_undedicated
		pm_monument_athletic
	}

	building_modifiers = {
		unscaled = {
			building_employment_laborers_add = 200
			building_employment_clerks_add = 50
		}
	}
}
```

- [ ] **Step 4: The group**

In `common/production_method_groups/grand_monument_pmgs.txt`, replace the `production_methods = { … }` list with:

```
	production_methods = {
		pm_monument_undedicated
		pm_monument_crown
		pm_monument_republic
		pm_monument_revolution
		pm_monument_leader
		pm_monument_religious
		pm_monument_civic
		pm_monument_war_memorial
		pm_monument_artistic
		pm_monument_naturalist
		pm_monument_scientific
		pm_monument_industrial
		pm_monument_athletic
	}
```

- [ ] **Step 5: The building**

In `common/buildings/grand_monuments.txt`:

(a) Replace the header comment (the lines above `building_grand_monument = {`) with:

```
#==================================================
# Grand Monuments
#==================================================
# A monument a regime raises to what it stands for: its crown, republic,
# revolution, leader, faith or nation. Expensive to build, cheap to run,
# repeatable (one per state, levels uncapped). Its level is its GRANDEUR; every
# effect grows with grandeur along the doubling curve, and national effects
# come from national totals on the Monuments journal entry, never from each
# building separately.
# Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
#
# Group is bg_grand_monuments, NOT bg_monuments -- see common/building_groups/
# extra_building_groups.txt for why that separation is load-bearing.
```

(b) Add after `required_construction = construction_cost_grand_monument`:

```

	# The game rule (spec §7).
	possible = {
		custom_tooltip = {
			text = gm_possible_rule_tt
			gm_system_enabled = yes
		}
	}
```

(c) Replace the whole `ai_value = { … }` block with:

```
	# Evaluated in STATE scope: ROOT is the state, owner reaches the country.
	ai_value = {
		value = 0

		# Only interesting to countries with money to spare.
		if = {
			limit = {
				owner = { is_great_or_major_power = yes }
			}
			add = 25
		}

		# The Tourism Industry throughput pays off where one exists.
		if = {
			limit = { has_building = building_tourism_industry }
			add = 50
		}

		# A regime short of legitimacy is the one that raises monuments (§7).
		if = {
			limit = {
				owner = { government_legitimacy < 40 }
			}
			add = 25
		}

		# Never at the expense of the war effort.
		if = {
			limit = {
				owner = { is_at_war = yes }
			}
			add = -100
		}

		# Never in hard times: a level finished then costs legitimacy (§5).
		if = {
			limit = {
				owner = { gm_country_hard_times = yes }
			}
			add = -100
		}
	}
```

- [ ] **Step 6: The country-level gates**

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  Country gates (spec §1, §5)
# ======================================================================
# Country scope. The regime To the Revolution honours.
gm_government_is_revolutionary = {
	OR = {
		has_law_or_variant = law_type:law_single_party_state
		has_law_or_variant = law_type:law_council_republic
	}
}

# Country scope. A personality cult: Autocracy or a Single-Party State under a
# head of state who is not crowned (a crowned ruler's statue is To the Crown).
gm_can_raise_leader_monument = {
	OR = {
		has_law_or_variant = law_type:law_autocracy
		has_law_or_variant = law_type:law_single_party_state
	}
	monument_government_is_crowned = no
}

# Country scope. Hard times: finishing a monument level now causes vanity
# backlash (§5). finance_cycle_value exists only once the banking journal
# entry has run, so the recession read is guarded.
gm_country_hard_times = {
	OR = {
		in_default = yes
		has_famine = yes
		AND = {
			has_variable = finance_cycle_value
			banking_cycle_is_recession = yes
		}
	}
}
```

- [ ] **Step 7: Loc**

In `localization/english/te_production_methods_l_english.yml`, replace the existing `pm_monument_*` entries with the following (in key order):

```yaml
 pm_monument_artistic:0 "Grand Opera House"
 pm_monument_artistic_desc:0 "A concert hall, an opera house, a national gallery. Pleases the Intelligentsia. #R The dedication is permanent.#!"
 pm_monument_athletic:0 "Grand Stadium"
 pm_monument_athletic_desc:0 "An arena, a stadium, an olympic complex. Pleases the Trade Unions. #R The dedication is permanent.#!"
 pm_monument_civic:0 "To the Nation"
 pm_monument_civic_desc:0 "Not to a party and not to a house, but to the country itself. Pleases the Petty Bourgeoisie, and never falls with a government. #R The dedication is permanent.#!"
 pm_monument_crown:0 "To the Crown"
 pm_monument_crown_desc:0 "Dynastic portraits, a royal box, a procession that passes beneath it. Lends legitimacy while the country is crowned, and becomes contested if the crown falls. #R The dedication is permanent.#!"
 pm_monument_industrial:0 "Great Exhibition Hall"
 pm_monument_industrial_desc:0 "A permanent world's fair. Pleases the Industrialists. #R The dedication is permanent.#!"
 pm_monument_leader:0 "To the Leader"
 pm_monument_leader_desc:0 "A statue of the head of state, raised while they rule. Lends legitimacy and authority while they rule, and becomes contested when they are gone. #R The dedication is permanent.#!"
 pm_monument_naturalist:0 "Botanical Gardens"
 pm_monument_naturalist_desc:0 "Glasshouses, an arboretum, a great public park. Pleases the Rural Folk. #R The dedication is permanent.#!"
 pm_monument_religious:0 "Grand Shrine"
 pm_monument_religious_desc:0 "A cathedral, a temple, a mosque built to outlast the government that paid for it. Pleases the Devout, and becomes contested if the country abandons the faith it honours. #R The dedication is permanent.#!"
 pm_monument_republic:0 "To the Republic"
 pm_monument_republic_desc:0 "Oaths of office, a wreath each year, a square named for the republic. Lends legitimacy while the country is a republic, and becomes contested if the republic falls. #R The dedication is permanent.#!"
 pm_monument_revolution:0 "To the Revolution"
 pm_monument_revolution_desc:0 "Banners, a tomb for the martyrs, a stage for the anniversary. Lends legitimacy under a single party or a council republic, and becomes contested if that regime falls. #R The dedication is permanent.#!"
 pm_monument_scientific:0 "Grand Observatory"
 pm_monument_scientific_desc:0 "A telescope, a planetarium, a museum of the sciences. Pleases the Intelligentsia. #R The dedication is permanent.#!"
 pm_monument_undedicated:0 "Undedicated"
 pm_monument_undedicated_desc:0 "The stone is up; the meaning is not yet settled. An undedicated monument gives prestige and draws visitors, nothing more. #R The dedication, once chosen, is permanent.#!"
 pm_monument_war_memorial:0 "War Memorial"
 pm_monument_war_memorial_desc:0 "Names cut into stone, and a place to read them. Pleases the Armed Forces. #R The dedication is permanent.#!"
```

In `localization/english/te_buildings_l_english.yml`, replace `building_grand_monument_desc` with:

```yaml
 building_grand_monument_desc:0 "A monument a government raises to what it stands for: its crown, its republic, its revolution, its leader, its faith or the nation. Its level is its [concept_grandeur]. It lends prestige, and legitimacy and the favour of like-minded interest groups while what it honours still stands. When that falls, the next government must decide what to do with it. See the Monuments journal entry."
```

Add to `te_miscellaneous_l_english.yml`, in key order:

```yaml
 gm_possible_rule_tt:0 "The Grand Monuments game rule is enabled"
```

- [ ] **Step 7b: Old monument loc that the rewrite retires**

The old tooltips `monument_events.2.*.tt` still name the removed per-level effects; Task 7 replaces them. Leave them for now.

- [ ] **Step 8: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all tests OK (26 so far).
Run: `python3 scripts/format_paradox_tabs.py --check common/production_methods/grand_monument_pms.txt common/production_method_groups/grand_monument_pmgs.txt common/buildings/grand_monuments.txt common/scripted_triggers/monument_triggers.txt && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.

- [ ] **Step 9: Commit**

```bash
git add common/production_methods/grand_monument_pms.txt common/production_method_groups/grand_monument_pmgs.txt \
        common/buildings/grand_monuments.txt common/scripted_triggers/monument_triggers.txt \
        localization/english/te_production_methods_l_english.yml localization/english/te_buildings_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): staff-only dedications, To the Crown/Republic/Revolution/Leader

Every effect leaves the PMs (they keep the caretaker staff); the old per-level
Tourism output and the per-building national effects go with them. Civic
becomes To the Nation under its old key. The building gains the rule gate and
stays out of hard times in the AI's plans.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---
### Task 4: Kinds, fit, status, records and the local pulse

**Files:**
- Modify: `common/scripted_triggers/monument_triggers.txt` (append)
- Create: `common/scripted_effects/gm_effects.txt`
- Modify: `common/script_values/gm_values.txt` (append)
- Modify: `common/on_actions/monument_events_on_actions.txt` (append)
- Modify: `test_grand_monument_registry.py` (add `FitTests`, `RecordTests`, `LocalPulseTests`)

**Interfaces:**
- Consumes: `gm_system_enabled` (Task 1); `gm_curve_steps_f5`, `gm_local_*` modifiers (Task 2); PM keys, `gm_government_is_revolutionary` (Task 3); `te_heritage_*` (Task 1).
- Produces (triggers, state scope): `gm_state_has_pm = { PM }`, `gm_state_is_dedicated`, `gm_state_kind_regime`, `gm_state_kind_ruler`, `gm_state_kind_faith`, `gm_state_is_bound`, `gm_state_raised_by_owner`, `gm_state_leader_fits`, `gm_state_shrine_fits`, `gm_state_message_fits`, `gm_state_is_contested`, `gm_state_is_heritage`, `gm_state_status_fits`, `gm_state_counts_standing`, `gm_state_takes_heritage_skin`.
- Produces (effect, interest-group scope): `gm_ig_to_flag_on_owner = { VAR }` (writes `flag:<ig>` to `$VAR$` on the IG's country).
- Produces (effects, state scope): `gm_state_first_sight`, `gm_state_record_honoree`, `gm_state_record_faith`, `gm_state_set_default_skin`, `gm_state_default_faith_skin`, `gm_state_default_heritage_skin`, `gm_state_try_faith_skin = { R }`, `gm_state_try_heritage_skin = { H }`, `gm_state_try_heritage_as_faith_skin = { H R }`, `gm_remove_local_modifiers`, `gm_remove_state_var = { VAR }`, `gm_clear_state`, `gm_state_monthly`, `gm_add_local = { KEY }`.
- Produces (script values, state scope): `gm_state_grandeur`, `gm_status_code` (0 none, 1 undedicated, 2 fits, 3 heritage, 4 contested).
- Produces (state variables): `gm_seen`, `gm_raised_by`, `gm_honoree`, `gm_honoree_ig` (flag), `gm_faith`, `gm_skin` (flags `generic`, `faith_<religion>`, `heritage_<language>`), `gm_curve_in`, `gm_local_steps`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 4: kinds, fit, status, records, the local pulse ----------------------------

REGIME_GATE = {"crown": "monument_government_is_crowned", "republic": "monument_government_is_republican",
               "revolution": "gm_government_is_revolutionary"}


class FitTests(unittest.TestCase):
    def setUp(self):
        self.t = read(TRIGGERS)

    def test_has_pm_reads_the_building(self):
        self.assertEqual(squash(block(self.t, "gm_state_has_pm")),
                         "b:building_grand_monument ?= { has_active_production_method = $PM$ }")

    def test_kinds_match_the_table(self):
        kind_trigger = {"regime": "gm_state_kind_regime", "ruler": "gm_state_kind_ruler",
                        "faith": "gm_state_kind_faith"}
        for d in DEDICATIONS:
            for kind, trig in kind_trigger.items():
                present = f"PM = pm_monument_{d.key} }}" in squash(block(self.t, trig))
                self.assertEqual(present, d.kind == kind, f"{d.key} in {trig}")
        bound = squash(block(self.t, "gm_state_is_bound"))
        for trig in kind_trigger.values():
            self.assertIn(f"{trig} = yes", bound)

    def test_bound_messages_fit_only_for_the_raiser(self):
        body = squash(block(self.t, "gm_state_message_fits"))
        self.assertTrue(body.startswith("OR = { gm_state_is_bound = no AND = { gm_state_raised_by_owner = yes OR = {"))
        for key, gate in REGIME_GATE.items():
            self.assertIn(f"AND = {{ gm_state_has_pm = {{ PM = pm_monument_{key} }} owner = {{ {gate} = yes }} }}", body)
        self.assertIn("AND = { gm_state_kind_ruler = yes gm_state_leader_fits = yes }", body)
        self.assertIn("AND = { gm_state_kind_faith = yes gm_state_shrine_fits = yes }", body)

    def test_raiser_honoree_faith_are_guarded(self):
        raiser = squash(block(self.t, "gm_state_raised_by_owner"))
        self.assertIn("has_variable = gm_raised_by var:gm_raised_by ?=", raiser)
        leader = squash(block(self.t, "gm_state_leader_fits"))
        self.assertIn("has_variable = gm_honoree var:gm_honoree ?=", leader)
        self.assertIn("ruler ?= { this = scope:gm_tmp_honoree }", leader)
        shrine = squash(block(self.t, "gm_state_shrine_fits"))
        self.assertIn("has_variable = gm_faith", shrine)
        self.assertIn("NOT = { has_law_or_variant = law_type:law_state_atheism }", shrine)
        self.assertIn("religion = scope:gm_tmp_faith", shrine)

    def test_statuses(self):
        fits = squash(block(self.t, "gm_state_status_fits"))
        self.assertEqual(fits, "gm_state_is_dedicated = yes gm_state_is_contested = no "
                               "gm_state_is_heritage = no gm_state_message_fits = yes")
        standing = squash(block(self.t, "gm_state_counts_standing"))
        self.assertEqual(standing, "has_building = building_grand_monument gm_state_is_contested = no")

    def test_heritage_skinned(self):
        body = squash(block(self.t, "gm_state_takes_heritage_skin"))
        for key in HERITAGE_SKINNED:
            d = BY_KEY[key]
            if d.kind == "regime":
                self.assertIn("gm_state_kind_regime = yes", body)
            elif d.kind == "ruler":
                self.assertIn("gm_state_kind_ruler = yes", body)
            else:
                self.assertIn(f"PM = pm_monument_{key} }}", body)
        self.assertNotIn("gm_state_kind_faith", body)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_first_sight(self):
        body = squash(block(self.e, "gm_state_first_sight"))
        self.assertIn("gm_state_is_dedicated = yes NOT = { has_variable = gm_seen }", body)
        self.assertIn("set_variable = gm_seen", body)
        self.assertIn("limit = { gm_state_is_bound = yes } set_variable = { name = gm_raised_by value = owner }", body)
        self.assertIn("limit = { gm_state_kind_ruler = yes } gm_state_record_honoree = yes", body)
        self.assertIn("limit = { gm_state_kind_faith = yes } gm_state_record_faith = yes", body)
        self.assertIn("gm_state_set_default_skin = yes", body)
        honoree = squash(block(self.e, "gm_state_record_honoree"))
        self.assertIn("set_variable = { name = gm_honoree value = owner.ruler }", honoree)
        self.assertIn("gm_ig_to_flag_on_owner = { VAR = gm_tmp_ig_flag }", honoree)
        self.assertIn("set_variable = { name = gm_honoree_ig value = owner.var:gm_tmp_ig_flag }", honoree)
        self.assertIn("value = owner.religion", squash(block(self.e, "gm_state_record_faith")))

    def test_ig_flags_cover_every_ig(self):
        body = squash(block(self.e, "gm_ig_to_flag_on_owner"))
        for ig in IGS:
            self.assertIn(f"is_interest_group_type = ig_{ig} }} owner = {{ set_variable = "
                          f"{{ name = $VAR$ value = flag:{ig} }} }}", body)

    def test_default_skin_covers_every_faith_and_heritage(self):
        body = squash(block(self.e, "gm_state_set_default_skin"))
        self.assertTrue(body.startswith("set_variable = { name = gm_skin value = flag:generic }"))
        self.assertIn("gm_state_kind_faith = yes } gm_state_default_faith_skin = yes", body)
        self.assertIn("gm_state_takes_heritage_skin = yes } gm_state_default_heritage_skin = yes", body)
        faith = squash(block(self.e, "gm_state_default_faith_skin"))
        for f in FAITHS:
            self.assertIn(f"gm_state_try_faith_skin = {{ R = {f} }}", faith)
        heritage = squash(block(self.e, "gm_state_default_heritage_skin"))
        order = []
        for m in re.finditer(r"gm_state_try_heritage(?:_as_faith)?_skin = \{ H = (\w+)(?: R = (\w+))? \}", heritage):
            order.append(m.group(1))
            if m.group(1) in HERITAGE_AS_FAITH:
                self.assertEqual(m.group(2), HERITAGE_AS_FAITH[m.group(1)])
        self.assertEqual(order, list(reversed(HERITAGES)), "reverse order: the partition's first wins")

    def test_skin_helpers(self):
        self.assertIn("owner = { religion = rel:$R$ } } set_variable = { name = gm_skin value = flag:faith_$R$ }",
                      squash(block(self.e, "gm_state_try_faith_skin")))
        self.assertIn("owner = { te_heritage_$H$ = yes } } set_variable = { name = gm_skin value = flag:heritage_$H$ }",
                      squash(block(self.e, "gm_state_try_heritage_skin")))
        self.assertIn("owner = { te_heritage_$H$ = yes } } set_variable = { name = gm_skin value = flag:faith_$R$ }",
                      squash(block(self.e, "gm_state_try_heritage_as_faith_skin")))


class LocalPulseTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_removes_every_local_modifier(self):
        body = squash(block(self.e, "gm_remove_local_modifiers"))
        self.assertIn("remove_modifier = gm_local_tourism", body)
        for d in DEDICATIONS:
            self.assertIn(f"remove_modifier = gm_local_{d.key}", body)

    def test_pulse_applies_the_curve(self):
        body = squash(block(self.e, "gm_state_monthly"))
        self.assertTrue(body.startswith("gm_remove_local_modifiers = yes"))
        self.assertIn("set_variable = { name = gm_curve_in value = gm_state_grandeur }", body)
        self.assertIn("set_variable = { name = gm_local_steps value = gm_curve_steps_f5 }", body)
        self.assertIn("add_modifier = { name = gm_local_tourism multiplier = var:gm_local_steps }", body)
        for d in DEDICATIONS:
            self.assertIn(f"gm_add_local = {{ KEY = {d.key} }}", body)
        self.assertIn("add_modifier = { name = gm_local_$KEY$ multiplier = var:gm_local_steps }",
                      squash(block(self.e, "gm_add_local")))

    def test_backing_variable_is_never_removed(self):
        self.assertNotRegex(strip_comments(self.e), r"remove_variable = gm_local_steps")
        self.assertIn("set_variable = { name = gm_local_steps value = 0 }", squash(block(self.e, "gm_clear_state")))

    def test_wired_to_the_state_pulse(self):
        oa = read(ON_ACTIONS)
        self.assertIn("gm_state_on_action", squash(block(oa, "on_monthly_pulse_state")))
        body = squash(block(oa, "gm_state_on_action"))
        self.assertIn("trigger = { gm_system_enabled = yes }", body)
        self.assertIn("gm_state_monthly = yes", body)

    def test_state_values(self):
        v = read(VALUES)
        self.assertIn("value = b:building_grand_monument.level", squash(block(v, "gm_state_grandeur")))
        code = squash(block(v, "gm_status_code"))
        for n in (1, 2, 3, 4):
            self.assertIn(f"value = {n} }}", code)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: the three new classes FAIL/ERROR (`gm_effects.txt` missing, triggers missing).

- [ ] **Step 3: The triggers**

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  A monument's kind, fit and status (spec §1, §2.3, §3)
# ======================================================================
# State scope. Everything a monument must remember lives on its STATE
# (buildings hold no variables; one Grand Monument per state):
#   gm_raised_by      the country that dedicated it (regime, ruler, faith)
#   gm_honoree        To the Leader: the ruler it honours
#   gm_honoree_ig     To the Leader: that ruler's IG, as a flag
#   gm_faith          Grand Shrine: the religion it honours
#   gm_skin           flag: the form it takes (§1.1)
#   gm_seen           its records have been written
#   gm_contested      months it has stood contested (§4)
#   gm_heritage       preserved as heritage (§4.3)
#   gm_base_ig / gm_supporter_ig   IG flags recorded at contest (§4.1)
# A missing record reads as "does not fit", never as "fits".

gm_state_has_pm = {
	b:building_grand_monument ?= { has_active_production_method = $PM$ }
}

gm_state_is_dedicated = {
	has_building = building_grand_monument
	NOT = { gm_state_has_pm = { PM = pm_monument_undedicated } }
}

gm_state_kind_regime = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_crown }
		gm_state_has_pm = { PM = pm_monument_republic }
		gm_state_has_pm = { PM = pm_monument_revolution }
	}
}

gm_state_kind_ruler = {
	gm_state_has_pm = { PM = pm_monument_leader }
}

gm_state_kind_faith = {
	gm_state_has_pm = { PM = pm_monument_religious }
}

# Regime, ruler or faith: a message that can fall. Everything else is timeless.
gm_state_is_bound = {
	OR = {
		gm_state_kind_regime = yes
		gm_state_kind_ruler = yes
		gm_state_kind_faith = yes
	}
}

# The country that raised it still owns it. Not true of a conquered monument,
# whatever the conqueror's laws (plan decision 2).
gm_state_raised_by_owner = {
	has_variable = gm_raised_by
	var:gm_raised_by ?= { save_temporary_scope_as = gm_tmp_raiser }
	owner = scope:gm_tmp_raiser
}

# The honoured character still rules. A dead honoree fails the `?=`.
gm_state_leader_fits = {
	has_variable = gm_honoree
	var:gm_honoree ?= { save_temporary_scope_as = gm_tmp_honoree }
	owner = {
		ruler ?= { this = scope:gm_tmp_honoree }
	}
}

# The state religion is still the one it honours, and not under State Atheism.
gm_state_shrine_fits = {
	has_variable = gm_faith
	owner = {
		NOT = { has_law_or_variant = law_type:law_state_atheism }
	}
	var:gm_faith ?= { save_temporary_scope_as = gm_tmp_faith }
	owner = { religion = scope:gm_tmp_faith }
}

# Its message still stands. Read live every month from the owner's laws,
# religion and ruler; never cached.
gm_state_message_fits = {
	OR = {
		gm_state_is_bound = no
		AND = {
			gm_state_raised_by_owner = yes
			OR = {
				AND = {
					gm_state_has_pm = { PM = pm_monument_crown }
					owner = { monument_government_is_crowned = yes }
				}
				AND = {
					gm_state_has_pm = { PM = pm_monument_republic }
					owner = { monument_government_is_republican = yes }
				}
				AND = {
					gm_state_has_pm = { PM = pm_monument_revolution }
					owner = { gm_government_is_revolutionary = yes }
				}
				AND = {
					gm_state_kind_ruler = yes
					gm_state_leader_fits = yes
				}
				AND = {
					gm_state_kind_faith = yes
					gm_state_shrine_fits = yes
				}
			}
		}
	}
}

gm_state_is_contested = {
	has_variable = gm_contested
}

gm_state_is_heritage = {
	has_variable = gm_heritage
}

# §2.3 "Fits": the monuments whose politics count.
gm_state_status_fits = {
	gm_state_is_dedicated = yes
	gm_state_is_contested = no
	gm_state_is_heritage = no
	gm_state_message_fits = yes
}

# §2.3 standing grandeur (prestige, cultural pull): every monument not contested.
gm_state_counts_standing = {
	has_building = building_grand_monument
	gm_state_is_contested = no
}

# §1.1: the dedications that take heritage skins. The Grand Shrine takes faith
# skins; the War Memorial takes heritage skins only (plan decision 4).
gm_state_takes_heritage_skin = {
	OR = {
		gm_state_kind_regime = yes
		gm_state_kind_ruler = yes
		gm_state_has_pm = { PM = pm_monument_civic }
		gm_state_has_pm = { PM = pm_monument_war_memorial }
	}
}
```

- [ ] **Step 4: The state values**

Append to `common/script_values/gm_values.txt`:

```

# ---- A monument's own numbers (state scope) --------------------------------
# Its level, or 0.
gm_state_grandeur = {
	value = 0
	if = {
		limit = { has_building = building_grand_monument }
		value = b:building_grand_monument.level
	}
}

# The journal entry row's status: 0 none, 1 undedicated, 2 fits (or not yet
# judged), 3 heritage, 4 contested. A code, so the .gui tests identity rather
# than a threshold (gui gotcha #23). Later ifs override earlier ones.
gm_status_code = {
	value = 0
	if = {
		limit = { has_building = building_grand_monument }
		value = 2
	}
	if = {
		limit = {
			has_building = building_grand_monument
			gm_state_is_dedicated = no
		}
		value = 1
	}
	if = {
		limit = { gm_state_is_heritage = yes }
		value = 3
	}
	if = {
		limit = { gm_state_is_contested = yes }
		value = 4
	}
}
```

- [ ] **Step 5: The effects**

Create `common/scripted_effects/gm_effects.txt` (BOM, tabs):

```
# ============================================================================
# GRAND MONUMENTS — scripted effects
# ============================================================================
# Design: docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md.
# The state-held records are listed in monument_triggers.txt § "kind, fit and
# status".
#
# Where modifiers are applied: state modifiers only from gm_state_monthly
# (on_monthly_pulse_state, ROOT = the state); national ones only from
# gm_country_refresh with ROOT = the country. A variable backing a multiplier
# is zeroed, never removed.

# ---- Records (§3) ------------------------------------------------------------
# State scope. A dedicated monument the pulse finds without records (a pick
# made in the building panel, or a monument from a save older than this
# system) gets them from its current owner, once. The ceremony writes them
# itself, so this does nothing for a monument it dedicated.
gm_state_first_sight = {
	if = {
		limit = {
			gm_state_is_dedicated = yes
			NOT = { has_variable = gm_seen }
		}
		set_variable = gm_seen
		if = {
			limit = { gm_state_is_bound = yes }
			set_variable = { name = gm_raised_by value = owner }
		}
		if = {
			limit = { gm_state_kind_ruler = yes }
			gm_state_record_honoree = yes
		}
		if = {
			limit = { gm_state_kind_faith = yes }
			gm_state_record_faith = yes
		}
		if = {
			limit = {
				NOT = { has_variable = gm_skin }
			}
			gm_state_set_default_skin = yes
		}
	}
}

# State scope. The ruler a Leader monument honours, and that ruler's IG as a
# flag (gm_honoree_ig): its supporters, whom a later Tear Down angers (§4.3).
# Recorded now because by the time the monument is contested the ruler has
# changed.
gm_state_record_honoree = {
	if = {
		limit = {
			owner = { exists = ruler }
		}
		set_variable = { name = gm_honoree value = owner.ruler }
		owner = {
			set_variable = { name = gm_tmp_ig_flag value = flag:none }
			ruler = {
				interest_group ?= {
					gm_ig_to_flag_on_owner = { VAR = gm_tmp_ig_flag }
				}
			}
		}
		set_variable = { name = gm_honoree_ig value = owner.var:gm_tmp_ig_flag }
	}
}

# Interest-group scope. Writes this IG's type as a flag to variable $VAR$ on
# its owner. A flag, not the IG scope: it names the same group in any country.
gm_ig_to_flag_on_owner = {
	if = {
		limit = { is_interest_group_type = ig_armed_forces }
		owner = { set_variable = { name = $VAR$ value = flag:armed_forces } }
	}
	if = {
		limit = { is_interest_group_type = ig_devout }
		owner = { set_variable = { name = $VAR$ value = flag:devout } }
	}
	if = {
		limit = { is_interest_group_type = ig_industrialists }
		owner = { set_variable = { name = $VAR$ value = flag:industrialists } }
	}
	if = {
		limit = { is_interest_group_type = ig_intelligentsia }
		owner = { set_variable = { name = $VAR$ value = flag:intelligentsia } }
	}
	if = {
		limit = { is_interest_group_type = ig_landowners }
		owner = { set_variable = { name = $VAR$ value = flag:landowners } }
	}
	if = {
		limit = { is_interest_group_type = ig_petty_bourgeoisie }
		owner = { set_variable = { name = $VAR$ value = flag:petty_bourgeoisie } }
	}
	if = {
		limit = { is_interest_group_type = ig_rural_folk }
		owner = { set_variable = { name = $VAR$ value = flag:rural_folk } }
	}
	if = {
		limit = { is_interest_group_type = ig_trade_unions }
		owner = { set_variable = { name = $VAR$ value = flag:trade_unions } }
	}
}

# State scope. The faith a Grand Shrine honours.
gm_state_record_faith = {
	set_variable = { name = gm_faith value = owner.religion }
}

# ---- Skins (§1.1) ------------------------------------------------------------
# State scope, with the dedication already active. The most specific skin that
# fits, without asking: the state religion's for a Shrine, the first heritage in
# the revival partition's order for a heritage-skinned dedication, else
# generic. Used for old saves, panel picks and as the ceremony follow-up's
# default (monument_events.11). Skins read only the owner's own religion and
# primary cultures.
gm_state_set_default_skin = {
	set_variable = { name = gm_skin value = flag:generic }
	if = {
		limit = { gm_state_kind_faith = yes }
		gm_state_default_faith_skin = yes
		# The mod's own religions have no faith skin: a heritage skin instead.
		if = {
			limit = { var:gm_skin = flag:generic }
			gm_state_default_heritage_skin = yes
		}
	}
	else_if = {
		limit = { gm_state_takes_heritage_skin = yes }
		gm_state_default_heritage_skin = yes
	}
}

# State scope. The state religion's faith skin, if it has one; else no change.
# Called directly by the ceremony (Task 7), which knows the dedication before
# the newly activated production method can be read back.
gm_state_default_faith_skin = {
	gm_state_try_faith_skin = { R = catholic }
	gm_state_try_faith_skin = { R = protestant }
	gm_state_try_faith_skin = { R = orthodox }
	gm_state_try_faith_skin = { R = oriental_orthodox }
	gm_state_try_faith_skin = { R = sunni }
	gm_state_try_faith_skin = { R = shiite }
	gm_state_try_faith_skin = { R = ibadi }
	gm_state_try_faith_skin = { R = jewish }
	gm_state_try_faith_skin = { R = mahayana }
	gm_state_try_faith_skin = { R = gelugpa }
	gm_state_try_faith_skin = { R = theravada }
	gm_state_try_faith_skin = { R = confucian }
	gm_state_try_faith_skin = { R = hindu }
	gm_state_try_faith_skin = { R = shinto }
	gm_state_try_faith_skin = { R = sikh }
	gm_state_try_faith_skin = { R = animist }
}

# State scope. The first heritage skin in the revival partition's order that
# the owner can claim; else no change. Reverse order: a later match overrides,
# so the partition's first wins.
gm_state_default_heritage_skin = {
	gm_state_try_heritage_skin = { H = aramaic }
	gm_state_try_heritage_skin = { H = prussian }
	gm_state_try_heritage_skin = { H = mayan }
	gm_state_try_heritage_skin = { H = gothic }
	gm_state_try_heritage_skin = { H = norse }
	gm_state_try_heritage_skin = { H = nahuatl }
	gm_state_try_heritage_as_faith_skin = { H = coptic R = oriental_orthodox }
	gm_state_try_heritage_skin = { H = irish }
	gm_state_try_heritage_skin = { H = greek }
	gm_state_try_heritage_skin = { H = chinese }
	gm_state_try_heritage_skin = { H = arabic }
	gm_state_try_heritage_skin = { H = avestan }
	gm_state_try_heritage_as_faith_skin = { H = pali R = theravada }
	gm_state_try_heritage_skin = { H = slavonic }
	gm_state_try_heritage_skin = { H = geez }
	gm_state_try_heritage_skin = { H = sanskrit }
	gm_state_try_heritage_skin = { H = hebrew }
	gm_state_try_heritage_skin = { H = latin }
}

gm_state_try_faith_skin = {
	if = {
		limit = {
			owner = { religion = rel:$R$ }
		}
		set_variable = { name = gm_skin value = flag:faith_$R$ }
	}
}

gm_state_try_heritage_skin = {
	if = {
		limit = {
			owner = { te_heritage_$H$ = yes }
		}
		set_variable = { name = gm_skin value = flag:heritage_$H$ }
	}
}

# Pali and Coptic are keyed on the state religion; their skin is that faith's.
gm_state_try_heritage_as_faith_skin = {
	if = {
		limit = {
			owner = { te_heritage_$H$ = yes }
		}
		set_variable = { name = gm_skin value = flag:faith_$R$ }
	}
}

# ---- Forgetting a monument ---------------------------------------------------
# State scope. Every local modifier, whichever dedication added it.
gm_remove_local_modifiers = {
	remove_modifier = gm_local_tourism
	remove_modifier = gm_local_crown
	remove_modifier = gm_local_republic
	remove_modifier = gm_local_revolution
	remove_modifier = gm_local_leader
	remove_modifier = gm_local_religious
	remove_modifier = gm_local_civic
	remove_modifier = gm_local_war_memorial
	remove_modifier = gm_local_artistic
	remove_modifier = gm_local_naturalist
	remove_modifier = gm_local_scientific
	remove_modifier = gm_local_industrial
	remove_modifier = gm_local_athletic
}

gm_remove_state_var = {
	if = {
		limit = { has_variable = $VAR$ }
		remove_variable = $VAR$
	}
}

# State scope. Forget a monument that is gone (demolished, torn down, or about
# to be rebuilt). gm_local_steps backs the local modifiers' multiplier: zeroed,
# never removed.
gm_clear_state = {
	gm_remove_local_modifiers = yes
	gm_remove_state_var = { VAR = gm_seen }
	gm_remove_state_var = { VAR = gm_raised_by }
	gm_remove_state_var = { VAR = gm_honoree }
	gm_remove_state_var = { VAR = gm_honoree_ig }
	gm_remove_state_var = { VAR = gm_faith }
	gm_remove_state_var = { VAR = gm_skin }
	gm_remove_state_var = { VAR = gm_skin_axis }
	gm_remove_state_var = { VAR = gm_contested }
	gm_remove_state_var = { VAR = gm_heritage }
	gm_remove_state_var = { VAR = gm_base_ig }
	gm_remove_state_var = { VAR = gm_supporter_ig }
	gm_remove_state_var = { VAR = gm_new_contest }
	gm_remove_state_var = { VAR = gm_grandeur }
	gm_remove_state_var = { VAR = gm_ceremony_pending }
	set_variable = { name = gm_local_steps value = 0 }
}

# ---- The local pulse (§2.5): on_monthly_pulse_state, ROOT = the state --------
# Tourism Industry throughput for every monument; the dedication's own local
# effect for every dedicated one (fits, heritage or contested, §2.3). Both on
# the curve over this monument's own level.
gm_state_monthly = {
	gm_remove_local_modifiers = yes
	if = {
		limit = { has_building = building_grand_monument }
		# Last known level, read if the building disappears before the next pulse.
		set_variable = { name = gm_grandeur value = gm_state_grandeur }
		set_variable = { name = gm_curve_in value = gm_state_grandeur }
		set_variable = { name = gm_local_steps value = gm_curve_steps_f5 }
		add_modifier = { name = gm_local_tourism multiplier = var:gm_local_steps }
		if = {
			limit = { gm_state_is_dedicated = yes }
			gm_add_local = { KEY = crown }
			gm_add_local = { KEY = republic }
			gm_add_local = { KEY = revolution }
			gm_add_local = { KEY = leader }
			gm_add_local = { KEY = religious }
			gm_add_local = { KEY = civic }
			gm_add_local = { KEY = war_memorial }
			gm_add_local = { KEY = artistic }
			gm_add_local = { KEY = naturalist }
			gm_add_local = { KEY = scientific }
			gm_add_local = { KEY = industrial }
			gm_add_local = { KEY = athletic }
		}
	}
	else = {
		if = {
			limit = { has_variable = gm_seen }
			gm_clear_state = yes
		}
		if = {
			limit = { has_variable = gm_local_steps }
			set_variable = { name = gm_local_steps value = 0 }
		}
	}
}

gm_add_local = {
	if = {
		limit = {
			gm_state_has_pm = { PM = pm_monument_$KEY$ }
		}
		add_modifier = { name = gm_local_$KEY$ multiplier = var:gm_local_steps }
	}
}
```

- [ ] **Step 6: Wire the state pulse**

Append to `common/on_actions/monument_events_on_actions.txt`:

```

# ============================================================================
# The local pulse (spec §2.5)
# ============================================================================
# State scope (ROOT = the state). A state modifier's multiplier resolves
# against ROOT, so each monument's local modifiers are refreshed here and never
# from the country pulse. Runs for a state with a monument, or one whose
# monument has just gone (records or a multiplier left to clear).
on_monthly_pulse_state = {
	on_actions = {
		gm_state_on_action
	}
}

gm_state_on_action = {
	trigger = {
		gm_system_enabled = yes
	}
	effect = {
		if = {
			limit = {
				OR = {
					has_building = building_grand_monument
					has_variable = gm_seen
					AND = {
						has_variable = gm_local_steps
						var:gm_local_steps > 0
					}
				}
			}
			gm_state_monthly = yes
		}
	}
}
```

- [ ] **Step 7: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_triggers/monument_triggers.txt common/scripted_effects/gm_effects.txt common/script_values/gm_values.txt common/on_actions/monument_events_on_actions.txt && python3 iterator_limit_audit.py --strict && python3 empty_effect_audit.py --strict && python3 prev_scope_audit.py --strict`
Expected: exit 0.

- [ ] **Step 8: Commit**

```bash
git add common/scripted_triggers/monument_triggers.txt common/scripted_effects/gm_effects.txt \
        common/script_values/gm_values.txt common/on_actions/monument_events_on_actions.txt \
        test_grand_monument_registry.py
git commit -m "feat(monuments): kinds, live fit, statuses, records and the local pulse

A regime, ruler or faith monument fits while the country that raised it owns
it and its crown, republic, revolution, leader or faith still stands, read
live each month. Records live on the state; first sight writes them for
panel picks and old saves. The state pulse applies the local modifiers along
the curve over the monument's own level.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 5: The national refresh, IG alignment, ledgers and the journal entry

**Files:**
- Modify: `common/scripted_triggers/monument_triggers.txt` (append IG alignment, ledger idleness)
- Modify: `common/script_values/gm_values.txt` (append sums and two displays)
- Modify: `common/scripted_effects/gm_effects.txt` (append the refresh)
- Create: `common/journal_entries/je_grand_monuments.txt`
- Modify: `events/monument_events.txt` (append `.20`)
- Modify: `common/on_actions/monument_events_on_actions.txt` (append the country pulse and the law/ruler hooks)
- Modify: `common/script_values/cultural_hegemony_script_values.txt`
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `NationalTests`)

**Interfaces:**
- Consumes: Task 2's curve and modifiers; Task 4's fit/status triggers, `gm_state_first_sight`, `gm_ig_to_flag_on_owner`, `gm_state_grandeur`.
- Produces (triggers, state scope): `gm_state_approved_by_<ig>`, `gm_state_opposed_by_<ig>` (8 each), `gm_state_leader_ig_is = { IG }`, `gm_state_leader_opposed_by = { IG }`. Country scope: `gm_ledger_idle = { VAR }`, `gm_ledgers_idle`.
- Produces (script values, country scope): `gm_sum_standing`, `gm_sum_regime`, `gm_sum_<key>` for the six `NATIONAL` keys, `gm_sum_monuments`, `gm_sum_contested`, `gm_display_count`, `gm_display_contested`.
- Produces (effects, country scope, ROOT must be the country): `gm_country_refresh`, `gm_country_monthly`, `gm_init_ledgers`, `gm_init_ledger = { VAR }`, `gm_decay_ledgers`, `gm_decay = { VAR RATE }`, `gm_set_opposition_ig`, `gm_set_steps = { IN OUT NEXT F }`, `gm_compute_totals`, `gm_compute_ig = { IG }`, `gm_apply_national_modifiers`, `gm_remove_national_modifiers`, `gm_add_national = { NAME VAR }`, `gm_add_national_signed = { NAME VAR }`.
- Produces (country variables): `gm_states` (list), `gm_opposition_ig` (flag), `gm_teardown_ledger`, `gm_vanity_ledger`, `gm_ig_ledger_<ig>`, `gm_g_standing`/`gm_s_standing`/`gm_n_standing`, `gm_s_culture`/`gm_n_culture`, `gm_g_regime`/`gm_s_regime`/`gm_n_regime`, `gm_g_<key>`/`gm_s_<key>`/`gm_n_<key>` (six), `gm_s_teardown`/`gm_n_teardown`, `gm_ig_net_<ig>`, `gm_s_ig_<ig>` (signed), `gm_count_monuments`, `gm_count_contested`, `gm_active`. State variable: `gm_grandeur`.
- Produces (event): `monument_events.20` (hidden country event: `gm_country_refresh`).
- Produces (JE): `je_grand_monuments`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 5: the national refresh, IG alignment, ledgers, the JE ---------------------

class NationalTests(unittest.TestCase):
    def setUp(self):
        self.t, self.e, self.v = read(TRIGGERS), read(EFFECTS), read(VALUES)

    def test_ig_alignment_matches_the_table(self):
        for ig in IGS:
            approve = squash(block(self.t, f"gm_state_approved_by_{ig}"))
            oppose = squash(block(self.t, f"gm_state_opposed_by_{ig}"))
            for d in DEDICATIONS:
                self.assertEqual(f"PM = pm_monument_{d.key} }}" in approve, d.approve == ig, f"{ig} approves {d.key}")
                self.assertEqual(f"PM = pm_monument_{d.key} }}" in oppose, d.oppose == ig, f"{ig} opposes {d.key}")
            self.assertIn(f"gm_state_leader_ig_is = {{ IG = {ig} }}", approve)
            self.assertIn(f"gm_state_leader_opposed_by = {{ IG = {ig} }}", oppose)

    def test_leader_pair_is_dynamic(self):
        self.assertIn("ruler ?= { interest_group ?= { is_interest_group_type = ig_$IG$ } }",
                      squash(block(self.t, "gm_state_leader_ig_is")))
        self.assertIn("var:gm_opposition_ig = flag:$IG$", squash(block(self.t, "gm_state_leader_opposed_by")))
        opp = squash(block(self.e, "gm_set_opposition_ig"))
        self.assertIn("limit = { is_in_government = no } order_by = ig_clout position = 0", opp)
        self.assertIn("gm_ig_to_flag_on_owner = { VAR = gm_opposition_ig }", opp)

    def test_sums_follow_the_status_table(self):
        self.assertIn("limit = { gm_state_counts_standing = yes } add = gm_state_grandeur",
                      squash(block(self.v, "gm_sum_standing")))
        self.assertIn("gm_state_status_fits = yes OR = { gm_state_kind_regime = yes gm_state_kind_ruler = yes }",
                      squash(block(self.v, "gm_sum_regime")))
        for key in NATIONAL:
            self.assertIn(f"gm_state_status_fits = yes gm_state_has_pm = {{ PM = pm_monument_{key} }}",
                          squash(block(self.v, f"gm_sum_{key}")))

    def test_totals_use_the_right_curves(self):
        body = squash(block(self.e, "gm_compute_totals"))
        self.assertIn("gm_set_steps = { IN = gm_g_standing OUT = gm_s_standing NEXT = gm_n_standing F = 5 }", body)
        self.assertIn("gm_set_steps = { IN = gm_g_standing OUT = gm_s_culture NEXT = gm_n_culture F = 10 }", body)
        self.assertIn("gm_set_steps = { IN = gm_g_regime OUT = gm_s_regime NEXT = gm_n_regime F = 10 }", body)
        self.assertIn("gm_set_steps = { IN = gm_teardown_ledger OUT = gm_s_teardown NEXT = gm_n_teardown F = 5 }", body)
        for key in NATIONAL:
            self.assertIn(f"set_variable = {{ name = gm_g_{key} value = gm_sum_{key} }}", body)
            self.assertIn(f"gm_set_steps = {{ IN = gm_g_{key} OUT = gm_s_{key} NEXT = gm_n_{key} F = 5 }}", body)
        for ig in IGS:
            self.assertIn(f"gm_compute_ig = {{ IG = {ig} }}", body)
        steps = squash(block(self.e, "gm_set_steps"))
        self.assertIn("value = gm_curve_steps_f$F$", steps)
        self.assertIn("value = gm_curve_next_f$F$", steps)

    def test_ig_net(self):
        body = squash(block(self.e, "gm_compute_ig"))
        self.assertTrue(body.startswith("set_variable = { name = gm_ig_net_$IG$ value = var:gm_ig_ledger_$IG$ }"))
        self.assertIn("gm_state_approved_by_$IG$ = yes } owner = { change_variable = { name = gm_ig_net_$IG$ add = prev.var:gm_grandeur } }", body)
        self.assertIn("gm_state_opposed_by_$IG$ = yes } owner = { change_variable = { name = gm_ig_net_$IG$ subtract = prev.var:gm_grandeur } }", body)
        self.assertIn("gm_state_is_contested = yes has_variable = gm_base_ig var:gm_base_ig = flag:$IG$", body)
        self.assertIn("multiply = -1", body)

    def test_national_modifiers_on_the_je_from_root(self):
        body = squash(block(self.e, "gm_apply_national_modifiers"))
        self.assertTrue(body.startswith("je:je_grand_monuments ?= { gm_remove_national_modifiers = yes"))
        pairs = [("gm_national_prestige", "gm_s_standing"), ("gm_national_legitimacy", "gm_s_regime"),
                 ("gm_national_teardown", "gm_s_teardown"), ("gm_national_vanity", "gm_vanity_ledger")]
        pairs += [(f"gm_national_{k}", f"gm_s_{k}") for k in NATIONAL]
        for name, var in pairs:
            self.assertIn(f"gm_add_national = {{ NAME = {name} VAR = {var} }}", body)
        for ig in IGS:
            self.assertIn(f"gm_add_national_signed = {{ NAME = gm_ig_approval_{ig} VAR = gm_s_ig_{ig} }}", body)
        removed = squash(block(self.e, "gm_remove_national_modifiers"))
        for name, _ in top_level_blocks(read(MODIFIERS)):
            if name.startswith(("gm_national_", "gm_ig_approval_")):
                self.assertIn(f"remove_modifier = {name}", removed)
        self.assertIn("multiplier = root.var:$VAR$", squash(block(self.e, "gm_add_national")))
        self.assertIn("multiplier = root.var:$VAR$", squash(block(self.e, "gm_add_national_signed")))

    def test_refresh_order(self):
        body = squash(block(self.e, "gm_country_refresh"))
        order = ["gm_init_ledgers = yes", "clear_variable_list = gm_states",
                 "set_variable = { name = gm_grandeur value = gm_state_grandeur }",
                 "gm_state_first_sight = yes", "add_to_variable_list = { name = gm_states target = prev }",
                 "gm_set_opposition_ig = yes", "gm_compute_totals = yes", "gm_apply_national_modifiers = yes"]
        positions = [body.find(s) for s in order]
        self.assertNotIn(-1, positions, dict(zip(order, positions)))
        self.assertEqual(positions, sorted(positions))

    def test_ledgers(self):
        init = squash(block(self.e, "gm_init_ledgers"))
        decay = squash(block(self.e, "gm_decay_ledgers"))
        idle = squash(block(self.t, "gm_ledgers_idle"))
        for var in ["gm_teardown_ledger", "gm_vanity_ledger"] + [f"gm_ig_ledger_{ig}" for ig in IGS]:
            self.assertIn(f"gm_init_ledger = {{ VAR = {var} }}", init)
            self.assertIn(f"gm_ledger_idle = {{ VAR = {var} }}", idle)
        self.assertIn("gm_decay = { VAR = gm_teardown_ledger RATE = 0.96 }", decay)
        self.assertIn("gm_decay = { VAR = gm_vanity_ledger RATE = 0.92 }", decay)
        for ig in IGS:
            self.assertIn(f"gm_decay = {{ VAR = gm_ig_ledger_{ig} RATE = 0.97 }}", decay)
        snap = squash(block(self.e, "gm_decay"))
        self.assertIn("var:$VAR$ < 0.05 var:$VAR$ > -0.05 } set_variable = { name = $VAR$ value = 0 }", snap)
        self.assertNotRegex(strip_comments(self.e), r"remove_variable = gm_(teardown|vanity|ig)_ledger")
        monthly = squash(block(self.e, "gm_country_monthly"))
        self.assertLess(monthly.find("gm_decay_ledgers = yes"), monthly.find("gm_country_refresh = yes"))

    def test_je_lifecycle(self):
        je = read(JE)
        self.assertIn("any_scope_state = { has_building = building_grand_monument }", squash(block(je, "possible")))
        invalid = squash(block(je, "invalid"))
        self.assertIn("gm_system_enabled = no", invalid)
        self.assertIn("gm_ledgers_idle = yes", invalid)
        self.assertIsNone(block(je, "immediate"), "nothing a revolution's winner would lose")
        for key in ("je_grand_monuments", "je_grand_monuments_reason", "je_grand_monuments_status",
                    "je_grand_monuments_status_contested"):
            self.assertIn(key, loc())

    def test_refresh_event_and_hooks(self):
        ev = squash(raw_block_at(read(EVENTS), r"(?m)^monument_events\.20\s*=\s*\{"))
        self.assertIn("type = country_event hidden = yes", ev)
        self.assertIn("immediate = { gm_country_refresh = yes }", ev)
        oa = read(ON_ACTIONS)
        self.assertIn("gm_country_on_action", squash(block(oa, "on_monthly_pulse_country")))
        self.assertIn("gm_country_monthly = yes", squash(block(oa, "gm_country_on_action")))
        for hook, oa_name in (("on_law_activated", "gm_law_activated_on_action"),
                              ("on_new_ruler", "gm_new_ruler_on_action")):
            self.assertIn(oa_name, squash(block(oa, hook)))
            self.assertIn("trigger_event = { id = monument_events.20 }", squash(block(oa, oa_name)))

    def test_cultural_pull(self):
        text = read(CULTURAL)
        body = squash(block(text, "cultural_pull_from_grand_monuments"))
        self.assertIn("value = var:gm_s_culture", body)
        self.assertIn("max = 5", body)
        self.assertIsNone(block(text, "grand_monument_levels_in_state"))
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry.NationalTests -v`
Expected: ERROR/FAIL (triggers, effects, JE missing).

- [ ] **Step 3: IG alignment and ledger triggers**

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  IG alignment (spec §1): which IG a monument pleases or offends
# ======================================================================
# State scope, for a monument whose status is Fits (gm_compute_ig checks).
# Timeless dedications have no opponents on purpose; the regime ones are
# divisive. The Leader's pair is dynamic: the ruler's own IG approves, and the
# strongest IG outside the government (gm_opposition_ig, set on the country by
# gm_set_opposition_ig each refresh) opposes. test_grand_monument_registry.py
# pins every pair against its DEDICATIONS table.

gm_state_leader_ig_is = {
	gm_state_kind_ruler = yes
	owner = {
		ruler ?= { interest_group ?= { is_interest_group_type = ig_$IG$ } }
	}
}

gm_state_leader_opposed_by = {
	gm_state_kind_ruler = yes
	owner = {
		has_variable = gm_opposition_ig
		var:gm_opposition_ig = flag:$IG$
	}
}

gm_state_approved_by_armed_forces = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_war_memorial }
		gm_state_leader_ig_is = { IG = armed_forces }
	}
}

gm_state_opposed_by_armed_forces = {
	gm_state_leader_opposed_by = { IG = armed_forces }
}

gm_state_approved_by_devout = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_religious }
		gm_state_leader_ig_is = { IG = devout }
	}
}

gm_state_opposed_by_devout = {
	gm_state_leader_opposed_by = { IG = devout }
}

gm_state_approved_by_industrialists = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_industrial }
		gm_state_leader_ig_is = { IG = industrialists }
	}
}

gm_state_opposed_by_industrialists = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_revolution }
		gm_state_leader_opposed_by = { IG = industrialists }
	}
}

gm_state_approved_by_intelligentsia = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_republic }
		gm_state_has_pm = { PM = pm_monument_artistic }
		gm_state_has_pm = { PM = pm_monument_scientific }
		gm_state_leader_ig_is = { IG = intelligentsia }
	}
}

gm_state_opposed_by_intelligentsia = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_crown }
		gm_state_leader_opposed_by = { IG = intelligentsia }
	}
}

gm_state_approved_by_landowners = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_crown }
		gm_state_leader_ig_is = { IG = landowners }
	}
}

gm_state_opposed_by_landowners = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_republic }
		gm_state_leader_opposed_by = { IG = landowners }
	}
}

gm_state_approved_by_petty_bourgeoisie = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_civic }
		gm_state_leader_ig_is = { IG = petty_bourgeoisie }
	}
}

gm_state_opposed_by_petty_bourgeoisie = {
	gm_state_leader_opposed_by = { IG = petty_bourgeoisie }
}

gm_state_approved_by_rural_folk = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_naturalist }
		gm_state_leader_ig_is = { IG = rural_folk }
	}
}

gm_state_opposed_by_rural_folk = {
	gm_state_leader_opposed_by = { IG = rural_folk }
}

gm_state_approved_by_trade_unions = {
	OR = {
		gm_state_has_pm = { PM = pm_monument_revolution }
		gm_state_has_pm = { PM = pm_monument_athletic }
		gm_state_leader_ig_is = { IG = trade_unions }
	}
}

gm_state_opposed_by_trade_unions = {
	gm_state_leader_opposed_by = { IG = trade_unions }
}

# ======================================================================
#  Ledgers (spec §4.3, §5)
# ======================================================================
# Country scope. A ledger no longer worth a modifier.
gm_ledger_idle = {
	OR = {
		NOT = { has_variable = $VAR$ }
		AND = {
			var:$VAR$ < 0.5
			var:$VAR$ > -0.5
		}
	}
}

# Country scope. Nothing left fading: with no monument either, the journal
# entry goes (plan decision 3).
gm_ledgers_idle = {
	gm_ledger_idle = { VAR = gm_teardown_ledger }
	gm_ledger_idle = { VAR = gm_vanity_ledger }
	gm_ledger_idle = { VAR = gm_ig_ledger_armed_forces }
	gm_ledger_idle = { VAR = gm_ig_ledger_devout }
	gm_ledger_idle = { VAR = gm_ig_ledger_industrialists }
	gm_ledger_idle = { VAR = gm_ig_ledger_intelligentsia }
	gm_ledger_idle = { VAR = gm_ig_ledger_landowners }
	gm_ledger_idle = { VAR = gm_ig_ledger_petty_bourgeoisie }
	gm_ledger_idle = { VAR = gm_ig_ledger_rural_folk }
	gm_ledger_idle = { VAR = gm_ig_ledger_trade_unions }
}
```

- [ ] **Step 4: The sums**

Append to `common/script_values/gm_values.txt`:

```

# ---- National sums (§2.3, §2.4), country scope ---------------------------------
# Standing grandeur: every monument that is not contested (prestige, cultural pull).
gm_sum_standing = {
	value = 0
	every_scope_state = {
		limit = { gm_state_counts_standing = yes }
		add = gm_state_grandeur
	}
}

# Regime grandeur: regime and ruler monuments that fit (legitimacy).
gm_sum_regime = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			OR = {
				gm_state_kind_regime = yes
				gm_state_kind_ruler = yes
			}
		}
		add = gm_state_grandeur
	}
}

# One per dedication with a national effect of its own.
gm_sum_leader = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_leader }
		}
		add = gm_state_grandeur
	}
}

gm_sum_religious = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_religious }
		}
		add = gm_state_grandeur
	}
}

gm_sum_war_memorial = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_war_memorial }
		}
		add = gm_state_grandeur
	}
}

gm_sum_artistic = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_artistic }
		}
		add = gm_state_grandeur
	}
}

gm_sum_scientific = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_scientific }
		}
		add = gm_state_grandeur
	}
}

gm_sum_industrial = {
	value = 0
	every_scope_state = {
		limit = {
			gm_state_status_fits = yes
			gm_state_has_pm = { PM = pm_monument_industrial }
		}
		add = gm_state_grandeur
	}
}

gm_sum_monuments = {
	value = 0
	every_scope_state = {
		limit = { has_building = building_grand_monument }
		add = 1
	}
}

gm_sum_contested = {
	value = 0
	every_scope_state = {
		limit = { gm_state_is_contested = yes }
		add = 1
	}
}

# ---- Displays (country scope; guarded: a save older than the system has none
# of these variables until the first refresh) -----------------------------------
gm_display_count = {
	value = 0
	if = {
		limit = { has_variable = gm_count_monuments }
		value = var:gm_count_monuments
	}
}

gm_display_contested = {
	value = 0
	if = {
		limit = { has_variable = gm_count_contested }
		value = var:gm_count_contested
	}
}
```

- [ ] **Step 5: The refresh**

Append to `common/scripted_effects/gm_effects.txt`:

```

# ---- Ledgers (§4.3, §5) --------------------------------------------------------
# Country scope. Every reward and cost of a contest choice, and vanity
# backlash, goes into a decaying ledger, never a stacking modifier. Ledgers back
# multipliers, so they are zeroed, never removed.
gm_init_ledger = {
	if = {
		limit = {
			NOT = { has_variable = $VAR$ }
		}
		set_variable = { name = $VAR$ value = 0 }
	}
}

gm_init_ledgers = {
	gm_init_ledger = { VAR = gm_teardown_ledger }
	gm_init_ledger = { VAR = gm_vanity_ledger }
	gm_init_ledger = { VAR = gm_ig_ledger_armed_forces }
	gm_init_ledger = { VAR = gm_ig_ledger_devout }
	gm_init_ledger = { VAR = gm_ig_ledger_industrialists }
	gm_init_ledger = { VAR = gm_ig_ledger_intelligentsia }
	gm_init_ledger = { VAR = gm_ig_ledger_landowners }
	gm_init_ledger = { VAR = gm_ig_ledger_petty_bourgeoisie }
	gm_init_ledger = { VAR = gm_ig_ledger_rural_folk }
	gm_init_ledger = { VAR = gm_ig_ledger_trade_unions }
}

gm_decay = {
	change_variable = { name = $VAR$ multiply = $RATE$ }
	if = {
		limit = {
			var:$VAR$ < 0.05
			var:$VAR$ > -0.05
		}
		set_variable = { name = $VAR$ value = 0 }
	}
}

# Once a month (gm_country_monthly), never on a mid-month refresh.
gm_decay_ledgers = {
	gm_decay = { VAR = gm_teardown_ledger RATE = 0.96 }
	gm_decay = { VAR = gm_vanity_ledger RATE = 0.92 }
	gm_decay = { VAR = gm_ig_ledger_armed_forces RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_devout RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_industrialists RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_intelligentsia RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_landowners RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_petty_bourgeoisie RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_rural_folk RATE = 0.97 }
	gm_decay = { VAR = gm_ig_ledger_trade_unions RATE = 0.97 }
}

# ---- The national refresh (§2.4) ---------------------------------------------
# Country scope, ROOT = the country: the monthly pulse, monument_events.20,
# a scripted GUI effect or a country event option. Never call it where ROOT is
# a state, building, law or character: the multipliers resolve against ROOT.
gm_country_refresh = {
	gm_init_ledgers = yes
	clear_variable_list = gm_states
	every_scope_state = {
		limit = { has_building = building_grand_monument }
		set_variable = { name = gm_grandeur value = gm_state_grandeur }
		gm_state_first_sight = yes
		owner = {
			add_to_variable_list = { name = gm_states target = prev }
		}
	}
	gm_set_opposition_ig = yes
	gm_compute_totals = yes
	gm_apply_national_modifiers = yes
}

# Country scope. The monthly pulse: decay, then refresh; gm_active keeps the
# pulse running while a ledger fades after the last monument has gone.
gm_country_monthly = {
	gm_init_ledgers = yes
	gm_decay_ledgers = yes
	gm_country_refresh = yes
	if = {
		limit = {
			NOT = { any_scope_state = { has_building = building_grand_monument } }
			gm_ledgers_idle = yes
		}
		if = {
			limit = { has_variable = gm_active }
			remove_variable = gm_active
		}
	}
	else = {
		set_variable = gm_active
	}
}

# Country scope. The strongest IG outside the government, as a flag: the
# opponent of a monument to the Leader (§1).
gm_set_opposition_ig = {
	set_variable = { name = gm_opposition_ig value = flag:none }
	ordered_interest_group = {
		limit = { is_in_government = no }
		order_by = ig_clout
		position = 0
		check_range_bounds = no
		gm_ig_to_flag_on_owner = { VAR = gm_opposition_ig }
	}
}

# Country scope. Grandeur -> step count and next step, along the curve with
# first step $F$ (5 or 10).
gm_set_steps = {
	set_variable = { name = gm_curve_in value = var:$IN$ }
	set_variable = { name = $OUT$ value = gm_curve_steps_f$F$ }
	set_variable = { name = $NEXT$ value = gm_curve_next_f$F$ }
}

gm_compute_totals = {
	set_variable = { name = gm_g_standing value = gm_sum_standing }
	set_variable = { name = gm_g_regime value = gm_sum_regime }
	set_variable = { name = gm_g_leader value = gm_sum_leader }
	set_variable = { name = gm_g_religious value = gm_sum_religious }
	set_variable = { name = gm_g_war_memorial value = gm_sum_war_memorial }
	set_variable = { name = gm_g_artistic value = gm_sum_artistic }
	set_variable = { name = gm_g_scientific value = gm_sum_scientific }
	set_variable = { name = gm_g_industrial value = gm_sum_industrial }
	gm_set_steps = { IN = gm_g_standing OUT = gm_s_standing NEXT = gm_n_standing F = 5 }
	gm_set_steps = { IN = gm_g_standing OUT = gm_s_culture NEXT = gm_n_culture F = 10 }
	gm_set_steps = { IN = gm_g_regime OUT = gm_s_regime NEXT = gm_n_regime F = 10 }
	gm_set_steps = { IN = gm_g_leader OUT = gm_s_leader NEXT = gm_n_leader F = 5 }
	gm_set_steps = { IN = gm_g_religious OUT = gm_s_religious NEXT = gm_n_religious F = 5 }
	gm_set_steps = { IN = gm_g_war_memorial OUT = gm_s_war_memorial NEXT = gm_n_war_memorial F = 5 }
	gm_set_steps = { IN = gm_g_artistic OUT = gm_s_artistic NEXT = gm_n_artistic F = 5 }
	gm_set_steps = { IN = gm_g_scientific OUT = gm_s_scientific NEXT = gm_n_scientific F = 5 }
	gm_set_steps = { IN = gm_g_industrial OUT = gm_s_industrial NEXT = gm_n_industrial F = 5 }
	gm_set_steps = { IN = gm_teardown_ledger OUT = gm_s_teardown NEXT = gm_n_teardown F = 5 }
	gm_compute_ig = { IG = armed_forces }
	gm_compute_ig = { IG = devout }
	gm_compute_ig = { IG = industrialists }
	gm_compute_ig = { IG = intelligentsia }
	gm_compute_ig = { IG = landowners }
	gm_compute_ig = { IG = petty_bourgeoisie }
	gm_compute_ig = { IG = rural_folk }
	gm_compute_ig = { IG = trade_unions }
	set_variable = { name = gm_count_monuments value = gm_sum_monuments }
	set_variable = { name = gm_count_contested value = gm_sum_contested }
}

# Country scope. One IG's net grandeur (§2.4): its ledger, plus each Fits
# monument it approves of, minus each it opposes, minus each contested
# monument whose new order it is (the standing penalty, §4.2). The result goes
# through the curve on its absolute value, with the sign put back: one cap per
# IG, across all monuments.
gm_compute_ig = {
	set_variable = { name = gm_ig_net_$IG$ value = var:gm_ig_ledger_$IG$ }
	every_scope_state = {
		limit = { has_building = building_grand_monument }
		if = {
			limit = {
				gm_state_status_fits = yes
				gm_state_approved_by_$IG$ = yes
			}
			owner = {
				change_variable = { name = gm_ig_net_$IG$ add = prev.var:gm_grandeur }
			}
		}
		if = {
			limit = {
				gm_state_status_fits = yes
				gm_state_opposed_by_$IG$ = yes
			}
			owner = {
				change_variable = { name = gm_ig_net_$IG$ subtract = prev.var:gm_grandeur }
			}
		}
		if = {
			limit = {
				gm_state_is_contested = yes
				has_variable = gm_base_ig
				var:gm_base_ig = flag:$IG$
			}
			owner = {
				change_variable = { name = gm_ig_net_$IG$ subtract = prev.var:gm_grandeur }
			}
		}
	}
	if = {
		limit = { var:gm_ig_net_$IG$ >= 0 }
		set_variable = { name = gm_curve_in value = var:gm_ig_net_$IG$ }
		set_variable = { name = gm_s_ig_$IG$ value = gm_curve_steps_f5 }
	}
	else = {
		set_variable = {
			name = gm_curve_in
			value = {
				value = var:gm_ig_net_$IG$
				multiply = -1
			}
		}
		set_variable = {
			name = gm_s_ig_$IG$
			value = {
				value = gm_curve_steps_f5
				multiply = -1
			}
		}
	}
}

# Country scope, ROOT = the country. Every national modifier lives on the
# journal entry (§2.4); the `?=` skips the months before it is active.
gm_apply_national_modifiers = {
	je:je_grand_monuments ?= {
		gm_remove_national_modifiers = yes
		gm_add_national = { NAME = gm_national_prestige VAR = gm_s_standing }
		gm_add_national = { NAME = gm_national_legitimacy VAR = gm_s_regime }
		gm_add_national = { NAME = gm_national_leader VAR = gm_s_leader }
		gm_add_national = { NAME = gm_national_religious VAR = gm_s_religious }
		gm_add_national = { NAME = gm_national_war_memorial VAR = gm_s_war_memorial }
		gm_add_national = { NAME = gm_national_artistic VAR = gm_s_artistic }
		gm_add_national = { NAME = gm_national_scientific VAR = gm_s_scientific }
		gm_add_national = { NAME = gm_national_industrial VAR = gm_s_industrial }
		gm_add_national = { NAME = gm_national_teardown VAR = gm_s_teardown }
		gm_add_national = { NAME = gm_national_vanity VAR = gm_vanity_ledger }
		gm_add_national_signed = { NAME = gm_ig_approval_armed_forces VAR = gm_s_ig_armed_forces }
		gm_add_national_signed = { NAME = gm_ig_approval_devout VAR = gm_s_ig_devout }
		gm_add_national_signed = { NAME = gm_ig_approval_industrialists VAR = gm_s_ig_industrialists }
		gm_add_national_signed = { NAME = gm_ig_approval_intelligentsia VAR = gm_s_ig_intelligentsia }
		gm_add_national_signed = { NAME = gm_ig_approval_landowners VAR = gm_s_ig_landowners }
		gm_add_national_signed = { NAME = gm_ig_approval_petty_bourgeoisie VAR = gm_s_ig_petty_bourgeoisie }
		gm_add_national_signed = { NAME = gm_ig_approval_rural_folk VAR = gm_s_ig_rural_folk }
		gm_add_national_signed = { NAME = gm_ig_approval_trade_unions VAR = gm_s_ig_trade_unions }
	}
}

# Journal-entry scope.
gm_remove_national_modifiers = {
	remove_modifier = gm_national_prestige
	remove_modifier = gm_national_legitimacy
	remove_modifier = gm_national_leader
	remove_modifier = gm_national_religious
	remove_modifier = gm_national_war_memorial
	remove_modifier = gm_national_artistic
	remove_modifier = gm_national_scientific
	remove_modifier = gm_national_industrial
	remove_modifier = gm_national_teardown
	remove_modifier = gm_national_vanity
	remove_modifier = gm_ig_approval_armed_forces
	remove_modifier = gm_ig_approval_devout
	remove_modifier = gm_ig_approval_industrialists
	remove_modifier = gm_ig_approval_intelligentsia
	remove_modifier = gm_ig_approval_landowners
	remove_modifier = gm_ig_approval_petty_bourgeoisie
	remove_modifier = gm_ig_approval_rural_folk
	remove_modifier = gm_ig_approval_trade_unions
}

# Journal-entry scope; the variable is ROOT's (the country's).
gm_add_national = {
	if = {
		limit = { root.var:$VAR$ > 0.001 }
		add_modifier = { name = $NAME$ multiplier = root.var:$VAR$ }
	}
}

gm_add_national_signed = {
	if = {
		limit = {
			OR = {
				root.var:$VAR$ > 0.001
				root.var:$VAR$ < -0.001
			}
		}
		add_modifier = { name = $NAME$ multiplier = root.var:$VAR$ }
	}
}
```

- [ ] **Step 6: The journal entry**

Create `common/journal_entries/je_grand_monuments.txt` (BOM, tabs):

```
# ============================================================================
# The Monuments journal entry (spec §6)
# ============================================================================
# Activates when the country owns a Grand Monument; goes when it owns none and
# no ledger is still fading (plan decision 3); comes back with the next
# monument. Holds the national modifiers (gm_apply_national_modifiers), which
# go with it. No `immediate`: nothing here a revolution's winner should lose.
# The widgets (Task 9) show the national lines and one row per monument.

je_grand_monuments = {
	icon = "gfx/interface/icons/building_icons/building_government_administration.dds"
	group = je_group_internal_affairs

	possible = {
		gm_system_enabled = yes
		any_scope_state = { has_building = building_grand_monument }
	}

	invalid = {
		OR = {
			gm_system_enabled = no
			AND = {
				NOT = {
					any_scope_state = { has_building = building_grand_monument }
				}
				gm_ledgers_idle = yes
			}
		}
	}

	status_desc = {
		first_valid = {
			triggered_desc = {
				desc = je_grand_monuments_status_contested
				trigger = {
					any_scope_state = { gm_state_is_contested = yes }
				}
			}
			triggered_desc = {
				desc = je_grand_monuments_status
				trigger = { always = yes }
			}
		}
	}

	weight = 400
	should_update_on_player_command = yes
}
```

Add to `localization/english/te_journal_entries_l_english.yml`, in key order:

```yaml
 je_grand_monuments:0 "Monuments"
 je_grand_monuments_desc:0 "What our monuments honour, and what they give us for it."
 je_grand_monuments_reason:0 "A monument says something about the government that raised it. While its crown, republic, revolution, leader or faith still stands, it lends prestige and legitimacy and pleases the interest groups that share its message. When that falls, the next government must decide what to do with it. Everything here grows with [concept_grandeur]."
 je_grand_monuments_status:0 "#bold [ROOT.GetCountry.MakeScope.ScriptValue('gm_display_count')|0]#! monuments"
 je_grand_monuments_status_contested:0 "#bold [ROOT.GetCountry.MakeScope.ScriptValue('gm_display_count')|0]#! monuments, #R [ROOT.GetCountry.MakeScope.ScriptValue('gm_display_contested')|0] contested#!"
```

- [ ] **Step 7: The refresh event and the hooks**

Append to `events/monument_events.txt`:

```

# ============================================================================
# Event 20: refresh (hidden plumbing)
# ============================================================================
# A country event, so ROOT is the country and the national modifiers'
# multipliers resolve against it. Fired by the hooks whose ROOT is not the
# country (law activated, new ruler, state owner change, a level finished) and
# after a ceremony.
monument_events.20 = {
	type = country_event
	hidden = yes

	trigger = {
		gm_system_enabled = yes
	}

	immediate = {
		gm_country_refresh = yes
	}
}
```

In `common/on_actions/monument_events_on_actions.txt`, the file already declares `on_monthly_pulse_country` (for the flavour events). Add the new on-action to that block's list, so the key appears once in the file (`duplicate_key_audit`):

```
on_monthly_pulse_country = {
	on_actions = {
		monument_events_on_action
		gm_country_on_action
	}
}
```

Then append:

```

# ============================================================================
# The national pulse (spec §2.4), and the hooks that re-read "fits" at once
# ============================================================================
gm_country_on_action = {
	trigger = {
		gm_system_enabled = yes
	}
	effect = {
		if = {
			limit = {
				OR = {
					any_scope_state = { has_building = building_grand_monument }
					has_variable = gm_active
				}
			}
			gm_country_monthly = yes
		}
	}
}

# ROOT = the law; its owner is the country. A new law can topple a crown, a
# republic or a revolution: refresh through the hidden country event.
on_law_activated = {
	on_actions = {
		gm_law_activated_on_action
	}
}

gm_law_activated_on_action = {
	trigger = {
		gm_system_enabled = yes
	}
	effect = {
		owner = {
			if = {
				limit = {
					any_scope_state = { has_building = building_grand_monument }
				}
				trigger_event = { id = monument_events.20 }
			}
		}
	}
}

# ROOT = the new ruler (a character). The fall of a leader.
on_new_ruler = {
	on_actions = {
		gm_new_ruler_on_action
	}
}

gm_new_ruler_on_action = {
	trigger = {
		gm_system_enabled = yes
	}
	effect = {
		owner ?= {
			if = {
				limit = {
					any_scope_state = { has_building = building_grand_monument }
				}
				trigger_event = { id = monument_events.20 }
			}
		}
	}
}
```

- [ ] **Step 8: Cultural pull**

In `common/script_values/cultural_hegemony_script_values.txt`, delete `grand_monument_levels_in_state` (and its comment) and replace `cultural_pull_from_grand_monuments` (and its comment) with:

```
# Grand Monument pull: standing grandeur (every monument not contested) through
# the doubling curve with a first step of 10, capped at 5 steps (+5, the old
# ceiling). gm_s_culture is set by gm_country_refresh (gm_effects.txt); absent
# until a country's first refresh. Spec
# docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md §2.4.
cultural_pull_from_grand_monuments = {
	value = 0
	if = {
		limit = { has_variable = gm_s_culture }
		value = var:gm_s_culture
		multiply = gm_step_culture
	}
	max = 5
}
```

- [ ] **Step 9: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_triggers/monument_triggers.txt common/script_values/gm_values.txt common/scripted_effects/gm_effects.txt common/journal_entries/je_grand_monuments.txt events/monument_events.txt common/on_actions/monument_events_on_actions.txt common/script_values/cultural_hegemony_script_values.txt && python3 scripts/analysis/check_localization_files.py && for a in iterator_limit prev_scope modifier_multiplier_var empty_effect je_immediate_reset any_limit; do python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"; done`
Expected: exit 0, no `FAIL` lines.

- [ ] **Step 10: Commit**

```bash
git add common/scripted_triggers/monument_triggers.txt common/script_values/gm_values.txt \
        common/scripted_effects/gm_effects.txt common/journal_entries/je_grand_monuments.txt \
        events/monument_events.txt common/on_actions/monument_events_on_actions.txt \
        common/script_values/cultural_hegemony_script_values.txt \
        localization/english/te_journal_entries_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): national totals on the Monuments journal entry

Prestige, legitimacy, each dedication's own effect and one approval total per
IG come from national grandeur sums through the curve, applied to the JE from
the country pulse (or a hidden country event after a law or ruler change).
Ledgers decay monthly and are never removed. Cultural pull reads the curve.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 6: Contested monuments

**Files:**
- Modify: `common/scripted_effects/gm_effects.txt` (append; edit `gm_country_refresh`, `gm_country_monthly`, `gm_state_monthly`)
- Modify: `common/script_values/gm_values.txt` (append)
- Create: `common/customizable_localization/gm_custom_loc.txt`
- Modify: `common/on_actions/monument_events_on_actions.txt` (append `on_state_owner_change`)
- Modify: `common/on_actions/te_civil_war_on_actions.txt` (`te_civil_war_on_won`)
- Modify: `common/scripted_effects/te_construction_market_build_effects.txt` (ladder 101–200)
- Modify: `events/monument_events.txt` (append `.16`, `.17`)
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `ContestTests`; extend `NationalTests.test_refresh_order`)

**Interfaces:**
- Consumes: Tasks 4–5 (fit/status triggers, records, ledgers, `gm_country_refresh`, `.20`), `te_construction_market_build_specified_level = { SPEC_TYPE SPEC_LEVEL }` (existing), `scope:te_cw_loser` (set by `te_civil_war_resolve_sides`).
- Produces (effects, state scope): `gm_state_contest`, `gm_state_record_contest_igs`, `gm_state_lift_contest`, `gm_state_changed_hands`, `gm_state_adopt_for_winner`, `gm_state_ledger_ig = { WHO FACTOR }`, `gm_state_ledger_ig_one = { WHO FACTOR IG }`, `gm_state_record_teardown`, `gm_state_tear_down`, `gm_state_rededicate`, `gm_state_preserve`, `gm_state_choose_tear_down`, `gm_state_choose_rededicate`, `gm_state_choose_preserve` (the three with their tooltips), `gm_state_start_ceremony`.
- Produces (effects, country scope): `gm_check_contests`, `gm_repair_after_civil_war`, `gm_ai_decide_contests`, `gm_notify_new_contests`.
- Produces (script values): `gm_state_rededicate_cost` (state), `gm_notice_count` (country).
- Produces (custom loc, state scope): `gm_dedication_name`, `gm_status_name`, `gm_base_ig_name`, `gm_supporter_ig_name`.
- Produces (events): `monument_events.16` (players' notice), `monument_events.17` (one monument's decision, state event).
- Produces (variables): state `gm_contested` (months), `gm_new_contest`, `gm_heritage`, `gm_base_ig`, `gm_supporter_ig`, `gm_ceremony_pending` (30 days), `gm_rebuild_level`, `gm_rebuild_cost`; country `gm_cw_loser`, `gm_cw_adopting` (30 days), `gm_notice_states` (list).

- [ ] **Step 1: Write the failing tests**

In `NationalTests.test_refresh_order`, replace the `order = [...]` list with:

```python
        order = ["gm_init_ledgers = yes", "clear_variable_list = gm_states",
                 "set_variable = { name = gm_grandeur value = gm_state_grandeur }",
                 "gm_state_first_sight = yes", "add_to_variable_list = { name = gm_states target = prev }",
                 "gm_set_opposition_ig = yes", "gm_check_contests = yes", "gm_compute_totals = yes",
                 "gm_apply_national_modifiers = yes", "gm_notify_new_contests = yes"]
```

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 6: contested monuments -----------------------------------------------------

class ContestTests(unittest.TestCase):
    def setUp(self):
        self.e = read(EFFECTS)

    def test_contest_records_the_table_igs(self):
        body = squash(block(self.e, "gm_state_record_contest_igs"))
        for d in DEDICATIONS:
            if d.kind == "regime":
                self.assertIn(f"gm_state_has_pm = {{ PM = pm_monument_{d.key} }} }} "
                              f"set_variable = {{ name = gm_base_ig value = flag:{d.oppose} }} "
                              f"set_variable = {{ name = gm_supporter_ig value = flag:{d.approve} }}", body)
        self.assertIn("gm_state_kind_faith = yes } set_variable = { name = gm_supporter_ig value = flag:devout }", body)
        self.assertIn("set_variable = { name = gm_base_ig value = owner.var:gm_opposition_ig }", body)
        self.assertIn("set_variable = { name = gm_supporter_ig value = var:gm_honoree_ig }", body)

    def test_monthly_check(self):
        body = squash(block(self.e, "gm_check_contests"))
        self.assertTrue(body.startswith("if = { limit = { NOT = { has_variable = te_cw_role } }"))
        self.assertIn("limit = { gm_state_is_dedicated = yes gm_state_is_bound = yes }", body)
        self.assertIn("owner = { has_variable = gm_cw_adopting } } gm_state_adopt_for_winner = yes", body)
        self.assertIn("gm_state_is_heritage = yes } gm_state_message_fits = yes } gm_state_lift_contest = yes", body)
        self.assertIn("gm_state_is_heritage = no gm_state_message_fits = no } gm_state_contest = yes", body)

    def test_months_count_once_a_month(self):
        self.assertNotIn("add = 1", squash(block(self.e, "gm_check_contests")))
        self.assertIn("limit = { gm_state_is_contested = yes } change_variable = { name = gm_contested add = 1 }",
                      squash(block(self.e, "gm_country_monthly")))

    def test_changed_hands(self):
        body = squash(block(self.e, "gm_state_changed_hands"))
        self.assertIn("owner = { NOT = { has_variable = te_cw_role } is_revolutionary = no }", body)
        self.assertIn("gm_state_raised_by_owner = no", body)
        self.assertIn("limit = { gm_state_kind_faith = yes } gm_state_lift_contest = yes set_variable = gm_heritage", body)
        self.assertIn("gm_state_contest = yes", body)
        self.assertTrue(body.endswith("owner = { trigger_event = { id = monument_events.20 } }"))
        oa = read(ON_ACTIONS)
        self.assertIn("gm_state_owner_change_on_action", squash(block(oa, "on_state_owner_change")))
        self.assertIn("gm_state_changed_hands = yes", squash(block(oa, "gm_state_owner_change_on_action")))

    def test_civil_war_winner_adopts(self):
        won = squash(block(read(CIVIL_WAR_ON_ACTIONS), "te_civil_war_on_won"))
        self.assertLess(won.find("te_civil_war_resolve_sides = yes"), won.find("gm_repair_after_civil_war = yes"))
        self.assertLess(won.find("gm_repair_after_civil_war = yes"), won.find("te_civil_war_clear = yes"))
        repair = squash(block(self.e, "gm_repair_after_civil_war"))
        self.assertIn("set_variable = { name = gm_cw_loser value = scope:te_cw_loser days = 30 }", repair)
        self.assertIn("set_variable = { name = gm_cw_adopting value = yes days = 30 }", repair)
        adopt = squash(block(self.e, "gm_state_adopt_for_winner"))
        self.assertIn("var:gm_raised_by = scope:gm_tmp_loser", adopt)
        self.assertIn("set_variable = { name = gm_raised_by value = owner }", adopt)

    def test_ledger_helper_covers_every_ig(self):
        body = squash(block(self.e, "gm_state_ledger_ig"))
        for ig in IGS:
            self.assertIn(f"gm_state_ledger_ig_one = {{ WHO = $WHO$ FACTOR = $FACTOR$ IG = {ig} }}", body)
        one = squash(block(self.e, "gm_state_ledger_ig_one"))
        self.assertIn("var:$WHO$ = flag:$IG$", one)
        self.assertIn("value = { value = prev.var:gm_grandeur multiply = $FACTOR$ add = var:gm_ig_ledger_$IG$ }", one)

    def test_the_three_choices(self):
        record = squash(block(self.e, "gm_state_record_teardown"))
        self.assertIn("add = prev.var:gm_grandeur", record)
        self.assertIn("gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = 1 }", record)
        self.assertIn("gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -1 }", record)
        tear = squash(block(self.e, "gm_state_tear_down"))
        for s in ("gm_state_record_teardown = yes", "remove_list_variable = { name = gm_states target = prev }",
                  "remove_building = building_grand_monument", "gm_clear_state = yes"):
            self.assertIn(s, tear)
        rededicate = squash(block(self.e, "gm_state_rededicate"))
        for s in ("set_variable = { name = gm_rebuild_cost value = gm_state_rededicate_cost }",
                  "add_treasury = { value = prev.var:gm_rebuild_cost multiply = -1 }",
                  "gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -0.5 }",
                  "divide = 2 ceiling = yes max = 200",
                  "SPEC_TYPE = building_grand_monument SPEC_LEVEL = var:gm_rebuild_level",
                  "gm_state_start_ceremony = yes"):
            self.assertIn(s, rededicate)
        self.assertLess(rededicate.find("gm_clear_state = yes"),
                        rededicate.find("te_construction_market_build_specified_level"))
        self.assertIn("multiply = 5000", squash(block(read(VALUES), "gm_state_rededicate_cost")))
        preserve = squash(block(self.e, "gm_state_preserve"))
        self.assertIn("gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = -1 }", preserve)
        self.assertIn("set_variable = gm_heritage", preserve)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertEqual(squash(block(self.e, f"gm_state_choose_{choice}")),
                             f"custom_tooltip = {{ text = gm_{choice}_tt gm_state_{choice} = yes }}")
            self.assertIn(f"gm_{choice}_tt", loc())

    def test_ladder_reaches_200(self):
        body = squash(block(read(LADDER), "te_construction_market_build_specified_level"))
        for n in range(1, 201):
            self.assertIn(f"{n} = {{ create_building = {{ building = $SPEC_TYPE$ level = {n} }} }}", body)

    def test_one_ceremony_at_a_time(self):
        body = squash(block(self.e, "gm_state_start_ceremony"))
        self.assertIn("NOT = { has_variable = gm_ceremony_pending }", body)
        self.assertIn("set_variable = { name = gm_ceremony_pending days = 30 }", body)
        self.assertIn("trigger_event = { id = monument_events.2 }", body)

    def test_demolished_contested_counts_as_torn_down(self):
        body = squash(block(self.e, "gm_state_monthly"))
        self.assertIn("limit = { gm_state_is_contested = yes } gm_state_record_teardown = yes", body)

    def test_ai_and_notice(self):
        monthly = squash(block(self.e, "gm_country_monthly"))
        self.assertIn("gm_ai_decide_contests = yes", monthly)
        ai = squash(block(self.e, "gm_ai_decide_contests"))
        self.assertTrue(ai.startswith("if = { limit = { is_ai = yes }"))
        for s in ("gm_state_tear_down = yes", "gm_state_preserve = yes", "gm_state_rededicate = yes",
                  "var:gm_contested >= 2"):
            self.assertIn(s, ai)
        notify = squash(block(self.e, "gm_notify_new_contests"))
        self.assertIn("limit = { is_ai = no } trigger_event = { id = monument_events.16 }", notify)

    def test_events(self):
        text = read(EVENTS)
        notice = squash(raw_block_at(text, r"(?m)^monument_events\.16\s*=\s*\{"))
        self.assertIn("type = country_event", notice)
        self.assertIn("remove_variable = gm_new_contest", notice)
        self.assertIn("gm_state_tear_down = yes", notice)
        self.assertIn("gm_state_preserve = yes", notice)
        self.assertIn("trigger_event = { id = monument_events.17 }", notice)
        self.assertIn("hidden_effect = { gm_country_refresh = yes }", notice)
        one = squash(raw_block_at(text, r"(?m)^monument_events\.17\s*=\s*\{"))
        self.assertIn("type = state_event", one)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertIn(f"gm_state_choose_{choice} = yes", one)
        L = loc()
        for key in ("t", "d", "f", "a", "b", "c", "a.tt", "b.tt", "c.tt"):
            self.assertIn(f"monument_events.16.{key}", L)
        for key in ("t", "desc", "f", "a", "b", "c", "d"):
            self.assertIn(f"monument_events.17.{key}", L)
        self.assertIn("desc = monument_events.17.desc", one)

    def test_custom_loc(self):
        text = read(CUSTOM_LOC)
        ded = squash(block(text, "gm_dedication_name"))
        for d in DEDICATIONS:
            self.assertIn(f"localization_key = pm_monument_{d.key}", ded)
        for name, var in (("gm_base_ig_name", "gm_base_ig"), ("gm_supporter_ig_name", "gm_supporter_ig")):
            body = squash(block(text, name))
            for ig in IGS:
                self.assertIn(f"var:{var} = flag:{ig} }} localization_key = ig_{ig}", body)
            self.assertIn("localization_key = gm_ig_nobody", body)
        status = squash(block(text, "gm_status_name"))
        for s in ("contested", "heritage", "undedicated", "unsettled", "fits"):
            self.assertIn(f"localization_key = gm_status_{s}", status)
            self.assertIn(f"gm_status_{s}", loc())
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: `ContestTests` and `NationalTests.test_refresh_order` FAIL.

- [ ] **Step 3: Extend the ladder**

The shared helper `te_construction_market_build_specified_level` builds a building at a variable level through a `switch` with literal cases (`create_building`'s `level` takes only a literal). It stops at 100; Rededicate needs up to 200. Extend it in place (don't copy it):

```bash
python3 - <<'EOF'
from pathlib import Path
p = Path("common/scripted_effects/te_construction_market_build_effects.txt")
text = p.read_text(encoding="utf-8-sig")
anchor = ("\t\t100 = {\n\t\t\tcreate_building = {\n\t\t\t\tbuilding = $SPEC_TYPE$\n"
          "\t\t\t\tlevel = 100\n\t\t\t}\n\t\t}\n")
assert text.count(anchor) == 1, "the level-100 case is not where expected"
cases = "".join(f"\t\t{n} = {{\n\t\t\tcreate_building = {{\n\t\t\t\tbuilding = $SPEC_TYPE$\n"
                f"\t\t\t\tlevel = {n}\n\t\t\t}}\n\t\t}}\n" for n in range(101, 201))
p.write_text("﻿" + text.replace(anchor, anchor + cases), encoding="utf-8")
EOF
```

Then, above `te_construction_market_build_specified_level = {`, add this comment line to the existing header comment:

```
# Cases run to 200 (the Grand Monument's Rededicate rebuilds at half a
# monument's level, up to 200; gm_state_rededicate in gm_effects.txt).
```

- [ ] **Step 4: The contest effects**

Append to `common/scripted_effects/gm_effects.txt`:

```

# ---- Contests (§4) -------------------------------------------------------------
# Country scope. From gm_country_refresh: a bound monument whose message no
# longer fits becomes contested; a contested or heritage one whose message
# fits again is restored (a Bourbon restoration gets its statues back). Not
# while this country is a side in a civil war: the winner is judged after it
# (plan decision 2). A civil war's winner first adopts the loser's monuments.
gm_check_contests = {
	if = {
		limit = {
			NOT = { has_variable = te_cw_role }
		}
		every_scope_state = {
			limit = {
				gm_state_is_dedicated = yes
				gm_state_is_bound = yes
			}
			if = {
				limit = {
					owner = { has_variable = gm_cw_adopting }
				}
				gm_state_adopt_for_winner = yes
			}
			if = {
				limit = {
					OR = {
						gm_state_is_contested = yes
						gm_state_is_heritage = yes
					}
					gm_state_message_fits = yes
				}
				gm_state_lift_contest = yes
			}
			else_if = {
				limit = {
					gm_state_is_contested = no
					gm_state_is_heritage = no
					gm_state_message_fits = no
				}
				gm_state_contest = yes
			}
		}
	}
}

# State scope. Contest this monument (§4.1).
gm_state_contest = {
	set_variable = { name = gm_contested value = 0 }
	set_variable = gm_new_contest
	gm_state_record_contest_igs = yes
}

# State scope. The IG that opposed its message (the new order's base) and the
# IG that approved it (its supporters), as flags, recorded now: the Leader's
# pair is dynamic and would otherwise follow the new government.
gm_state_record_contest_igs = {
	set_variable = { name = gm_base_ig value = flag:none }
	set_variable = { name = gm_supporter_ig value = flag:none }
	if = {
		limit = { gm_state_has_pm = { PM = pm_monument_crown } }
		set_variable = { name = gm_base_ig value = flag:intelligentsia }
		set_variable = { name = gm_supporter_ig value = flag:landowners }
	}
	else_if = {
		limit = { gm_state_has_pm = { PM = pm_monument_republic } }
		set_variable = { name = gm_base_ig value = flag:landowners }
		set_variable = { name = gm_supporter_ig value = flag:intelligentsia }
	}
	else_if = {
		limit = { gm_state_has_pm = { PM = pm_monument_revolution } }
		set_variable = { name = gm_base_ig value = flag:industrialists }
		set_variable = { name = gm_supporter_ig value = flag:trade_unions }
	}
	else_if = {
		limit = { gm_state_kind_faith = yes }
		set_variable = { name = gm_supporter_ig value = flag:devout }
	}
	else_if = {
		limit = { gm_state_kind_ruler = yes }
		if = {
			limit = {
				owner = { has_variable = gm_opposition_ig }
			}
			set_variable = { name = gm_base_ig value = owner.var:gm_opposition_ig }
		}
		if = {
			limit = { has_variable = gm_honoree_ig }
			set_variable = { name = gm_supporter_ig value = var:gm_honoree_ig }
		}
	}
}

# State scope. Lift a contest, or restore a heritage monument to full effect.
gm_state_lift_contest = {
	gm_remove_state_var = { VAR = gm_contested }
	gm_remove_state_var = { VAR = gm_heritage }
	gm_remove_state_var = { VAR = gm_new_contest }
	gm_remove_state_var = { VAR = gm_base_ig }
	gm_remove_state_var = { VAR = gm_supporter_ig }
}

# ---- A change of owner (§1, §4.1) ----------------------------------------------
# State scope, ROOT = the state (on_state_owner_change). A regime or ruler
# monument now owned by a country that did not raise it honours a foreign
# order: contested for the new owner. A shrine becomes heritage, never
# contested (§1). This does not rely on the records surviving the transfer.
# Skipped for a civil war's transfers (the new owner is a side: te_cw_role, or
# a revolutionary country); the nation that raised it taking it back fails
# `gm_state_raised_by_owner = no`, and the monthly check restores it.
gm_state_changed_hands = {
	if = {
		limit = {
			owner = { has_variable = gm_cw_adopting }
		}
		gm_state_adopt_for_winner = yes
	}
	if = {
		limit = {
			gm_state_is_dedicated = yes
			gm_state_is_bound = yes
			owner = {
				NOT = { has_variable = te_cw_role }
				is_revolutionary = no
			}
			gm_state_raised_by_owner = no
		}
		set_variable = gm_seen
		if = {
			limit = { gm_state_kind_faith = yes }
			gm_state_lift_contest = yes
			set_variable = gm_heritage
		}
		else = {
			gm_remove_state_var = { VAR = gm_heritage }
			if = {
				limit = { gm_state_is_contested = no }
				gm_state_contest = yes
			}
		}
	}
	owner = { trigger_event = { id = monument_events.20 } }
}

# ---- Civil wars: the winner continues the nation (#460-#465) -------------------
# Country scope, ROOT = the winner (te_civil_war_on_won, between
# te_civil_war_resolve_sides and te_civil_war_clear). The monuments the loser
# raised become the winner's, now and, for 30 days, in states still changing
# hands (gm_state_changed_hands and gm_check_contests call
# gm_state_adopt_for_winner). The fit test then contests them only if the
# winner's laws differ.
gm_repair_after_civil_war = {
	if = {
		limit = { exists = scope:te_cw_loser }
		set_variable = { name = gm_cw_loser value = scope:te_cw_loser days = 30 }
		set_variable = { name = gm_cw_adopting value = yes days = 30 }
		every_scope_state = {
			limit = { has_building = building_grand_monument }
			gm_state_adopt_for_winner = yes
		}
	}
}

# State scope, owner = a civil war's winner.
gm_state_adopt_for_winner = {
	if = {
		limit = {
			has_variable = gm_raised_by
			owner = { has_variable = gm_cw_loser }
			owner.var:gm_cw_loser ?= { save_temporary_scope_as = gm_tmp_loser }
			var:gm_raised_by = scope:gm_tmp_loser
		}
		set_variable = { name = gm_raised_by value = owner }
	}
}

# ---- The three choices (§4.3) --------------------------------------------------
# State scope. Adds FACTOR x this monument's grandeur to the owner's ledger of
# the IG whose flag the state's variable $WHO$ holds (gm_base_ig or
# gm_supporter_ig). The owner's ledgers must exist (gm_init_ledgers).
gm_state_ledger_ig = {
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = armed_forces }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = devout }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = industrialists }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = intelligentsia }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = landowners }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = petty_bourgeoisie }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = rural_folk }
	gm_state_ledger_ig_one = { WHO = $WHO$ FACTOR = $FACTOR$ IG = trade_unions }
}

gm_state_ledger_ig_one = {
	if = {
		limit = {
			has_variable = $WHO$
			var:$WHO$ = flag:$IG$
		}
		owner = {
			set_variable = {
				name = gm_ig_ledger_$IG$
				value = {
					value = prev.var:gm_grandeur
					multiply = $FACTOR$
					add = var:gm_ig_ledger_$IG$
				}
			}
		}
	}
}

# State scope. What pulling this monument down does (§4.3): its grandeur to
# the teardown ledger (legitimacy for the new order, fading), positive to the
# new order's base, negative to its old supporters. Reads gm_grandeur, the
# level last recorded (current when called from gm_state_tear_down).
gm_state_record_teardown = {
	owner = {
		gm_init_ledgers = yes
		set_variable = {
			name = gm_teardown_ledger
			value = {
				value = var:gm_teardown_ledger
				add = prev.var:gm_grandeur
			}
		}
	}
	gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = 1 }
	gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -1 }
}

gm_state_tear_down = {
	set_variable = { name = gm_grandeur value = gm_state_grandeur }
	gm_state_record_teardown = yes
	owner = {
		remove_list_variable = { name = gm_states target = prev }
	}
	remove_building = building_grand_monument
	gm_clear_state = yes
}

# Rebuilt at half its level (rounded up, at most 200: the ladder's reach) and
# dedicated again under current laws. No effect removes levels, so the old
# building goes and a new one is built (nuclear_strike_halve_building's path).
gm_state_rededicate = {
	set_variable = { name = gm_grandeur value = gm_state_grandeur }
	set_variable = { name = gm_rebuild_cost value = gm_state_rededicate_cost }
	owner = {
		add_treasury = {
			value = prev.var:gm_rebuild_cost
			multiply = -1
		}
		gm_init_ledgers = yes
	}
	gm_state_ledger_ig = { WHO = gm_supporter_ig FACTOR = -0.5 }
	set_variable = {
		name = gm_rebuild_level
		value = {
			value = var:gm_grandeur
			divide = 2
			ceiling = yes
			max = 200
		}
	}
	remove_building = building_grand_monument
	gm_clear_state = yes
	te_construction_market_build_specified_level = {
		SPEC_TYPE = building_grand_monument
		SPEC_LEVEL = var:gm_rebuild_level
	}
	remove_variable = gm_rebuild_level
	remove_variable = gm_rebuild_cost
	gm_state_start_ceremony = yes
}

gm_state_preserve = {
	set_variable = { name = gm_grandeur value = gm_state_grandeur }
	owner = { gm_init_ledgers = yes }
	gm_state_ledger_ig = { WHO = gm_base_ig FACTOR = -1 }
	gm_state_lift_contest = yes
	set_variable = gm_heritage
}

# State scope. Each choice with the tooltip that says what it does. One
# wrapper per choice, so the notice, the per-monument event and the journal
# entry's buttons show the same words. The loc reads the state as THIS.
gm_state_choose_tear_down = {
	custom_tooltip = {
		text = gm_tear_down_tt
		gm_state_tear_down = yes
	}
}

gm_state_choose_rededicate = {
	custom_tooltip = {
		text = gm_rededicate_tt
		gm_state_rededicate = yes
	}
}

gm_state_choose_preserve = {
	custom_tooltip = {
		text = gm_preserve_tt
		gm_state_preserve = yes
	}
}

# State scope. The dedication ceremony, once: a rebuilt monument may also fire
# on_building_built, and two ceremonies queued together would both show.
gm_state_start_ceremony = {
	if = {
		limit = {
			NOT = { has_variable = gm_ceremony_pending }
		}
		set_variable = { name = gm_ceremony_pending days = 30 }
		trigger_event = { id = monument_events.2 }
	}
}

# ---- The AI and the notice (§4.5, §4.6) ----------------------------------------
# Country scope, AI only: a monument contested two months or more is decided,
# by weight. Tear Down is likelier for a small monument or under a
# revolutionary government, Preserve for a tall one, Rededicate only with
# money in the treasury.
gm_ai_decide_contests = {
	if = {
		limit = { is_ai = yes }
		every_scope_state = {
			limit = {
				gm_state_is_contested = yes
				var:gm_contested >= 2
			}
			random_list = {
				10 = {
					modifier = {
						if = {
							limit = { var:gm_grandeur < 5 }
							add = 10
						}
						if = {
							limit = {
								owner = { gm_government_is_revolutionary = yes }
							}
							add = 10
						}
					}
					gm_state_tear_down = yes
				}
				10 = {
					modifier = {
						if = {
							limit = { var:gm_grandeur >= 10 }
							add = 10
						}
					}
					gm_state_preserve = yes
				}
				5 = {
					modifier = {
						if = {
							limit = {
								owner = { scaled_gold_reserves < 0.5 }
							}
							multiply = 0
						}
					}
					gm_state_rededicate = yes
				}
			}
		}
	}
}

# Country scope. New contests since the last notice: a player gets one notice
# (monument_events.16, which clears the flags as it opens); the AI's flags are
# cleared (it decides monthly, above).
gm_notify_new_contests = {
	if = {
		limit = {
			any_scope_state = { has_variable = gm_new_contest }
		}
		if = {
			limit = { is_ai = no }
			trigger_event = { id = monument_events.16 }
		}
		else = {
			every_scope_state = {
				limit = { has_variable = gm_new_contest }
				remove_variable = gm_new_contest
			}
		}
	}
}
```

- [ ] **Step 5: Wire the new steps into the pulses**

In `gm_country_refresh`, insert `gm_check_contests = yes` directly after `gm_set_opposition_ig = yes`, and append `gm_notify_new_contests = yes` as its last line.

In `gm_country_monthly`, insert directly after `gm_country_refresh = yes`:

```
	every_scope_state = {
		limit = { gm_state_is_contested = yes }
		change_variable = { name = gm_contested add = 1 }
	}
	gm_ai_decide_contests = yes
```

In `gm_state_monthly`'s `else` branch, replace

```
		if = {
			limit = { has_variable = gm_seen }
			gm_clear_state = yes
		}
```

with

```
		if = {
			limit = { has_variable = gm_seen }
			# Gone without the Tear Down button (demolished from the building
			# panel): a contested monument counts as torn down (plan decision 6).
			if = {
				limit = { gm_state_is_contested = yes }
				gm_state_record_teardown = yes
			}
			gm_clear_state = yes
		}
```

- [ ] **Step 6: Script values**

Append to `common/script_values/gm_values.txt`:

```

# ---- Contests (§4.3, §4.5) ----------------------------------------------------
# State scope. What Rededicate costs: 5,000 a level.
gm_state_rededicate_cost = {
	value = gm_state_grandeur
	multiply = 5000
}

# Country scope. How many monuments the open notice (monument_events.16) names.
gm_notice_count = {
	value = 0
	if = {
		limit = { has_variable_list = gm_notice_states }
		every_in_list = {
			variable = gm_notice_states
			add = 1
		}
	}
}
```

- [ ] **Step 7: Customizable loc**

Create `common/customizable_localization/gm_custom_loc.txt` (BOM, tabs):

```
# ============================================================================
# GRAND MONUMENTS — customizable localization (spec §1.1, §4, §6)
# ============================================================================
# State scope: the Grand Monument in that state. First valid entry wins.

gm_dedication_name = {
	type = state
	random_valid = no

	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_crown } }
		localization_key = pm_monument_crown
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_republic } }
		localization_key = pm_monument_republic
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_revolution } }
		localization_key = pm_monument_revolution
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_leader } }
		localization_key = pm_monument_leader
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_religious } }
		localization_key = pm_monument_religious
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_civic } }
		localization_key = pm_monument_civic
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_war_memorial } }
		localization_key = pm_monument_war_memorial
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_artistic } }
		localization_key = pm_monument_artistic
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_naturalist } }
		localization_key = pm_monument_naturalist
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_scientific } }
		localization_key = pm_monument_scientific
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_industrial } }
		localization_key = pm_monument_industrial
	}
	text = {
		trigger = { gm_state_has_pm = { PM = pm_monument_athletic } }
		localization_key = pm_monument_athletic
	}
	text = {
		localization_key = pm_monument_undedicated
	}
}

gm_status_name = {
	type = state
	random_valid = no

	text = {
		trigger = { gm_state_is_contested = yes }
		localization_key = gm_status_contested
	}
	text = {
		trigger = { gm_state_is_heritage = yes }
		localization_key = gm_status_heritage
	}
	text = {
		trigger = { gm_state_is_dedicated = no }
		localization_key = gm_status_undedicated
	}
	text = {
		trigger = { gm_state_message_fits = no }
		localization_key = gm_status_unsettled
	}
	text = {
		localization_key = gm_status_fits
	}
}

gm_base_ig_name = {
	type = state
	random_valid = no

	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:armed_forces }
		localization_key = ig_armed_forces
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:devout }
		localization_key = ig_devout
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:industrialists }
		localization_key = ig_industrialists
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:intelligentsia }
		localization_key = ig_intelligentsia
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:landowners }
		localization_key = ig_landowners
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:petty_bourgeoisie }
		localization_key = ig_petty_bourgeoisie
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:rural_folk }
		localization_key = ig_rural_folk
	}
	text = {
		trigger = { has_variable = gm_base_ig var:gm_base_ig = flag:trade_unions }
		localization_key = ig_trade_unions
	}
	text = {
		localization_key = gm_ig_nobody
	}
}

gm_supporter_ig_name = {
	type = state
	random_valid = no

	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:armed_forces }
		localization_key = ig_armed_forces
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:devout }
		localization_key = ig_devout
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:industrialists }
		localization_key = ig_industrialists
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:intelligentsia }
		localization_key = ig_intelligentsia
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:landowners }
		localization_key = ig_landowners
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:petty_bourgeoisie }
		localization_key = ig_petty_bourgeoisie
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:rural_folk }
		localization_key = ig_rural_folk
	}
	text = {
		trigger = { has_variable = gm_supporter_ig var:gm_supporter_ig = flag:trade_unions }
		localization_key = ig_trade_unions
	}
	text = {
		localization_key = gm_ig_nobody
	}
}
```

- [ ] **Step 8: The hooks**

Append to `common/on_actions/monument_events_on_actions.txt`:

```

# ROOT = the state that changed hands (conquest, cession, release, annexation).
on_state_owner_change = {
	on_actions = {
		gm_state_owner_change_on_action
	}
}

gm_state_owner_change_on_action = {
	trigger = {
		gm_system_enabled = yes
		has_building = building_grand_monument
	}
	effect = {
		gm_state_changed_hands = yes
	}
}
```

In `common/on_actions/te_civil_war_on_actions.txt`, `te_civil_war_on_won`, add a line directly before `te_civil_war_clear = yes`:

```
		gm_repair_after_civil_war = yes			# Grand Monuments: adopt the loser's monuments
```

- [ ] **Step 9: The notice and the per-monument event**

Append to `events/monument_events.txt`. Before writing `event_image`, view the picture: `python3 scripts/image_pipeline/contact_sheet.py unspecific_vandalized_storefront` (the event-art rule); if it contradicts the text (a looted shop rather than a crowd), use `unspecific_politicians_arguing` instead and say so in the commit.

```

# ============================================================================
# Event 16: monuments to a fallen order (§4.5)
# ============================================================================
# Players only (gm_notify_new_contests); the AI decides monthly. One notice per
# fall, naming how many monuments it contested. The immediate moves the flags
# into gm_notice_states, so a second refresh this month cannot fire it again.
monument_events.16 = {
	type = country_event
	placement = root

	event_image = { video = "unspecific_vandalized_storefront" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_protest.dds"

	title = monument_events.16.t
	desc = monument_events.16.d
	flavor = monument_events.16.f

	duration = 3

	trigger = {
		any_scope_state = { has_variable = gm_new_contest }
	}

	immediate = {
		clear_variable_list = gm_notice_states
		every_scope_state = {
			limit = { has_variable = gm_new_contest }
			remove_variable = gm_new_contest
			owner = {
				add_to_variable_list = { name = gm_notice_states target = prev }
			}
		}
	}

	# Tear them all down.
	option = {
		name = monument_events.16.a
		custom_tooltip = {
			text = monument_events.16.a.tt
			every_in_list = {
				variable = gm_notice_states
				limit = { gm_state_is_contested = yes }
				gm_state_tear_down = yes
			}
		}
		hidden_effect = { gm_country_refresh = yes }
		ai_chance = { base = 0 }
	}

	# Keep them all as heritage.
	option = {
		name = monument_events.16.b
		custom_tooltip = {
			text = monument_events.16.b.tt
			every_in_list = {
				variable = gm_notice_states
				limit = { gm_state_is_contested = yes }
				gm_state_preserve = yes
			}
		}
		hidden_effect = { gm_country_refresh = yes }
		ai_chance = { base = 0 }
	}

	# Decide on each in turn: one decision per monument.
	option = {
		name = monument_events.16.c
		default_option = yes
		custom_tooltip = {
			text = monument_events.16.c.tt
			every_in_list = {
				variable = gm_notice_states
				limit = { gm_state_is_contested = yes }
				trigger_event = { id = monument_events.17 }
			}
		}
		ai_chance = { base = 1 }
	}
}

# ============================================================================
# Event 17: one contested monument (§4.3)
# ============================================================================
# A state event on the monument's state, from the notice's "Decide on each in
# turn". The same three choices as the journal entry row's buttons (plan
# decision 5), through the same wrappers.
monument_events.17 = {
	type = state_event
	placement = ROOT

	event_image = { video = "unspecific_vandalized_storefront" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_protest.dds"

	title = monument_events.17.t
	# .desc, not .d: .d is the fourth option's name.
	desc = monument_events.17.desc
	flavor = monument_events.17.f

	duration = 3

	trigger = {
		gm_state_is_contested = yes
	}

	immediate = {
		save_scope_as = monument_state
	}

	option = {
		name = monument_events.17.a
		gm_state_choose_tear_down = yes
		hidden_effect = {
			owner = { trigger_event = { id = monument_events.20 } }
		}
	}

	option = {
		name = monument_events.17.b
		gm_state_choose_rededicate = yes
		hidden_effect = {
			owner = { trigger_event = { id = monument_events.20 } }
		}
	}

	option = {
		name = monument_events.17.c
		gm_state_choose_preserve = yes
		hidden_effect = {
			owner = { trigger_event = { id = monument_events.20 } }
		}
	}

	option = {
		name = monument_events.17.d
		# REVIEWED 2026-09-27 (no_effect_option): the decision waits on the monument's journal entry row; the tooltip says the standing penalty continues
		default_option = yes
		custom_tooltip = gm_leave_contested_tt
	}
}
```

- [ ] **Step 10: Loc**

Add to `localization/english/te_events_l_english.yml`, in key order:

```yaml
 monument_events.16.a:0 "Tear them all down"
 monument_events.16.a.tt:0 "Every one of them is pulled down, and its [concept_grandeur] with it. The new order gains legitimacy that fades over about five years. Those who opposed the old order approve; those who raised the monuments resent it."
 monument_events.16.b:0 "Keep them all as heritage"
 monument_events.16.b.tt:0 "Every one of them stays as heritage. Their prestige, visitors and local effects return, but they lend this government no legitimacy, and those who opposed the old order resent that they still stand, less each year."
 monument_events.16.c:0 "Decide on each in turn"
 monument_events.16.c.tt:0 "One decision follows for each monument. Any of them can also be decided later, from its row in the Monuments journal entry. Until then, those who opposed the old order resent every one still standing."
 monument_events.16.d:0 "The order our monuments were raised to honour is gone. [SCOPE.GetRootScope.ScriptValue('gm_notice_count')|0] of them now stand for something this government is not, and crowds have gathered at some of them already, with ropes."
 monument_events.16.f:0 "“We could leave them,” the minister says. “People have always walked past statues of men they disliked.”\n\n“Not while those men are still being cheered in the next street.”"
 monument_events.16.t:0 "Monuments to a Fallen Order"
 monument_events.17.a:0 "Pull it down"
 monument_events.17.b:0 "Rededicate it"
 monument_events.17.c:0 "Keep it as heritage"
 monument_events.17.d:0 "Leave it for now"
 monument_events.17.desc:0 "The [SCOPE.sState('monument_state').GetCustom('gm_dedication_name')] in [SCOPE.sState('monument_state').GetName] honours something this government is not. It must be pulled down, rededicated or kept."
 monument_events.17.f:0 "The stonemasons have been asked for three estimates: one to take it down, one to change the inscription, and one to clean it."
 monument_events.17.t:0 "What Becomes of the Monument"
```

Add to `localization/english/te_miscellaneous_l_english.yml`, in key order:

```yaml
 gm_ig_nobody:0 "no one"
 gm_leave_contested_tt:0 "Decide later, from the monument's row in the Monuments journal entry. While it stands contested it lends nothing but visitors, and #v [THIS.GetState.GetCustom('gm_base_ig_name')]#! resent it."
 gm_preserve_tt:0 "Keep it as heritage. Its prestige, visitors and local effects return; under this government it lends no legitimacy. #v [THIS.GetState.GetCustom('gm_base_ig_name')]#! resent that it still stands, less each year."
 gm_rededicate_tt:0 "Rebuild it at half its [concept_grandeur] under a new dedication, for #R @money![THIS.GetState.MakeScope.ScriptValue('gm_state_rededicate_cost')|0]#!. Its old supporters, #v [THIS.GetState.GetCustom('gm_supporter_ig_name')]#!, resent it a little."
 gm_status_contested:0 "#R Contested#!"
 gm_status_fits:0 "#G Stands#!"
 gm_status_heritage:0 "Heritage"
 gm_status_undedicated:0 "Undedicated"
 gm_status_unsettled:0 "Unsettled"
 gm_tear_down_tt:0 "Pull it down. The new order gains legitimacy that fades over about five years, and #v [THIS.GetState.GetCustom('gm_base_ig_name')]#! approve; #v [THIS.GetState.GetCustom('gm_supporter_ig_name')]#! resent it. All of its [concept_grandeur] is lost."
```

- [ ] **Step 11: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_effects/gm_effects.txt common/script_values/gm_values.txt common/customizable_localization/gm_custom_loc.txt common/on_actions/monument_events_on_actions.txt common/on_actions/te_civil_war_on_actions.txt common/scripted_effects/te_construction_market_build_effects.txt events/monument_events.txt && python3 scripts/analysis/check_localization_files.py && for a in duplicate_key iterator_limit prev_scope modifier_multiplier_var empty_effect silent_variable orphaned_event event_context loc_render; do python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"; done`
Expected: exit 0, no `FAIL` lines. (`event_image_audit` needs the pictures; Task 13 runs it.)

- [ ] **Step 12: Commit**

```bash
git add common/scripted_effects/gm_effects.txt common/script_values/gm_values.txt \
        common/customizable_localization/gm_custom_loc.txt common/on_actions/monument_events_on_actions.txt \
        common/on_actions/te_civil_war_on_actions.txt common/scripted_effects/te_construction_market_build_effects.txt \
        events/monument_events.txt localization/english/te_events_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): contested monuments — Tear Down, Rededicate, Preserve

A monument whose crown, republic, revolution, leader or faith falls, or that
changes hands, becomes contested; the new order's base resents it until the
owner decides. Tear Down, Rededicate (rebuilt at half its level) and Preserve
go into decaying ledgers, so nothing stacks. A civil war's winner adopts the
loser's monuments. Players get one notice per fall; the AI decides monthly.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 7: The dedication ceremony, skins and the inscription

**Files:**
- Modify: `events/monument_events.txt` (rewrite `.2`; append `.11`)
- Modify: `common/scripted_effects/gm_effects.txt` (append the dedication wrappers and skin choice)
- Modify: `common/scripted_triggers/monument_triggers.txt` (append `gm_country_has_revived`)
- Modify: `common/customizable_localization/gm_custom_loc.txt` (append `gm_skin_name`, `gm_inscription`)
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `CeremonyTests`, `SkinTests`)

**Interfaces:**
- Consumes: Task 4's records and default-skin helpers, Task 5's `.20`, Task 1's `te_heritage_*`, Task 3's gates.
- Produces (effects, state scope): `gm_state_dedicate = { KEY }`, `gm_state_dedicate_timeless = { KEY AXIS }` (AXIS `heritage` or `none`), `gm_state_dedicate_regime = { KEY }`, `gm_state_dedicate_leader`, `gm_state_dedicate_faith`, `gm_state_offer_skins = { AXIS }` (`none`, `faith`, `heritage`), `gm_state_offer_skins_none`, `gm_state_offer_skins_faith`, `gm_state_offer_skins_heritage`, `gm_state_choose_skin = { SKIN }`.
- Produces (trigger, country scope): `gm_country_has_revived = { LANG }`.
- Produces (custom loc, state scope): `gm_skin_name`, `gm_inscription`.
- Produces (event): `monument_events.11` (state event: choose the skin).
- Produces (state variable): `gm_skin_axis` (flag `faith` / `heritage`, while the choice is open).

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 7: the ceremony, skins, the inscription ------------------------------------

CEREMONY_OPTION = {"crown": "l", "republic": "b", "revolution": "n", "leader": "o", "religious": "c",
                   "civic": "m", "war_memorial": "e", "artistic": "g", "naturalist": "h", "scientific": "i",
                   "industrial": "j", "athletic": "k"}
CEREMONY_GATE = {"crown": "monument_government_is_crowned = yes",
                 "republic": "monument_government_is_republican = yes",
                 "revolution": "gm_government_is_revolutionary = yes",
                 "leader": "gm_can_raise_leader_monument = yes",
                 "religious": "NOT = { has_law_or_variant = law_type:law_state_atheism }",
                 "industrial": "NOT = { has_law_or_variant = law_type:law_industry_banned }"}
INSCRIPTION_FAITHS = {"catholic": "latin", "jewish": "hebrew", "hindu": "sanskrit", "theravada": "pali",
                      "oriental_orthodox": "coptic", "sunni": "arabic", "shiite": "arabic", "ibadi": "arabic",
                      "orthodox": "slavonic"}
# Named landmarks (spec §1.1, phase 2): (key, the dedications it can take). Each
# is a skin flag `landmark_<key>`, an option `monument_events.11.landmark_<key>`
# placed before the faith options (a landmark is the most specific form), whose
# trigger names its state, and the loc `gm_skin_landmark_<key>`. Empty in phase 1.
LANDMARKS = ()


def ceremony_options():
    event = raw_block_at(read(EVENTS), r"(?m)^monument_events\.2\s*=\s*\{")
    out = {}
    for m in re.finditer(r"option\s*=\s*\{", event):
        body = _match_brace(event, m.end())
        name = re.search(r"name = monument_events\.2\.(\w+)", body)
        out[name.group(1)] = body
    return out


def wrapper_call(d):
    if d.kind == "regime":
        return f"gm_state_dedicate_regime = {{ KEY = {d.key} }}"
    if d.kind == "ruler":
        return "gm_state_dedicate_leader = yes"
    if d.kind == "faith":
        return "gm_state_dedicate_faith = yes"
    axis = "heritage" if d.key in HERITAGE_SKINNED else "none"
    return f"gm_state_dedicate_timeless = {{ KEY = {d.key} AXIS = {axis} }}"


class CeremonyTests(unittest.TestCase):
    def test_every_dedication_has_its_option(self):
        options = ceremony_options()
        self.assertEqual(set(options), set(CEREMONY_OPTION.values()) | {"a"})
        for d in DEDICATIONS:
            body = squash(strip_comments(options[CEREMONY_OPTION[d.key]]))
            self.assertIn(f"text = monument_events.2.{CEREMONY_OPTION[d.key]}.tt {wrapper_call(d)}", body, d.key)
            if d.key in CEREMONY_GATE:
                self.assertIn(CEREMONY_GATE[d.key], body, d.key)
            if d.key in TECH_GATES:
                self.assertIn(f"has_technology_researched = {TECH_GATES[d.key]}", body, d.key)

    def test_leave_undedicated_clears_the_pending_flag(self):
        body = ceremony_options()["a"]
        self.assertNotIn("REVIEWED", body)
        self.assertIn("gm_remove_state_var = { VAR = gm_ceremony_pending }", squash(body))

    def test_tooltips_hold_no_hand_kept_numbers(self):
        L = loc()
        keys = [f"monument_events.2.{o}.tt" for o in list(CEREMONY_OPTION.values()) + ["a"]]
        keys.append("monument_events.2.common_tt")
        for key in keys:
            self.assertIn(key, L)
            self.assertNotRegex(L[key], r"#G [+-]?\d", f"{key}: numbers come from gm_step_* script values")
        for o in CEREMONY_OPTION.values():
            self.assertIn("$monument_events.2.common_tt$", L[f"monument_events.2.{o}.tt"])

    def test_wrappers(self):
        e = read(EFFECTS)
        base = squash(block(e, "gm_state_dedicate"))
        self.assertIn("production_method = pm_monument_$KEY$", base)
        self.assertIn("set_variable = gm_seen", base)
        self.assertIn("set_variable = { name = gm_raised_by value = owner }", squash(block(e, "gm_state_dedicate_regime")))
        leader = squash(block(e, "gm_state_dedicate_leader"))
        self.assertIn("gm_state_record_honoree = yes", leader)
        self.assertIn("gm_state_offer_skins = { AXIS = heritage }", leader)
        faith = squash(block(e, "gm_state_dedicate_faith"))
        self.assertIn("gm_state_record_faith = yes", faith)
        self.assertIn("gm_state_offer_skins = { AXIS = faith }", faith)
        self.assertNotIn("gm_raised_by", squash(block(e, "gm_state_dedicate_timeless")))
        offer = squash(block(e, "gm_state_offer_skins"))
        self.assertIn("gm_state_offer_skins_$AXIS$ = yes", offer)
        self.assertIn("trigger_event = { id = monument_events.20 }", offer)
        faith_offer = squash(block(e, "gm_state_offer_skins_faith"))
        self.assertIn("gm_state_offer_skins_heritage = yes", faith_offer, "mod religions fall back to heritage")


class SkinTests(unittest.TestCase):
    def setUp(self):
        self.event = raw_block_at(read(EVENTS), r"(?m)^monument_events\.11\s*=\s*\{")
        self.assertIsNotNone(self.event)

    def _options(self):
        out = []
        for m in re.finditer(r"option\s*=\s*\{", self.event):
            body = squash(strip_comments(_match_brace(self.event, m.end())))
            name = re.search(r"name = monument_events\.11\.(\w+)", body).group(1)
            out.append((name, body))
        return out

    def test_an_option_per_skin_generic_last(self):
        options = self._options()
        names = [n for n, _ in options]
        expected = ([f"landmark_{k}" for k, _ in LANDMARKS] + [f"faith_{f}" for f in FAITHS]
                    + [f"heritage_{h}" for h in HERITAGES] + ["generic"])
        self.assertEqual(names, expected)
        bodies = dict(options)
        for f in FAITHS:
            self.assertIn(f"var:gm_skin_axis = flag:faith owner = {{ religion = rel:{f} }}", bodies[f"faith_{f}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = faith_{f} }}", bodies[f"faith_{f}"])
        for h in HERITAGES:
            skin = f"faith_{HERITAGE_AS_FAITH[h]}" if h in HERITAGE_AS_FAITH else f"heritage_{h}"
            self.assertIn(f"var:gm_skin_axis = flag:heritage owner = {{ te_heritage_{h} = yes }}",
                          bodies[f"heritage_{h}"])
            self.assertIn(f"gm_state_choose_skin = {{ SKIN = {skin} }}", bodies[f"heritage_{h}"])
        self.assertNotIn("default_option", squash(strip_comments(self.event)))

    def test_skins_read_only_own_identity(self):
        body = strip_comments(self.event)
        self.assertNotRegex(body, r"\bculture\s*=|\bhas_discrimination_trait|any_scope_pop")

    def test_skin_loc_and_names(self):
        L = loc()
        for name, _ in self._options():
            self.assertIn(f"monument_events.11.{name}", L)
        for key in ("t", "d", "f"):
            self.assertIn(f"monument_events.11.{key}", L)
        names = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        for skin in SKINS:
            self.assertIn(f"gm_skin_{skin}", L, skin)
            if skin != "generic":
                self.assertIn(f"var:gm_skin = flag:{skin} }} localization_key = gm_skin_{skin}", names)
        self.assertTrue(names.endswith("text = { localization_key = gm_skin_generic }"))

    def test_landmarks_phase_2_hook(self):
        L = loc()
        names = [n for n, _ in self._options()]
        names_block = squash(block(read(CUSTOM_LOC), "gm_skin_name"))
        for key, _dedications in LANDMARKS:
            self.assertIn(f"landmark_{key}", names)
            self.assertLess(names.index(f"landmark_{key}"), names.index(f"faith_{FAITHS[0]}"))
            self.assertIn(f"gm_skin_landmark_{key}", L)
            self.assertIn(f"flag:landmark_{key} }} localization_key = gm_skin_landmark_{key}", names_block)

    def test_inscription(self):
        body = squash(block(read(CUSTOM_LOC), "gm_inscription"))
        L = loc()
        for h in HERITAGE_SKINS:
            self.assertIn(f"var:gm_skin = flag:heritage_{h} owner = {{ gm_country_has_revived = {{ LANG = {h} }} }}", body)
        for f, lang in INSCRIPTION_FAITHS.items():
            self.assertIn(f"var:gm_skin = flag:faith_{f} owner = {{ gm_country_has_revived = {{ LANG = {lang} }} }}", body)
        for h in HERITAGES:
            self.assertIn(f"gm_inscription_{h}", L)
        self.assertIn("gm_inscription_none", L)
        revived = squash(block(read(TRIGGERS), "gm_country_has_revived"))
        self.assertIn("has_amendment = amendment_type:amendment_langreform_revived_$LANG$", revived)
```

- [ ] **Step 2: Run to confirm they fail**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: `CeremonyTests`, `SkinTests` FAIL/ERROR.

- [ ] **Step 3: The dedication wrappers and the skin choice**

Append to `common/scripted_effects/gm_effects.txt`:

```

# ---- The dedication (§3): from the ceremony, monument_events.2 (ROOT = state) ----
# The ceremony's option knows the dedication, so these wrappers never read the
# production method back: whether activate_production_method is visible within
# the same effect is not established.
gm_state_dedicate = {
	activate_production_method = {
		building_type = building_grand_monument
		production_method = pm_monument_$KEY$
	}
	gm_remove_state_var = { VAR = gm_ceremony_pending }
	set_variable = gm_seen
}

# AXIS: heritage (To the Nation, War Memorial) or none (the civic-progress five).
gm_state_dedicate_timeless = {
	gm_state_dedicate = { KEY = $KEY$ }
	gm_state_offer_skins = { AXIS = $AXIS$ }
}

gm_state_dedicate_regime = {
	gm_state_dedicate = { KEY = $KEY$ }
	set_variable = { name = gm_raised_by value = owner }
	gm_state_offer_skins = { AXIS = heritage }
}

gm_state_dedicate_leader = {
	gm_state_dedicate = { KEY = leader }
	set_variable = { name = gm_raised_by value = owner }
	gm_state_record_honoree = yes
	gm_state_offer_skins = { AXIS = heritage }
}

gm_state_dedicate_faith = {
	gm_state_dedicate = { KEY = religious }
	set_variable = { name = gm_raised_by value = owner }
	gm_state_record_faith = yes
	gm_state_offer_skins = { AXIS = faith }
}

# ---- Skins (§1.1) ----------------------------------------------------------------
# State scope. The most specific skin for the axis, set at once; then, if it is
# not the generic one, the choice (monument_events.11), whose first valid
# option is that same skin. Then a national refresh.
gm_state_offer_skins = {
	set_variable = { name = gm_skin value = flag:generic }
	gm_state_offer_skins_$AXIS$ = yes
	owner = { trigger_event = { id = monument_events.20 } }
}

gm_state_offer_skins_none = {
	gm_remove_state_var = { VAR = gm_skin_axis }
}

gm_state_offer_skins_faith = {
	gm_state_default_faith_skin = yes
	if = {
		limit = { var:gm_skin = flag:generic }
		# The mod's own religions have no faith skin: a heritage skin instead.
		gm_state_offer_skins_heritage = yes
	}
	else = {
		set_variable = { name = gm_skin_axis value = flag:faith }
		trigger_event = { id = monument_events.11 }
	}
}

gm_state_offer_skins_heritage = {
	gm_state_default_heritage_skin = yes
	if = {
		limit = {
			NOT = { var:gm_skin = flag:generic }
		}
		set_variable = { name = gm_skin_axis value = flag:heritage }
		trigger_event = { id = monument_events.11 }
	}
}

# State scope, an option of monument_events.11.
gm_state_choose_skin = {
	custom_tooltip = {
		text = gm_skin_choice_tt
		set_variable = { name = gm_skin value = flag:$SKIN$ }
		gm_remove_state_var = { VAR = gm_skin_axis }
	}
}
```

- [ ] **Step 4: The revival trigger**

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  The revived-language inscription (spec §1.1)
# ======================================================================
# Country scope. The country has revived $LANG$ under language reform
# (amendment_langreform_revived_<language>; common/scripted_triggers/
# misc_triggers.txt reads the same amendments).
gm_country_has_revived = {
	has_law = law_type:law_state_led_language_reform
	active_law:lawgroup_language_policy = {
		has_amendment = amendment_type:amendment_langreform_revived_$LANG$
	}
}
```

- [ ] **Step 5: Skin names and the inscription**

Append to `common/customizable_localization/gm_custom_loc.txt`:

```

# The form the monument takes (§1.1), from the state variable gm_skin.
gm_skin_name = {
	type = state
	random_valid = no

	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_catholic }
		localization_key = gm_skin_faith_catholic
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_protestant }
		localization_key = gm_skin_faith_protestant
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_orthodox }
		localization_key = gm_skin_faith_orthodox
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_oriental_orthodox }
		localization_key = gm_skin_faith_oriental_orthodox
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_sunni }
		localization_key = gm_skin_faith_sunni
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_shiite }
		localization_key = gm_skin_faith_shiite
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_ibadi }
		localization_key = gm_skin_faith_ibadi
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_jewish }
		localization_key = gm_skin_faith_jewish
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_mahayana }
		localization_key = gm_skin_faith_mahayana
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_gelugpa }
		localization_key = gm_skin_faith_gelugpa
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_theravada }
		localization_key = gm_skin_faith_theravada
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_confucian }
		localization_key = gm_skin_faith_confucian
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_hindu }
		localization_key = gm_skin_faith_hindu
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_shinto }
		localization_key = gm_skin_faith_shinto
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_sikh }
		localization_key = gm_skin_faith_sikh
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:faith_animist }
		localization_key = gm_skin_faith_animist
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_latin }
		localization_key = gm_skin_heritage_latin
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_hebrew }
		localization_key = gm_skin_heritage_hebrew
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_sanskrit }
		localization_key = gm_skin_heritage_sanskrit
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_geez }
		localization_key = gm_skin_heritage_geez
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_slavonic }
		localization_key = gm_skin_heritage_slavonic
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_avestan }
		localization_key = gm_skin_heritage_avestan
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_arabic }
		localization_key = gm_skin_heritage_arabic
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_chinese }
		localization_key = gm_skin_heritage_chinese
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_greek }
		localization_key = gm_skin_heritage_greek
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_irish }
		localization_key = gm_skin_heritage_irish
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_nahuatl }
		localization_key = gm_skin_heritage_nahuatl
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_norse }
		localization_key = gm_skin_heritage_norse
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_gothic }
		localization_key = gm_skin_heritage_gothic
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_mayan }
		localization_key = gm_skin_heritage_mayan
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_prussian }
		localization_key = gm_skin_heritage_prussian
	}
	text = {
		trigger = { has_variable = gm_skin var:gm_skin = flag:heritage_aramaic }
		localization_key = gm_skin_heritage_aramaic
	}
	text = {
		localization_key = gm_skin_generic
	}
}

# One line when the monument's skin draws on a language the country has
# revived under language reform; empty otherwise.
gm_inscription = {
	type = state
	random_valid = no

	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_latin
			owner = { gm_country_has_revived = { LANG = latin } }
		}
		localization_key = gm_inscription_latin
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_hebrew
			owner = { gm_country_has_revived = { LANG = hebrew } }
		}
		localization_key = gm_inscription_hebrew
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_sanskrit
			owner = { gm_country_has_revived = { LANG = sanskrit } }
		}
		localization_key = gm_inscription_sanskrit
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_geez
			owner = { gm_country_has_revived = { LANG = geez } }
		}
		localization_key = gm_inscription_geez
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_slavonic
			owner = { gm_country_has_revived = { LANG = slavonic } }
		}
		localization_key = gm_inscription_slavonic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_avestan
			owner = { gm_country_has_revived = { LANG = avestan } }
		}
		localization_key = gm_inscription_avestan
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_arabic
			owner = { gm_country_has_revived = { LANG = arabic } }
		}
		localization_key = gm_inscription_arabic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_chinese
			owner = { gm_country_has_revived = { LANG = chinese } }
		}
		localization_key = gm_inscription_chinese
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_greek
			owner = { gm_country_has_revived = { LANG = greek } }
		}
		localization_key = gm_inscription_greek
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_irish
			owner = { gm_country_has_revived = { LANG = irish } }
		}
		localization_key = gm_inscription_irish
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_nahuatl
			owner = { gm_country_has_revived = { LANG = nahuatl } }
		}
		localization_key = gm_inscription_nahuatl
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_norse
			owner = { gm_country_has_revived = { LANG = norse } }
		}
		localization_key = gm_inscription_norse
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_gothic
			owner = { gm_country_has_revived = { LANG = gothic } }
		}
		localization_key = gm_inscription_gothic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_mayan
			owner = { gm_country_has_revived = { LANG = mayan } }
		}
		localization_key = gm_inscription_mayan
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_prussian
			owner = { gm_country_has_revived = { LANG = prussian } }
		}
		localization_key = gm_inscription_prussian
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:heritage_aramaic
			owner = { gm_country_has_revived = { LANG = aramaic } }
		}
		localization_key = gm_inscription_aramaic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_catholic
			owner = { gm_country_has_revived = { LANG = latin } }
		}
		localization_key = gm_inscription_latin
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_jewish
			owner = { gm_country_has_revived = { LANG = hebrew } }
		}
		localization_key = gm_inscription_hebrew
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_hindu
			owner = { gm_country_has_revived = { LANG = sanskrit } }
		}
		localization_key = gm_inscription_sanskrit
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_theravada
			owner = { gm_country_has_revived = { LANG = pali } }
		}
		localization_key = gm_inscription_pali
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_oriental_orthodox
			owner = { gm_country_has_revived = { LANG = coptic } }
		}
		localization_key = gm_inscription_coptic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_sunni
			owner = { gm_country_has_revived = { LANG = arabic } }
		}
		localization_key = gm_inscription_arabic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_shiite
			owner = { gm_country_has_revived = { LANG = arabic } }
		}
		localization_key = gm_inscription_arabic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_ibadi
			owner = { gm_country_has_revived = { LANG = arabic } }
		}
		localization_key = gm_inscription_arabic
	}
	text = {
		trigger = {
			has_variable = gm_skin
			var:gm_skin = flag:faith_orthodox
			owner = { gm_country_has_revived = { LANG = slavonic } }
		}
		localization_key = gm_inscription_slavonic
	}
	text = {
		localization_key = gm_inscription_none
	}
}
```

- [ ] **Step 6: The ceremony**

In `events/monument_events.txt`, update the file header's `Event 2` line to `Event 2  - the dedication ceremony (state event), then Event 11 - the skin (§1.1).`, and replace the whole comment block above `monument_events.2 = {` and the event itself with:

```
# Event 2: The Dedication (§3). A STATE event placed on the monument's state;
# ROOT is that state, and every country-level gate goes through `owner`. Each
# option dedicates through a gm_state_dedicate_* wrapper (gm_effects.txt),
# which writes the records, offers the skins that fit (Event 11) and refreshes
# the nation (Event 20).
#
# OPTION GATING: a `trigger` hides a dedication the country cannot raise (a
# crown it does not wear, a faith under State Atheism, an untaught technology);
# ai_chance tilts the rest.
#
# TOOLTIPS: every number is read from the gm_step_* script values
# (gm_values.txt), which the registry test pins to the static modifiers. The
# loc holds no hand-kept numbers.
monument_events.2 = {
	type = state_event
	placement = ROOT

	event_image = { video = "unspecific_world_fair" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = monument_events.2.t
	desc = monument_events.2.d
	flavor = monument_events.2.f

	duration = 3

	# Only for a monument not yet dedicated. `has_building` alone would re-open
	# the question every time an existing monument gains a level.
	trigger = {
		gm_system_enabled = yes
		any_scope_building = {
			is_building_type = building_grand_monument
			has_active_production_method = pm_monument_undedicated
		}
	}

	# Named in the description and in every option tooltip.
	immediate = {
		save_scope_as = monument_state
	}

	# Leave it undedicated; the ceremony asks again at the next level.
	option = {
		name = monument_events.2.a
		default_option = yes
		ai_chance = { base = 1 }
		custom_tooltip = monument_events.2.a.tt
		hidden_effect = {
			gm_remove_state_var = { VAR = gm_ceremony_pending }
		}
	}

	# To the Crown.
	option = {
		name = monument_events.2.l
		trigger = {
			owner = { monument_government_is_crowned = yes }
		}
		ai_chance = {
			base = 3
			modifier = {
				trigger = {
					owner = { government_legitimacy < 40 }
				}
				add = 5
			}
		}
		custom_tooltip = {
			text = monument_events.2.l.tt
			gm_state_dedicate_regime = { KEY = crown }
		}
	}

	# To the Republic.
	option = {
		name = monument_events.2.b
		trigger = {
			owner = { monument_government_is_republican = yes }
		}
		ai_chance = {
			base = 3
			modifier = {
				trigger = {
					owner = { government_legitimacy < 40 }
				}
				add = 5
			}
		}
		custom_tooltip = {
			text = monument_events.2.b.tt
			gm_state_dedicate_regime = { KEY = republic }
		}
	}

	# To the Revolution.
	option = {
		name = monument_events.2.n
		trigger = {
			owner = { gm_government_is_revolutionary = yes }
		}
		ai_chance = {
			base = 3
			modifier = {
				trigger = {
					owner = { government_legitimacy < 40 }
				}
				add = 5
			}
		}
		custom_tooltip = {
			text = monument_events.2.n.tt
			gm_state_dedicate_regime = { KEY = revolution }
		}
	}

	# To the Leader: a personality cult.
	option = {
		name = monument_events.2.o
		trigger = {
			owner = { gm_can_raise_leader_monument = yes }
		}
		ai_chance = {
			base = 5
			modifier = {
				trigger = {
					owner = { government_legitimacy < 40 }
				}
				add = 5
			}
		}
		custom_tooltip = {
			text = monument_events.2.o.tt
			gm_state_dedicate_leader = yes
		}
	}

	# A grand shrine. Hidden only under State Atheism.
	option = {
		name = monument_events.2.c
		trigger = {
			owner = {
				NOT = { has_law_or_variant = law_type:law_state_atheism }
			}
		}
		ai_chance = {
			base = 3
			modifier = {
				trigger = {
					owner = { has_law_or_variant = law_type:law_total_separation }
				}
				add = -2
			}
			modifier = {
				trigger = {
					owner = { has_law_or_variant = law_type:law_state_religion }
				}
				add = 2
			}
			modifier = {
				trigger = {
					owner = { ig:ig_devout = { is_in_government = yes } }
				}
				add = 3
			}
		}
		custom_tooltip = {
			text = monument_events.2.c.tt
			gm_state_dedicate_faith = yes
		}
	}

	# To the Nation: never hidden, never falls.
	option = {
		name = monument_events.2.m
		ai_chance = { base = 3 }
		custom_tooltip = {
			text = monument_events.2.m.tt
			gm_state_dedicate_timeless = { KEY = civic AXIS = heritage }
		}
	}

	# War memorial. A country just through a war reaches for it.
	option = {
		name = monument_events.2.e
		ai_chance = {
			base = 3
			modifier = {
				trigger = {
					owner = { is_at_war = yes }
				}
				add = 3
			}
		}
		custom_tooltip = {
			text = monument_events.2.e.tt
			gm_state_dedicate_timeless = { KEY = war_memorial AXIS = heritage }
		}
	}

	# Opera house.
	option = {
		name = monument_events.2.g
		trigger = {
			owner = { has_technology_researched = romanticism }
		}
		ai_chance = { base = 3 }
		custom_tooltip = {
			text = monument_events.2.g.tt
			gm_state_dedicate_timeless = { KEY = artistic AXIS = none }
		}
	}

	# Botanical gardens.
	option = {
		name = monument_events.2.h
		trigger = {
			owner = { has_technology_researched = romanticism }
		}
		ai_chance = {
			base = 3
			# The state itself has industry worth planting over.
			modifier = {
				trigger = {
					pollution_generation >= 200
				}
				add = 3
			}
		}
		custom_tooltip = {
			text = monument_events.2.h.tt
			gm_state_dedicate_timeless = { KEY = naturalist AXIS = none }
		}
	}

	# Observatory.
	option = {
		name = monument_events.2.i
		trigger = {
			owner = { has_technology_researched = empiricism }
		}
		ai_chance = { base = 3 }
		custom_tooltip = {
			text = monument_events.2.i.tt
			gm_state_dedicate_timeless = { KEY = scientific AXIS = none }
		}
	}

	# Exhibition hall. Hidden where industry itself is outlawed.
	option = {
		name = monument_events.2.j
		trigger = {
			owner = {
				has_technology_researched = marketing_research
				NOT = { has_law_or_variant = law_type:law_industry_banned }
			}
		}
		ai_chance = { base = 3 }
		custom_tooltip = {
			text = monument_events.2.j.tt
			gm_state_dedicate_timeless = { KEY = industrial AXIS = none }
		}
	}

	# Stadium.
	option = {
		name = monument_events.2.k
		trigger = {
			owner = { has_technology_researched = television_broadcasting }
		}
		ai_chance = { base = 3 }
		custom_tooltip = {
			text = monument_events.2.k.tt
			gm_state_dedicate_timeless = { KEY = athletic AXIS = none }
		}
	}
}
```

- [ ] **Step 7: The skin choice**

Before writing `event_image`, view the pictures (`python3 scripts/image_pipeline/contact_sheet.py unspecific_world_fair europenorthamerica_judaism southamerica_christianity asia_hinduism_sikhism asia_confucianism_shinto asia_buddhism middleeast_islam africa_animism`); these are the ones `monument_events.4` already shows per faith. Append to `events/monument_events.txt`:

```

# ============================================================================
# Event 11: the form the monument takes (§1.1)
# ============================================================================
# A state event, from gm_state_offer_skins when a specific skin fits. Offers
# the skins of the builder's own faith (a Shrine) or of each primary culture's
# classical heritage (the language-reform revival partition, te_heritage_*),
# and the plain style. Faith first, then heritage in the partition's order,
# generic last, and no default_option: an expired event takes the first valid
# option, which is the most specific skin, the one already set.
monument_events.11 = {
	type = state_event
	placement = ROOT

	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:jewish }
		}
		video = "europenorthamerica_judaism"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = {
				OR = {
					religion = rel:protestant
					religion = rel:catholic
					religion = rel:orthodox
					religion = rel:oriental_orthodox
				}
			}
		}
		video = "southamerica_christianity"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = {
				OR = {
					religion = rel:hindu
					religion = rel:sikh
				}
			}
		}
		video = "asia_hinduism_sikhism"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = {
				OR = {
					religion = rel:shinto
					religion = rel:confucian
				}
			}
		}
		video = "asia_confucianism_shinto"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = {
				OR = {
					religion = rel:mahayana
					religion = rel:gelugpa
					religion = rel:theravada
				}
			}
		}
		video = "asia_buddhism"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = {
				OR = {
					religion = rel:sunni
					religion = rel:shiite
					religion = rel:ibadi
				}
			}
		}
		video = "middleeast_islam"
	}
	event_image = {
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:animist }
		}
		video = "africa_animism"
	}
	event_image = {
		video = "unspecific_world_fair"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = monument_events.11.t
	desc = monument_events.11.d
	flavor = monument_events.11.f

	duration = 3

	trigger = {
		has_variable = gm_skin_axis
	}

	immediate = {
		save_scope_as = monument_state
	}

	option = {
		name = monument_events.11.faith_catholic
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:catholic }
		}
		gm_state_choose_skin = { SKIN = faith_catholic }
	}

	option = {
		name = monument_events.11.faith_protestant
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:protestant }
		}
		gm_state_choose_skin = { SKIN = faith_protestant }
	}

	option = {
		name = monument_events.11.faith_orthodox
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:orthodox }
		}
		gm_state_choose_skin = { SKIN = faith_orthodox }
	}

	option = {
		name = monument_events.11.faith_oriental_orthodox
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:oriental_orthodox }
		}
		gm_state_choose_skin = { SKIN = faith_oriental_orthodox }
	}

	option = {
		name = monument_events.11.faith_sunni
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:sunni }
		}
		gm_state_choose_skin = { SKIN = faith_sunni }
	}

	option = {
		name = monument_events.11.faith_shiite
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:shiite }
		}
		gm_state_choose_skin = { SKIN = faith_shiite }
	}

	option = {
		name = monument_events.11.faith_ibadi
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:ibadi }
		}
		gm_state_choose_skin = { SKIN = faith_ibadi }
	}

	option = {
		name = monument_events.11.faith_jewish
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:jewish }
		}
		gm_state_choose_skin = { SKIN = faith_jewish }
	}

	option = {
		name = monument_events.11.faith_mahayana
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:mahayana }
		}
		gm_state_choose_skin = { SKIN = faith_mahayana }
	}

	option = {
		name = monument_events.11.faith_gelugpa
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:gelugpa }
		}
		gm_state_choose_skin = { SKIN = faith_gelugpa }
	}

	option = {
		name = monument_events.11.faith_theravada
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:theravada }
		}
		gm_state_choose_skin = { SKIN = faith_theravada }
	}

	option = {
		name = monument_events.11.faith_confucian
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:confucian }
		}
		gm_state_choose_skin = { SKIN = faith_confucian }
	}

	option = {
		name = monument_events.11.faith_hindu
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:hindu }
		}
		gm_state_choose_skin = { SKIN = faith_hindu }
	}

	option = {
		name = monument_events.11.faith_shinto
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:shinto }
		}
		gm_state_choose_skin = { SKIN = faith_shinto }
	}

	option = {
		name = monument_events.11.faith_sikh
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:sikh }
		}
		gm_state_choose_skin = { SKIN = faith_sikh }
	}

	option = {
		name = monument_events.11.faith_animist
		trigger = {
			var:gm_skin_axis = flag:faith
			owner = { religion = rel:animist }
		}
		gm_state_choose_skin = { SKIN = faith_animist }
	}

	option = {
		name = monument_events.11.heritage_latin
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_latin = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_latin }
	}

	option = {
		name = monument_events.11.heritage_hebrew
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_hebrew = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_hebrew }
	}

	option = {
		name = monument_events.11.heritage_sanskrit
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_sanskrit = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_sanskrit }
	}

	option = {
		name = monument_events.11.heritage_geez
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_geez = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_geez }
	}

	option = {
		name = monument_events.11.heritage_slavonic
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_slavonic = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_slavonic }
	}

	option = {
		name = monument_events.11.heritage_pali
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_pali = yes }
		}
		gm_state_choose_skin = { SKIN = faith_theravada }
	}

	option = {
		name = monument_events.11.heritage_avestan
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_avestan = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_avestan }
	}

	option = {
		name = monument_events.11.heritage_arabic
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_arabic = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_arabic }
	}

	option = {
		name = monument_events.11.heritage_chinese
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_chinese = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_chinese }
	}

	option = {
		name = monument_events.11.heritage_greek
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_greek = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_greek }
	}

	option = {
		name = monument_events.11.heritage_irish
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_irish = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_irish }
	}

	option = {
		name = monument_events.11.heritage_coptic
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_coptic = yes }
		}
		gm_state_choose_skin = { SKIN = faith_oriental_orthodox }
	}

	option = {
		name = monument_events.11.heritage_nahuatl
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_nahuatl = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_nahuatl }
	}

	option = {
		name = monument_events.11.heritage_norse
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_norse = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_norse }
	}

	option = {
		name = monument_events.11.heritage_gothic
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_gothic = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_gothic }
	}

	option = {
		name = monument_events.11.heritage_mayan
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_mayan = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_mayan }
	}

	option = {
		name = monument_events.11.heritage_prussian
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_prussian = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_prussian }
	}

	option = {
		name = monument_events.11.heritage_aramaic
		trigger = {
			var:gm_skin_axis = flag:heritage
			owner = { te_heritage_aramaic = yes }
		}
		gm_state_choose_skin = { SKIN = heritage_aramaic }
	}

	# Always offered, last: with no default_option, an expired event takes the
	# first valid option, which is the most specific skin.
	option = {
		name = monument_events.11.generic
		gm_state_choose_skin = { SKIN = generic }
	}
}
```

- [ ] **Step 8: Loc**

Replace the existing `monument_events.2.*.tt` values in `localization/english/te_events_l_english.yml`, and add the new keys, in key order. Every number comes from a `gm_step_*` script value:

```yaml
 monument_events.2.a.tt:0 "It opens under no flag and draws visitors on its size alone. The ceremony asks again when its next level is finished.\n\n$monument_events.2.common_tt$"
 monument_events.2.b.tt:0 "A monument to the republic. While the country is a republic and still owns it, it lends #v $country_legitimacy_base_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_legitimacy')|0]#! for each step of regime [concept_grandeur], counted with our other monuments to the regime. The $ig_intelligentsia$ approve and the $ig_landowners$ object. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_republic')|%0]#! $state_loyalists_from_political_movements_mult$ for each step of its own.\n\nIf the republic falls, or the state passes to another country, it becomes #R contested#!.\n\n$monument_events.2.common_tt$"
 monument_events.2.c.tt:0 "A grand shrine to our faith. The $ig_devout$ approve, and #v $interest_group_ig_devout_pop_attraction_mult$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_national_religious')|%0]#! for each step of [concept_grandeur], counted with our other shrines. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_religious')|%0]#! $state_conversion_mult$ for each step of its own.\n\nIf the country abandons the faith it honours, or adopts State Atheism, it becomes #R contested#!. If the state passes to another country, it becomes heritage.\n\n$monument_events.2.common_tt$"
 monument_events.2.common_tt:0 "Every monument: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_prestige')|0]#! prestige for each step of standing [concept_grandeur], counted with our other monuments, and #G +[SCOPE.GetRootScope.ScriptValue('gm_step_tourism')|%0]#! $building_tourism_industry_throughput_add$ in [SCOPE.sState('monument_state').GetName] for each step of its own."
 monument_events.2.e.tt:0 "A memorial to the fallen. The $ig_armed_forces$ approve, and #v $country_war_support_casualties_mult$#! #G [SCOPE.GetRootScope.ScriptValue('gm_step_national_war_memorial')|%0]#! for each step of [concept_grandeur], counted with our other memorials. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_war_memorial')|%0]#! $state_conscription_rate_add$ for each step of its own. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.g.tt:0 "A grand opera house. The $ig_intelligentsia$ approve, and #v $interest_group_ig_intelligentsia_pop_attraction_mult$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_national_artistic')|%0]#! for each step of [concept_grandeur], counted with our other opera houses. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_artistic')|%0]#! $building_art_academy_throughput_add$ for each step of its own. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.h.tt:0 "Botanical gardens. The $ig_rural_folk$ approve. In [SCOPE.sState('monument_state').GetName]: #G [SCOPE.GetRootScope.ScriptValue('gm_step_local_naturalist')|0]#! $state_pollution_generation_add$ for each step of its own [concept_grandeur]. They never fall with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.i.tt:0 "A grand observatory. The $ig_intelligentsia$ approve, and #v $country_weekly_innovation_max_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_national_scientific')|0]#! for each step of [concept_grandeur], counted with our other observatories. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_scientific')|%3]#! $state_literacy_growth_add$ for each step of its own. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.j.tt:0 "A great exhibition hall. The $ig_industrialists$ approve, and #v $interest_group_ig_industrialists_pop_attraction_mult$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_national_industrial')|%0]#! for each step of [concept_grandeur], counted with our other exhibition halls. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_industrial')|%0]#! $state_migration_pull_mult$ for each step of its own. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.k.tt:0 "A grand stadium. The $ig_trade_unions$ approve. In [SCOPE.sState('monument_state').GetName]: #G [SCOPE.GetRootScope.ScriptValue('gm_step_local_athletic')|%0]#! $state_turmoil_effects_mult$ for each step of its own [concept_grandeur]. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.l.tt:0 "A monument to the Crown. While the country is crowned and still owns it, it lends #v $country_legitimacy_base_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_legitimacy')|0]#! for each step of regime [concept_grandeur], counted with our other monuments to the regime. The $ig_landowners$ approve and the $ig_intelligentsia$ object. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_crown')|%0]#! $state_loyalists_from_political_movements_mult$ for each step of its own.\n\nIf the crown falls, or the state passes to another country, it becomes #R contested#!.\n\n$monument_events.2.common_tt$"
 monument_events.2.m.tt:0 "Not to a party and not to a house, but to the country itself. The $ig_petty_bourgeoisie$ approve. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_civic')|%0]#! $state_loyalists_from_political_movements_mult$ for each step of its own [concept_grandeur]. It never falls with a government.\n\n$monument_events.2.common_tt$"
 monument_events.2.n:0 "Dedicate it to the revolution"
 monument_events.2.n.tt:0 "A monument to the revolution. While the country is a single-party state or a council republic and still owns it, it lends #v $country_legitimacy_base_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_legitimacy')|0]#! for each step of regime [concept_grandeur], counted with our other monuments to the regime. The $ig_trade_unions$ approve and the $ig_industrialists$ object. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_revolution')|%0]#! $state_loyalists_from_political_movements_mult$ for each step of its own.\n\nIf that regime falls, or the state passes to another country, it becomes #R contested#!.\n\n$monument_events.2.common_tt$"
 monument_events.2.o:0 "Raise it to our leader"
 monument_events.2.o.tt:0 "A monument to our head of state, raised while they rule. While they rule and the country still owns it, it lends #v $country_legitimacy_base_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_legitimacy')|0]#! for each step of regime [concept_grandeur] and #v $country_authority_add$#! #G +[SCOPE.GetRootScope.ScriptValue('gm_step_national_leader')|0]#! for each step of its own kind. The leader's own interest group approves; the strongest group outside the government objects. In [SCOPE.sState('monument_state').GetName]: #G +[SCOPE.GetRootScope.ScriptValue('gm_step_local_leader')|%0]#! $state_loyalists_from_political_movements_mult$ for each step of its own.\n\nWhen they are gone, dead, deposed or retired, it becomes #R contested#!, and their successor decides what to do with it.\n\n$monument_events.2.common_tt$"
```

Add the skin-choice keys to `te_events_l_english.yml`, in key order:

```yaml
 monument_events.11.d:0 "The dedication is settled; the form is not. The architects have drawn it several ways, each borrowing from a tradition we claim as our own."
 monument_events.11.f:0 "“Every nation builds its monuments to look older than it is,” the architect says. “The only question is which past to borrow.”"
 monument_events.11.faith_animist:0 "Plant it as a sacred grove"
 monument_events.11.faith_catholic:0 "Raise it as a basilica"
 monument_events.11.faith_confucian:0 "Raise it as a temple of Confucius"
 monument_events.11.faith_gelugpa:0 "Raise it as a great monastery"
 monument_events.11.faith_hindu:0 "Raise it as a temple complex"
 monument_events.11.faith_ibadi:0 "Raise it as a great mosque"
 monument_events.11.faith_jewish:0 "Raise it as a great temple"
 monument_events.11.faith_mahayana:0 "Raise it as a pagoda"
 monument_events.11.faith_oriental_orthodox:0 "Raise it as a great church"
 monument_events.11.faith_orthodox:0 "Raise it as an Orthodox cathedral"
 monument_events.11.faith_protestant:0 "Raise it as a cathedral"
 monument_events.11.faith_shiite:0 "Raise it as a shrine mosque"
 monument_events.11.faith_shinto:0 "Raise it as a grand shrine"
 monument_events.11.faith_sikh:0 "Raise it as a gurdwara"
 monument_events.11.faith_sunni:0 "Raise it as a great mosque"
 monument_events.11.faith_theravada:0 "Raise it as a great stupa"
 monument_events.11.generic:0 "Keep to the plain classical style"
 monument_events.11.heritage_arabic:0 "Raise it as a caliphal hall"
 monument_events.11.heritage_aramaic:0 "Raise it as a rock-cut monument"
 monument_events.11.heritage_avestan:0 "Raise it as a gate of nations"
 monument_events.11.heritage_chinese:0 "Raise it as a hall of dynasties"
 monument_events.11.heritage_coptic:0 "Raise it as a great church"
 monument_events.11.heritage_geez:0 "Raise it as an Aksumite stele"
 monument_events.11.heritage_gothic:0 "Raise it as a hall of heroes"
 monument_events.11.heritage_greek:0 "Raise it as a pantheon"
 monument_events.11.heritage_hebrew:0 "Raise it as a great menorah"
 monument_events.11.heritage_irish:0 "Raise it as a round tower and high cross"
 monument_events.11.heritage_latin:0 "Raise it as a forum and triumphal column"
 monument_events.11.heritage_mayan:0 "Raise it as a temple-pyramid"
 monument_events.11.heritage_nahuatl:0 "Raise it as a stepped pyramid"
 monument_events.11.heritage_norse:0 "Raise it as a rune-stone hall"
 monument_events.11.heritage_pali:0 "Raise it as a great stupa"
 monument_events.11.heritage_prussian:0 "Raise it as a hill-fort monument"
 monument_events.11.heritage_sanskrit:0 "Raise it as a pillar of dharma"
 monument_events.11.heritage_slavonic:0 "Raise it as a memorial bell tower"
 monument_events.11.t:0 "A Form for the Monument"
```

Add the skin names and inscriptions to `te_miscellaneous_l_english.yml`, in key order:

```yaml
 gm_inscription_arabic:0 "Its dedication is carved in revived Classical Arabic."
 gm_inscription_aramaic:0 "Its dedication is carved in revived Aramaic."
 gm_inscription_avestan:0 "Its dedication is carved in revived Avestan."
 gm_inscription_chinese:0 "Its dedication is carved in revived Literary Chinese."
 gm_inscription_coptic:0 "Its dedication is carved in revived Coptic."
 gm_inscription_geez:0 "Its dedication is carved in revived Ge'ez."
 gm_inscription_gothic:0 "Its dedication is carved in revived Gothic."
 gm_inscription_greek:0 "Its dedication is carved in revived Classical Greek."
 gm_inscription_hebrew:0 "Its dedication is carved in revived Hebrew."
 gm_inscription_irish:0 "Its dedication is carved in revived Classical Irish."
 gm_inscription_latin:0 "Its dedication is carved in revived Latin."
 gm_inscription_mayan:0 "Its dedication is carved in revived Classic Mayan."
 gm_inscription_nahuatl:0 "Its dedication is carved in revived Classical Nahuatl."
 gm_inscription_none:0 ""
 gm_inscription_norse:0 "Its dedication is carved in revived Old Norse."
 gm_inscription_pali:0 "Its dedication is carved in revived Pali."
 gm_inscription_prussian:0 "Its dedication is carved in revived Old Prussian."
 gm_inscription_sanskrit:0 "Its dedication is carved in revived Sanskrit."
 gm_inscription_slavonic:0 "Its dedication is carved in revived Old Church Slavonic."
 gm_skin_choice_tt:0 "The monument takes this form. The form changes its name and look, not what it does."
 gm_skin_faith_animist:0 "Sacred Grove"
 gm_skin_faith_catholic:0 "Basilica"
 gm_skin_faith_confucian:0 "Temple of Confucius"
 gm_skin_faith_gelugpa:0 "Great Monastery"
 gm_skin_faith_hindu:0 "Temple Complex"
 gm_skin_faith_ibadi:0 "Great Mosque"
 gm_skin_faith_jewish:0 "Great Temple"
 gm_skin_faith_mahayana:0 "Pagoda"
 gm_skin_faith_oriental_orthodox:0 "Great Church"
 gm_skin_faith_orthodox:0 "Orthodox Cathedral"
 gm_skin_faith_protestant:0 "Cathedral"
 gm_skin_faith_shiite:0 "Shrine Mosque"
 gm_skin_faith_shinto:0 "Grand Shrine"
 gm_skin_faith_sikh:0 "Gurdwara"
 gm_skin_faith_sunni:0 "Great Mosque"
 gm_skin_faith_theravada:0 "Great Stupa"
 gm_skin_generic:0 "Grand Monument"
 gm_skin_heritage_arabic:0 "Caliphal Hall"
 gm_skin_heritage_aramaic:0 "Rock-Cut Monument"
 gm_skin_heritage_avestan:0 "Gate of Nations"
 gm_skin_heritage_chinese:0 "Hall of Dynasties"
 gm_skin_heritage_geez:0 "Aksumite Stele"
 gm_skin_heritage_gothic:0 "Hall of Heroes"
 gm_skin_heritage_greek:0 "Pantheon"
 gm_skin_heritage_hebrew:0 "Great Menorah"
 gm_skin_heritage_irish:0 "Round Tower and High Cross"
 gm_skin_heritage_latin:0 "Forum and Triumphal Column"
 gm_skin_heritage_mayan:0 "Temple-Pyramid"
 gm_skin_heritage_nahuatl:0 "Stepped Pyramid"
 gm_skin_heritage_norse:0 "Rune-Stone Hall"
 gm_skin_heritage_prussian:0 "Hill-Fort Monument"
 gm_skin_heritage_sanskrit:0 "Pillar of Dharma"
 gm_skin_heritage_slavonic:0 "Memorial Bell Tower"
```

- [ ] **Step 9: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check events/monument_events.txt common/scripted_effects/gm_effects.txt common/scripted_triggers/monument_triggers.txt common/customizable_localization/gm_custom_loc.txt && python3 scripts/analysis/check_localization_files.py && for a in empty_effect silent_variable orphaned_event loc_render duplicate_key; do python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"; done`
Expected: exit 0, no `FAIL` lines. `empty_effect_audit --strict` fails on a stale `(no_effect_option)` tag: `monument_events.2.a` no longer carries one, because its option now clears a flag.

- [ ] **Step 10: Commit**

```bash
git add events/monument_events.txt common/scripted_effects/gm_effects.txt common/scripted_triggers/monument_triggers.txt \
        common/customizable_localization/gm_custom_loc.txt localization/english/te_events_l_english.yml \
        localization/english/te_miscellaneous_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): the ceremony, identity skins and the revived-language inscription

The ceremony offers the four regime and ruler dedications beside the old ones,
writes each monument's records and asks its form: the builder's own faith for
a Shrine, a primary culture's classical heritage for the regime, nation and
memorial dedications (the language-reform revival partition). A monument whose
heritage language the country has revived is inscribed in it. Tooltip numbers
are read from the step values.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 8: Vanity backlash

**Files:**
- Modify: `events/monument_events.txt` (rewrite `.1`)
- Modify: `common/scripted_effects/gm_effects.txt` (append)
- Modify: `common/messages/extra_messages.txt` (append)
- Modify: `localization/english/te_notifications_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `VanityTests`)

**Interfaces:**
- Consumes: `gm_country_hard_times` (Task 3), `gm_state_start_ceremony` (Task 6), `gm_init_ledgers` and `.20` (Task 5).
- Produces (effect, state scope): `gm_state_vanity_backlash`.
- Produces (message): `gm_vanity_backlash_notice`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 8: vanity backlash ---------------------------------------------------------

class VanityTests(unittest.TestCase):
    def test_level_finished_hook(self):
        ev = squash(strip_comments(raw_block_at(read(EVENTS), r"(?m)^monument_events\.1\s*=\s*\{")))
        self.assertIn("type = building_event hidden = yes", ev)
        self.assertIn("owner = { gm_country_hard_times = yes } } gm_state_vanity_backlash = yes", ev)
        self.assertIn("gm_state_is_dedicated = no } gm_state_start_ceremony = yes", ev)
        self.assertIn("owner = { trigger_event = { id = monument_events.20 } }", ev)
        self.assertNotIn("add_modifier", ev, "ROOT is the building here: no multiplier modifiers")

    def test_backlash(self):
        body = squash(block(read(EFFECTS), "gm_state_vanity_backlash"))
        self.assertIn("add_radicals_in_state = { value = 0.05 }", body)
        self.assertIn("change_variable = { name = gm_vanity_ledger add = 1 }", body)
        self.assertIn("post_notification = gm_vanity_backlash_notice", body)

    def test_notice(self):
        msg = squash(block(read(MESSAGES), "gm_vanity_backlash_notice"))
        self.assertIn("type = country", msg)
        self.assertIn("notification_type = toast", msg)
        L = loc()
        self.assertIn("notification_gm_vanity_backlash_notice_name", L)
        self.assertIn("notification_gm_vanity_backlash_notice_desc", L)
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry.VanityTests -v`
Expected: FAIL.

- [ ] **Step 3: The level-finished hook**

Replace `monument_events.1` (and its two-line comment above it) in `events/monument_events.txt` with:

```
# Event 1: a level finished (hidden plumbing). ROOT is the BUILDING, so
# nothing here adds a multiplier modifier: it hops to the state for vanity
# backlash (§5) and the ceremony, then refreshes the nation through the hidden
# country event.
monument_events.1 = {
	type = building_event
	hidden = yes

	immediate = {
		if = {
			limit = {
				is_building_group = bg_grand_monuments
				exists = owner
			}
			state = {
				if = {
					limit = { gm_system_enabled = yes }
					if = {
						limit = {
							owner = { gm_country_hard_times = yes }
						}
						gm_state_vanity_backlash = yes
					}
					if = {
						limit = { gm_state_is_dedicated = no }
						gm_state_start_ceremony = yes
					}
					owner = { trigger_event = { id = monument_events.20 } }
				}
			}
		}
	}
}
```

- [ ] **Step 4: The backlash**

Append to `common/scripted_effects/gm_effects.txt`:

```

# ---- Vanity backlash (§5) --------------------------------------------------------
# State scope. A level finished while the country is in default, famine or
# recession: radicals in the state, and one more unit on the vanity ledger,
# which takes legitimacy linearly (gm_national_vanity) and fades over about
# two years. The journal entry warns beforehand (gm_hard_times_sgui, Task 9).
gm_state_vanity_backlash = {
	add_radicals_in_state = { value = 0.05 }
	owner = {
		gm_init_ledgers = yes
		change_variable = { name = gm_vanity_ledger add = 1 }
		post_notification = gm_vanity_backlash_notice
	}
}
```

- [ ] **Step 5: The notice**

Append to `common/messages/extra_messages.txt`:

```

# Grand Monuments: vanity backlash (docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md §5)
gm_vanity_backlash_notice = {
	type = country
	texture = "gfx/interface/icons/notification_icons/interest_group_bad.dds"
	notification_type = toast
	color = bad
}
```

Add to `localization/english/te_notifications_l_english.yml`, in key order:

```yaml
 notification_gm_vanity_backlash_notice_desc:0 "A new level of a Grand Monument opened while the country was in default, famine or recession. The state's people resent it, and the government's legitimacy suffers for about two years."
 notification_gm_vanity_backlash_notice_name:0 "A Palace amid Hardship"
```

- [ ] **Step 6: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check events/monument_events.txt common/scripted_effects/gm_effects.txt common/messages/extra_messages.txt && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.

- [ ] **Step 7: Commit**

```bash
git add events/monument_events.txt common/scripted_effects/gm_effects.txt common/messages/extra_messages.txt \
        localization/english/te_notifications_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): vanity backlash for levels finished in hard times

A level finished during default, famine or recession radicalizes 5% of the
state's pops and adds to a vanity ledger that costs legitimacy linearly and
fades. The level-finished hook only sets variables and hands off to the
hidden refresh event, since its ROOT is the building.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 9: The journal entry's widgets and buttons

**Files:**
- Create: `gui/journal_entry_widgets/grand_monuments_widget.gui`
- Create: `common/scripted_guis/gm_sguis.txt`
- Modify: `common/journal_entries/je_grand_monuments.txt` (mount the widgets)
- Modify: `common/script_values/gm_values.txt` (append the displays)
- Modify: `localization/english/te_miscellaneous_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `WidgetTests`)

**Interfaces:**
- Consumes: Task 5's country variables and `gm_states` list, Task 4's `gm_status_code`/`gm_state_grandeur`, Task 6's `gm_state_choose_*` and custom loc, Task 7's `gm_skin_name`/`gm_inscription`, Task 3's `gm_country_hard_times`.
- Produces (script values, country scope, guarded): `gm_display_prestige`, `gm_display_legitimacy`, `gm_display_culture`, `gm_display_<key>` (six), `gm_display_ig_<ig>` (eight, signed), `gm_display_teardown`, `gm_display_vanity`, and `gm_display_g_*` / `gm_display_n_*` for the totals.
- Produces (scripted GUIs, country scope): `gm_tear_down_sgui`, `gm_rededicate_sgui`, `gm_preserve_sgui` (saved scope `gm_state`), `gm_hard_times_sgui` (is_shown only).
- Produces (widgets): `widget_je_gm_national` (container 1), `widget_je_gm_monuments` (container 2).

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 9: the journal entry's widgets and buttons ---------------------------------

class WidgetTests(unittest.TestCase):
    def setUp(self):
        self.gui = read(WIDGET)

    def test_mounted(self):
        je = squash(read(JE))
        for name, container in (("widget_je_gm_national", "custom_widget_container_1"),
                                ("widget_je_gm_monuments", "custom_widget_container_2")):
            self.assertIn(f'gui = "gui/journal_entry_widgets/grand_monuments_widget.gui" name = "{name}" '
                          f'container = "{container}"', je)
            self.assertIn(f'name = "{name}"', self.gui)

    def test_roots_gated_and_rows_from_the_list(self):
        g = squash(strip_comments(self.gui))
        self.assertEqual(g.count('visible = "[JournalEntry.IsActive]"'), 2)
        self.assertIn('datamodel = "[JournalEntry.GetCountry.MakeScope.GetList(\'gm_states\')]"', g)
        self.assertIn('widget_je_gm_row = { datacontext = "[Scope.GetState]" }', g)

    def test_national_lines_read_guarded_displays(self):
        values = read(VALUES)
        for display in re.findall(r"ScriptValue\('(gm_display_\w+)'\)", self.gui):
            body = squash(block(values, display))
            self.assertIsNotNone(block(values, display), display)
            self.assertIn("if = { limit = { has_variable =", body, display)
        shown = set(re.findall(r"ScriptValue\('(gm_display_\w+)'\)", self.gui))
        for key in ["prestige", "legitimacy", "culture", "teardown", "vanity"] + list(NATIONAL):
            self.assertIn(f"gm_display_{key}", shown)
        for ig in IGS:
            self.assertIn(f"gm_display_ig_{ig}", shown)

    def test_buttons(self):
        g = squash(strip_comments(self.gui))
        self.assertIn("visible = \"[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )]\"", g)
        for choice in ("tear_down", "rededicate", "preserve"):
            self.assertIn(f"datacontext = \"[GetScriptedGui('gm_{choice}_sgui')]\"", g)
        self.assertIn("AddScope( 'gm_state', State.MakeScope )", g)
        sguis = read(SGUIS)
        for choice in ("tear_down", "rededicate", "preserve"):
            body = squash(block(sguis, f"gm_{choice}_sgui"))
            self.assertIn("saved_scopes = { gm_state }", body)
            self.assertIn("exists = scope:gm_state scope:gm_state = { owner = root", body)
            self.assertIn("gm_state_is_contested = yes", body)
            self.assertIn(f"scope:gm_state = {{ gm_state_choose_{choice} = yes }}", body)
            self.assertIn("hidden_effect = { gm_country_refresh = yes }", body)
            self.assertIn("ai_is_valid = { always = no }", body)
        self.assertIn("is_shown = { gm_country_hard_times = yes }", squash(block(sguis, "gm_hard_times_sgui")))

    def test_every_gui_loc_key_exists(self):
        L = loc()
        for key in set(re.findall(r'(?:text|tooltip) = "([a-z][\w.]*)"', self.gui)):
            self.assertIn(key, L, key)
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry.WidgetTests -v`
Expected: ERROR (`grand_monuments_widget.gui` missing).

- [ ] **Step 3: The displays**

Append to `common/script_values/gm_values.txt`:

```

# ---- Journal entry displays (country scope) ------------------------------------
# Every read guarded: the widget renders from the month the entry activates,
# possibly before the first refresh has written these (gui gotcha #14).
gm_display_prestige = {
	value = 0
	if = {
		limit = { has_variable = gm_s_standing }
		value = var:gm_s_standing
		multiply = gm_step_prestige
	}
}

gm_display_g_standing = {
	value = 0
	if = {
		limit = { has_variable = gm_g_standing }
		value = var:gm_g_standing
	}
}

gm_display_n_standing = {
	value = 0
	if = {
		limit = { has_variable = gm_n_standing }
		value = var:gm_n_standing
	}
}

gm_display_legitimacy = {
	value = 0
	if = {
		limit = { has_variable = gm_s_regime }
		value = var:gm_s_regime
		multiply = gm_step_legitimacy
	}
}

gm_display_g_regime = {
	value = 0
	if = {
		limit = { has_variable = gm_g_regime }
		value = var:gm_g_regime
	}
}

gm_display_n_regime = {
	value = 0
	if = {
		limit = { has_variable = gm_n_regime }
		value = var:gm_n_regime
	}
}

gm_display_culture = {
	value = 0
	if = {
		limit = { has_variable = gm_s_culture }
		value = var:gm_s_culture
		multiply = gm_step_culture
	}
	max = 5
}

gm_display_n_culture = {
	value = 0
	if = {
		limit = { has_variable = gm_n_culture }
		value = var:gm_n_culture
	}
}

gm_display_leader = {
	value = 0
	if = {
		limit = { has_variable = gm_s_leader }
		value = var:gm_s_leader
		multiply = gm_step_national_leader
	}
}

gm_display_g_leader = {
	value = 0
	if = {
		limit = { has_variable = gm_g_leader }
		value = var:gm_g_leader
	}
}

gm_display_n_leader = {
	value = 0
	if = {
		limit = { has_variable = gm_n_leader }
		value = var:gm_n_leader
	}
}

gm_display_religious = {
	value = 0
	if = {
		limit = { has_variable = gm_s_religious }
		value = var:gm_s_religious
		multiply = gm_step_national_religious
	}
}

gm_display_g_religious = {
	value = 0
	if = {
		limit = { has_variable = gm_g_religious }
		value = var:gm_g_religious
	}
}

gm_display_n_religious = {
	value = 0
	if = {
		limit = { has_variable = gm_n_religious }
		value = var:gm_n_religious
	}
}

gm_display_war_memorial = {
	value = 0
	if = {
		limit = { has_variable = gm_s_war_memorial }
		value = var:gm_s_war_memorial
		multiply = gm_step_national_war_memorial
	}
}

gm_display_g_war_memorial = {
	value = 0
	if = {
		limit = { has_variable = gm_g_war_memorial }
		value = var:gm_g_war_memorial
	}
}

gm_display_n_war_memorial = {
	value = 0
	if = {
		limit = { has_variable = gm_n_war_memorial }
		value = var:gm_n_war_memorial
	}
}

gm_display_artistic = {
	value = 0
	if = {
		limit = { has_variable = gm_s_artistic }
		value = var:gm_s_artistic
		multiply = gm_step_national_artistic
	}
}

gm_display_g_artistic = {
	value = 0
	if = {
		limit = { has_variable = gm_g_artistic }
		value = var:gm_g_artistic
	}
}

gm_display_n_artistic = {
	value = 0
	if = {
		limit = { has_variable = gm_n_artistic }
		value = var:gm_n_artistic
	}
}

gm_display_scientific = {
	value = 0
	if = {
		limit = { has_variable = gm_s_scientific }
		value = var:gm_s_scientific
		multiply = gm_step_national_scientific
	}
}

gm_display_g_scientific = {
	value = 0
	if = {
		limit = { has_variable = gm_g_scientific }
		value = var:gm_g_scientific
	}
}

gm_display_n_scientific = {
	value = 0
	if = {
		limit = { has_variable = gm_n_scientific }
		value = var:gm_n_scientific
	}
}

gm_display_industrial = {
	value = 0
	if = {
		limit = { has_variable = gm_s_industrial }
		value = var:gm_s_industrial
		multiply = gm_step_national_industrial
	}
}

gm_display_g_industrial = {
	value = 0
	if = {
		limit = { has_variable = gm_g_industrial }
		value = var:gm_g_industrial
	}
}

gm_display_n_industrial = {
	value = 0
	if = {
		limit = { has_variable = gm_n_industrial }
		value = var:gm_n_industrial
	}
}

gm_display_ig_armed_forces = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_armed_forces }
		value = var:gm_s_ig_armed_forces
		multiply = gm_step_ig
	}
}

gm_display_ig_devout = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_devout }
		value = var:gm_s_ig_devout
		multiply = gm_step_ig
	}
}

gm_display_ig_industrialists = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_industrialists }
		value = var:gm_s_ig_industrialists
		multiply = gm_step_ig
	}
}

gm_display_ig_intelligentsia = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_intelligentsia }
		value = var:gm_s_ig_intelligentsia
		multiply = gm_step_ig
	}
}

gm_display_ig_landowners = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_landowners }
		value = var:gm_s_ig_landowners
		multiply = gm_step_ig
	}
}

gm_display_ig_petty_bourgeoisie = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_petty_bourgeoisie }
		value = var:gm_s_ig_petty_bourgeoisie
		multiply = gm_step_ig
	}
}

gm_display_ig_rural_folk = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_rural_folk }
		value = var:gm_s_ig_rural_folk
		multiply = gm_step_ig
	}
}

gm_display_ig_trade_unions = {
	value = 0
	if = {
		limit = { has_variable = gm_s_ig_trade_unions }
		value = var:gm_s_ig_trade_unions
		multiply = gm_step_ig
	}
}

gm_display_teardown = {
	value = 0
	if = {
		limit = { has_variable = gm_s_teardown }
		value = var:gm_s_teardown
		multiply = gm_step_teardown
	}
}

gm_display_vanity = {
	value = 0
	if = {
		limit = { has_variable = gm_vanity_ledger }
		value = var:gm_vanity_ledger
		multiply = gm_step_vanity
	}
}
```

- [ ] **Step 4: The scripted GUIs**

Create `common/scripted_guis/gm_sguis.txt` (BOM, tabs):

```
# ============================================================================
# GRAND MONUMENTS — scripted GUIs (spec §6)
# ============================================================================
# gui/journal_entry_widgets/grand_monuments_widget.gui. The three row buttons
# pass the row's state as the saved scope gm_state; which action is chosen by
# which scripted GUI the button points at (the covert rows' shape). A State
# object in saved_scopes has no vanilla precedent (gui gotcha #22), so every
# is_valid fails closed: the scope exists, we own it, it is contested.
# monument_events.17 is the proven path to the same three choices.

gm_tear_down_sgui = {
	scope = country
	saved_scopes = { gm_state }

	is_shown = {
		always = yes
	}

	is_valid = {
		exists = scope:gm_state
		scope:gm_state = {
			owner = root
			custom_tooltip = {
				text = gm_sgui_contested_tt
				gm_state_is_contested = yes
			}
		}
	}

	effect = {
		scope:gm_state = { gm_state_choose_tear_down = yes }
		hidden_effect = { gm_country_refresh = yes }
	}

	ai_is_valid = {
		always = no
	}
}

gm_rededicate_sgui = {
	scope = country
	saved_scopes = { gm_state }

	is_shown = {
		always = yes
	}

	is_valid = {
		exists = scope:gm_state
		scope:gm_state = {
			owner = root
			custom_tooltip = {
				text = gm_sgui_contested_tt
				gm_state_is_contested = yes
			}
		}
	}

	effect = {
		scope:gm_state = { gm_state_choose_rededicate = yes }
		hidden_effect = { gm_country_refresh = yes }
	}

	ai_is_valid = {
		always = no
	}
}

gm_preserve_sgui = {
	scope = country
	saved_scopes = { gm_state }

	is_shown = {
		always = yes
	}

	is_valid = {
		exists = scope:gm_state
		scope:gm_state = {
			owner = root
			custom_tooltip = {
				text = gm_sgui_contested_tt
				gm_state_is_contested = yes
			}
		}
	}

	effect = {
		scope:gm_state = { gm_state_choose_preserve = yes }
		hidden_effect = { gm_country_refresh = yes }
	}

	ai_is_valid = {
		always = no
	}
}

# YES/NO: would a level finished now cause vanity backlash (§5)? Read-only,
# scope-free (gotcha #22): the warning line's visibility.
gm_hard_times_sgui = {
	scope = country

	is_shown = {
		gm_country_hard_times = yes
	}

	is_valid = {
		always = no
	}

	effect = { }

	ai_is_valid = {
		always = no
	}
}
```

- [ ] **Step 5: The widget**

Create `gui/journal_entry_widgets/grand_monuments_widget.gui` (BOM, tabs):

```
### Grand Monuments JE widgets (spec §6)
###
### Two widgets, mounted from je_grand_monuments:
###   widget_je_gm_national   custom_widget_container_1 (above the status desc)
###     One line per national total in force, with its next step, and the
###     hard-times warning (§5).
###   widget_je_gm_monuments  custom_widget_container_2 (below the status desc)
###     One row per monument, from the country's gm_states list (rebuilt by
###     every gm_country_refresh). A contested row carries three buttons.
###
### EDITING RULES
### * Numbers come from JournalEntry.GetCountry.MakeScope.ScriptValue (the
###   guarded gm_display_* values) and State.MakeScope.ScriptValue.
### * A row's status is gm_status_code (0-4), tested for identity, never a
###   threshold (gotcha #23).
### * The row buttons pass the row's state as the saved scope gm_state, one
###   scripted GUI per action (common/scripted_guis/gm_sguis.txt).
### * Both roots are gated on [JournalEntry.IsActive] (gotcha #14).

types grand_monuments_widget_types
{
	type gm_header = textbox {
		autoresize = yes
		multiline = yes
		minimumsize = { 480 -1 }
		maximumsize = { 480 -1 }
		align = left|nobaseline
		using = fontsize_medium
		margin_top = 4
		block "header_text" {}
	}

	type gm_line = textbox {
		autoresize = yes
		multiline = yes
		minimumsize = { 480 -1 }
		maximumsize = { 480 -1 }
		align = left|nobaseline
		using = fontsize_small
		block "line_text" {}
		block "line_extra" {}
	}

	### One of a contested row's three choices. choice_context points it at its
	### scripted GUI; the row's state travels as the saved scope gm_state.
	type gm_choice_button = button {
		using = default_button_action
		size = { 150 24 }
		margin_top = 2

		block "choice_context" {}

		enabled = "[ScriptedGui.IsValid( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]"
		onclick = "[ScriptedGui.Execute( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]"

		block "choice_tooltip" {}

		textbox = {
			parentanchor = center
			align = center|nobaseline
			autoresize = yes
			max_width = 140
			elide = right
			using = fontsize_small
			block "choice_text" {}
		}
	}

	type widget_je_gm_row = flowcontainer {
		direction = vertical
		ignoreinvisible = yes
		parentanchor = hcenter
		margin = { 20 8 }

		background = {
			using = entry_bg_fancy_dark
			alpha = 0.5
		}

		# ---- Its form and dedication ----
		textbox = {
			autoresize = yes
			multiline = yes
			minimumsize = { 480 -1 }
			maximumsize = { 480 -1 }
			align = left|nobaseline
			using = fontsize_large
			text = "gm_row_title"
		}

		# ---- Where, how grand, its status ----
		gm_line = {
			blockoverride "line_text" { text = "gm_row_detail" }
		}

		# ---- The revived-language inscription (empty when none) ----
		gm_line = {
			blockoverride "line_text" { text = "gm_row_inscription" }
		}

		# ---- Contested: who wants what, and the three choices ----
		gm_line = {
			blockoverride "line_text" { text = "gm_row_contest" }
			blockoverride "line_extra" {
				visible = "[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )]"
			}
		}

		flowcontainer = {
			direction = horizontal
			spacing = 4
			margin_left = 12
			visible = "[EqualTo_CFixedPoint( State.MakeScope.ScriptValue('gm_status_code'), '(CFixedPoint)4' )]"

			gm_choice_button = {
				blockoverride "choice_context" { datacontext = "[GetScriptedGui('gm_tear_down_sgui')]" }
				blockoverride "choice_tooltip" { tooltip = "gm_button_tear_down_tooltip" }
				blockoverride "choice_text" { text = "gm_button_tear_down" }
			}
			gm_choice_button = {
				blockoverride "choice_context" { datacontext = "[GetScriptedGui('gm_rededicate_sgui')]" }
				blockoverride "choice_tooltip" { tooltip = "gm_button_rededicate_tooltip" }
				blockoverride "choice_text" { text = "gm_button_rededicate" }
			}
			gm_choice_button = {
				blockoverride "choice_context" { datacontext = "[GetScriptedGui('gm_preserve_sgui')]" }
				blockoverride "choice_tooltip" { tooltip = "gm_button_preserve_tooltip" }
				blockoverride "choice_text" { text = "gm_button_preserve" }
			}
		}
	}
}


### WIDGETS

### National effects: a line per total in force.
flowcontainer = {
	name = "widget_je_gm_national"
	direction = vertical
	parentanchor = hcenter
	spacing = 2
	visible = "[JournalEntry.IsActive]"

	gm_header = {
		blockoverride "header_text" { text = "gm_je_header_national" }
	}

	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_prestige" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_prestige'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_legitimacy" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_legitimacy'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_culture" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_culture'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_leader" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_leader'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_religious" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_religious'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_war_memorial" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_war_memorial'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_artistic" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_artistic'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_scientific" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_scientific'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_industrial" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_industrial'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_armed_forces" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_armed_forces'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_devout" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_devout'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_industrialists" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_industrialists'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_intelligentsia" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_intelligentsia'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_landowners" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_landowners'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_petty_bourgeoisie" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_petty_bourgeoisie'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_rural_folk" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_rural_folk'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_ig_trade_unions" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_trade_unions'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_teardown" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_teardown'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_line_vanity" }
		blockoverride "line_extra" {
			visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_vanity'), '(CFixedPoint)0' )]"
		}
	}
	gm_line = {
		blockoverride "line_text" { text = "gm_je_hard_times" }
		blockoverride "line_extra" {
			visible = "[GetScriptedGui('gm_hard_times_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
		}
	}
}

### One row per monument.
flowcontainer = {
	name = "widget_je_gm_monuments"
	direction = vertical
	parentanchor = hcenter
	spacing = 4
	visible = "[JournalEntry.IsActive]"

	gm_header = {
		blockoverride "header_text" { text = "gm_je_header_monuments" }
	}

	flowcontainer = {
		direction = vertical
		parentanchor = hcenter
		spacing = 4
		datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('gm_states')]"

		item = {
			widget_je_gm_row = { datacontext = "[Scope.GetState]" }
		}
	}
}
```

- [ ] **Step 6: Mount the widgets**

In `common/journal_entries/je_grand_monuments.txt`, add after `group = je_group_internal_affairs`:

```

	widget = {
		gui = "gui/journal_entry_widgets/grand_monuments_widget.gui"
		name = "widget_je_gm_national"
		container = "custom_widget_container_1"
	}

	widget = {
		gui = "gui/journal_entry_widgets/grand_monuments_widget.gui"
		name = "widget_je_gm_monuments"
		container = "custom_widget_container_2"
	}
```

- [ ] **Step 7: Loc**

Add to `localization/english/te_miscellaneous_l_english.yml`, in key order:

```yaml
 gm_button_preserve:0 "Keep as Heritage"
 gm_button_preserve_tooltip:0 "#b Keep it as heritage#!\n[ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]\n[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]"
 gm_button_rededicate:0 "Rededicate"
 gm_button_rededicate_tooltip:0 "#b Rededicate it#!\n[ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]\n[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]"
 gm_button_tear_down:0 "Pull Down"
 gm_button_tear_down_tooltip:0 "#b Pull it down#!\n[ScriptedGui.IsValidTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]\n[ScriptedGui.ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'gm_state', State.MakeScope ).End )]"
 gm_je_hard_times:0 "#R Hard times: finishing a monument level now radicalizes its state and costs legitimacy for about two years. Pause monument construction until the country recovers.#!"
 gm_je_header_monuments:0 "#title Our monuments#!"
 gm_je_header_national:0 "#title National effects#!"
 gm_je_line_artistic:0 "#b $interest_group_ig_intelligentsia_pop_attraction_mult$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_artistic')|%0]#! from opera houses, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_artistic')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_artistic')|0]"
 gm_je_line_culture:0 "#b Cultural pull#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_culture')|1]#! of +5; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_culture')|0] [concept_grandeur]"
 gm_je_line_ig_armed_forces:0 "#b $ig_armed_forces$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_armed_forces')|+=1]"
 gm_je_line_ig_devout:0 "#b $ig_devout$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_devout')|+=1]"
 gm_je_line_ig_industrialists:0 "#b $ig_industrialists$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_industrialists')|+=1]"
 gm_je_line_ig_intelligentsia:0 "#b $ig_intelligentsia$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_intelligentsia')|+=1]"
 gm_je_line_ig_landowners:0 "#b $ig_landowners$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_landowners')|+=1]"
 gm_je_line_ig_petty_bourgeoisie:0 "#b $ig_petty_bourgeoisie$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_petty_bourgeoisie')|+=1]"
 gm_je_line_ig_rural_folk:0 "#b $ig_rural_folk$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_rural_folk')|+=1]"
 gm_je_line_ig_trade_unions:0 "#b $ig_trade_unions$#! approval [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_ig_trade_unions')|+=1]"
 gm_je_line_industrial:0 "#b $interest_group_ig_industrialists_pop_attraction_mult$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_industrial')|%0]#! from exhibition halls, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_industrial')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_industrial')|0]"
 gm_je_line_leader:0 "#b $country_authority_add$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_leader')|0]#! from monuments to the leader, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_leader')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_leader')|0]"
 gm_je_line_legitimacy:0 "#b $country_legitimacy_base_add$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_legitimacy')|1]#! from regime [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_regime')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_regime')|0]"
 gm_je_line_prestige:0 "#b Prestige#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_prestige')|0]#! from [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_standing')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_standing')|0]"
 gm_je_line_religious:0 "#b $interest_group_ig_devout_pop_attraction_mult$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_religious')|%0]#! from grand shrines, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_religious')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_religious')|0]"
 gm_je_line_scientific:0 "#b $country_weekly_innovation_max_add$#! #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_scientific')|1]#! from observatories, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_scientific')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_scientific')|0]"
 gm_je_line_teardown:0 "#b The Old Order Torn Down#! $country_legitimacy_base_add$ #G +[JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_teardown')|1]#!, fading"
 gm_je_line_vanity:0 "#b Palaces amid Hardship#! $country_legitimacy_base_add$ #R [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_vanity')|1]#!, fading"
 gm_je_line_war_memorial:0 "#b $country_war_support_casualties_mult$#! #G [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_war_memorial')|%0]#! from war memorials, [concept_grandeur] [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_g_war_memorial')|0]; next step at [JournalEntry.GetCountry.MakeScope.ScriptValue('gm_display_n_war_memorial')|0]"
 gm_row_contest:0 "It honours something this government is not. Its old supporters, [State.GetCustom('gm_supporter_ig_name')], want it kept; [State.GetCustom('gm_base_ig_name')] resent it for as long as it stands undecided."
 gm_row_detail:0 "[State.GetName] · [concept_grandeur] [State.MakeScope.ScriptValue('gm_state_grandeur')|0] · [State.GetCustom('gm_status_name')]"
 gm_row_inscription:0 "[State.GetCustom('gm_inscription')]"
 gm_row_title:0 "#b [State.GetCustom('gm_skin_name')]#! — [State.GetCustom('gm_dedication_name')]"
 gm_sgui_contested_tt:0 "The monument is contested"
```

- [ ] **Step 8: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check common/scripted_guis/gm_sguis.txt common/journal_entries/je_grand_monuments.txt common/script_values/gm_values.txt && python3 scripts/analysis/check_localization_files.py && python3 loc_render_audit.py --strict && python3 -c "open('gui/journal_entry_widgets/grand_monuments_widget.gui','rb').read(3)==b'\xef\xbb\xbf' or exit('no BOM')"`
Expected: exit 0. (`format_paradox_tabs.py` covers `.txt` only; keep the `.gui` tab-indented by hand.)

- [ ] **Step 9: Commit**

```bash
git add gui/journal_entry_widgets/grand_monuments_widget.gui common/scripted_guis/gm_sguis.txt \
        common/journal_entries/je_grand_monuments.txt common/script_values/gm_values.txt \
        localization/english/te_miscellaneous_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): the Monuments journal entry's widgets

National lines show each total in force with its next step, and a red line
warns of hard times before a level finishes. One row per monument names its
form, dedication, grandeur and status; a contested row carries Pull Down,
Rededicate and Keep as Heritage.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 10: Flavour events with real choices

Every dedication gets one recurring event: `.3`–`.10` keep their text and gain two options; `.12`–`.15` are new. Every option is positive; money is the only cost an option may carry (plan decision 7 for the sizes).

**Files:**
- Modify: `events/monument_events.txt` (`.3`–`.10`; append `.12`–`.15`)
- Modify: `common/on_actions/monument_events_on_actions.txt` (rewrite `monument_events_on_action`)
- Modify: `common/scripted_triggers/monument_triggers.txt` (append `gm_state_holds_anniversary`)
- Modify: `common/static_modifiers/gm_modifiers.txt` (append the event modifiers)
- Modify: `localization/english/te_events_l_english.yml`, `te_miscellaneous_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `FlavourTests`)

**Interfaces:**
- Consumes: `gm_state_status_fits`, `gm_state_has_pm`, `gm_state_grandeur` (Task 4), `gm_event_cost`/`gm_event_income` (Task 2), `gm_skin_name` (Task 7).
- Produces (trigger, state scope): `gm_state_holds_anniversary = { PM }`.
- Produces (static modifiers): the 22 `gm_evt_*` below.
- Produces (events): `monument_events.12`–`.15`.

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 10: flavour events ---------------------------------------------------------

class FlavourTests(unittest.TestCase):
    def test_dispatch(self):
        body = squash(block(read(ON_ACTIONS), "monument_events_on_action"))
        self.assertIn("trigger = { gm_system_enabled = yes }", body)
        for d in DEDICATIONS:
            self.assertIn(f"gm_state_holds_anniversary = {{ PM = pm_monument_{d.key} }} }} }} "
                          f"trigger_event = {{ id = monument_events.{d.event} }}", body)

    def test_only_a_fitting_landmark_holds_anniversaries(self):
        self.assertEqual(squash(block(read(TRIGGERS), "gm_state_holds_anniversary")),
                         "gm_state_status_fits = yes gm_state_has_pm = { PM = $PM$ } "
                         "b:building_grand_monument ?= { level >= 3 }")

    def test_events(self):
        text, L = read(EVENTS), loc()
        for d in DEDICATIONS:
            ev = raw_block_at(text, rf"(?m)^monument_events\.{d.event}\s*=\s*\{{")
            self.assertIsNotNone(ev, d.event)
            se = strip_comments(ev)
            s = squash(se)
            self.assertIn(f"gm_state_holds_anniversary = {{ PM = pm_monument_{d.key} }}", s)
            self.assertIn("order_by = gm_state_grandeur position = 0", s)
            self.assertIn("save_scope_as = monument_state", s)
            self.assertEqual(s.count("default_option = yes"), 1, d.event)
            options = [squash(_match_brace(se, m.end())) for m in re.finditer(r"option\s*=\s*\{", se)]
            self.assertEqual(len(options), 2, d.event)
            for o in options:
                effects = re.sub(r"name = \S+|default_option = yes|ai_chance = \{ base = \d+ \}", "", o).strip()
                self.assertTrue(effects, f"{d.event}: an option with no effect")
                self.assertNotRegex(o, r"add_treasury = (?!gm_event_(cost|income)\b)",
                                    "money moves only through gm_event_cost / gm_event_income")
            for k in ("t", "d", "f", "a", "b"):
                self.assertIn(f"monument_events.{d.event}.{k}", L)
            self.assertNotEqual(L[f"monument_events.{d.event}.a"], "A fine thing to have built")

    def test_event_modifiers_are_all_positive(self):
        good_when_negative = {"state_turmoil_effects_mult", "country_war_support_casualties_mult"}
        seen = 0
        for name, body in top_level_blocks(read(MODIFIERS)):
            if not name.startswith("gm_evt_"):
                continue
            seen += 1
            for field, value in re.findall(r"(?m)^\s*(\w+)\s*=\s*(-?[\d.]+)\s*$", body):
                v = float(value)
                self.assertTrue(v < 0 if field in good_when_negative else v > 0, f"{name}.{field}")
        self.assertEqual(seen, 22)
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry.FlavourTests -v`
Expected: FAIL.

- [ ] **Step 3: The anniversary trigger**

Append to `common/scripted_triggers/monument_triggers.txt`:

```

# ======================================================================
#  Anniversaries (spec §6.1)
# ======================================================================
# State scope. A monument of this dedication that fits and is a real
# landmark (level 3 or more) holds anniversaries; a contested or heritage one
# does not.
gm_state_holds_anniversary = {
	gm_state_status_fits = yes
	gm_state_has_pm = { PM = $PM$ }
	b:building_grand_monument ?= { level >= 3 }
}
```

- [ ] **Step 4: The dispatch**

In `common/on_actions/monument_events_on_actions.txt`, replace the whole `monument_events_on_action = { … }` block (and update the comment above it to say it gates on a monument that fits, level 3 or more, and dispatches one event per dedication) with:

```
monument_events_on_action = {
	trigger = {
		gm_system_enabled = yes
	}
	effect = {
		random_list = {
			800 = { } # overwhelmingly nothing

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_civic }
					}
				}
				trigger_event = { id = monument_events.3 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_religious }
					}
				}
				trigger_event = { id = monument_events.4 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_war_memorial }
					}
				}
				trigger_event = { id = monument_events.5 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_artistic }
					}
				}
				trigger_event = { id = monument_events.6 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_naturalist }
					}
				}
				trigger_event = { id = monument_events.7 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_scientific }
					}
				}
				trigger_event = { id = monument_events.8 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_industrial }
					}
				}
				trigger_event = { id = monument_events.9 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_athletic }
					}
				}
				trigger_event = { id = monument_events.10 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_crown }
					}
				}
				trigger_event = { id = monument_events.12 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_republic }
					}
				}
				trigger_event = { id = monument_events.13 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_revolution }
					}
				}
				trigger_event = { id = monument_events.14 }
			}

			3 = {
				trigger = {
					any_scope_state = {
						gm_state_holds_anniversary = { PM = pm_monument_leader }
					}
				}
				trigger_event = { id = monument_events.15 }
			}
		}
	}
}
```

- [ ] **Step 5: The event modifiers**

Append to `common/static_modifiers/gm_modifiers.txt`:

```

# ---- Flavour event rewards (§6.1): timed, normal_modifier_time (5 years) -----
# Every one is a benefit: the events choose between two benefits, and the
# only cost an option may carry is money.
gm_evt_state_occasion = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_prestige_add = 10
	interest_group_ig_petty_bourgeoisie_approval_add = 2
}

gm_evt_pilgrim_hostels = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	building_tourism_industry_throughput_add = 0.1
}

gm_evt_devout_pleased = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_devout_approval_add = 2
}

gm_evt_clergy_trusted = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_devout_approval_add = 3
}

gm_evt_remembrance_day = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_armed_forces_approval_add = 2
	country_war_support_casualties_mult = -0.1
}

gm_evt_quiet_remembrance = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_turmoil_effects_mult = -0.1
}

gm_evt_artists_defended = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_intelligentsia_approval_add = 2
}

gm_evt_works_closed = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_devout_approval_add = 2
}

gm_evt_gardens_open = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_standard_of_living_add = 1
}

gm_evt_public_lectures = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_literacy_growth_add = 0.0005
}

gm_evt_research_nights = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_weekly_innovation_add = 5
}

gm_evt_domestic_exhibition = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_industrialists_approval_add = 2
}

gm_evt_foreign_exhibitors = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_influence_add = 10
	country_prestige_add = 5
}

gm_evt_subsidised_tickets = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	state_turmoil_effects_mult = -0.1
}

gm_evt_unions_pleased = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_trade_unions_approval_add = 2
}

gm_evt_jubilee = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_legitimacy_base_add = 3
	interest_group_ig_landowners_approval_add = 2
}

gm_evt_ruler_popular = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	character_popularity_add = 10
}

gm_evt_citizens_assembly = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_intelligentsia_approval_add = 2
}

gm_evt_military_parade = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_armed_forces_approval_add = 2
}

gm_evt_mass_rally = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_authority_add = 25
}

gm_evt_quiet_commemoration = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	interest_group_ig_trade_unions_approval_add = 2
}

gm_evt_leader_celebrated = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_statue_positive.dds
	country_legitimacy_base_add = 3
}
```

- [ ] **Step 6: Rework `.3`–`.10`**

View the art each event already shows before keeping it: `python3 scripts/image_pipeline/contact_sheet.py --event monument_events.3 monument_events.4 monument_events.5 monument_events.6 monument_events.7 monument_events.8 monument_events.9 monument_events.10`.

In each event below, replace its `trigger = { … }` block and its single `option = { … }` with the code given; keep everything else (image, icon, title, desc, flavor, duration, cooldown). Update the section comment above `.3` to say each event gates on a fitting monument of level 3 or more and offers a choice between two benefits.

**`monument_events.3`** (civic):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_civic }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_civic }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.3.a
		add_treasury = gm_event_cost
		add_modifier = { name = gm_evt_state_occasion days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.3.b
		default_option = yes
		scope:monument_state = {
			add_loyalists_in_state = { value = 0.05 }
		}
		ai_chance = { base = 2 }
	}
```

**`monument_events.4`** (religious):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_religious }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_religious }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.4.a
		add_treasury = gm_event_cost
		scope:monument_state = {
			add_modifier = { name = gm_evt_pilgrim_hostels days = normal_modifier_time }
		}
		add_modifier = { name = gm_evt_devout_pleased days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.4.b
		default_option = yes
		add_modifier = { name = gm_evt_clergy_trusted days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
```

**`monument_events.5`** (war_memorial):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_war_memorial }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_war_memorial }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.5.a
		add_modifier = { name = gm_evt_remembrance_day days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.5.b
		default_option = yes
		scope:monument_state = {
			add_modifier = { name = gm_evt_quiet_remembrance days = normal_modifier_time }
		}
		ai_chance = { base = 2 }
	}
```

**`monument_events.6`** (artistic):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_artistic }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_artistic }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.6.a
		add_modifier = { name = gm_evt_artists_defended days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.6.b
		default_option = yes
		add_modifier = { name = gm_evt_works_closed days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
```

**`monument_events.7`** (naturalist):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_naturalist }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_naturalist }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.7.a
		add_treasury = gm_event_cost
		scope:monument_state = {
			add_modifier = { name = gm_evt_gardens_open days = normal_modifier_time }
		}
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.7.b
		default_option = yes
		add_treasury = gm_event_income
		ai_chance = { base = 2 }
	}
```

**`monument_events.8`** (scientific):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_scientific }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_scientific }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.8.a
		scope:monument_state = {
			add_modifier = { name = gm_evt_public_lectures days = normal_modifier_time }
		}
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.8.b
		default_option = yes
		add_modifier = { name = gm_evt_research_nights days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
```

**`monument_events.9`** (industrial):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_industrial }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_industrial }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.9.a
		add_modifier = { name = gm_evt_domestic_exhibition days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.9.b
		default_option = yes
		add_modifier = { name = gm_evt_foreign_exhibitors days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
```

**`monument_events.10`** (athletic):

```
	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_athletic }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_athletic }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.10.a
		add_treasury = gm_event_cost
		scope:monument_state = {
			add_modifier = { name = gm_evt_subsidised_tickets days = normal_modifier_time }
		}
		add_modifier = { name = gm_evt_unions_pleased days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.10.b
		default_option = yes
		add_treasury = gm_event_income
		ai_chance = { base = 2 }
	}
```

- [ ] **Step 7: The four new events**

View the art first: `python3 scripts/image_pipeline/contact_sheet.py unspecific_ruler_speaking_to_people unspecific_politicians_arguing unspecific_military_parade`. Append to `events/monument_events.txt`:

```

# ============================================================================
# Events 12-15: anniversaries of the regime and ruler dedications (§6.1)
# ============================================================================
# As 3-10: dispatched from monument_events_on_action, gated on a fitting
# monument of level 3 or more, a choice between two benefits.

monument_events.12 = {
	type = country_event
	placement = root

	event_image = { video = "unspecific_ruler_speaking_to_people" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/waving_flag.dds"

	title = monument_events.12.t
	desc = monument_events.12.d
	flavor = monument_events.12.f

	duration = 3
	cooldown = { days = long_modifier_time }

	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_crown }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_crown }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.12.a
		add_treasury = gm_event_cost
		add_modifier = { name = gm_evt_jubilee days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.12.b
		default_option = yes
		ruler = {
			add_modifier = { name = gm_evt_ruler_popular days = normal_modifier_time }
		}
		ai_chance = { base = 2 }
	}
}

monument_events.13 = {
	type = country_event
	placement = root

	event_image = { video = "unspecific_politicians_arguing" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_election.dds"

	title = monument_events.13.t
	desc = monument_events.13.d
	flavor = monument_events.13.f

	duration = 3
	cooldown = { days = long_modifier_time }

	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_republic }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_republic }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.13.a
		add_modifier = { name = gm_evt_citizens_assembly days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.13.b
		default_option = yes
		add_modifier = { name = gm_evt_military_parade days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
}

monument_events.14 = {
	type = country_event
	placement = root

	event_image = { video = "unspecific_military_parade" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/waving_flag.dds"

	title = monument_events.14.t
	desc = monument_events.14.d
	flavor = monument_events.14.f

	duration = 3
	cooldown = { days = long_modifier_time }

	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_revolution }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_revolution }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.14.a
		add_treasury = gm_event_cost
		add_modifier = { name = gm_evt_mass_rally days = normal_modifier_time }
		scope:monument_state = {
			add_loyalists_in_state = { value = 0.05 }
		}
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.14.b
		default_option = yes
		add_modifier = { name = gm_evt_quiet_commemoration days = normal_modifier_time }
		ai_chance = { base = 2 }
	}
}

monument_events.15 = {
	type = country_event
	placement = root

	event_image = { video = "unspecific_ruler_speaking_to_people" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_portrait.dds"

	title = monument_events.15.t
	desc = monument_events.15.d
	flavor = monument_events.15.f

	duration = 3
	cooldown = { days = long_modifier_time }

	trigger = {
		any_scope_state = {
			gm_state_holds_anniversary = { PM = pm_monument_leader }
		}
	}

	# The country's tallest monument of this dedication that holds anniversaries.
	immediate = {
		ordered_scope_state = {
			limit = {
				gm_state_holds_anniversary = { PM = pm_monument_leader }
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			save_scope_as = monument_state
		}
	}

	option = {
		name = monument_events.15.a
		add_treasury = gm_event_cost
		add_modifier = { name = gm_evt_leader_celebrated days = normal_modifier_time }
		ai_chance = { base = 1 }
	}

	option = {
		name = monument_events.15.b
		default_option = yes
		ruler = {
			add_modifier = { name = gm_evt_ruler_popular days = normal_modifier_time }
		}
		ai_chance = { base = 2 }
	}
}
```

- [ ] **Step 8: Loc**

In `localization/english/te_events_l_english.yml`, replace the `.a` values of `.3`–`.10` and add the rest, in key order:

```yaml
 monument_events.10.a:0 "Subsidise the tickets"
 monument_events.10.b:0 "Let the clubs keep the gate"
 monument_events.12.a:0 "Hold a lavish jubilee"
 monument_events.12.b:0 "A simple service, and the sovereign walks among the crowd"
 monument_events.12.d:0 "The anniversary of the reign falls this year, and the court wants it marked at the [SCOPE.sState('monument_state').GetCustom('gm_skin_name')] in [SCOPE.sState('monument_state').GetName]. The treasury would rather it were marked quietly."
 monument_events.12.f:0 "“Nobody remembers a quiet jubilee,” the chamberlain says.\n\n“Nobody remembers what a loud one cost, either. That is rather the point.”"
 monument_events.12.t:0 "Jubilee at the Monument"
 monument_events.13.a:0 "Convene a citizens' assembly"
 monument_events.13.b:0 "Hold a military parade"
 monument_events.13.d:0 "Constitution Day comes round again at the [SCOPE.sState('monument_state').GetCustom('gm_skin_name')] in [SCOPE.sState('monument_state').GetName]. Two proposals are on the minister's desk: open the monument to a citizens' assembly, or march the regiments past it."
 monument_events.13.f:0 "“An assembly will say things we have to answer,” the minister says.\n\n“A parade says nothing at all. People like that too.”"
 monument_events.13.t:0 "Constitution Day"
 monument_events.14.a:0 "Fill the square"
 monument_events.14.b:0 "A quiet commemoration with the veterans"
 monument_events.14.d:0 "Every year the revolution is remembered at the [SCOPE.sState('monument_state').GetCustom('gm_skin_name')] in [SCOPE.sState('monument_state').GetName]. This year the party wants the square full."
 monument_events.14.f:0 "“The people who made the revolution are old now,” the organizer says.\n\n“Then bring their grandchildren. It is theirs too.”"
 monument_events.14.t:0 "Anniversary of the Revolution"
 monument_events.15.a:0 "Let the celebrations go ahead"
 monument_events.15.b:0 "The leader declines the honour, in public"
 monument_events.15.d:0 "The head of state's birthday falls this week, and the [SCOPE.sState('monument_state').GetCustom('gm_skin_name')] in [SCOPE.sState('monument_state').GetName] has been decked out in advance by people eager to be seen doing it."
 monument_events.15.f:0 "“The leader says there is to be no fuss,” the aide says.\n\n“Then the fuss must look spontaneous.”"
 monument_events.15.t:0 "The Leader's Birthday"
 monument_events.3.a:0 "Make it a state occasion"
 monument_events.3.b:0 "Let the day keep itself"
 monument_events.4.a:0 "Build hostels for the pilgrims"
 monument_events.4.b:0 "Leave the pilgrims to the clergy"
 monument_events.5.a:0 "Make it a national day of remembrance"
 monument_events.5.b:0 "Keep it a quiet ceremony"
 monument_events.6.a:0 "Defend the artists"
 monument_events.6.b:0 "Close the scandalous works"
 monument_events.7.a:0 "Open the gardens free to all"
 monument_events.7.b:0 "Charge a small admission"
 monument_events.8.a:0 "Fund public lectures"
 monument_events.8.b:0 "Keep the telescopes for research"
 monument_events.9.a:0 "Reserve the halls for our own manufacturers"
 monument_events.9.b:0 "Invite exhibitors from abroad"
```

Add the modifier names to `te_miscellaneous_l_english.yml`, in key order:

```yaml
 gm_evt_artists_defended:0 "Artists Defended"
 gm_evt_artists_defended_desc:0 "The government stood by the opera house's scandalous season."
 gm_evt_citizens_assembly:0 "A Citizens' Assembly"
 gm_evt_citizens_assembly_desc:0 "Constitution Day was marked with a citizens' assembly at our monument to the republic."
 gm_evt_clergy_trusted:0 "The Clergy Trusted"
 gm_evt_clergy_trusted_desc:0 "The government left the shrine's pilgrims to the clergy."
 gm_evt_devout_pleased:0 "Pilgrims Welcomed"
 gm_evt_devout_pleased_desc:0 "The government built hostels for the shrine's pilgrims."
 gm_evt_domestic_exhibition:0 "Our Own Manufacturers"
 gm_evt_domestic_exhibition_desc:0 "The exhibition halls are reserved for our own industry."
 gm_evt_foreign_exhibitors:0 "Exhibitors from Abroad"
 gm_evt_foreign_exhibitors_desc:0 "Foreign manufacturers now show their machines in our exhibition halls."
 gm_evt_gardens_open:0 "Gardens Open to All"
 gm_evt_gardens_open_desc:0 "The botanical gardens here are free to all."
 gm_evt_jubilee:0 "A Royal Jubilee"
 gm_evt_jubilee_desc:0 "The reign was celebrated at our monument to the Crown."
 gm_evt_leader_celebrated:0 "The Leader Celebrated"
 gm_evt_leader_celebrated_desc:0 "The head of state's birthday was celebrated at the monument to them."
 gm_evt_mass_rally:0 "The Square Filled"
 gm_evt_mass_rally_desc:0 "The revolution's anniversary filled the square at our monument to it."
 gm_evt_military_parade:0 "A Constitution Day Parade"
 gm_evt_military_parade_desc:0 "Constitution Day was marked with a military parade."
 gm_evt_pilgrim_hostels:0 "Pilgrim Hostels"
 gm_evt_pilgrim_hostels_desc:0 "Hostels for the pilgrims who come to the shrine in this state."
 gm_evt_public_lectures:0 "Public Lectures"
 gm_evt_public_lectures_desc:0 "The observatory here holds public lectures."
 gm_evt_quiet_commemoration:0 "With the Veterans"
 gm_evt_quiet_commemoration_desc:0 "The revolution was remembered quietly, with those who made it."
 gm_evt_quiet_remembrance:0 "A Quiet Remembrance"
 gm_evt_quiet_remembrance_desc:0 "The names are read at the war memorial here each year, without ceremony."
 gm_evt_remembrance_day:0 "A Day of Remembrance"
 gm_evt_remembrance_day_desc:0 "The reading of the names at our war memorial is now a national day."
 gm_evt_research_nights:0 "The Telescopes Kept for Research"
 gm_evt_research_nights_desc:0 "The observatory's nights go to its astronomers."
 gm_evt_ruler_popular:0 "Among the People"
 gm_evt_ruler_popular_desc:0 "The head of state was seen among the crowd rather than above it."
 gm_evt_state_occasion:0 "A State Occasion"
 gm_evt_state_occasion_desc:0 "The anniversary at our monument to the nation was made a state occasion."
 gm_evt_subsidised_tickets:0 "Subsidised Tickets"
 gm_evt_subsidised_tickets_desc:0 "The government pays toward tickets at the stadium here."
 gm_evt_unions_pleased:0 "Cheap Seats"
 gm_evt_unions_pleased_desc:0 "The government made the stadium affordable to working people."
 gm_evt_works_closed:0 "Scandalous Works Closed"
 gm_evt_works_closed_desc:0 "The government closed the opera house's scandalous works."
```

- [ ] **Step 9: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check events/monument_events.txt common/on_actions/monument_events_on_actions.txt common/scripted_triggers/monument_triggers.txt common/static_modifiers/gm_modifiers.txt && python3 scripts/analysis/check_localization_files.py && for a in empty_effect event_context orphaned_event loc_render duplicate_key; do python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"; done`
Expected: exit 0, no `FAIL` lines.

- [ ] **Step 10: Commit**

```bash
git add events/monument_events.txt common/on_actions/monument_events_on_actions.txt \
        common/scripted_triggers/monument_triggers.txt common/static_modifiers/gm_modifiers.txt \
        localization/english/te_events_l_english.yml localization/english/te_miscellaneous_l_english.yml \
        test_grand_monument_registry.py
git commit -m "feat(monuments): anniversaries with real choices, for every dedication

The eight flavour events gain two options each, and Crown, Republic,
Revolution and Leader get one of their own. Each is a choice between two
benefits for two constituencies; money is the only cost an option carries.
A contested or heritage monument holds no anniversaries.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 11: The debug event and the monthly log line

**Files:**
- Create: `events/te_debug_monuments_events.txt`
- Modify: `common/scripted_effects/gm_effects.txt` (append `gm_debug_log`; call it from `gm_country_monthly`)
- Modify: `localization/english/te_events_l_english.yml`
- Modify: `test_grand_monument_registry.py` (add `DebugTests`)

**Interfaces:**
- Consumes: everything above.
- Produces (effect, country scope): `gm_debug_log` (writes `TE_MONUMENTS:` lines).
- Produces (event): `te_debug_monuments.1` (console only: `event te_debug_monuments.1`).

- [ ] **Step 1: Write the failing tests**

Append to `test_grand_monument_registry.py`:

```python
# ---- Task 11: the debug event ---------------------------------------------------------

class DebugTests(unittest.TestCase):
    def test_debug_event(self):
        text = read(DEBUG_EVENTS)
        self.assertIn("namespace = te_debug_monuments", text)
        self.assertRegex(text, r"(?m)^te_debug_monuments\.1 = \{ # REVIEWED \d{4}-\d{2}-\d{2}: console-only")
        body = squash(strip_comments(raw_block_at(text, r"(?m)^te_debug_monuments\.1\s*=\s*\{")))
        for s in ("gm_state_start_ceremony = yes", "gm_country_monthly = yes", "gm_state_contest = yes",
                  "gm_state_vanity_backlash = yes", "gm_debug_log = yes"):
            self.assertIn(s, body)
        L = loc()
        for k in ("t", "desc", "flavor", "a", "b", "c", "d", "e"):
            self.assertIn(f"te_debug_monuments.1.{k}", L)

    def test_monthly_log_for_players(self):
        monthly = squash(block(read(EFFECTS), "gm_country_monthly"))
        self.assertIn("limit = { is_ai = no } gm_debug_log = yes", monthly)
        log = block(read(EFFECTS), "gm_debug_log")
        self.assertIn('debug_log = "TE_MONUMENTS:', log)
        self.assertNotIn(".MakeScope", log, "debug_log's working form is [SCOPE.ScriptValue('x')|N]")
```

- [ ] **Step 2: Run to confirm it fails**

Run: `python3 -m unittest test_grand_monument_registry.DebugTests -v`
Expected: ERROR.

- [ ] **Step 3: The log effect**

Append to `common/scripted_effects/gm_effects.txt`:

```

# ---- Debug (spec §10) ------------------------------------------------------------
# Country scope. TE_MONUMENTS: lines in debug.log. Only the documented working
# debug_log form ([SCOPE.ScriptValue('...')|N], no .MakeScope, no names:
# scripting_best_practices.md § "debug_log Loc-String Templating Limitations").
gm_debug_log = {
	debug_log = "TE_MONUMENTS: [SCOPE.ScriptValue('gm_display_count')|0] monuments, [SCOPE.ScriptValue('gm_display_contested')|0] contested"
	debug_log = "TE_MONUMENTS: standing grandeur [SCOPE.ScriptValue('gm_display_g_standing')|0], prestige +[SCOPE.ScriptValue('gm_display_prestige')|1]; regime grandeur [SCOPE.ScriptValue('gm_display_g_regime')|0], legitimacy +[SCOPE.ScriptValue('gm_display_legitimacy')|1]; cultural pull +[SCOPE.ScriptValue('gm_display_culture')|1]"
	debug_log = "TE_MONUMENTS: teardown legitimacy +[SCOPE.ScriptValue('gm_display_teardown')|1], vanity legitimacy [SCOPE.ScriptValue('gm_display_vanity')|1]"
	debug_log = "TE_MONUMENTS: IG approval AF [SCOPE.ScriptValue('gm_display_ig_armed_forces')|1] DV [SCOPE.ScriptValue('gm_display_ig_devout')|1] IN [SCOPE.ScriptValue('gm_display_ig_industrialists')|1] IT [SCOPE.ScriptValue('gm_display_ig_intelligentsia')|1] LO [SCOPE.ScriptValue('gm_display_ig_landowners')|1] PB [SCOPE.ScriptValue('gm_display_ig_petty_bourgeoisie')|1] RF [SCOPE.ScriptValue('gm_display_ig_rural_folk')|1] TU [SCOPE.ScriptValue('gm_display_ig_trade_unions')|1]"
}
```

In `gm_country_monthly`, add as its last lines:

```
	if = {
		limit = { is_ai = no }
		gm_debug_log = yes
	}
```

- [ ] **Step 4: The debug event**

Create `events/te_debug_monuments_events.txt` (BOM, tabs):

```
namespace = te_debug_monuments

# ============================================================================
# GRAND MONUMENTS — console test event: `event te_debug_monuments.1`
# ============================================================================
# Each option writes TE_MONUMENTS: lines to debug.log (gm_debug_log). The
# options together answer the in-game checklist: a ceremony, a monthly pass,
# a forced contest, vanity backlash, and a print of every total.

te_debug_monuments.1 = { # REVIEWED 2026-09-27: console-only test event (`event te_debug_monuments.1`); never fired by script on purpose
	type = country_event
	placement = ROOT

	event_image = { video = "unspecific_world_fair" }
	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = te_debug_monuments.1.t
	desc = te_debug_monuments.1.desc
	flavor = te_debug_monuments.1.flavor

	# Raise a level-20 monument in the capital and hold the ceremony.
	option = {
		name = te_debug_monuments.1.a
		default_option = yes
		capital = {
			if = {
				limit = {
					NOT = { has_building = building_grand_monument }
				}
				create_building = { building = building_grand_monument level = 20 }
			}
			gm_state_start_ceremony = yes
		}
	}

	# Run this month's pass now (contests, ledgers, totals, the log).
	option = {
		name = te_debug_monuments.1.b
		gm_country_monthly = yes
	}

	# Contest our tallest regime, ruler or faith monument now, as if it had fallen.
	option = {
		name = te_debug_monuments.1.c
		ordered_scope_state = {
			limit = {
				gm_state_is_dedicated = yes
				gm_state_is_bound = yes
				gm_state_is_contested = no
			}
			order_by = gm_state_grandeur
			position = 0
			check_range_bounds = no
			gm_state_contest = yes
		}
		gm_country_refresh = yes
	}

	# Vanity backlash in the capital's monument, as if a level had finished in hard times.
	option = {
		name = te_debug_monuments.1.d
		capital = {
			if = {
				limit = { has_building = building_grand_monument }
				gm_state_vanity_backlash = yes
			}
		}
		gm_country_refresh = yes
	}

	# Print every total.
	option = {
		name = te_debug_monuments.1.e
		gm_debug_log = yes
	}
}
```

Add to `localization/english/te_events_l_english.yml`, in key order:

```yaml
 te_debug_monuments.1.a:0 "Raise a level-20 monument in the capital and hold its ceremony"
 te_debug_monuments.1.b:0 "Run this month's monument pass now"
 te_debug_monuments.1.c:0 "Contest our tallest regime, ruler or faith monument"
 te_debug_monuments.1.d:0 "Vanity backlash at the capital's monument"
 te_debug_monuments.1.desc:0 "Grand Monument test tools. Each writes TE_MONUMENTS: lines to debug.log."
 te_debug_monuments.1.e:0 "Print every monument total to debug.log"
 te_debug_monuments.1.flavor:0 "Console only."
 te_debug_monuments.1.t:0 "Debug: Grand Monuments"
```

- [ ] **Step 5: Run the tests to confirm they pass**

Run: `python3 -m unittest test_grand_monument_registry -v`
Expected: all OK.
Run: `python3 scripts/format_paradox_tabs.py --check events/te_debug_monuments_events.txt common/scripted_effects/gm_effects.txt && python3 orphaned_event_audit.py --strict && python3 scripts/analysis/check_localization_files.py`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add events/te_debug_monuments_events.txt common/scripted_effects/gm_effects.txt \
        localization/english/te_events_l_english.yml test_grand_monument_registry.py
git commit -m "feat(monuments): console test event and TE_MONUMENTS: log lines

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 12: Docs and the player guide

No new behavior. The system doc and the player guide describe what Tasks 1–11 built; the PDF is rebuilt.

**Files:**
- Modify: `docs/systems/mod_systems.md` (replace § "Grand Monuments (Repeatable Construction Sink)")
- Modify: `docs/player_guide/02-timeline.md`, `01-introduction.md`, `07-states.md`, `10-influence.md`, `16-reference.md`
- Rebuild: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`
- Modify (if anything was learned about the engine while building): `docs/guides/scripting_best_practices.md`

- [ ] **Step 1: The system doc**

In `docs/systems/mod_systems.md`, replace the whole section from `## Grand Monuments (Repeatable Construction Sink)` up to (not including) `## Temporary Amendments (Sunset Clauses)` with:

```markdown
## Grand Monuments (Political Instrument)

A government raises a Grand Monument to what it stands for, and the next government deals with its legacy. Design: `docs/superpowers/specs/2026-09-27-grand-monument-rework-design.md`; plan: `docs/superpowers/plans/2026-09-27-grand-monument-rework.md`. **Add a dedication:** add its row to `DEDICATIONS` in `test_grand_monument_registry.py`; the failures are the checklist.

- **Files:** `common/buildings/grand_monuments.txt`, `common/production_methods/grand_monument_pms.txt`, `common/production_method_groups/grand_monument_pmgs.txt`, `common/scripted_triggers/monument_triggers.txt`, `common/scripted_effects/gm_effects.txt`, `common/script_values/gm_values.txt`, `common/static_modifiers/gm_modifiers.txt`, `common/journal_entries/je_grand_monuments.txt`, `gui/journal_entry_widgets/grand_monuments_widget.gui`, `common/scripted_guis/gm_sguis.txt`, `common/customizable_localization/gm_custom_loc.txt`, `common/on_actions/monument_events_on_actions.txt`, `events/monument_events.txt`, `events/te_debug_monuments_events.txt`; the shared `common/scripted_triggers/te_heritage_triggers.txt`; `grand_monuments_rule` in `extra_game_rules.txt`.
- **Grandeur and the curve.** A monument's grandeur is its level (uncapped). Every effect grows in steps, each costing twice the grandeur of the last (`gm_curve_steps_f5` / `_f10`, eight terms; `gm_curve_next_*` for the JE's "next step"). Each static modifier carries **one step** and the multiplier is the step count; `gm_step_*` script values mirror them for loc, pinned equal by the registry test.
- **PMs carry only staff.** The dedication PMs keep the self-reference ratchet (see the file header) and `unscaled` employment; no `country_modifiers`, `state_modifiers` or goods.
- **Where modifiers live.** Local effects (`gm_local_*`) are state modifiers refreshed by `gm_state_monthly` from `on_monthly_pulse_state`. National effects (`gm_national_*`, `gm_ig_approval_<ig>`) sit on `je:je_grand_monuments`, applied by `gm_country_refresh` with ROOT = the country (monthly, or `monument_events.20` after `on_law_activated`, `on_new_ruler`, `on_state_owner_change` and a finished level, whose ROOTs are not the country). A variable backing a multiplier is zeroed, never removed.
- **Kinds and fit.** Regime (Crown, Republic, Revolution), ruler (Leader), faith (Shrine), timeless (the rest). Fit is read live each month (`gm_state_message_fits`). Records live on the **state** (buildings hold no variables): `gm_raised_by` (a bound monument fits only while that country owns it), `gm_honoree` / `gm_honoree_ig`, `gm_faith`, `gm_skin`. `gm_state_first_sight` writes them for panel picks and old saves; after that a missing record reads as "does not fit".
- **National totals** (`gm_compute_totals`): standing grandeur (every monument not contested: prestige, cultural pull), regime grandeur (fitting regime and ruler monuments: legitimacy), one per dedication with a national effect, and one signed total per IG (approvals minus oppositions, plus its ledger, minus contested monuments whose "new order" it is), each through the curve on its absolute value.
- **Contests** (`gm_check_contests`, skipped while the country has `te_cw_role`): a bound monument that stops fitting records `gm_base_ig` / `gm_supporter_ig` flags and becomes contested; one that fits again is restored. `gm_state_changed_hands` contests a conquered regime or ruler monument and makes a conquered shrine heritage. The winner of a civil war adopts the loser's monuments (`gm_repair_after_civil_war`, in `te_civil_war_on_won`). Choices: `gm_state_tear_down` / `_rededicate` (rebuilt at half level through the shared ladder, which runs to 200) / `_preserve`; each writes decaying ledgers (`gm_teardown_ledger`, `gm_ig_ledger_<ig>`), so nothing stacks. Players get `monument_events.16` (and `.17` per monument); the AI decides monthly. A contested monument demolished from the panel counts as torn down.
- **Skins** (`gm_skin`): faith skins by state religion, heritage skins by the language-reform revival partition (`te_heritage_<language>`, also called by `extra_law_events.25`), chosen in `monument_events.11`; `gm_inscription` names a revived language.
- **Vanity backlash:** `monument_events.1` (a level finished, ROOT = the building) calls `gm_state_vanity_backlash` in hard times (`gm_country_hard_times`): radicals, and the linear `gm_vanity_ledger`.
- **Anniversaries:** `.3`–`.10`, `.12`–`.15`, dispatched by `monument_events_on_action` for a fitting monument of level 3 or more; every option is positive, money the only cost.
- **NOT in `bg_monuments`, and that is load-bearing.** `tourism_throughput_from_monuments` and `cultural_pull_from_monuments` iterate `bg_monuments` and assume one-off wonders. `bg_grand_monuments` is a top-level group with no `parent_group`; Grand Monument cultural pull is `cultural_pull_from_grand_monuments` (standing grandeur through the curve, at most +5).
- **Debug:** `event te_debug_monuments.1`; `TE_MONUMENTS:` lines each month for players.
```

- [ ] **Step 2: The player guide**

(a) `docs/player_guide/02-timeline.md`: in the opening paragraph, replace `37 wonders, seven megaprojects and a\nrepeatable Grand Monument. None of this is behind a game rule:` with `37 wonders and seven megaprojects. None of this is behind a game rule:`, and after the paragraph's last sentence (`...which needs a Moon landing from the space\nrace.`) add ` The repeatable [Grand Monument](#grand-monuments) has a game rule of its own.` In the goods table (line 159), change `Tourism Industry, National Park, Grand Monument and others` to `Tourism Industry, National Park and others`.

(b) Replace the whole `## Grand monuments` section (to the end of the file) with:

```markdown
## Grand monuments

The Grand Monument is a building you can raise in any state from the start of
the game. A government raises one to what it stands for: its crown, its
republic, its revolution, its leader, its faith or the nation. Each level costs
10,000 construction and needs only maintenance and a small caretaker staff. A
monument's level is its **grandeur**, and it has no cap. The Grand Monuments
game rule can switch the system off.

Everything a monument gives grows with grandeur in steps. The first step takes 5
grandeur and each further step takes twice as much as the one before, so steps
complete at 5, 15, 35, 75, 155 and so on. Inside a step every level counts.
Legitimacy and cultural pull take steps of 10. National effects count all your
monuments' grandeur together, so twenty small monuments give the same national
effects as one tall one; local effects count each monument on its own.

<!-- screenshot: the Monuments journal entry with its national lines and a contested monument's row -->

### The Monuments journal entry

The Monuments journal entry appears when you own a Grand Monument. It lists each
national effect with the grandeur behind it and the grandeur at which its next
step completes, a red warning while a finished level would cause vanity
backlash, and one row per monument with its form, dedication, grandeur and
status.

Every monument, whatever it honours, gives:

- +25 prestige for each step of standing grandeur, counting every monument that
  is not contested.
- +25% Tourism Industry throughput in its state for each step of its own
  grandeur, so its first five levels match one of the base game's monuments.
- +1 cultural pull for each step of standing grandeur (steps of 10), up to +5.

### Monument dedications

When a level of an undedicated monument finishes, a dedication ceremony asks
what it honours. The choice is permanent, and the ceremony's tooltips list each
dedication's effects. An undedicated monument gives only the prestige, tourism
and cultural pull above; the ceremony asks again at its next level.

| Dedication | Requires | Approves / objects | National, per step | In its state, per step |
|---|---|---|---|---|
| To the Crown | A crowned head of state | Landowners / Intelligentsia | +2 legitimacy | +10% loyalists from movements |
| To the Republic | A republic | Intelligentsia / Landowners | +2 legitimacy | +10% loyalists from movements |
| To the Revolution | Single-Party State or Council Republic | Trade Unions / Industrialists | +2 legitimacy | +10% loyalists from movements |
| To the Leader | Autocracy or Single-Party State, not crowned | The ruler's own group / the strongest group outside the government | +2 legitimacy, +25 authority | +10% loyalists from movements |
| Grand Shrine | No State Atheism | Devout | +5% Devout attraction | +10% conversion |
| To the Nation | | Petty Bourgeoisie | | +10% loyalists from movements |
| War Memorial | | Armed Forces | 3% less war support lost to casualties | +5% conscription rate |
| Grand Opera House | Romanticism | Intelligentsia | +5% Intelligentsia attraction | +10% Creative Industries throughput |
| Botanical Gardens | Romanticism | Rural Folk | | 5,000 less pollution |
| Grand Observatory | Empiricism | Intelligentsia | +3 innovation cap | Faster literacy growth |
| Great Exhibition Hall | Marketing Research, no Industry Banned | Industrialists | +5% Industrialists attraction | +10% migration pull |
| Grand Stadium | Television Broadcasting | Trade Unions | | 10% lower turmoil effects |

Legitimacy counts the grandeur of all your monuments to the Crown, the Republic,
the Revolution and the Leader together, in steps of 10, and only while each
still fits. Each interest group's approval counts the grandeur of the monuments
it approves of, minus those it objects to, and moves by 1 per step either way.
No number of monuments can buy a group outright: each group has one total.

### Monument forms

A monument to the Crown, the Republic, the Revolution, the Leader or the nation,
or a War Memorial, can take the form of your primary cultures' classical
heritage: a forum and triumphal column for a Romance-speaking country, a hall of
dynasties for a Chinese, Japanese or Korean one, an Aksumite stele for an
Amharic or Tigrinya one, and so on through the classical languages that language
reform can revive. A Grand Shrine takes the form of your state religion's great
building: a basilica, a great mosque, a great temple, a pagoda. When more than
one form fits, an event asks which. The form changes the monument's name and
look, not what it does. If you have revived the matching language under a
state-led language reform, the monument's row says its dedication is carved in
it.

### Contested monuments

A monument to the Crown, the Republic, the Revolution, the Leader or a faith can
outlive what it honours. It becomes **contested** when its crown, republic or
revolution falls, when its leader stops ruling for any reason, when the country
adopts State Atheism or changes its state religion, or when another country
takes its state. A contested monument keeps its tourism and its effect in the
state, but gives no prestige, legitimacy or approval, and the group that objected
to its message resents it every month it stands undecided.

When it happens, a notice lets you decide for all of them at once or one at a
time. You can also decide later from the monument's row in the journal entry.

| Choice | What happens |
|---|---|
| Pull Down | The monument and all its grandeur are gone. The new government gains legitimacy that fades over about five years. The group that objected to the old message approves and the group that raised it resents it, both fading. |
| Rededicate | Costs 5,000 per level. The monument is rebuilt at half its level, rounded up, and the ceremony dedicates it again under your current laws. Its old supporters resent it a little. |
| Keep as Heritage | The monument stays and its prestige returns, but under this government it lends no legitimacy and gives no approval. The group that objected resents it, less each year. |

Pulling down many monuments at once gives what pulling down one of their
combined grandeur would: each reward and resentment comes from a single total
that fades month by month. If what a contested or heritage monument honours
comes back, for example when the monarchy is restored, it counts in full again.
Pulling it down is the only permanent choice. A shrine in a state that another
country takes becomes heritage at once and cannot be pulled down. After a civil
war the winner inherits the monuments the loser raised, and they are contested
only if its laws no longer fit them. Demolishing a contested monument from its
building panel counts as pulling it down.

### Vanity backlash

Finishing a monument level while the country is in default, in famine or in
recession angers people: 5% of the state's pops turn radical, and legitimacy
falls by 3 for each such level, fading over about two years. The journal entry
shows a red warning while this would happen, so you can pause construction
first.

### Monument anniversaries

Every dedication has an anniversary event that can fire once a monument of that
dedication reaches level 3 and still fits. Each offers a choice between two
benefits, usually for two interest groups, and the only cost is money. A
contested or heritage monument holds no anniversaries.

The AI raises monuments mainly as a great or major power, in a state with a
Tourism Industry, or when its legitimacy is low, and never while at war or in
hard times. It decides its contested monuments within a few months: small ones
and those under a revolutionary government tend to come down, tall ones are kept
as heritage, and it rededicates only with money in the treasury.
```

(c) `docs/player_guide/01-introduction.md`: `fifteen game rules` → `sixteen game rules`; in the rules table, after the `Internal Resettlement` row, add:

```markdown
| Grand Monuments | Enabled | Grand Monuments, their dedications, the Monuments journal entry and contested monuments. | [The extended timeline](02-timeline.md#grand-monuments) |
```

(d) `docs/player_guide/07-states.md` (line 200): replace `a Grand Monument (+1% per level)` with `a Grand Monument (+25% for each step of its grandeur, see [Grand monuments](02-timeline.md#grand-monuments))`.

(e) `docs/player_guide/10-influence.md` (the Monuments row): replace `Up to +5 more from grand monuments (+1 per 20 levels).` with `Up to +5 more from grand monuments: +1 for each step of their combined grandeur, in steps of 10, counting only monuments that are not contested.`

(f) `docs/player_guide/16-reference.md`: in the systems table, change the Grand Monument row's rule from `none` to `Grand Monuments`; in the glossary, replace the Grand Monument row with the first line below and add the second after it:

```markdown
| Grand Monument | A building a government raises to what it stands for. Its effects grow with its grandeur, and it can become contested when what it honours falls. | [The extended timeline](02-timeline.md#grand-monuments) |
| Grandeur | A Grand Monument's level. Its effects grow in steps, each taking twice the grandeur of the one before. | [The extended timeline](02-timeline.md#grand-monuments) |
```

- [ ] **Step 3: Lint and rebuild the PDF**

```bash
python3 scripts/analysis/check_player_guide_style.py --strict
~/src/Vic3TimelineExtended/.venv/bin/python scripts/build_player_guide.py
python3 scripts/build_player_guide.py --check
```

Expected: the lint passes (fix any heading collision or wording it flags); the build writes `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`; `--check` passes. The worktree has no `.venv`; the main checkout's venv runs the build against the worktree's files because the script resolves paths from its own location. If the build needs `gfx/` (it should not), `git sparse-checkout add /gfx/` first.

- [ ] **Step 4: Lessons**

If building this taught anything about the engine that isn't in `docs/guides/scripting_best_practices.md` (for example, whether `activate_production_method` is visible to a trigger later in the same effect), add a short paragraph there now. If nothing new was learned, skip this step.

- [ ] **Step 5: Commit**

```bash
git add docs/systems/mod_systems.md docs/player_guide/02-timeline.md docs/player_guide/01-introduction.md \
        docs/player_guide/07-states.md docs/player_guide/10-influence.md docs/player_guide/16-reference.md \
        docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf
git add docs/guides/scripting_best_practices.md 2>/dev/null || true
git commit -m "docs(monuments): system doc and player guide for the Grand Monument rework

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_0136QyjfDp4WH6JxUeLod8xh"
```

---

### Task 13: Full verification and the PR body

No new behavior. This runs every game-independent check CI runs, then a reload on a second server from the worktree, then writes the PR body with the in-game checklist.

- [ ] **Step 1: CI's checks, locally**

```bash
cd ~/src/vic3te-grand-monument
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent \
       VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
python3 -m compileall -q . >/dev/null && echo compile-ok
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs python3 -m unittest 2>&1 | tail -3
ruff check .
python3 scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt' | grep -v -x -E 'common/ideologies/modified\.txt|common/interest_groups/00_.*\.txt|common/scripted_effects/extra_law_consistency_generated\.txt')
python3 scripts/analysis/check_localization_files.py
python3 scripts/analysis/check_post_load_rosters.py
python3 scripts/analysis/check_dds_dimensions.py
python3 scripts/analysis/check_player_guide_style.py --strict
python3 scripts/build_player_guide.py --check
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var \
         treaty_leverage_side event_context silent_variable prev_scope container_timed_variable \
         je_immediate_reset empty_effect change_variable_clamp; do
  python3 ${a}_audit.py --strict >/dev/null || echo "FAIL $a"
done
python3 kill_character_audit.py --check >/dev/null || echo "FAIL kill_character"
python3 attitude_key_audit.py >/dev/null || echo "FAIL attitude_key"
```

Expected: `compile-ok`; unittest `OK` (skips allowed); ruff clean; no `FAIL` lines. Fix anything that fails in the task that owns it, re-run that task's tests, and commit the fix there. Also run the PEP 701 scan on the new test file: `grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" test_grand_monument_registry.py` (CI's Python 3.11 rejects a quote reused inside an f-string's braces).

- [ ] **Step 2: Event images**

The worktree is sparse (`gfx/` excluded), so `event_image_audit` cannot see mod textures. Re-include the event pictures and run it:

```bash
git sparse-checkout add /gfx/event_pictures/
python3 event_image_audit.py --strict && echo images-ok
```

- [ ] **Step 3: A reload from a second server**

Start a server **from the worktree** on port 8951 (`docs/guides/python_tools.md` § "Starting the Server"); never POST to the main checkout's server on 8950. Run it as a background task (`run_in_background`, not `&`):

```bash
cd ~/src/vic3te-grand-monument && cp ~/src/Vic3TimelineExtended/paths.local.json .
VIC3_SKIP_DIGESTS_FETCH=1 ~/src/Vic3TimelineExtended/.venv/bin/python -c "import mod_state_server as m; m.PORT=8951; m.main()"
```

When `curl -s http://127.0.0.1:8951/status` answers:

```bash
curl -s -X POST "http://127.0.0.1:8951/reload?mod_only=true&audits_only=true" | python3 -c "
import json,sys; r=json.load(sys.stdin)
print('parse_failures', r.get('parse_failures')); print('warnings', len(r.get('warnings', [])))
[print(w.get('label'), str(w)[:300]) for w in r.get('warnings', []) if any(s in json.dumps(w).lower() for s in ('monument', 'gm_', 'heritage'))]"
```

Expected: `parse_failures` empty; no warning naming a monument, `gm_` or heritage key. Then check `docs/engine/loc_coverage_report.md`, `docs/engine/modifier_visibility_report.md` (the `gm_local_scientific` literacy step, 0.00025, is the likeliest "+0") and `docs/engine/effect_trigger_validity_report.md` in the worktree for any `gm_`, `monument` or `te_heritage` line. Fix any real finding in its task; don't commit the regenerated `docs/engine/*` churn. Stop the server with `kill $(cat mod_state_server.pid)` from the worktree, then `git checkout -- docs/engine/` and remove the copied `paths.local.json`.

- [ ] **Step 4: The PR body with the in-game checklist**

Write `PR_BODY.md` in the worktree root (untracked). It holds: a summary of what changed and why (from the spec's Context and Decisions), the seven "Decisions this plan makes" above for the owner to confirm, a "Not built in phase 1" line (named landmarks and new art, phase 2; the building readout of spec §2.5, which waits on #500's check), "Player guide: chapters 1, 2, 7, 10 and 16 updated, PDF rebuilt", the commit list, and this checklist:

```markdown
## In-game checks

Setup: build an integration from this branch in the **full** main checkout (CLAUDE.md "Play-testing unmerged work"), `./scripts/deploy.sh --apply`, and make sure no Workshop copy of the mod is enabled.

1. The ratchet holds: a dedicated monument's building panel shows one production method.
2. `event te_debug_monuments.1` → **a**: a level-20 monument in the capital, the ceremony opens with the dedications your laws allow, and a regime or Shrine pick opens the form event (`.11`) when a heritage or faith form fits.
3. `on_building_built` fires for each finished level (the ceremony re-asks on an undedicated monument); note whether it also fires for the script-built monument in (2) (only one ceremony should show either way).
4. → **b**: `TE_MONUMENTS:` lines in `debug.log`; the Monuments journal entry shows prestige, legitimacy and the IG lines with real numbers and "next step at"; the state shows *Grand Monument* and *Grand Monument: To the Crown* (or the chosen dedication) with multiplied values, not the one-step value.
5. The ceremony tooltips show real numbers (from `gm_step_*`), not blanks.
6. JE-scoped approval: the IG panel's approval breakdown shows *Grand Monuments* for the approving and objecting groups.
7. A contest by law: change a crowned government to a republic (console law change). The Crown monument becomes contested, the notice (`.16`) fires, and each of Pull Down / Keep as Heritage / Decide each in turn does what its tooltip says; restoring the monarchy lifts a heritage monument back to full.
8. The row buttons: on a contested row, Pull Down, Rededicate and Keep as Heritage are enabled and act on that row's state (the saved `gm_state` scope; if they stay greyed, the scope is not arriving: report it, `.17` is the fallback).
9. Rededicate: the monument comes back at half its level (rounded up), rehired, with the ceremony; the treasury pays 5,000 a level.
10. A Leader monument: under Autocracy with an uncrowned head of state, raise one; when the ruler changes, it becomes contested; the objecting group read is the strongest one outside the government.
11. Conquest: take a state with a foreign Crown monument in a war. It is contested for you even if you are also a monarchy; a foreign Grand Shrine becomes heritage at once. Note whether the state's `gm_` variables survived the transfer (`debug.log` via option **e**, or the row's form).
12. A civil war: rebel-held monuments are not contested during the war; after the rebels win, their monuments are theirs, contested only if their laws differ.
13. Vanity backlash: with the country in default (or famine), finish a level: the red warning showed beforehand, the toast fires, radicals appear, *Palaces amid Hardship* costs legitimacy and fades.
14. With a revived language (state-led language reform with, say, Revived Latin), a Forum and Triumphal Column row shows the inscription line; language reform still offers the same revivals as before.
15. Anniversaries: a fitting level-3 monument eventually fires its event; both options do what their tooltips say; a Leader's popularity option lands on the ruler.
16. The Disabled rule: no Grand Monument can be built, and no journal entry appears.
17. An old save with pre-rework monuments loads; civic monuments show as To the Nation; no monument is contested on the first month unless it genuinely does not fit.
```

- [ ] **Step 5: Hand over**

Report the results to the owner and invoke `superpowers:finishing-a-development-branch`. Don't push or open the PR without the owner's go-ahead. Update the project memory `project_grand_monument_rework.md` (branch, plan done, PR body path, awaiting in-game checks).
