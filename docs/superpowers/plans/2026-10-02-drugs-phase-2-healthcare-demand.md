# Drugs phase 2: Healthcare demand and plantation penalties

**Status:** not started. A brief for a local Claude Code session on the owner's machine, which has the game install and saves. Read it whole before starting.
**Phase 1:** [jakeOmega/Vic3TimelineExtended#652](https://github.com/jakeOmega/Vic3TimelineExtended/pull/652) (branch `claude/youthful-turing-sbvv47`). If it hasn't merged, branch from it and open the phase-2 PR with `--base main` (CLAUDE.md § "Stacked PRs must target `main`").
**Outcome:** pops from about wealth 25 buy a small amount of Drugs as healthcare, and the amount levels off. Health and consumer-protection institutions shrink opium plantations. Every threshold comes from wealth distributions measured in real saves, not from guesses.

## 0. What is settled

The owner agreed these on 2026-10-02. Don't reopen them without asking.

- **One good.** Drugs are vanilla's `opium` (`localization/english/replace/timeline_extended_override_l_english.yml`). We are not splitting off a separate Medicine good. Its couplings to vanilla content are few, and each has a fix. They are listed in `docs/systems/mod_systems.md` § "Drugs (vanilla `opium`) and Pharmaceutical Industries"; read that section first.
- **What phase 1 shipped.**
  - Pharmaceutical Industries unlock at `pharmaceuticals` (era 2) for 800 construction and get a six-method ladder. Alkaloid Extraction has a wage breakeven of 0.05, a quarter of a plantation's 0.20. Precision Medicine reaches 2.40. The design rule is in the comment above `pm_pharma_alkaloid_extraction` in `common/production_methods/extra_pms.txt`.
  - The opium Mechanized Farm is cut to 55 Drugs.
  - The building can't be built under a Drugs ban.
  - The Opium Trade (`je_opium`) closes on 23 January 1912 (`common/journal_entries/te_vanilla_opium.txt`).
  - Field Hospitals take Drugs again.
- **The shape the owner wants for demand** (their words, paraphrased): "very low below SoL ~25, and it never rises very high per pop, so the ultra-wealthy don't buy orders of magnitude more than those at SoL 30. You don't see much demand until a lot of pops are fairly rich: 1950s and beyond."
- **Buy packages are keyed by wealth level, not SoL.** A pop's SoL tracks its wealth level (`docs/guides/scripting_best_practices.md`, the paragraph on `*_standard_of_living_add`), so the owner's "SoL 25" means wealth 25.

## 1. Measure first

None of the numbers in § 2 should be fixed until this step is done. Nothing in the repo records what wealth levels pops reach in each era.

**Goal.** Get the share of population at wealth 15, 20, 25, 30, 35 and 40 or more. Get it for the world and for about six countries: Great Britain, the USA, a German state, Qing/China, India and one poor country. Take it at about 1880, 1910, 1950, 1980 and 2010, ideally from one observer campaign. In the same saves, record the Drugs price in a few markets and where the supply comes from (plantations vs Pharmaceutical Industries).

**How.** Saves are binary, and the pop object's token names are unknown (see `scripts/analysis/save_country_probe.py`'s header), so read wealth with script instead:

1. Add a console-only event, `events/te_debug_drugs_events.txt`, modelled on `events/te_debug_un_events.txt`. Copy its `# REVIEWED` opener comment, its `event_image`, and its loc pattern, because the orphaned-event and event-image audits run `--strict` in CI.
2. For each country, the event sets variables such as `te_dbg_drugs_w25` to the share of its population at that wealth or above. Use a script value of the shape `common/script_values/resettlement_values.txt` already uses: `every_scope_pop = { limit = { wealth >= 25 } add = total_size }`, divided by `total_population`. Check first that `every_scope_pop` resolves in country scope (`/engine-docs/...` on the mod state server). World totals go in global variables.
3. Fire it from the console with `event te_debug_drugs.1` in each save, save again, and read the results with `scripts/analysis/save_country_probe.py <save> --var '^te_dbg_drugs_'`.
4. Write the results to `docs/testing/drugs-wealth-probe-results-<date>.md` (precedent: `docs/testing/tax-code-probe-results-2026-10-02.md`). Show the owner the table before choosing thresholds.

**Do the phase-1 in-game checks at the same time** (from #652):
- whether Qing builds Pharmaceutical Industries early;
- that The Opium Trade's 1912 failure shows its tooltip and doesn't come back;
- that the six `cat_flask_gold_p*` icons look right on the ladder.

## 2. The Healthcare pop need

**Files.**
- `common/pop_needs/extra_pop_needs.txt`: add `popneed_healthcare` with `default = opium` and one entry, `goods = opium`, `weight = 1`, `max_supply_share = 1.0`, `min_supply_share = 0.0`. Recommend Drugs only. Doctors and hospitals are already part of the Services need, and a services entry would split the demand by market share, not by wealth.
- **Leave out `obsession_demand_min` / `obsession_demand_mult`.** Vanilla's staple needs omit them. Intoxicants and leisure declare them, which is how Han's opium obsession multiplies opium demand there. Leaving them out should keep the obsession from inflating healthcare; confirm it in game (§ 4).
- `pop_needs_curves.py`: add `healthcare_need(wealth_level)` and register it in `NEED_CURVES` (around line 100). `generate_buy_packages` already inserts a need a wealth block lacks. It extrapolates wealth 100–200 with a power-law fit over 90–99, so confirm those rows stay at the cap.
- Localization: `popneed_healthcare` in `localization/english/te_goods_and_needs_l_english.yml`. Vanilla localizes each need with its name key only, and the mod's Convenience and Tourism needs are the precedent.
- `common/buy_packages/00_buy_packages.txt` is generated. Never hand-edit it; it comes from the full `/reload` in § 4.

**Starting curve** (rescale it from § 1's measurements). Totals are from the committed buy packages, valuing each need at its default good's base price:

| Wealth | Total spending | Intoxicants | Proposed healthcare | Share of spending |
|---|---|---|---|---|
| 20 | 28,920 | 75 | 0 | 0 |
| 25 | 51,790 | 120 | ~15 | 1.4% |
| 30 | 97,500 | 216 | ~40 | 2.1% |
| 40 | 367,170 | 216 | 60 (cap) | 0.8% |
| 50+ | 1.2M+ | 216 | 60 | <0.3% |

Intoxicants already has the owner's shape: it reaches 216 by wealth 30 and stays flat to 99, while total spending roughly doubles every five levels. Real-world drug spending is about 1–2% of consumption, so a peak near wealth 30 lands in the right place. For scale, intoxicants' 216 is split between liquor (weight 1.0), tobacco (0.9), Drugs (0.75) and wine (0.25). By weight alone Drugs get about 55, so a cap of 60 roughly doubles what a rich pop buys.

**Decide with the owner whether to lower Drugs' weight in intoxicants** (`REPLACE:popneed_intoxicants`). Doing so keeps total Drugs demand near today's level while moving it toward medicine.

**Interactions to check:**
- **Qing's Opium Crisis ban** blocks healthcare in Qing's market. It should cost little at Qing's wealth levels; confirm that with § 1's numbers.
- **Price spikes.** If healthcare demand arrives before Antibiotic Fermentation (era 7) is widespread, Drugs prices spike and plantations profit. Compare the Drugs price in the 1950 and 1980 saves before and after.
- **SoL.** An unmet need lowers SoL. Check that rich countries' SoL doesn't fall when Drugs are short, and that the AI builds Pharmaceutical Industries in response.

## 3. Plantation penalties

**Modifier.** Use `building_opium_plantation_throughput_add`. It is a vanilla modifier type that vanilla's own `opium_production_modifier` uses at +0.33. A plantation has no inputs, so lost throughput is lost profit, and the AI shrinks the buildings.

**Hooks:**
- **Health-system laws.** Add `institution_modifier` entries to the `INJECT:law_*_health_*` blocks in `common/laws/modified_health_system.txt`. An `INJECT` sums with vanilla's values, which is confirmed in game (`scripting_best_practices.md` § "CONFIRMED: an `INJECT:` block **sums** with vanilla's"). Institution modifiers scale with investment level, so read the level caps before sizing. A starting proposal for the owner: Charitable −2% per level, Private −3%, Public −5%.
- **Ministry of Consumer Protection** (era 6, `consumer_credit`). The mod defines this institution itself (`common/institutions/extra_institutions.txt`, `institution_ministry_of_consumer_protection`), so edit it directly. A starting proposal: −10% per level.

These cut only the enacting country's own plantations. India, Persia and the other exporters rarely enact them and keep exporting until Pharmaceutical Industries undercut them on price. That is intended.

**Optional; ask the owner and keep each in its own PR:**
- **A UN convention** modelled on the 1961 Single Convention on Narcotic Drugs. It is the only hook that reaches exporting countries. See `docs/player_guide/09-united-nations.md` § "UN conventions and agencies" and `test_un_convention_registry.py`.
- **A shortage modifier:** a state pulse reads `market.mg:opium.market_goods_shortage_ratio` and scales a mortality modifier. It must run from a state pulse with one refresh site, per CLAUDE.md's dynamic-modifier rules.

## 4. Validate

- **Reload.** Start the mod state server on a clean tree and run a full `POST /reload`, which runs `pop_needs_curves` and needs the game files. Read `warnings`, `generators_wrote_files` and `parse_failures`. Stage everything the regenerators wrote as one unit; a half-committed `organize_loc` move drops keys.
- **CI.** Run every CI step locally (`.github/workflows/ci.yml`), including `organize_loc.py --check`, the `--strict` audits and `build_player_guide.py --check`.
- **In game:**
  - Load the 1950, 1980 and 2010 saves and check the Drugs price, the healthcare-need satisfaction and the SoL of a rich and a poor country, the number of Pharmaceutical Industries levels, and plantation levels.
  - Compare a Han pop with a non-Han pop at the same wealth to confirm the opium obsession doesn't inflate healthcare demand.
  - Read `debug.log` first, using the `log-triage` skill.
- **Player guide.**
  - `03-economy.md` § "Pop consumption at high wealth": the new need and when it starts.
  - `02-timeline.md` § "Pharmaceutical Industries and Drugs": the plantation penalties.
  - Wherever the health-system laws' effects are listed (check `05-politics.md` and `16-reference.md`).
  - Rebuild the PDF and commit it with the chapters.
- **PR body:** include the "Player guide" line, and the measurement table or a link to it.

## 5. Questions for the owner

1. The final curve: start wealth, cap and the level where it reaches the cap, from § 1's table.
2. Should Drugs' weight in intoxicants come down?
3. The penalty sizes for each health law and for the Ministry of Consumer Protection.
4. Do the UN convention and the shortage modifier go ahead, and in which order?
