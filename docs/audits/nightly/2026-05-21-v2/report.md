# Nightly audit report — 2026-05-21-v2 (manual re-run)

Slice: 15 files / 2499 lines — `laws_and_politics` (14) + `scripted_effects_and_triggers` (1). All targets "never audited" before this run. Dedup: zero open GitHub issues, `open_issues.md` carried no overlapping entries.

## Findings & actions

### Fixed (auto-fix PR)

1. **`common/character_traits/ruler_aptitude_traits.txt:525` — diplomat tier monotonicity bug.**
   `ruler_exceptional_diplomat` (top tier — replaces all lower diplomat traits, gated on GP rank + age 40) gave `country_diplomatic_reputation_add = 3`, *lower* than the tier below it (`ruler_skilled_diplomat` = 5). Every other field doubles cleanly skilled→exceptional (prestige 0.10→0.20, influence 0.1→0.25, infamy −0.10→−0.2, amenability 5→10, pop_attraction 0.05→0.10) and the admin ladder mirrors it (legitimacy 5→10). The `3` is a typo. **Fixed → 10.**

2. **`common/political_movement_pop_support/extra_political_movement_pop_support.txt:9-11` — removed orphaned `movement_support_low_gpd_per_capita`** (follow-up at user request). The factor was referenced by no movement (only the wired sibling `movement_support_high_pollution` survives) and carried a `gpd` typo. Removed the entity and its directly-tied live loc key `POP_LOW_GDP_PER_CAPITA` (`te_miscellaneous_l_english.yml:446`). Left `POP_LOW_GDP_PER_CAPITA_REL` in `te_unused_l_english.yml` untouched — the deliberate revival parking-lot, orphaned independently.

### Flagged then reverted — false positive

- **`common/laws/colonial_empire_law_injections.txt:133-142` — secret_police colonial garrison in `institution_modifier`.** Initially flagged as mis-placed (the five sibling laws use a flat `modifier` block, and the original IF-block precedent in `b359b19` was flat). **The user confirmed this is intentional**: secret_police's colonial garrison contribution is *meant* to scale with `institution_home_affairs` investment rather than apply flat. Change reverted; the file is back to its `main` state. Recorded in agent memory so future audits don't re-flag it.

## Checked clean / non-findings

- **Modifier validity** — all suspect modifier names across the slice (`state_pollution_reduction_health_mult`, `country_state_religion_wages_mult`, `country_loyalism_increases_full_acceptance_mult`, `political_movement_radicalism_from_enactment_disapproval_mult`, the colonial/legislative/cultural-pull/sol-expectations families, dynamic `_institution_<name>_mult` patterns, etc.) validate EXACT via `/modifier-search`.
- **`technocratic_party.txt`** — all 17 referenced ideology IDs exist (mod + vanilla). Join-weight gradient coherent. A few `join_weight` entries for ideologies already excluded by `available_for_interest_group` (ethno_nationalist, communist) are unreachable-but-harmless; not filed.
- **New laws in `extra_laws.txt` (1-600)** — all 13 mod-defined laws have ideology stance coverage in `common/ideologies/{extra_ideologies,modified}.txt`. No systemic missing-stance gap.
- **`law_secret_police` institution check** — it grants `institution_home_affairs`, so the colonial `institution_modifier` is valid and (per user) intentionally investment-scaled. See the reverted false-positive above.

## Observed, deliberately not filed

- **`common/state_traits/te_harbor_traits.txt`** (untracked) — header `# temp, for cheaty game with friend`; deliberate personal content. Note: under `common/` it *will* rsync-deploy to the game. Left to the user.
- **`assassinate_foreign`** (`extra_interactions.txt:59`, `# doesn't work D:`) — player-exposed but non-functional; dates to the **initial commit (2024-03-25)**, long-parked with explicit dev awareness. Treated like other dormant content; not filed as noise.

## Verify
`POST /reload?mod_only=true&audits_only=true` → `status: reloaded`, `warnings: 0`.
