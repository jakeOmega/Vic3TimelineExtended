# Nuclear custody: civil wars, annexation and the first loose warheads — design

## Context

`docs/systems/nuclear_crisis_design.md` §0.10 is the agreed roadmap for nuclear arsenals in civil wars, secession
and annexation. Step 1 (the engine test from saves) is done: `docs/audits/civil_war_inheritance_audit.md` and
`scripting_best_practices.md` § "What a Civil War's Winner Inherits". This document is step 2 (**custody transfer**) and
the first event of step 3 (**"Who Holds the Button?"**). The rest of step 3, step 4 (Budapest path) and step 5 (the
loose-warhead pool's detonation, attribution and recovery) stay in §0.10.

Baseline: `main` at `8744c8f4` (#459 merged).

## Decisions (owner, 2026-09-26)

| Question | Decision |
|---|---|
| Scope | **Everything in step 2**: civil wars both ways, secession, war annexation, diplomatic annexation, formables, any `annex` |
| The fraction lost at a custody change | **Recorded for step 5**: removed from both arsenals, added to a global count and a per-origin count. Nothing detonates yet |
| What a winning revolution's new regime keeps | **Doctrine and investments** (the military establishment). Credibility resets to 50; the old regime's pledges and "defied us" records lapse; the AI re-reviews its posture at once; a human is told |
| Step 3's outbreak event | **In this PR** |
| Striking one's own rebels (2026-09-25, not re-asked) | Allowed at a very high price: legitimacy −50, fading over many years, plus heavy radicalization; repressive laws shrink the radical surge, free-speech laws enlarge it; the AI does it only when losing badly under those laws |

## Engine facts this rests on

Verified (saves, 2026-09-25): the revolution's winner annexes the loser; country variables merge with the **winner's
own values taking precedence**; variable lists and modifiers are not inherited; the loser object is still in the save just
after the win, gone two weeks later.

From vanilla script and the engine docs:
- `on_revolution_start` / `on_secession_start` / `on_revolution_end` / `on_secession_end` have ROOT = the original country,
  `scope:target` = the uprising country. `on_civil_war_won` has ROOT = the winner and fires after `on_revolution_end`.
- Vanilla's `on_secession_end` reads a dead rebel through `scope:target` (`capital.state_region`, "owned by a dead
  country at this point").
- `civil_war_origin_country` links a civil-war country to its origin. `is_country_alive` is false for a country with no
  state. `dp_revolution` mirrors an `annex_country` war goal, so **both** sides of a revolution already pass
  `nd_enemy_threatens_existence` and the Rules of War exception today, at no cost.
- `create_container` without a parent makes a freestanding script container, which outlives any country.

**Not tested, and designed around:** whether a dead-but-undeleted loser resolves through a stored scope variable at
`on_civil_war_won`. Nothing in this design reads a dead country for a value it needs. Every hook `debug_log`s what it
finds (`TE_CIVIL_WAR:` / `TE_CUSTODY:` lines in `debug.log`), so the first civil war in a test game answers the question.

## 1. The arsenal ledger

Every country that holds an arsenal gets one **ledger record**: a freestanding script container tagged `nd_arsenal`,
listed in the global list `nd_arsenal_records`, reached from its owner through the country variable `nd_arsenal_record`.
It holds:

| Variable | Meaning |
|---|---|
| `nd_ar_owner` | the country |
| `nd_ar_count` | its warheads at the last refresh |
| `nd_ar_progress` | its progress toward the next warhead |
| `nd_ar_capital_region` | its capital's state region |
| `nd_ar_at_war` | 1 if it was at war at the last refresh |
| `nd_ar_doctrine`, `nd_ar_authority`, `nd_ar_safeguards`, `nd_ar_hardening` | its posture |
| `nd_ar_loose` | warheads **from this arsenal** that are unaccounted for (step 5's per-origin count) |

`nd_ledger_refresh` writes it: every week from the entry's pulse, every month from the country pulse for any country
with a record, and after every launch (`nd_record_nuclear_use`). A record is created when a country is first armed, and
for both sides of a civil war whose origin is armed.

**Invariant.** Both sides of a civil war hold their own `nuclear_weapon_stockpile` and their own record from the
outbreak on. So the merge never hands a winner the loser's stockpile or record pointer, and no transfer is counted twice.

## 2. The reconcile — one helper for every way an arsenal's owner can end

`nd_custody_reconcile` (no ROOT; safe from any scope) walks `nd_arsenal_records`. A record whose owner no longer
resolves, or is no longer alive, is **settled**:

1. **Successor**: the owner of the most populous live state in `nd_ar_capital_region`. With none, the record waits for
   the next pass.
2. **Loss**: `nd_ar_count × loss rate`, stochastically rounded (§4).
3. The successor's `nuclear_weapon_stockpile` gains the rest. Its record's `nd_ar_loose` gains the loss plus the dead
   record's own `nd_ar_loose` (an origin's count passes to its successor). The global `nd_loose_warheads` gains the loss.
4. The successor gets a hidden country event (`nuclear_custody.3`, so ROOT is the successor): its own record, the entry
   at once if it lacks one, the posture initialiser, the snapped public estimate, and, for a human, the notice
   "The Arsenal Changes Hands" (`.4`, received and unaccounted for). A new regime gets `.5` instead (§3.3).
5. The dead record leaves the list and is destroyed (temporary list → remove → destroy, the covert-network idiom).

Callers: `on_civil_war_won` (after the regime step), `on_secession_end`, `on_wargoal_enforced`, `on_country_formed`,
the mod's own `annex =` sites, and the global `on_monthly_pulse` as the catch-all for every other path (vanilla
diplomatic annexation, formables, event scripts). It is idempotent, so extra calls cost a list walk.

## 3. Civil wars

### 3.1 Shared civil-war hooks (`common/on_actions/te_civil_war_on_actions.txt`)

The audit's cross-cutting repair site, built once for every system:

- **Start** (`on_revolution_start`, `on_secession_start`): the rebel gets `te_cw_origin` = the original country (the
  parent pointer the audit proposed), and each side gets `te_cw_role` (1 original, 2 rebel) for the readability probe.
  Then `nd_custody_on_civil_war_start`.
- **End** (`on_revolution_end`, `on_secession_end`): record the pair in globals (`te_cw_ending_origin`,
  `te_cw_ending_rebel`, `te_cw_ending_kind` 1 revolution / 2 secession) and log both sides' `exists` /
  `is_country_alive`. A secession also reconciles here, since `on_civil_war_won` may not fire for one.
- **Won** (`on_civil_war_won`): `te_civil_war_resolve_sides` saves `scope:te_cw_winner` / `scope:te_cw_loser` and sets
  `te_cw_rebels_won` from the pair. If the pair is missing, it falls back to `te_cw_origin` pointing somewhere other than
  ROOT. It logs whether the loser resolves, is alive, and whether its `te_cw_role` reads (**the engine test**). Then
  `nd_custody_on_civil_war_won`, then clean-up of `te_cw_*` and the globals. The #460–#465 repairs plug in here later.

### 3.2 Outbreak: "Who Holds the Button?" (`nuclear_custody.1`)

If the original country is armed, the rebel gets `nuclear_weapon_stockpile = 0`, its own record, and
`nd_cw_origin_record` (the original's record — what the rebel's winning regime will read). The original gets
`nuclear_custody.1`, whose `immediate` rolls the split once, so every option shows exact numbers:

- **Share** the rebels could seize: `stock × their population share × 1.5 under delegated authority or launch on
  warning × (1 − 0.2 × safeguards)`, stochastically rounded and capped at the stock.
- **Lost** from what is seized: seized × loss rate × 2 (chaos), stochastically rounded.

| Option | Effect |
|---|---|
| **Hold the line** (default) | The rebels take the share less the loss; the loss is recorded against our arsenal |
| **Pull them back** | Readiness goes to Recessed at once and is held there while any civil war of ours lasts (`nd_cw_withdrawn`: every raise greyed, the AI review, the at-war mating and the retaliation paths respect it). The rebels still take half the share under delegated authority (commanders who hold weapons defect with them), less its loss; otherwise nothing |
| **Dismantle them** | Our stockpile goes to 0 and `nuclear_power` comes off; the rebels get nothing and nothing is lost; every other country +10 relations |

AI weights favour pulling back when the rebels would take warheads, holding when they would take none, and dismantling
only under a cautious ruler facing rebels with half the country.

The rebel's share arrives through a hidden event on the rebel (`nuclear_custody.2`, ROOT = rebel): the entry at once,
the posture initialiser (defaults), `nuclear_weapons_program_first_nuke_done = 1`, the snapped estimate; `nuclear_power`
follows on the entry's first pulse.

### 3.3 The end

- **Loyalists win**: the reconcile settles the dead rebel's record to the original country (it holds the rebel capital's
  region again): its warheads come home less the loss.
- **Revolutionaries win** (a new regime), before the reconcile, from `var:nd_cw_origin_record` (a live container, not
  the dead loser):
  - doctrine, authority, safeguards and hardening are the old state's, with both tenures satisfied so the new regime may
    re-choose at once;
  - credibility is 50;
  - pledges and defiance records the old regime held are gone (lists are not inherited); every country's
    `nd_nonuse_pledges` / `nd_defied_us` entry for the dead loser is removed if it still resolves;
  - an inherited crisis whose other side no longer mirrors it is dropped without consequences (outcome 9);
  - the old state's warhead progress is carried (`nd_custody_progress_carry`) and restored on the entry's next weekly
    pulse, after any fresh activation zeroed it;
  - `nd_cw_withdrawn` is cleared;
  - the AI re-reviews its posture at once; a human gets "The Old Regime's Arsenal" (`.5`).
  Then the reconcile moves the old state's remaining warheads to the winner, less the loss.
- **Secessionists win**: nothing is merged; they keep their share (step 4's Budapest pressure comes later).
- `can_revolution_inherit` stays `no`: an armed rebel already has its own entry, and the reconcile's follow-up adds it at
  once for a winner that has none, so nothing is gained by inheriting the loser's.

## 4. Loss rate

`1 % + 2 % × (3 − safeguards) + 3 % under delegated authority or launch on warning`, doubled if the holder was at war
(always, at an outbreak). A settled record uses its own stored posture and `nd_ar_at_war`. Stochastic rounding:
`floor(x)`, plus one with a chance equal to the fractional part.

Examples: 20 warheads, no safeguards, central authority, a peaceful annexation → 7 % → 1.4 expected lost. The same
arsenal at war → 2.8. Safeguards 3 → 1 % (2 % at war).

## 5. Striking one's own side

`nd_is_civil_war_counterpart = { ENEMY = X }`: X's `civil_war_origin_country` is us, or ours is X.

- **Cost**, in `nd_record_nuclear_use` **outside** its `hidden_effect`, so every strike's tooltip shows it:
  `nd_struck_own_people` (country, −50 `country_legitimacy_base_add`, decaying over 20 years; a second strike renews
  it) and `add_radicals` of 0.2 × the law factors (Outlawed Dissent 0.5, Censorship 0.75, Right of Assembly 1.25,
  Protected Speech 1.5; Secret Police or a variant 0.75, Guaranteed Liberties 1.25): 0.075–0.375. Symmetric: a rebel
  striking the original country pays too.
- **AI**: `nd_ai_nuclear_use_justified` refuses a counterpart unless `enemy_occupation ≥ 0.4` under Outlawed Dissent or
  Secret Police. Retaliation is not exempt.

## 6. Tests, docs, in-game checks

- `test_nuclear_deterrence.py`: the new script and event files join the fired-event, loc and modifier checks. A
  `TestCustody` class pins the reconcile's callers, the mod's `annex =` sites, the civil-war cost sitting outside the
  `hidden_effect`, and the withdrawn lock's readers.
- The CI `--strict` audits; the reload-only audits via their `regenerate(ms)` hooks from the worktree.
- Docs: `nuclear_crisis_design.md` §0.1 (files), §0.7 (the civil-war bullet), §0.9 (checklist), §0.10 (what is built);
  `mod_systems.md` § Nuclear Weapons "Civil wars"; the audit's F15 note.
- In-game: listed in §0.9; the `TE_CIVIL_WAR:` log lines answer the readability question.

## Out of scope

"Deny them the bomb", the foreign-reaction event, the Budapest path, detonation / attribution / recovery of loose
warheads, a panel line for the pool, and the #460–#465 repairs (which plug into §3.1's hooks).
