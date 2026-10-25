# Grand Monuments: the monument policy, upkeep and prestige (design)

Date: 2026-10-23. Follows `docs/superpowers/specs/2026-10-23-tourism-heritage-design.md` § 15 (the owner's notes) and
§ 8 (the prestige figures). Owner decisions are marked *(owner)*; calls I made are marked *(my call)* and listed in
§ 13 for checking.

## 1. Why

The owner nearly always plays Open to the Public or State Ceremonial. Standard's only advantage is the upkeep it
saves, and upkeep doesn't matter late in the game. In a 1927 game (GDP £309M, weekly expenses £7.4M, 13 monuments, all
Open, construction about 40% over its base price), the monuments cost £56k a week, or 0.8%. Early in the game the
same upkeep is large: Greece's Parthenon, a level-10 landmark dedicated as Civic, costs about £1,000 a week against
Greece's £5,400 of weekly spending in 1843, or 18%. The AI mothballs on any debt, which throws away its monuments'
benefits for savings it barely notices. Prestige is a flat +25 a step, so monuments alone can lift a minor a long way
up the rankings, and they matter little to a large country that already has a lot of prestige.

**The test every policy must pass** *(owner)*: a country in 2100 should have a case for any policy, whatever it built
a century earlier. That includes a country that built only regime monuments and one that built none.

## 2. Goals, non-goals, anti-goals

**Goals**
- Four policies. Each is the best at one thing, and its cost is the others you give up *(owner: "you always choose
  one policy; the comparison is between two policies")*.
- No upkeep for Grand Monuments *(owner)*.
- Prestige from monuments becomes a smaller flat amount plus a small percentage *(owner)*.

**Non-goals**
- Grandeur, ageing, the curves, each dedication's national and local effects, contests, trophies and opportunities
  are unchanged, except where § 4 names a change.
- Hard times keeps its other job: finishing a monument level in hard times still brings Palaces amid Hardship
  (`gm_country_hard_times`, `monument_events`).
- The five-year wait after a change (`gm_policy_set`, 60 months) is unchanged.
- Vanilla wonders' tourism figures (`tourism_bonus_from_monuments` in `tourism.txt`) and their maintenance are
  unchanged. No policy touches them, as today *(my call)*.

**Anti-goals**
- A policy that is worthless to a country because of what it built.
- A policy with a penalty of its own. The cost of a policy is the policies you didn't pick *(owner)*.
- Anything that rewards switching the policy back and forth.

## 3. The four policies

| Policy | Key | What it does | Default |
|---|---|---|---|
| Open to the Public | `open` | Tourism output from monuments ×1.5 | |
| State Ceremonial | `ceremonial` | Legitimacy, and the Leader's authority, count a quarter of every monument's grandeur (§ 4.2) | |
| Cultural Promotion | `culture` | Cultural pull from monuments ×1.5; prestige from monuments ×1.5 with the Cultural Hegemony rule off | yes: a country that never chose one |
| Public Education | `education` | +1% education access a step in every state, from every monument (§ 4.4) | |

Cultural Promotion replaces Standard and Public Education replaces Mothballed, so the panel keeps four buttons *(my
call on the order: Open, Ceremonial, Cultural Promotion, Public Education)*.

These no longer depend on the policy, under any of the four *(owner)*:
- prestige, except under Cultural Promotion with the Cultural Hegemony rule off (§ 4.3);
- ageing;
- each dedication's local effect;
- anniversaries;
- the national effects of signatures other than Ancestral Antiquity's pull;
- upkeep, which is gone (§ 5).

## 4. Each policy

### 4.1 Open to the Public

Tourism output ×1.5 on the steps of `gm_local_tourism`, as today (`gm_policy_factor_tourism` in `gm_state_monthly`).
The factor loses its ×0.5 branch: no policy cuts tourism any more. Open no longer raises upkeep (there is none) and
no longer doubles anniversaries *(owner: anniversaries "muddy the waters"; state functions would count too)*.

**The signatures' tourism counts too** *(my call)*. Ancestral Antiquity (`gm_local_sig_antiquity`, +5% a step) and
the First Emperor's Army (`gm_local_sig_first_emperor`, +10% a step) are monument tourism, so they take the same
factor in `gm_state_sig_local_steps_one`; the other signatures' local effects aren't tourism and don't. This follows
§ 4.3's reasoning for Antiquity's pull.

Unchanged from today: the factor applies to Grand Monument tourism only. The vanilla wonders' figures stay as they are.

### 4.2 State Ceremonial

Today Ceremonial multiplies the steps of regime and Leader grandeur by 1.5, so it gives nothing to a country with no
regime monuments. **It becomes an addition before the curve** *(owner)*:

- **Legitimacy's input** is the regime grandeur as today (`gm_g_regime`: fitting Crown, Republic, Revolution and Leader
  monuments), **plus a share of the venue grandeur V**.
- **V counts every monument the country holds** (primaries and secondaries) that is not contested and is not To
  History. Heritage counts, so a new regime can hold its events in the old king's palace *(owner)*. Held trophies
  count for what they count in standing grandeur (`gm_tr_disp_held_grandeur`, each trophy's `gm_tr_grandeur`): a
  nationalist government shows off the state's power through what it has taken *(owner)*.
- **A regime monument counts twice:** fully in the regime grandeur and again in V. That is the owner's "all the
  grandeur as normal, plus 0.25 times all".
- **The Leader's authority** gets the same treatment: To the Leader grandeur (`gm_g_leader`) plus a share of V *(owner,
  "Otherwise, yes" to the same treatment)*.
- **The share is a quarter for both** *(owner: +140 authority at 1,000 grandeur "is a little more than 1 decree")*.
- **The curves are unchanged.** Legitimacy is the doubling curve with a first step of 10, at +2 a step. Authority is
  the doubling curve with a first step of 5, at +25 a step. Both stop at 8 steps.

What the share gives a country **with no regime or Leader monuments**:

| V (grandeur) | Legitimacy | Authority |
|---:|---:|---:|
| 100 | +3.5 | +62 |
| 300 | +6.1 | +100 |
| 1,000 | +9.2 | +140 |
| 3,000 | +12.4 | +179 |

And for countries that do have them:
- **Regime grandeur 300 within V = 1,000:** legitimacy is +9.9 with no policy. Today's Ceremonial makes it +14.8, and
  the share makes it +11.5.
- **Leader grandeur 100 within V = 1,000:** authority is +108 with no policy and +162 under today's Ceremonial. The
  share makes it +153.

For scale, vanilla laws give 50–200 authority and the Forbidden City gives 50.

**Implementation:**
- Keep `gm_g_regime` and `gm_g_leader` as they are; the panel shows them. Add the share as its own variable, for
  example `gm_g_ceremonial` (V times the share, 0 under any other policy), set in `gm_compute_totals`.
- Feed `gm_g_regime + gm_g_ceremonial` to the legitimacy curve, and the Leader equivalent to the authority curve.
- V is a new sum beside `gm_sum_regime`: state primaries through a new trigger (dedicated or heritage, not contested,
  not To History), plus `gm_monuments_held` through its container twin, plus `gm_tr_disp_held_grandeur`.
- `gm_policy_factor_regime` and its two `gm_policy_scale_steps` calls go.
- The legitimacy and authority rows' bar, grandeur hover and next-step figure read the curve's real input (regime
  grandeur plus the share), not `gm_g_regime` alone, so a country with no regime monuments doesn't show a bonus beside
  an empty bar. The hover names both parts, for example "+N from state ceremonies at your other monuments".

### 4.3 Cultural Promotion (the default)

Cultural pull from monuments ×1.5, applied to the steps after the curve as today's factors are:
- `gm_s_culture`, the Grand Monuments' pull;
- `gm_s_sig_antiquity`, Ancestral Antiquity's pull *(my call: Antiquity's pull is monument pull, and Egypt and Greece
  would otherwise get little from this policy)*.

The vanilla wonders' +3 each (`cultural_pull_monument_bonus`) is unchanged.

| Standing grandeur | Monument pull (no policy) | Extra under Cultural Promotion |
|---:|---:|---:|
| 140 (Egypt, 1836) | +4.8 | +2.4 |
| 300 | +7.2 | +3.6 |
| 1,000 | +13.6 | +6.8 |
| 3,000 | +24.0 | +12.0 |

For scale, a great power's living standards give at most +20.

**With the Cultural Hegemony rule off** (`cultural_hegemony_rule = cultural_hegemony_disabled`), cultural pull does
nothing: `cultural_pull_from_monuments` is read only by the Cultural Hegemony pulses, which run only under
`cultural_hegemony_enabled`. Cultural Promotion would then be a dead default for every country that never chose, every
migrated save and the AI's fallback. **Under that rule Cultural Promotion raises monuments' prestige ×1.5 instead**,
both the flat part and the percentage (`gm_s_standing` after the curve), so all four buttons still work *(owner)*. Its
button tooltip and the guide say which it does, by the rule.

### 4.4 Public Education (new)

A new national modifier, `gm_national_education`, with `state_education_access_add = 0.01` a step
(`gm_step_education = 0.01`) *(owner)*. Its steps,
`gm_s_education`, are standing grandeur on the open 1/n curve with a first step of 10 (`gm_set_steps_lin_open`, as
cultural pull). Standing grandeur counts every uncontested monument and held trophies at half; a museum teaches.

Unlike the other three policies, it adds an effect monuments don't otherwise give. It is 0 under every other policy.

| Standing grandeur | Steps | At +0.5% a step | At +1% a step |
|---:|---:|---:|---:|
| 140 (Egypt, 1836) | 4.8 | +2.4% | +4.8% |
| 300 | 7.2 | +3.6% | +7.2% |
| 1,000 | 13.6 | +6.8% | +13.6% |
| 3,000 | 24.0 | +12.0% | +24.0% |

The mod's schooling laws and amendments give +5% to +10% education access. At +1% a step, Egypt in 1836 gets about
half a schooling law and a large late collection two or three; rich countries reach the ceiling anyway, and the policy
has to compete with Open's money *(owner)*.

**Education access, not literacy growth or qualifications** *(owner)*. Access is the ceiling literacy drifts toward,
and a player can read it in the state view. It stops mattering once a country's literacy is near its ceiling. That is
a test of development, not of what was built, so Public Education is the developing country's policy, as Ceremonial is
the low-legitimacy country's.

**An engine fact nobody has verified:** a `state_*` field in a modifier held by a journal entry. Every national effect
lives on `je_grand_monuments` (`gm_apply_national_modifiers`). Three signatures there already carry `state_*` fields:
- `gm_national_sig_liberty` has `state_migration_pull_mult`;
- `gm_national_sig_olympic` has `state_mortality_mult`;
- `gm_national_sig_heroes` has `state_assimilation_mult`.

None has been checked in game. Country-held law modifiers with `state_*` fields do reach every state.
- **Preferred version:** the JE, like every other national effect, with a once-a-game
  `TE_SELF_CHECK OK|BROKEN gm_education_reaches_states` line. It compares a state's education access with the
  modifier on and off, or reads the state's modifier value. The builder picks the read, and excludes a country with no
  steps so OK can't pass on nothing.
- **Fallback, named in the play-test list's Self-checks table:** add the modifier to the country instead.

### 4.5 To History monuments: half under every policy (phase 2)

To History arrives in tourism heritage phase 2 (that spec, § 7). Under every policy it counts at half *(owner: "all
the policies apply to them, at a reduced rate"; half is my call)*:
- **Open:** its tourism ×1.25. In a state where it stands beside another dedication, the factor follows each
  monument's share of the state's grandeur, as § 7 of that spec already has it, with To History at ×1.25 and the rest
  at ×1.5.
- **Ceremonial:** it joins V at half its grandeur, so it counts an eighth under a quarter share.
- **Cultural Promotion:** for pull the factor is applied to the steps, so it can't tell monuments apart. The factor
  becomes 1 + 0.5 × (G_other + 0.5 × G_history) ÷ G_standing.
- **Public Education:** its grandeur counts half in the education input.

That spec's rule that To History "ignores `gm_policy_factor_tourism`" kept a policy from cutting the heritage that
moved off base appeal. No policy cuts tourism now, so the rule is replaced by this one. Its upkeep line ("Upkeep:
none") is moot (§ 5). **This pass amends that spec's § 7 and leaves the code to phase 2**, since `historic` doesn't
exist yet.

## 5. Upkeep goes

Grand Monuments cost nothing to maintain *(owner)*. Upkeep was too small to matter late and too large early, and the
policy that saved it was the AI's reason to throw away its monuments' benefits. Building a monument remains the real
cost.

- **The proven path:** `gm_state_upkeep_mult` becomes −1 under every policy and for unmigrated buildings too. That is
  exactly what Mothballed does today. `gm_upkeep` (`goods_input_construction_mult = 1`) at −1 cancels the level-scaled
  maintenance input whatever the level, which is how Mothballed shows "No maintenance" now.
- `pmg_maintenance` stays on `building_grand_monument`. Removing a PMG from a building type in a running save is
  unverified, and nothing here needs it.
- `gm_policy_factor_upkeep` goes. `gm_policy_upkeep_open` and `gm_policy_upkeep_mothballed` stay defined only so the
  monthly pass can remove them from older saves (as now).
- The construction site's costs are unchanged.

## 6. Mothballed and Standard go: older saves

- `gm_policy_is` reads an unset `gm_policy` as the default (`STANDARD = yes`). Cultural Promotion takes that default:
  `gm_policy_is = { P = culture STANDARD = yes }`.
- **Migration:** a country whose `gm_policy` is `flag:mothballed` or `flag:standard` has the variable removed on the
  country refresh. It then reads as Cultural Promotion. `gm_policy_chosen` and `gm_policy_cooldown` are untouched, so
  no new wait starts and a running one keeps running. The two old flags are written nowhere after that.
- **What goes with them:**
  - `gm_policy_factor_standing`, `_local`, `_age` and `_upkeep`;
  - their `gm_policy_scale_steps` calls in `gm_compute_totals` and `gm_signature_effects.txt`;
  - their uses in `gm_state_monthly`, `gm_state_age_step` and `gm_mon_age_step` (`gm_monument_values.txt`);
  - the anniversary dispatcher's Mothballed gate and Open's weight halving (`monument_events_on_actions.txt`).
- The four sguis in `gm_sguis.txt` become Open, Ceremonial, Cultural Promotion and Public Education.

## 7. The AI

No policy saves money now, so the owner's crisis rule ("mothball only when defaulting or in severe financial crisis")
is met by having nothing to mothball. `gm_policy_ai_choose` runs each January as now, picks the first that holds, and
changes only when the pick differs *(my call, order and thresholds)*:

1. **Ceremonial:** legitimacy under 40, and its input under Ceremonial (regime grandeur plus the share) reaches the
   curve's first step (10).
2. **Open to the Public:** a monument stands in a state with a Tourism Industry. Tourism pays, which is the case for it.
3. **Public Education:** `literacy_rate < 0.5`.
4. **Cultural Promotion** otherwise.

## 8. Prestige

The figures from the tourism heritage spec, § 8 *(owner)*:
- `gm_step_prestige` goes from 25 to 10.
- A new `gm_national_prestige_pct` gives `country_prestige_mult = 0.01` a step (`gm_step_prestige_pct = 0.01`), on the
  same steps (`gm_s_standing`, the open 1/n curve with a first step of 5).
- Both go on the JE from `gm_apply_national_modifiers`, removed with the others in `gm_remove_national_modifiers`.
- The panel's Prestige row shows both, and its hover names both.

| Standing grandeur | Steps | Today | New |
|---:|---:|---:|---:|
| 35 (one level-7 landmark in 1836) | 3.2 | +81 | +32 and +3% |
| 140 (Egypt, 1836) | 7.0 | +175 | +70 and +7% |
| 1,000 | 19.5 | +488 | +195 and +20% |
| 3,000 | 34.1 | +854 | +341 and +34% |

A minor's monument prestige falls by more than half. A great power with 1,500 base prestige and 3,000 grandeur gets
+341 and +34% (+510), which is +851, about what it gets today.

`scripts/generators/gen_nation_tab.py` already covers both new modifiers: they're on the JE, and its `NOT_ON_COUNTRY`
registry has the glob `"gm_*"`. The builder confirms `test_nation_tab.py` passes. If Public Education falls back to
the country (§ 4.4), `gm_national_education` needs its own row.

## 9. What the player sees

- **The four buttons** at the foot of National Effects, with new names and tooltips. Each tooltip says what the policy
  raises and that the others don't apply. The overview's last line names the policy in force.
- **National Effects:**
  - a new Education Access row while Public Education is in force;
  - the Prestige row with both parts;
  - the legitimacy and authority rows' hovers naming the ceremonies' share.
- **The state card** shows no maintenance line (or reads 0, whichever is simpler) and the tourism factor as today.
- **Loc:**
  - every key naming Standard or Mothballed is renamed or deleted;
  - the policy concept text is rewritten;
  - `te_unused_l_english.yml` loses any stale copy (CLAUDE.md, #617).

## 10. Tests

The registry pins and new tests in `test_grand_monument_registry.py`, or a new test file, cover:
- `gm_step_prestige = 10`;
- `gm_step_prestige_pct = 0.01`, paired with `gm_national_prestige_pct`'s `country_prestige_mult`;
- `gm_step_education = 0.01`, paired with `gm_national_education`'s `state_education_access_add`;
- the ceremonial share at 0.25;
- Cultural Promotion's prestige branch gated on `cultural_hegemony_disabled`;
- no script outside the migration naming `mothballed` or `standard` as a policy;
- `gm_state_upkeep_mult` constant at −1;
- the four sguis' keys.

The builder writes them test-first. Targeted tests and the system's lints per round; CI runs the whole suite.

## 11. Play-test list and self-checks

A new `docs/testing/grand-monuments-policy-playtest.md`, beside the ageing, archaeology, multiple and signatures
files:
- **Egypt's and Persia's rank,** 1836–1846, against a game before this change (§ 15 of the heritage spec).
- **A country with no regime monuments** switches to Ceremonial: legitimacy rises by the share, and the hover names it.
- **Public Education:** a state's education access rises by the modifier. Read the self-check.
- **An older save on Mothballed** loads on Cultural Promotion with no new wait.
- **Maintenance:** a monument building's maintenance input reads zero under every policy.
- **The AI:** a low-literacy AI with monuments and no Tourism Industry picks Public Education in January.

Self-checks table: `gm_education_reaches_states`, with the fallback in § 4.4.

## 12. Settled with the owner after the builder check

1. **Ceremonial's share is a quarter for legitimacy and for the Leader's authority** (§ 4.2).
2. **Public Education gives +1% education access a step** (§ 4.4).
3. **With the Cultural Hegemony rule off, Cultural Promotion raises monuments' prestige ×1.5** (§ 4.3).

## 13. Calls I made

- Vanilla wonders stay outside every policy (§ 2, § 4.1, § 4.3).
- Cultural Promotion covers Ancestral Antiquity's pull (§ 4.3), and Open covers the two signatures' tourism (§ 4.1).
- To History counts at half under every policy (§ 4.5).
- The button order and the keys `culture` and `education` (§ 3).
- The AI's order and thresholds (§ 7).
- `pmg_maintenance` stays on the building, cancelled by the −1 multiplier (§ 5).

## 14. Left to the builder

- Loc text for the new names, tooltips and the policy concept, in the house style.
- The self-check's read (§ 4.4).
- Whether the state card hides the maintenance line or shows 0.
- The exact sum and trigger names for V.

## 15. Docs this pass amends

- **The tourism heritage spec:**
  - § 7 gets the To History rule from § 4.5, and its upkeep line is marked moot;
  - § 13 notes that phase 2's gate is this pass;
  - § 15 is marked resolved, with its "Mothballed only halves upkeep" line corrected: Mothballed already removed all
    upkeep from 2026-10-18.
- **The player guide's `02-timeline.md`:** the monument policy table and text (about lines 1043–1062), and the
  Mothballed mentions near lines 757, 855 and 1276. Rebuild the PDF.
- **`docs/systems/mod_systems.md`:** the "Monument policy" bullet and the ageing bullet's Mothballed clause.
- **The Grand Monuments play-test files:** any check that relies on Mothballed or Standard.
