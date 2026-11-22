# Extraplanetary Base Ground Types Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Extraplanetary Base site a ground type whose goods mix rides on each base building, one shared basket for the four mining methods, and a Bases view where levels are assigned to sites by hand or by a profit checkbox, every move paced.

**Architecture:** A pure-Python module (`ebase_ground.py`) holds the types, the site map, the basket and a model of the month, and is the reference the generated script must match. A new generator (`gen_ebase.py`) writes the per-place script values and effects, which a rewritten `sr_ebase_refresh` calls. The panel is hand-written GUI in `space_race_widget.gui` with per-colony overrides from `gen_solar_sites._colony_row`, as the other Colonies views are built.

**Tech Stack:** Paradox script (Victoria 3 1.15), the mod's Python generators, unittest under pytest.

**Spec:** `docs/superpowers/specs/2026-11-05-extraplanetary-base-ground-types-design.md` (§ n below means that document's). Read it first; this plan argues from it.

**Branch:** a new branch from `main` once #1397 has merged (`feature/ebase-ground-types`), in a sparse worktree (`docs/guides/git_workflow.md` § Parallel checkouts). One PR, five stages as commits (§ 10). If the owner keeps the build in #1397 instead, build on `claude/zealous-curie-qr239n`. The PR description carries an "Intended balance" section (§ 7, the Deep-Sea paragraph, owner 2026-11-21), the per-method output changes for the release notes (`docs/releases/<version>.md` is written from PR descriptions at release), and a "Player guide" line.

## Global Constraints

- Goods, in this order everywhere: `iron` (Structural Metals), `tech_metals` (Tech-Critical Metals), `gold`, `copper` (Conductive Metals), `lead` (Base Metals), `sulfur` (Chemical and Industrial Minerals), `glass` (Glass and Plastics). Base prices 40, 80, 100, 40, 40, 50, 40.
- Types, in this order: `mixed`, `metallic`, `rocky`, `carbonaceous`, `sulfurous`, `hydrocarbon`, `icy`. Loc names Mixed, Metallic, Rocky, Carbonaceous, Sulfurous, Hydrocarbon, Icy.
- Each type's composition, a factor of the basket before normalization (§ 6.2); the generator normalizes it to a value-weighted mean of exactly zero:

  | type | iron | tech_metals | gold | copper | lead | sulfur | glass |
  |---|---|---|---|---|---|---|---|
  | mixed | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
  | metallic | 1.2 | 1.1 | 1.4 | 1.2 | 1.0 | 0.3 | 0.1 |
  | rocky | 1.3 | 1.0 | 0.5 | 0.85 | 0.85 | 1.1 | 1.4 |
  | carbonaceous | 0.8 | 0.9 | 0.65 | 0.9 | 0.9 | 2.0 | 2.1 |
  | sulfurous | 0.8 | 0.85 | 0.6 | 1.0 | 1.0 | 4.0 | 1.2 |
  | hydrocarbon | 0.75 | 0.85 | 0.5 | 0.8 | 0.8 | 1.8 | 3.5 |
  | icy | 1.0 | 0.95 | 0.6 | 0.9 | 0.9 | 1.6 | 1.8 |

- Normalized and rounded to whole percent, the figures the loc states (§ 6.2): metallic +12 +2 +30 +12 −7 −72 −91; rocky +26 −3 −51 −17 −17 +7 +36; carbonaceous −17 −7 −33 −7 −7 +107 +117; sulfurous −16 −11 −37 +5 +5 +320 +26; hydrocarbon −25 −15 −50 −20 −20 +80 +249; icy 0 −5 −40 −10 −10 +61 +81.
- Ground (§ 6.3): `near_earth` mixed; `psyche` metallic; rocky: `vesta valles_marineris olympus_mons hellas_planitia mercury tranquility marius_hills daedalus imbrium`; carbonaceous: `ceres pallas hygiea himalia callisto enceladus`; sulfurous: `amalthea io europa venus`; hydrocarbon: `titan iapetus pluto makemake sedna`; icy: `utopia_planitia arcadia_planitia shackleton peary ganymede rhea mimas titania oberon miranda ariel triton proteus eris haumea`.
- The basket, outputs a level (§ 7). Asteroid Mine `pm_space_mine`: iron 250, tech_metals 175, gold 50, copper 95, lead 10, sulfur 25, glass 70. Mining Colony `pm_space_colony_mining`: four times that. Self-Replicating Miners `pm_self_replicating_miners`: five times. Regolith Processing `pm_regolith_processing`: iron 111.41, tech_metals 78.00, gold 22.27, copper 42.34, lead 4.46, sulfur 11.14, glass 31.19 (£16,600.00 exactly). Inputs, crews and every other PM line unchanged.
- Places: `near_earth` (index 0, room 10 at grade 0, only with `asteroid_mining`) and the 40 sites (`Site.index` 1 to 40). Levels past all room work at −75% (`gen_solar_sites.OVERFLOW_GRADE`) and count as mixed.
- Pace `ceil(L / 48)` levels a month, at least 1 (`PACE_MONTHS = 48`). Checkbox margin 5% of the yardstick (`MARGIN = 0.05`). Notice once a move has carried 5% of the levels (`NOTICE_SHARE = 0.05`), once per new type pair, at most once a year.
- The Resort Colony (`pm_space_colony_vacation`) may leave the building (#1948). Read the methods from `pmg_base_building_space_mine` at generation time, never from a hard-coded list; a method's goods outside the seven get no mix.
- A worktree has no `.venv`: run Python, pytest and ruff with the main checkout's (`<mod_path>/.venv/bin/python`); `.venv/bin/python` below means that one.
- Repo rules: tabs and exactly one BOM in `.txt`, `.gui` and loc `.yml`; American English; never hand-edit generated files; `python3 organize_loc.py` after new loc keys; a new generated file gets a row in `docs/auto_generated_files.md` and a class in `scripts/nightly_audit_select.py`; a static modifier added without a duration gets a `gen_nation_tab.py` registry line; no old-save code (1.15 loads no older save).

## Review Focus

1. **Levels outnumbering all the room.** Every place is full, nothing moves, `T` counts the rest at −75% and the mix counts them as mixed. Task 4 pins it in the model; Task 6 pins the generated pass.
2. **A blockade, then its end.** Levels leave at once into `away`, the target is kept, no pace is spent, and they come back at once when the site serves again. Task 4 (model) and Task 6 (script).
3. **A base captured by a country without In-Situ Resource Utilization.** Its old owner's mix modifiers come off at the new owner's next monthly pulse. Task 5 pins the widened gate and the strip-only branch.
4. **Every site losing money.** Nothing moves under the checkbox, and new levels go by grade. Task 4 (model) and Task 6 (script).
5. **Switching the checkbox off and on within a month.** No more levels move that month than the pace. Task 4 (model) and Task 7 (the scripted GUI never moves levels itself).

---

### Task 1: Ground types and the site map

**Files:**
- Create: `scripts/generators/ebase_ground.py`
- Test: `test_ebase_ground.py`

**Interfaces:**
- Produces: `GOODS: tuple[str, ...]`, `BASE_PRICE: dict[str, int]`, `TYPES: tuple[str, ...]`, `COMPOSITION: dict[str, dict[str, float]]`, `GROUND: dict[str, str]` (place key to type, `near_earth` included), `PLACES: tuple[str, ...]` (`near_earth` first, then sites in `Site.index` order), `BASKET: dict[str, float]` (the Asteroid Mine's outputs), `shares(outputs: dict[str, float]) -> dict[str, float]` (value shares at base prices), `mix(type_: str) -> dict[str, float]` (normalized, fractions), `grade(place: str) -> float` (fraction; near_earth 0), `score(place: str, good: str) -> float` (`(1 + grade)(1 + mix) − 1`).

- [ ] **Step 1: Write the failing tests** in `test_ebase_ground.py`, class `GroundTypes`:
  - `test_every_place_has_a_type`: `set(GROUND) == {"near_earth"} | {s.key for s in gss.SITES}` and every value is in `TYPES`.
  - `test_each_mix_averages_to_zero`: for each type, `abs(sum(shares(BASKET)[g] * mix(t)[g] for g in GOODS)) < 1e-12`.
  - `test_every_derived_grade_is_the_site_s`: for each place, `sum(shares(BASKET)[g] * score(p, g)) == grade(p)` within 1e-12.
  - `test_rounded_mixes_match_the_spec`: `round(100 * mix(t)[g])` equals the Global Constraints' rounded table for all 49 cells.
  - `test_base_prices_match_the_goods_files`: `BASE_PRICE` equals each good's `cost` in the goods files (read as `test_deep_sea_rebalance._Data` reads prices).
  - `test_mixed_is_the_basket`: `mix("mixed")` is all zeros.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest test_ebase_ground.py -q`. Expected: FAIL, `ModuleNotFoundError: scripts.generators.ebase_ground`.
- [ ] **Step 3: Implement `ebase_ground.py`** with the constants of Global Constraints and the functions above. `mix` is `COMPOSITION[t][g] / Σ_g shares(BASKET)[g] × COMPOSITION[t][g] − 1`. `grade` reads `gen_solar_sites.SITES[...].ebase_grade / 100`. No file I/O in this module except the PM reader of Task 2.
- [ ] **Step 4: Run the tests.** Expected: 6 passed.
- [ ] **Step 5: Commit** `git add scripts/generators/ebase_ground.py test_ebase_ground.py && git commit -m "Extraplanetary Base ground types: the seven types and the site map"`.

### Task 2: The shared basket

**Files:**
- Modify: `common/production_methods/extra_pms.txt` (`pm_regolith_processing`, `pm_space_mine`, `pm_space_colony_mining`, `pm_self_replicating_miners`, and the note above `pm_space_mine`)
- Modify: `scripts/generators/ebase_ground.py` (PM reader)
- Modify: `test_deep_sea_rebalance.py`
- Test: `test_ebase_ground.py`

**Interfaces:**
- Consumes: Task 1's `GOODS`, `BASE_PRICE`, `BASKET`, `shares`, `mix`, `TYPES`.
- Produces: `MethodGoods = NamedTuple("MethodGoods", [("outputs", dict[str, float]), ("inputs", dict[str, float])])` and `base_methods() -> dict[str, MethodGoods]`, every method in `pmg_base_building_space_mine` with its `workforce_scaled` goods lines, read with `paradox_file_parser`.

- [ ] **Step 1: Write the failing tests** in `test_ebase_ground.py`, class `Basket`:
  - `test_mining_methods_share_the_basket`: for each method in `base_methods()` whose outputs are a subset of `GOODS`, every `shares(outputs)[g]` is within 0.0001 of `shares(BASKET)[g]`.
  - `test_every_type_earns_base_profit_at_base_prices`: for each such method and type, `Σ_g out × price × (1 + mix) − Σ_i in × price` is within 0.1% of the method's base profit.
  - `test_regolith_output_value_is_unchanged`: Regolith Processing's output value is 16,600 within 0.005.

  In `test_deep_sea_rebalance.py`: rename `test_era_11_outputs_each_at_least_the_asteroid_mine_but_tech_critical` to `test_era_11_outputs_each_at_least_the_asteroid_mine_but_tech_critical_and_glass`, with the exception set `{ASTEROIDS_LEAD, "glass"}` and a docstring line giving § 7's reason for glass. The Conductive floor (`MIN_CONDUCTIVE_SHARE`) and four-times tests stay unchanged and must pass.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest test_ebase_ground.py test_deep_sea_rebalance.py -q`. Expected: the Basket tests fail on today's outputs.
- [ ] **Step 3: Edit the four methods' outputs** to the Global Constraints' basket and rewrite the note above `pm_space_mine`: the 2026-11-21 move of 7.5% from Tech-Critical Metals to Glass and Plastics at equal value, why (the bases oversupply Tech-Critical Metals 1.5 times over in the game behind the 2026-11-15 change), and that Conductive Metals keep their tenth. Leave the cost comments to `pm_costs`: run `.venv/bin/python pm_costs.py` from the worktree (a `POST /reload` would regenerate the main checkout, not the worktree).
- [ ] **Step 4: Run the tests and** `.venv/bin/python -m pytest test_production_methods*.py test_deep_sea_rebalance.py -q`. Expected: all pass, Regolith Processing's £1,600 and 2.0 included.
- [ ] **Step 5: Commit** `"Extraplanetary Base: one basket of seven goods for the four mining methods"`.

### Task 3: The mix modifiers and their registration

**Files:**
- Modify: `common/static_modifiers/space_race_modifiers.txt`
- Modify: `common/modifier_type_definitions/mod_entity_modifier_types.txt` (`# === Goods ===` section)
- Modify: `scripts/generators/gen_nation_tab.py` (the registry), then re-run it
- Modify: the modifiers' loc file (where `sr_ebase_room_bonus` is localized)
- Test: `test_ebase_ground.py`, `test_nation_tab.py`

**Interfaces:**
- Produces: static modifiers `sr_ebase_mix_<good>_bonus` (`goods_output_<good>_mult = 0.01`) and `sr_ebase_mix_<good>_penalty` (`= -0.01`) for the seven goods, with the icon `sr_ebase_room_bonus` uses.

- [ ] **Step 1: Write the failing test** `Modifiers.test_fourteen_unit_modifiers`. Each of the 14 blocks exists with exactly its one line at ±0.01. `goods_output_lead_mult` has an entry in `mod_entity_modifier_types.txt` shaped like `goods_output_glass_mult`'s (`color = good`, `percent = yes`). Each modifier has a loc name, "Extraplanetary Base Ground", and a `_desc` saying it applies on top of Extraplanetary Base Room, which carries the grade (§ 9.5).
- [ ] **Step 2: Run it.** Expected: FAIL.
- [ ] **Step 3: Add the blocks, the display entry, the loc, and** `"sr_ebase_mix_*"` beside `"sr_ebase_room_*"` in `gen_nation_tab.py`'s `NOT_ON_COUNTRY`-style list (they sit on buildings). Run `.venv/bin/python scripts/generators/gen_nation_tab.py` and `python3 organize_loc.py`.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest test_ebase_ground.py test_nation_tab.py -q` and `.venv/bin/python scripts/run_audits.py modifier_field_audit loc_coverage_audit`. Expected: pass, no new flags.
- [ ] **Step 5: Commit** `"Extraplanetary Base: the fourteen ground mix modifiers"`.

### Task 4: The month, in Python

The model is the reference for Task 6's script: each rule of § 8.2 to § 8.5 written once, testably.

**Files:**
- Modify: `scripts/generators/ebase_ground.py`
- Test: `test_ebase_ground.py`

**Interfaces:**
- Consumes: Task 1's `PLACES`, `GROUND`, `grade`, `mix`; Task 2's `base_methods`.
- Produces:
  - `@dataclass class BaseState: at: dict[str, int]; target: dict[str, int]; away: dict[str, int]; over: int; manual: bool; placed: bool`
  - `profit_a_level(place: str, method_shares: dict[str, float], price_rel: dict[str, float]) -> float`: § 8.3's formula; `price_rel` is the signed premium per good, inputs included (0 = base price).
  - `yardstick(method_shares) -> float`: the methods' profit a level at grade 0 and base prices.
  - `month(state, *, room: dict[str, int], serves: dict[str, bool], built: int, queued: int, profit: dict[str, float], yard: float) -> BaseState`: § 8.2's steps 1 to 5 in order.
  - `forecast(state, *, room, profit, yard) -> BaseState`: the checkbox's rule run to where it stops, unpaced, for the "If prices hold" row (§ 9.1).
  - `mix_now(state) -> tuple[float, dict[str, float]]`: `T` and `D(g)` (§ 5.2), fractions.

- [ ] **Step 1: Write the failing tests**, class `Month`. Each builds a state and asserts the next:
  - `test_first_month_places_everything_at_once`: `placed=False`, 150 built, Psyche (300) and Ceres (200) held, base prices: all 150 at Psyche, `placed` true.
  - `test_checkbox_moves_at_the_pace`: 150 at Psyche, profits Ceres 11,835 and Psyche 9,594 (§ 9.1's sketch), yardstick 7,250: one month moves exactly 4 to Ceres.
  - `test_checkbox_stops_inside_the_margin`: a gap under 0.05 × yardstick moves nothing.
  - `test_never_to_a_losing_site`: every profit negative: nothing moves; 10 new levels go by grade.
  - `test_by_hand_moves_toward_targets_at_the_pace`: `manual`, targets Psyche 50 and Ceres 100, at Psyche 150: 4 move, to Ceres.
  - `test_level_with_no_target_stays`: `manual`, targets summing below `at`: the excess stays where it works.
  - `test_blockade_and_return_are_at_once`: Psyche stops serving: its 150 go to `away` and to Ceres (or past the room) in one month, with no pace spent; it serves again: all 150 back in one month; Psyche's target unchanged throughout.
  - `test_overflow_moves_into_new_room_at_once`: 400 built, room 250, then a new 200-room site: 150 leave `over` in one month.
  - `test_more_levels_than_room`: nothing moves; `mix_now` counts `over` at −75% as mixed.
  - `test_toggling_gains_nothing`: a month run with `manual` flipped on and back off around it moves no more than `ceil(L/48)`.
  - `test_lost_levels_come_off_overflow_first`: 400 built, room 250, then 350 built: `over` falls by 50 and `at` doesn't change.
  - `test_forecast_is_where_the_checkbox_stops`: from § 9.1's sketch state, `forecast` puts all 150 at Ceres, and with the gap under the margin it moves nothing.
  - `test_one_type_base_carries_the_type_mix`: all levels on rocky sites of different grades: `D(g) == mix("rocky")[g]` within 1e-12.
- [ ] **Step 2: Run them.** Expected: FAIL, names undefined.
- [ ] **Step 3: Implement** the functions. Place order is by profit under the checkbox and by grade with it off (ties by `PLACES` order). New levels go first to places below their target (by hand) or to the best place with room that makes money (checkbox), then by grade, then past the room. A move pass picks one source and one destination, moves `min(pace left, source excess, destination free room)`, and repeats until the pace is spent or no pair qualifies.
- [ ] **Step 4: Run the tests.** Expected: all pass.
- [ ] **Step 5: Commit** `"Extraplanetary Base: the month's rules as a Python model"`.

### Task 5: Generated values, the two layers on today's order, the refresh

**Files:**
- Create: `scripts/generators/gen_ebase.py`, writing `common/script_values/sr_ebase_generated.txt` and `common/scripted_effects/sr_ebase_generated.txt`
- Modify: `scripts/generators/gen_solar_sites.py` (remove `sr_ebase_fill` and `sr_ebase_next_fill` rendering; keep `ebase_tiers`)
- Modify: `common/scripted_effects/sr_colony_module_effects.txt` (`sr_ebase_refresh`; the self-check)
- Modify: `common/on_actions/space_race_on_actions.txt` (the refresh's gate)
- Modify: `server/post_load.py` (register `gen_ebase` right after `gen_solar_sites`), `docs/auto_generated_files.md`, `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS`)
- Modify: `test_solar_sites.py` (its `sr_ebase_fill` and refresh assertions move to the new file's names)
- Test: `test_ebase_assignment.py`

**Interfaces:**
- Consumes: Tasks 1, 2 and 4.
- Produces (script values, country scope): `sr_eb_room_<k>` (room serving us now; `near_earth` 10 with `asteroid_mining`), `sr_eb_grade_<k>` (percent), `sr_eb_price_rel_<good>` for the seven goods and every input of the base methods (read as `st_res_grain_price_rel` is: `market = { mg:<good> = { add = market_goods_pricier } } min = 0` less the cheaper read), `sr_eb_share_<pm>` (levels on that method ÷ levels), `sr_eb_margin_<type>` (£ a week a level at grade 0, the generator baking `out × price × (1 + mix)` into constants), `sr_eb_profit_<k>` (`(1 + grade) × margin of its type`), `sr_eb_yardstick`, `sr_eb_pace` (`sr_ebase_levels / 48`, `ceiling = yes`, `min = 1`; check `ceiling` with `/engine-docs` first and use `round_up` or a floor plus one if it isn't there).
- Produces (effects, country scope): `sr_eb_fill_by_grade` (today's order into `var:sr_eb_at_<k>` and `var:sr_eb_over`), `sr_eb_compute_mix` (into `var:sr_ebase_grade` as today, `var:sr_ebase_mix_<good>` the signed `D(g)` in percent, and `var:sr_ebase_mix_<good>_units` its absolute value), `sr_eb_apply_mix` (`every_scope_state` → `every_scope_building` with `is_building_type = building_space_mine`: remove all 14, then add the bonus where the signed value is above 0 and the penalty where it is below, each at `multiplier = root.var:sr_ebase_mix_<good>_units`), `sr_eb_strip_mix` (removal only).

- [ ] **Step 1: Write the failing tests** in `test_ebase_assignment.py`:
  - `test_every_place_has_room_grade_and_profit_values`: one each for all 41 places.
  - `test_margins_name_every_base_method`: each `sr_eb_margin_<type>` reads `sr_eb_share_<pm>` for every method `base_methods()` returns.
  - `test_margin_constants_match_the_model`: at zero premiums, each `sr_eb_margin_<type>`'s constant sum equals `profit_a_level` at grade 0 within £0.01.
  - `test_refresh_removes_before_it_adds`: in `sr_ebase_refresh`, `sr_eb_strip_mix` precedes `sr_eb_apply_mix`.
  - `test_gate_reaches_captured_bases`: the on_action's limit is an `OR` of `has_technology_researched = in_situ_resource_utilization` and `any_scope_building = { is_building_type = building_space_mine }`, and without the technology the refresh only strips.
  - `test_races_only_strips`: with `sr_colonies_contested_enabled` false (Races Only, or the rule switched mid-game), the refresh strips the mix and adds none, and leaves the `sr_eb_*` counts as they are (§ 8.8: a rule switched off pauses).
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Write `gen_ebase.py`** (a `main()` and a `--check` flag, as `gen_solar_sites` has). Rewrite `sr_ebase_refresh` as: strip; if the room rule is on and we have the technology, `sr_eb_fill_by_grade`, `sr_eb_compute_mix`, the two room modifiers as today, `sr_eb_apply_mix`, `sr_ebase_next_fill`'s successor. Add the self-check `TE_SELF_CHECK ebase_mix` beside `sr_mod_fabrication_self_check`. Once a game, on the first country with a base and a nonzero Tech-Critical mix, a month after arming, it compares one base building's `modifier:goods_output_tech_metals_mult` with `var:sr_ebase_mix_tech_metals / 100` within 0.005. It logs both numbers, and skips a country whose state holds a unique mine that changes the read. Add a row to the Self-checks table in `docs/testing/solar-colonies-playtest.md`. Register the generator and the files.
- [ ] **Step 4: Run** `.venv/bin/python scripts/generators/gen_ebase.py`, then `.venv/bin/python -m pytest test_ebase_assignment.py test_solar_sites.py test_ebase_ground.py -q`, then `.venv/bin/python scripts/preflight.py --changed`. Expected: all pass. The generated files carry the AUTO-GENERATED header.
- [ ] **Step 5: Commit** `"Extraplanetary Base: the ground mix on every base building, on today's order"`.

### Task 6: Where the levels work, in script

**Files:**
- Modify: `scripts/generators/gen_ebase.py`
- Modify: `common/scripted_effects/sr_colony_module_effects.txt` (`sr_ebase_refresh` calls the month instead of the grade fill)
- Test: `test_ebase_assignment.py`

**Interfaces:**
- Consumes: Task 4's rules (the script must do what `month` does), Task 5's values.
- Produces (country variables, § 8.1): `sr_eb_at_<k>`, `sr_eb_target_<k>`, `sr_eb_away_<k>`, `sr_eb_over`, `sr_eb_manual`, `sr_eb_placed`, and the move record `sr_eb_move_from`, `sr_eb_move_to` (place index), `sr_eb_move_began` (`te_history_month_index`), `sr_eb_move_carried`, `sr_eb_last_from`, `sr_eb_last_to`, `sr_eb_last_began`, `sr_eb_last_ended`. Effects: `sr_eb_month` (§ 8.2's steps 1 to 5), `sr_eb_place_new` (local `sr_eb_left` levels in the mode's order), `sr_eb_move_pass` (one source and destination pair), `sr_eb_next_place` (`var:sr_ebase_next_place`, the index the next level goes to, −1 past the room).

- [ ] **Step 1: Write the failing tests**:
  - `test_month_runs_the_steps_in_order`: in `sr_eb_month`, displacement, return, gained and lost, and the move loop appear in that order.
  - `test_move_loop_is_bounded_by_the_pace`: a `while` whose limit reads `local_var:sr_eb_pace_left > 0`, with `count` at most 41 (`<int>` effects take no script value; memory: use `while = { count = … }`).
  - `test_checkbox_margin_reads_the_yardstick`: the move pass's limit compares the profit gap with `sr_eb_yardstick` × 0.05, and requires the destination's profit above 0.
  - `test_every_place_in_every_pass`: each of the 41 places appears in displacement, return, placement and both move searches.
  - `test_first_placement_is_unpaced`: with `sr_eb_placed` unset, the month places all levels and sets it.
  - `test_variables_on_the_country`: no `set_variable` in the generated effects targets a state or a building (a revolution's winner keeps country variables).
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Generate** the effects, following Task 4's `month` rule for rule. Comment each block with the § it implements. Run `python3 scripts/lessons.py while` and `python3 scripts/lessons.py local_var` before writing the loops.
- [ ] **Step 4: Run** the tests, `.venv/bin/python scripts/run_audits.py` (expect no new flags; `variable_guard_audit` and `script_argument_audit` matter most here), and a `POST /reload?audits_only=true` against a server started from the worktree on another port. Read its `warnings`.
- [ ] **Step 5: Commit** `"Extraplanetary Base: where the levels work, by hand or by the checkbox, paced"`.

### Task 7: The checkbox, the buttons, the forecast and the notice

**Files:**
- Modify: `common/scripted_guis/sr_colony_sguis.txt`
- Modify: `scripts/generators/gen_ebase.py` (forecast and totals effects)
- Modify: `common/messages/extra_messages.txt` and the messages' loc
- Test: `test_ebase_assignment.py`

**Interfaces:**
- Consumes: Task 6's variables and `sr_eb_month`.
- Produces: `sr_ebase_auto_sgui` (no scopes: off sets every `target` to its `at` and sets `sr_eb_manual`; on clears both), `sr_ebase_assign_sgui` (`scope:site` the place index, 0 for near-Earth; `scope:op` 1 = +5, 2 = −5, 3 = +25, 4 = −25; when the checkbox is on, a click switches it off first), `sr_eb_totals` (into `var:sr_eb_now_<good>`, `var:sr_eb_now_profit`, and `var:sr_eb_end_<good>`, `var:sr_eb_end_profit` from the forecast with the checkbox on or the targets with it off; players only), message `sr_ebase_move_notice` (`type = country`, `notification_type = feed`, as `banking_eliq_wound_down_notice`).

- [ ] **Step 1: Write the failing tests**:
  - `test_buttons_never_move_levels`: neither sgui's effect writes `sr_eb_at_*`, so a click moves no level and toggling gains nothing.
  - `test_plus_needs_an_unassigned_level`: `sr_ebase_assign_sgui`'s `is_valid` for ops 1 and 3 requires the targets' sum below built plus queued levels and the place below its room. Each condition is a `custom_tooltip` (the button carries its reasons).
  - `test_notice_threshold_and_throttle`: the notice fires only with `sr_eb_move_carried` at or above 5% of `sr_ebase_levels`, for a type pair other than the last notice's, and at least 12 months after it.
  - `test_totals_skip_the_ai`: `sr_eb_totals` is called under `is_ai = no`.
  - `test_only_the_checkbox_sets_manual`: `sr_eb_manual` is set nowhere but `sr_ebase_auto_sgui` and the switch-off in `sr_ebase_assign_sgui`, and both are `is_shown` only for `is_ai = no` (the AI always runs the checkbox).
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Call `sr_eb_totals` from the refresh and from both sguis' effects. Run `python3 scripts/lessons.py scripted_gui` first. A tooltip walks the effect each frame, so guard reads of variables set in the same body (`tooltip_walk_variable_audit`).
- [ ] **Step 4: Run** the tests and `.venv/bin/python scripts/run_audits.py tooltip_walk_variable_audit silent_variable_audit loc_coverage_audit`. Expected: pass, no new flags.
- [ ] **Step 5: Commit** `"Extraplanetary Base: the checkbox, the assignment buttons, the forecast and the move notice"`.

### Task 8: The Bases view

**Files:**
- Modify: `gui/journal_entry_widgets/space_race_widget.gui`: a fifth `te_sr_colony_view_button` (`sr_colony_view` value `bases`, shown with `sr_disp_ebase_shown`; add `'bases'` to the People button's `enabled` list); the view's section above the rows; the `te_sr_colony_row` blocks the view uses
- Modify: `scripts/generators/gen_solar_sites.py` (`_colony_row`: the Bases overrides, from a `gen_ebase.colony_row_overrides(site) -> list[str]` helper; the listing rule lists a held site in Bases as Defenses does, occupied included)
- Modify: `common/script_values/space_race_display_values.txt` (the `sr_disp_eb_*` display values)
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_space_race_layout.py`, `test_space_race_labels.py`, `test_ebase_assignment.py`

**Interfaces:**
- Consumes: Tasks 6 and 7.
- Produces: the view as § 9.1 sketches it. Above the rows: the checkbox (`checkbutton`, `sr_ebase_auto_sgui`), the levels line, the move line (states: moving with the gap in percent; every site losing money; no gap worth a move; moving toward our assignments with levels left and months; the last move), the totals table (seven goods, icons first, and profit a week; rows "Now" and "If prices hold" or "At our assignments"), and the near-Earth row (place 0). Each box: the type word and grade; levels over room with "→ N" while moving; − and +; profit a level; output a level for the method most levels run; a not-serving line ("Blockaded: N levels working elsewhere until it is freed", the occupied variant).

- [ ] **Step 1: Write the failing tests**:
  - `test_space_race_layout.py`: the view button exists with value `bases`. Every colony row has the Bases overrides, the type word naming `sr_ground_<type>` of its own site and both buttons calling `sr_ebase_assign_sgui` with its `Site.index`. The near-Earth row uses index 0.
  - `test_space_race_labels.py`: the widest box line (seven goods at five digits) and the move line fit the 480 column, measured as the other views are. Add the new figures to the bounds table.
  - `test_ebase_assignment.py`, `test_output_figures_use_the_model`: each box's output-a-level display value for a good equals `BASKET` scaled by the method × `(1 + score)`, generated from `ebase_ground`.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Build the view** to `docs/guides/gui_style_guide.md` (rules 3, 5, 6) and `.claude/rules/gui.md`. Write the loc with the `event-text` skill's style. Run `python3 organize_loc.py`.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest test_space_race_layout.py test_space_race_labels.py test_ebase_assignment.py -q` and the GUI audits (`.venv/bin/python scripts/run_audits.py`). Expected: pass. Add a play-test item for the view's look to `docs/testing/solar-colonies-playtest.md`.
- [ ] **Step 5: Commit** `"Extraplanetary Base: the Bases view"`.

### Task 9: The other readings

**Files:**
- Modify: `scripts/generators/gen_solar_sites.py` (`_site_row`'s `site_bases`: the type word after the figure; its hover per type)
- Modify: `scripts/generators/gen_ebase.py` (a custom loc file `common/customizable_localization/sr_ebase_generated_custom_loc.txt` naming a place from an index variable, for the move line, the last move, the notice and the Base Room cell)
- Modify: `common/script_values/space_race_display_values.txt` and the Base Room cell in `space_race_widget.gui` ("next: <place>", hover with type, grade and profit a level; −75% past the room as today)
- Modify: loc: `sr_ground_<type>` (the word) and `sr_ground_<type>_desc` (all seven figures, from the rounded table) for the seven types; `je_space_race_widget_ss_bases_tt_<type>` (replacing the shared `je_space_race_widget_ss_bases_tt`); the 40 `je_space_race_widget_bases_tt_<site>` rewritten to splice `$sr_ground_<type>_desc$` and state the grade; `concept_sr_base_grade_desc` rewritten and a new concept `concept_sr_ground_type` (§ 9.6); the Help page's How Solar Colonization Works gains a line per type and the checkbox's rule; `sr_site_name_near_earth`
- Test: `test_ebase_assignment.py`

The 40 site hovers stay hand-written, each splicing its type's key (§ 9.6); the test below keeps them in step.

**Interfaces:**
- Consumes: Task 1's rounded figures, Task 6's `sr_ebase_next_place` and move record.

- [ ] **Step 1: Write the failing tests**:
  - `test_type_desc_figures_match_the_model`: every `sr_ground_<type>_desc` states the seven rounded figures of `mix(type)`, in the goods' order.
  - `test_site_hover_splices_its_own_type`: each `je_space_race_widget_bases_tt_<site>` contains `$sr_ground_<GROUND[site]>_desc$` and no other type's key.
  - `test_help_lines_cover_every_type`: the Help page loc names all seven types.
  - `test_custom_loc_names_every_place`: the custom loc has 41 entries keyed by index, 0 to 40.
  - In `test_space_race_labels.py`: replace the `sr_disp_ebase_next_grade` bound with the next place's name at the longest place name, measured in the Base Room cell's column.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Write the loc and the custom loc.** Use the `event-text` skill for the prose; name goods with `$iron$`-style splices, never spelled out (single-source names).
- [ ] **Step 4: Run** the tests, `python3 organize_loc.py`, and `.venv/bin/python scripts/run_audits.py loc_coverage_audit`. Expected: pass.
- [ ] **Step 5: Commit** `"Extraplanetary Base: ground types in Solar System, the Base Room cell, concepts and the Help page"`.

### Task 10: Docs, the player guide, the PR

**Files:**
- Modify: `docs/systems/mod_systems/space_race.md` (*Colony modules and Extraplanetary Base room*: the types, the month, the checkbox, the view, the self-check), `docs/guides/production_methods.md` or wherever the base methods' figures are (`git grep -l pm_space_mine docs/`)
- Modify: `docs/player_guide/16-space.md` (§ Extraplanetary Base room: a types table with each type's sites, § 6.4's patterns in a few sentences, a subsection on the Bases view and the checkbox), `docs/player_guide/02-timeline.md` (Regolith Processing's goods), then `.venv/bin/python scripts/build_player_guide.py`
- Modify: `docs/testing/solar-colonies-playtest.md` (a section: § 2's acceptance test; a large base under a glut watched for a back-and-forth; a blockade and its return; the building's output tooltip at one site reading base × (1 + T) × (1 + D))
- Modify: `docs/superpowers/README.md` (the spec's and the plan's status: built in this PR)

- [ ] **Step 1: Write the docs.** Follow `docs/player_guide/STYLE.md`, at the depth of the chapter's peers.
- [ ] **Step 2: Rebuild the PDF** and run the guide checks (`.venv/bin/python scripts/preflight.py --only docs`: `guide-style` and `guide-pdf`). Expected: pass.
- [ ] **Step 3: Run the full preflight**, `.venv/bin/python scripts/preflight.py` (about 8 minutes). Expected: green.
- [ ] **Step 4: Commit** `"Extraplanetary Base ground types: docs and the player guide"`, push, and open the PR against `main`. The description has the summary, "Intended balance" (§ 7's Deep-Sea paragraph), "Output changes by method" (§ 7, for the release notes), the self-check and the play-test items, a "Player guide" line naming `16-space.md` and `02-timeline.md`, and `Closes` for any issue it settles (not #1948).
- [ ] **Step 5: Get an independent review of the branch** before handing it to the owner. A fresh reviewer reads the diff against the spec, especially Task 6's script against Task 4's model. Don't self-merge.
