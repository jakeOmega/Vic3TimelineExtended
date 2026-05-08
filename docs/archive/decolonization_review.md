# Decolonization Mechanics Review

## Status: audit + redesign

The previous version of this doc was a snapshot taken right after a "10 items implemented" pass. Two things have moved since:

1. The 10 items are mostly done — cross-checking each against the live code below.
2. The design question has changed. Symmetric play (AI and human face the same pressure, both can hold or lose) is no longer the goal. The new framing: **most AI colonial overlords should lose most of their colonies by default; players actively steering for it should be able to hold reliably; an AI in the rare configuration of right government + right IGs + sufficient power can also hold, but rarely.**

Crucially, the asymmetry must be **in outcomes, not in mechanics**. No `is_ai` checks on bar drift, no AI-gated buttons, no AI-only resolution routes. The mechanics are uniform; the *conditions* under which the bar trends down (versus can be held) differ — and the AI rarely meets the holding-conditions for long, while a player can deliberately set them up and maintain them. The redesign below works through how to express "conditions" in mod vocabulary so they bite the AI's typical configuration and reward the player's deliberate one.

---

## State-of-play audit

Cross-reference of the prior 10-item recommendation list against the current code:

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Tech moved to era 6 | ✅ | `common/technology/technologies/era_6.txt:791` |
| 2 | Modifiers on top 3 bands | ✅ | `colonial_empire_solidified_modifier`, `_stable_`, `_strained_` in `extra_modifiers.txt` (~L1760–1773, 1848). Solidified gives +15% prestige mult, +15 acceptance, +20% loyalist conversion; Strained inverts. |
| 3 | GP-condemners drain | ✅ | `extra_progress_bars.txt:101–119`. Linear -0.6 per condemner + tiered -1.0 at ≥4 + -2.0 at ≥6. Worst case -6.6/mo. |
| 4 | Invest vs Assimilation differentiated | ✅ | `colonial_cultural_assimilation_modifier` carries `+10% state_radicals_from_political_movements_mult` (`extra_modifiers.txt:1748`); Invest does not. Distinct tradeoff. |
| 5 | Event firing density audited | ⚠️ partial | One reweight (#2 10→15). No documented audit run; firing weights elsewhere untouched. |
| 6 | Metropole-side pressure events | ⚠️ partial | Some events drain via `colonial_stability_negative_event` (8mo `-1.0/mo`) but no dedicated home-front cluster. |
| 7 | Path-dependent resolution (200/201 → 4–6 outcomes) | ✅ | Events 200–205. JE tracks `colonial_invest_months / _garrison_months / _assimilate_months` (`je_colonial_empire.txt:106–156`). |
| 8 | Path-dependent successor states | ⚠️ partial | `apply_decolonization_path` applies legacy modifiers reflecting parent's path. Successor's *laws and ideology* still default — only color is randomized. |
| 9 | Round Table Conference decision | ✅ | `colonial_empire_buttons.txt:361–446`. Authority cost 200, Intelligentsia approval, +12mo stability. |
| 10 | "Cultural Assimilation" loc rewording | ❓ | Button + modifier exist; loc text not re-audited. |

Two former concerns the old review flagged were already addressed at the time — GP-condemners drain (it's wired, not display-only) and event density (~10 events per playthrough). Don't relitigate those.

Real remaining gaps from the original list:
- Item 8: successor state ideology/laws are not path-dependent.
- Item 6: home-front pressure events aren't a distinct cluster.
- Item 5: no documented firing-weight audit.

---

## The new design question

**Where the system stands today:** the bar's monthly progress is uniform across countries. Base drift -1.0/mo, modulated by `colonial_state_count` (overstretch), country rank, era tech (`globalization` adds -1.5), GP-condemner count, and whether one of the three policy modifiers is active (Invest +0.5, Garrison +1.0, Assimilation +0.7). State-level acceptance counts feed in.

The system has **no mechanical link to the metropole's governing profile** — its laws, IG clout distribution, ideology composition. A 1960 AI Britain that's drifted to a multiparty / strong-Intelligentsia / no-Landowners profile faces the same bar drift as a 1936 AI Britain still under landed-voters-with-strong-aristocracy. The bar can't tell the difference, so the mod can't deliver the historical pattern.

**What the design needs:** uniform mechanics that produce divergent outcomes — AI loses by default because *its typical political configuration over time* doesn't support holding; a player can deliberately steer into the holding configuration and stay there.

**Two distinct viable hold strategies, each requiring real commitment:**

The crucial axis is Minority Rights. **Cruelty toward subjects produces high baseline unrest** (more liberty desire, more radicals, faster bar drain) **but unlocks powerful tools** (Garrison is devastating when you've already legalized violent hostility; the world doesn't condemn what your laws already endorse). **Benevolence produces low baseline unrest** (subjects are co-opted, not rebellious) **but cripples your tools** (Garrison contradicts your protection-of-minorities laws; Cultural Assimilation contradicts your multiculturalism). Both are viable hold strategies; they look completely different.

Note especially: a benevolent metropole that *also* keeps `law_colonial_exploitation` is not a contradiction — it's the British Raj liberal-paternalist mode, or Lyautey-era French Morocco. You're committed to running an empire, you just want to be nice to your subjects while you do it. This profile has the **lowest** baseline unrest of any holding configuration. It's only undone by the fact that you can't escalate when crisis hits — every lever has huge side-effects under nice laws.

The two profiles:

| Axis | Iron-Fist Profile | Civilizing-Mission Profile |
|---|---|---|
| Colonial Affairs | `law_colonial_exploitation` | `law_colonial_exploitation` |
| Minority Rights | violent_hostility / ghettoization / discrimination | indifference / protection / affirmative_action / cultural_assimilation |
| Citizenship | ethnostate / national_supremacy / racial_segregation | cultural_exclusion / multicultural |
| Distribution of Power | autocracy / single_party / oligarchy | universal_suffrage / census_voting / wealth_voting |
| Free Speech | outlawed_dissent / censorship | right_of_assembly / protected_speech |
| Internal Security | secret_police | guaranteed_liberties |
| Rules of War | total_war / traditional | humanitarian_regulations / limited_war |
| Baseline drift | **high drain** (cruelty creates unrest) | **low drain** (subjects pacified by inclusion) |
| Garrison | **very strong** | **near-useless / actively counterproductive** |
| Cultural Assimilation | weak (you're killing them, not assimilating) | weak (you're contradicting yourself) |
| Investment | weak (no taxpayer buy-in under autocracy) | **very strong** (broad franchise + protective minority laws fund it) |

**Why the AI loses anyway:** holding requires a coherent, sustained profile across 4–5 lawgroups for 50+ years, plus active button management matched to that profile. AI Britain that has Colonial Exploitation + Outlawed Dissent in 1936 will typically drift to Right of Assembly by 1955 and Universal Suffrage by 1965 (the "Iron-Fist" profile decays). AI Britain that has Colonial Exploitation + Affirmative Action sounds rare but is actually closer to vanilla AI behavior — *except* AI also tends to drift Colonial Affairs to `law_neocolonialism` once `decolonization` tech lands, abandoning the third leg of the stool. Either way the AI's natural drift breaks one of the legs, and the bar collapses.

**Why the player can hold:** the player can pick one profile and lock it in. Most players will choose Iron-Fist (the more dramatic playstyle); a smaller subset will choose Civilizing-Mission (the patient developmentalist play). Either works.

**Other relevant lawgroups** (smaller modifiers, but reinforce the story):
- Language Policy (mod-added): `law_civic_monolingualism` / `law_linguistic_purity` boost Cultural Assimilation; `law_multilingual_federalism` blunts it.
- State Power (mod-added): `law_unitary_state` consolidates control; `law_federal_system` / `law_devolution` drain.
- Conservative IGs: strong Landowners, strong Armed Forces, weak Intelligentsia, weak Trade Unions.
- Great Power rank + sustainable budget surplus (already in bar).

**Why this profile is rare for AI:** vanilla's law-progression and IG-clout dynamics naturally drift AIs toward more liberal laws and stronger Intelligentsia/Trade Unions clout over time, particularly under industrialization. By 1960 most AI majors have shed the holding profile. The Colonial Affairs lawgroup in particular tends to drift away from `law_colonial_exploitation` (which has high radicals/turmoil cost in vanilla) toward `law_neocolonialism` once the decolonization tech lands. A few outliers (counterfactual France-on-Algeria with stronger conservatives, USA had it had the inclination) are the "rarely they hold" case the design wants.

**Why the player can sustain it:** because the player chooses laws and chases IG outcomes deliberately. A player in 1936 UK with the goal of keeping the empire can lock in `law_colonial_exploitation` + `law_national_supremacy`, suppress Intelligentsia, bolster Landowners, and ride it out. The same options exist for the AI — the AI just doesn't pursue them coherently for 50+ years.

The win condition for the rewrite is that two playthroughs as USA-observer in 1936 produce something like the historical wave: India ~1947, Suez-tier crisis ~1956, Wind of Change ~1960, withdrawal cascades ~1960s, with each big colonial AI losing 60–90% of overseas territory. A player attempting to hold UK should be able to, with effort.

---

## Concrete proposed changes

Order is roughly increasing implementation cost. Items 1–4 deliver the AI-default-decolonize behavior through governance-coupled mechanics; items 5–7 give player and AI alike new tools that the player will use more effectively; items 8–10 close the prior-review gaps.

### 1. Replace flat base drift with governance-coupled drift `[S]`

In `common/scripted_progress_bars/extra_progress_bars.txt`, the `colonial_stability_bar.monthly_progress` block currently begins with `add = { value = -1.0 }`. Replace with a softer base plus government / IG / law terms. Target arithmetic for two reference profiles:

- **"Liberal industrial" profile** (typical 1960 AI: multiparty, no national supremacy, strong intelligentsia, weak landowners): base + governance terms ≈ **-2.5 to -3.0/mo**, irrecoverable without aggressive button play.
- **"Iron-fisted reactionary" profile** (rare AI / deliberate player build: autocracy + national supremacy + outlawed dissent + strong landowners + strong armed forces): base + governance terms ≈ **-0.3 to +0.5/mo**, recoverable with normal button rotation.

Concrete terms (signs and magnitudes intentionally rough; tune after first in-game pass). All law IDs verified against `common/laws/` (vanilla) and the mod's added lawgroups. Note that **Minority Rights cruelty produces NEGATIVE base drift** — the cruelty *creates* unrest. The cruel state's payoff comes through Garrison effectiveness (proposal #2), not bar baseline.

```
add = { desc = "colonial_base_drift_tt"  value = -0.5 }   # softer than the old -1.0

# COLONIAL AFFAIRS — the metropole's stated relationship to empire
if = { limit = { owner = { has_law = law_type:law_colonial_exploitation } }
       add = { desc = "colonial_law_exploitation_tt"  value = 0.5 } }
if = { limit = { owner = { has_law = law_type:law_colonial_resettlement } }
       add = { desc = "colonial_law_resettlement_tt"  value = 0.3 } }
if = { limit = { owner = { has_law = law_type:law_neocolonialism } }
       add = { desc = "colonial_law_neocolonialism_tt"  value = -0.3 } }
if = { limit = { owner = { has_law = law_type:law_no_colonial_affairs } }
       add = { desc = "colonial_law_no_affairs_tt"  value = -0.6 } }

# MINORITY RIGHTS — cruelty drains the bar (it creates the unrest); benevolence stabilizes
# (Note inversion from earlier draft: this is the BASE; tools compensate in proposal #2)
if = { limit = { owner = { has_law = law_type:law_minority_rights_violent_hostility } }
       add = { desc = "colonial_law_violent_hostility_tt"  value = -0.7 } }
if = { limit = { owner = { has_law = law_type:law_minority_rights_ghettoization } }
       add = { desc = "colonial_law_ghettoization_tt"  value = -0.5 } }
if = { limit = { owner = { has_law = law_type:law_minority_rights_discrimination } }
       add = { desc = "colonial_law_discrimination_tt"  value = -0.3 } }
if = { limit = { owner = { has_law = law_type:law_minority_rights_cultural_assimilation } }
       add = { desc = "colonial_law_minority_assim_tt"  value = -0.1 } }   # mild — cultural pressure builds resentment slowly
if = { limit = { owner = { has_law = law_type:law_minority_rights_indifference } }
       add = { desc = "colonial_law_indifference_tt"  value = 0.0 } }      # neutral
if = { limit = { owner = { has_law = law_type:law_minority_rights_protection } }
       add = { desc = "colonial_law_protection_tt"  value = 0.3 } }
if = { limit = { owner = { has_law = law_type:law_minority_rights_affirmative_action } }
       add = { desc = "colonial_law_affirmative_action_tt"  value = 0.5 } }

# CITIZENSHIP — secondary signal; reinforces minority-rights direction
if = { limit = { owner = { OR = { has_law = law_type:law_ethnostate
                                  has_law = law_type:law_national_supremacy
                                  has_law = law_type:law_racial_segregation } } }
       add = { desc = "colonial_law_hardline_citizenship_tt"  value = -0.1 } }   # sharpens cruelty effect
if = { limit = { owner = { has_law = law_type:law_multicultural } }
       add = { desc = "colonial_law_multicultural_tt"  value = 0.2 } }            # benevolent profile reinforcement

# DISTRIBUTION OF POWER — small base contribution; main effect is on tool effectiveness
if = { limit = { owner = { OR = { has_law = law_type:law_autocracy
                                  has_law = law_type:law_single_party_state } } }
       add = { desc = "colonial_law_authoritarian_dp_tt"  value = 0.2 } }
if = { limit = { owner = { OR = { has_law = law_type:law_oligarchy
                                  has_law = law_type:law_landed_voting } } }
       add = { desc = "colonial_law_conservative_dp_tt"  value = 0.1 } }
if = { limit = { owner = { OR = { has_law = law_type:law_universal_suffrage
                                  has_law = law_type:law_anarchy } } }
       add = { desc = "colonial_law_democratic_dp_tt"  value = -0.2 } }

# FREE SPEECH — secondary
if = { limit = { owner = { has_law = law_type:law_outlawed_dissent } }
       add = { desc = "colonial_law_outlawed_dissent_tt"  value = 0.2 } }
if = { limit = { owner = { has_law = law_type:law_protected_speech } }
       add = { desc = "colonial_law_protected_speech_tt"  value = -0.2 } }

# INTERNAL SECURITY
if = { limit = { owner = { has_law = law_type:law_secret_police } }
       add = { desc = "colonial_law_secret_police_tt"  value = 0.2 } }
if = { limit = { owner = { has_law = law_type:law_guaranteed_liberties } }
       add = { desc = "colonial_law_guaranteed_liberties_tt"  value = -0.2 } }

# STATE POWER — federalism leaks
if = { limit = { owner = { OR = { has_law = law_type:law_federal_system
                                  has_law = law_type:law_devolution } } }
       add = { desc = "colonial_law_decentralized_state_tt"  value = -0.2 } }

# IG composition
if = { limit = { owner = { ig:ig_landowners = { is_powerful = yes } } }
       add = { desc = "colonial_ig_landowners_strong_tt"  value = 0.3 } }
if = { limit = { owner = { ig:ig_armed_forces = { is_powerful = yes } } }
       add = { desc = "colonial_ig_armed_forces_strong_tt"  value = 0.2 } }
if = { limit = { owner = { ig:ig_intelligentsia = { is_powerful = yes } } }
       add = { desc = "colonial_ig_intelligentsia_strong_tt"  value = -0.4 } }
if = { limit = { owner = { ig:ig_trade_unions = { is_powerful = yes } } }
       add = { desc = "colonial_ig_unions_strong_tt"  value = -0.3 } }
```

**Replace the existing overstretch term with a metropole-scaled overreach.** Currently `-0.01 * colonial_state_count` punishes UK and Netherlands proportionally, but the real-world dynamic is that France could carry an Indochina-Algeria-West-Africa portfolio sustainably while Belgium's much smaller empire was equally proportionate. Scale by ratio of colonies to metropole, not raw count.

Add to `common/script_values/colonial_empire_values.txt`:

```
metropole_state_count = {
    value = num_states
    subtract = colonial_state_count
    min = 1     # avoid divide-by-zero pathology for fully-colonial states
}

colonial_overreach_ratio = {
    value = colonial_state_count
    divide = metropole_state_count
    subtract = 1.5   # tolerance: up to 1.5x metropole size = no penalty
    min = 0
}
```

Replace the existing overstretch term in the bar with:

```
# Overreach: penalty when colonial holdings exceed ~1.5x metropole size
if = {
    limit = { owner = { colonial_overreach_ratio > 0 } }
    add = {
        desc = "colonial_overreach_tt"
        value = owner.colonial_overreach_ratio
        multiply = -0.4
    }
}
```

Reference numbers (1936-style empires):

| Empire | Metropole | Colonial | Ratio | Tolerance | Overreach drain |
|---|---|---|---|---|---|
| Belgium | ~9 | ~5 | 0.55 | 1.5 | **0** (Congo fits) |
| Netherlands | ~3 | ~12 | 4.0 | 1.5 | -1.0/mo |
| Portugal | ~5 | ~10 | 2.0 | 1.5 | -0.2/mo |
| France | ~25 | ~40 | 1.6 | 1.5 | -0.04/mo |
| UK | ~15 | ~80 | 5.3 | 1.5 | -1.5/mo |
| Italy | ~20 | ~6 | 0.3 | 1.5 | **0** |

UK pays the most because its empire genuinely was disproportionate. France and Italy escape easily. Belgium escapes because its empire is small relative to its metropole.

Reference profile arithmetic (before button application):

| Profile | Colonial | Minority | Citizenship | DP | Net (with -0.5 base) |
|---|---|---|---|---|---|
| Iron-Fist (exploitation + violent_hostility + national_supremacy + autocracy) | +0.5 | -0.7 | -0.1 | +0.2 | **-0.6/mo** |
| Civilizing-Mission (exploitation + affirmative_action + multicultural + universal_suffrage) | +0.5 | +0.5 | +0.2 | -0.2 | **+0.5/mo** |
| Standard liberal-industrial AI 1960 (neocolonialism + indifference + multicultural + universal_suffrage) | -0.3 | 0.0 | +0.2 | -0.2 | **-0.8/mo** |
| Drifting AI 1955 (exploitation + discrimination + national_supremacy + landed_voting) | +0.5 | -0.3 | -0.1 | +0.1 | **-0.3/mo** |

Iron-Fist needs Garrison constantly (which it can deliver effectively); Civilizing-Mission can stabilize naturally and use Invest as its primary tool.

Verify the `ig:ig_X = { is_powerful = yes }` syntax against `/engine-docs/triggers?q=is_powerful` before committing — if vanilla wants the dotted form `ig:ig_landowners.is_powerful = yes` instead, switch.

The existing `country_rank` / `colonial_state_count` / `globalization` / GP-condemner / button / acceptance terms stay as-is. The change is purely additive in the bar's monthly_progress.

This is the load-bearing change. Same mechanics for everyone; the AI's typical drift toward liberal-industrial laws + IG composition makes the bar bleed; a player on the iron-fisted profile sees it stabilize.

### 2. Make button effectiveness scale with governance `[S]`

Currently the three policy modifiers each add a flat amount to the bar (Invest +0.5, Garrison +1.0, Assimilation +0.7). Replace with **additive composition**: a baseline rate plus law-specific bonuses and penalties. This produces the cruel-empire-strong-tools / benevolent-empire-weak-tools dynamic the design needs.

Garrison and Cultural Assimilation are weak-or-counterproductive under the benevolent profile (the player is contradicting their own stated laws). Invest is the benevolent profile's primary tool. Iron-Fist gets Garrison up past +2.0/mo, can afford to weather the high baseline drain.

```
# GARRISON: cruelty + dissent suppression unlocks devastating force; nice laws cripple it
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier } }
       add = { desc = "colonial_garrison_baseline_tt"  value = 1.0 } }

# Cruelty bonus: violent hostility / ghettoization legalize the methods
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           OR = { has_law = law_type:law_minority_rights_violent_hostility
                                  has_law = law_type:law_minority_rights_ghettoization } } }
       add = { desc = "colonial_garrison_cruelty_bonus_tt"  value = 0.7 } }

# Speech-suppression bonus: no domestic backlash to project force
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           has_law = law_type:law_outlawed_dissent } }
       add = { desc = "colonial_garrison_dissent_bonus_tt"  value = 0.4 } }

# COIN infrastructure
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           has_law = law_type:law_secret_police } }
       add = { desc = "colonial_garrison_secret_police_bonus_tt"  value = 0.2 } }

# Total War lifts the lid on what's permissible
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           has_law = law_type:law_total_war } }
       add = { desc = "colonial_garrison_total_war_bonus_tt"  value = 0.2 } }

# Nice-laws penalty: Garrison directly contradicts your protection-of-minorities laws
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           OR = { has_law = law_type:law_minority_rights_protection
                                  has_law = law_type:law_minority_rights_affirmative_action } } }
       add = { desc = "colonial_garrison_nice_law_penalty_tt"  value = -0.7 } }

# Humanitarian / limited war + protected speech — domestic + international legitimacy crisis
if = { limit = { owner = { has_modifier = colonial_military_garrison_modifier
                           OR = { has_law = law_type:law_humanitarian_regulations
                                  has_law = law_type:law_limited_war
                                  has_law = law_type:law_protected_speech } } }
       add = { desc = "colonial_garrison_legitimacy_penalty_tt"  value = -0.4 } }


# CULTURAL ASSIMILATION: works best with the matching minority law; ultra-cruel BLOCKS it
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier } }
       add = { desc = "colonial_assim_baseline_tt"  value = 0.7 } }

# law_minority_rights_cultural_assimilation IS the law-level version of this button
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier
                           has_law = law_type:law_minority_rights_cultural_assimilation } }
       add = { desc = "colonial_assim_law_match_bonus_tt"  value = 0.5 } }

# Hard-line citizenship + linguistic homogenization compound the assimilation pressure
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier
                           OR = { has_law = law_type:law_national_supremacy
                                  has_law = law_type:law_ethnostate
                                  has_law = law_type:law_cultural_exclusion } } }
       add = { desc = "colonial_assim_hardline_citizenship_tt"  value = 0.3 } }
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier
                           OR = { has_law = law_type:law_civic_monolingualism
                                  has_law = law_type:law_linguistic_purity } } }
       add = { desc = "colonial_assim_lang_bonus_tt"  value = 0.2 } }

# Ultra-cruel BLOCKS assimilation — you can't culturally absorb people you're attacking
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier
                           OR = { has_law = law_type:law_minority_rights_violent_hostility
                                  has_law = law_type:law_minority_rights_ghettoization } } }
       add = { desc = "colonial_assim_cruelty_block_tt"  value = -0.6 } }

# Pluralist contradiction
if = { limit = { owner = { has_modifier = colonial_cultural_assimilation_modifier
                           OR = { has_law = law_type:law_multicultural
                                  has_law = law_type:law_multilingual_federalism
                                  has_law = law_type:law_minority_rights_protection
                                  has_law = law_type:law_minority_rights_affirmative_action } } }
       add = { desc = "colonial_assim_pluralist_tt"  value = -0.5 } }


# INVESTMENT: the benevolent-empire primary tool; weak under cruelty + autocracy
if = { limit = { owner = { has_modifier = colonial_development_investment_modifier } }
       add = { desc = "colonial_invest_baseline_tt"  value = 0.5 } }

# Broad franchise: taxpayers buy in to development as legitimate spending
if = { limit = { owner = { has_modifier = colonial_development_investment_modifier
                           OR = { has_law = law_type:law_universal_suffrage
                                  has_law = law_type:law_wealth_voting
                                  has_law = law_type:law_census_voting } } }
       add = { desc = "colonial_invest_franchise_bonus_tt"  value = 0.3 } }

# Protective minority laws: development is read by subjects as good-faith inclusion
if = { limit = { owner = { has_modifier = colonial_development_investment_modifier
                           OR = { has_law = law_type:law_minority_rights_protection
                                  has_law = law_type:law_minority_rights_affirmative_action } } }
       add = { desc = "colonial_invest_protection_bonus_tt"  value = 0.3 } }

# Cruelty undermines investment: people don't accept roads while being shot
if = { limit = { owner = { has_modifier = colonial_development_investment_modifier
                           OR = { has_law = law_type:law_minority_rights_violent_hostility
                                  has_law = law_type:law_minority_rights_ghettoization } } }
       add = { desc = "colonial_invest_cruelty_penalty_tt"  value = -0.3 } }

# Authoritarian DP: no public legitimacy for the spending
if = { limit = { owner = { has_modifier = colonial_development_investment_modifier
                           OR = { has_law = law_type:law_autocracy
                                  has_law = law_type:law_oligarchy } } }
       add = { desc = "colonial_invest_autocracy_penalty_tt"  value = -0.2 } }
```

**Resulting tool effectiveness by profile:**

| Profile | Garrison | Assimilation | Invest |
|---|---|---|---|
| Iron-Fist max-cruel (violent_hostility + outlawed_dissent + secret_police + total_war + national_supremacy + autocracy) | **+2.5** | +0.4 (blocked by violence offset by hardline citizenship) | 0.0 |
| Iron-Fist standard (discrimination + outlawed_dissent + national_supremacy + autocracy) | +1.4 | +1.0 | +0.3 |
| Civilizing-Mission (affirmative_action + multicultural + protected_speech + universal_suffrage) | **-0.1** (negative — clicking it actively hurts) | +0.2 | **+1.1** |
| Standard drifting AI (indifference + national_supremacy + landed_voting) | +1.0 | +1.0 | +0.5 |
| Late-game liberal AI 1965 (protection + multicultural + protected_speech + universal_suffrage) | -0.1 | -0.5 (negative!) | +1.1 |

The benevolent-empire player **must** rely on Invest. The Iron-Fist player **must** rely on Garrison. The drifting AI gets moderate access to all three but doesn't sustain a coherent profile, so it never optimizes any of them.

Note that Garrison and Assimilation can go *negative* under the wrong law profile. This is the "huge downside" the user described — a benevolent-empire player who clicks Garrison literally drains their own bar (the world condemns the contradiction). This is intentional. Players who want to escalate must first relegislate.

### 3. Tune button costs so each approach is meaningful but distinct `[M]`

The current button costs are too cheap to constrain choice. Each approach needs a *primary* cost that gates its viability and *secondary* costs that flavor its tradeoffs. The intent: Iron-Fist is the cheapest in money terms (regressive laws supply Authority), Civilizing-Mission is the most expensive (developmentalism is GDP-draining), Assimilation scales painfully with empire size. AI decisions become cost-aware uniformly — no `is_ai` weights needed, since most AIs lack the reserves to sustain any of these for long.

Costs are applied as part of each button's `colonial_*_modifier` (already exists for all three). Note vanilla's `available` block on buttons can hard-block firing without sufficient authority/treasury — preferred over after-the-fact bankruptcy.

**Garrison — primary: Authority + Infamy. Secondary: IG anger, modest money.**

Modifier `colonial_military_garrison_modifier`:
- `country_authority_add = -300` (ongoing while modifier active; significant for non-GPs, manageable for GPs with regressive laws which generate Authority)
- `interest_group_ig_intelligentsia_approval_add = -2` (the universities don't like brutality)
- `interest_group_ig_trade_unions_approval_add = -1`
- `country_loan_interest_rate_mult = 0.05` (small money cost — credit dries up when you're shooting people)

Activation (`effect` block in the button, fires once per click):
- `add_infamy = 10` (compounds with repeat clicks; cumulative infamy tier unlocks GP condemners on its own — natural feedback)
- `available = { country_authority > 300 }` — hard gate, AI without authority surplus simply can't click

Iron-Fist profiles generate Authority through `law_outlawed_dissent`, `law_secret_police`, `law_autocracy` — they can sustain repeated Garrison cycles. Liberal-industrial AIs run Authority-tight and get blocked.

**Cultural Assimilation — primary: Bureaucracy mult (scales with empire). Secondary: colonial production drag.**

Modifier `colonial_cultural_assimilation_modifier`:
- `country_bureaucracy_mult = -0.15` (replaces current -4%; bites big empires hardest, which is the whole point)
- `country_authority_add = -100` (mild)
- Apply state-side modifier `colonial_assimilation_disruption_modifier` to all overseas colonial states while active: `state_goods_output_mult = -0.05`, `state_pop_qualification_growth_mult = -0.1` (the local economy stalls when teachers are forced to teach the metropole's curriculum)

State-side modifier wiring: in `on_monthly_pulse_country`, when the country has `colonial_cultural_assimilation_modifier`, iterate `every_scope_state = { limit = { is_overseas_colonial_state = yes } add_modifier = { name = colonial_assimilation_disruption_modifier months = 2 } }`. The 2-month duration auto-expires; constant reapplication keeps it on while the country-modifier is active.

**Investment — primary: GDP-scaled money drain. Secondary: domestic anger via SoL expectations.**

Modifier `colonial_development_investment_modifier`:
- `country_minimum_expected_sol_add = 1` (the "why aren't you investing here?" reaction — domestic pops expect more, generating radicals if metropole SoL doesn't keep up)
- `interest_group_ig_industrialists_approval_add = -2` (capital wanted at home)
- `interest_group_ig_petite_bourgeoisie_approval_add = -1`
- `country_construction_add = -3` (some construction capacity diverted to colonies)

Plus a per-month treasury debit applied via the JE's monthly pulse (script effect), since vanilla has no direct GDP-scaled-monthly-cost modifier:

```
# In je_colonial_empire on_monthly_pulse_country effect block:
if = {
    limit = { has_modifier = colonial_development_investment_modifier }
    add_treasury = {
        value = country_gdp
        multiply = -0.005   # 0.5% of GDP/mo while investing
    }
}
```

A 1960 UK GDP of ~£700M means -£3.5M/month, ~6% of typical metropole budget. Substantial. Anyone CAN fund it; few AIs sustain it for decades.

**Why Iron-Fist is cheapest:** Authority and infamy are both supplied by the same regressive-law profile that boosts Garrison effectiveness. The cruel state generates Authority faster than the protective state and is already infamous; an extra +10 infamy is almost free. Whereas the Civilizing-Mission profile must spend real treasury (5-10% of GDP/year) plus take a -2 industrialist approval hit *every cycle*. The benevolent path is sustainable but expensive — exactly the British informal-empire pattern, which was real but always under fiscal pressure.

**Why AI doesn't trivially win with Iron-Fist Garrison:** infamy compounds. 10 infamy per click → at 4 clicks/decade, that's +40 infamy by 1976. Combined with the existing GP-condemner mechanic (3+ condemners adds escalating bar drain), a sustained Iron-Fist AI hits "extreme" condemnation tier (-6.6/mo bar drain) within 20 years and crashes anyway. The Iron-Fist profile is a managed *delay*, not a permanent solution.

### 4. Liberation contagion: independence inspires the next colony `[M]`

In `apply_decolonization_path` (`scripted_effects/decolonization.txt`), after the new country is formed, apply `colonial_stability_negative_event` to *every other country* with the JE active that shares macro-region with the newly-independent colony or the parent metropole. 12-month duration, -1.0/mo via the existing modifier.

This produces the historical wave: India 1947 ripples to Burma, Ceylon, Indonesia; Ghana 1957 ripples to Nigeria, Kenya, Tanganyika. Universal — AI and player both feel it.

### 5. "Imperial Federation Act" — capstone decision that completes the JE `[M]`

The IF Act is the **victory condition** for a well-played colonial-empire run. Taking it ends the JE entirely, fires a path-specific victory event, and applies a permanent modifier expressing "the empire is now structurally embedded — no longer a thing the world is contesting." Vanilla precedent: the Greek "King Otto" / "Restoration of Greece" decisions and Italy's "Risorgimento" capstone decisions complete their respective JEs once a long-term goal is realized; this is the same shape.

Add a one-shot decision to `common/decisions/extra_decisions.txt` with **two alternative gate paths**, one per viable hold profile. Universally available; AI rarely sustains either profile coherently for the required duration.

**Sustained-Solidified requirement.** Add a new variable `colonial_solidified_months` to the JE's `on_monthly_pulse_country` (counter increments while bar ≥90, resets to 0 if it drops below). The IF Act requires `colonial_solidified_months >= 36` — three years of consistent Solidified band. This is the load-bearing gate; it forces the player to not just *reach* 100 once but *hold* it through a full election cycle / war chance / law shift.

Common prerequisites:
- `colonial_solidified_months >= 36`
- Colonial Affairs: `law_colonial_exploitation` OR `law_colonial_resettlement`
- Country rank ≥ great_power
- ≥4 colonial states currently

**Path A — Iron Fist Federation:**
- Minority Rights: `law_minority_rights_violent_hostility` OR `law_minority_rights_ghettoization` OR `law_minority_rights_discrimination` OR `law_minority_rights_cultural_assimilation`
- Citizenship: `law_national_supremacy` OR `law_ethnostate` OR `law_racial_segregation`
- Free Speech: `law_outlawed_dissent` OR `law_censorship`
- Distribution of Power: `law_autocracy` OR `law_oligarchy` OR `law_single_party_state` OR `law_landed_voting`

**Path B — Civilizing Mission Federation:**
- Minority Rights: `law_minority_rights_protection` OR `law_minority_rights_affirmative_action`
- Citizenship: `law_multicultural` OR `law_cultural_exclusion`
- Free Speech: `law_protected_speech` OR `law_right_of_assembly`
- Distribution of Power: `law_universal_suffrage` OR `law_census_voting` OR `law_wealth_voting`

Each path requires all four lawgroups lining up, plus the colonial commitment, plus 3 sustained years at ≥90.

Cost: 300 authority + 100 prestige + 1 character loyalty hit.

**Effects** (the activation `effect` block on the decision):
- Apply permanent country modifier `imperial_federation_modifier`: +5% migration pull from colonies, +5% acceptance from prestige, -15% radicals from civil rights movement, +5% prestige (the global system is now structured around your empire).
- Fire victory event: `decolonization_events.300` for Path A (Iron Fist Federation flavor) or `decolonization_events.301` for Path B (Civilizing Mission flavor). Each is a one-screen narrative beat.
- `complete_journal_entry = je_colonial_empire` — the JE finishes, the bar disappears, the buttons go away. This is intentional: the empire is *settled*, not actively contested anymore. Future colonial events can still fire from `on_yearly_pulse_country` independently if useful, but the player isn't trapped in an infinite-decade JE loop.

The decision text should sell this as the satisfying endpoint: "You have answered the imperial question. The world has accepted what you built." The capstone replaces the open-ended "watch the bar" mid-game grind with a clean narrative resolution — once and done, the empire is a done deal.

### 6. "Mandate System" decision — universal but pivot-gated `[M]`

Counterpart for the player who wants to manage decolonization rather than fight it. One-shot at ≥65 bar + Round Table Conference already taken at least once + the right legal scaffolding:

- Colonial Affairs: `law_neocolonialism` (the actual mod expression of "informal empire / economic influence" — gated on the `decolonization` tech, so not available before era 6)
- Distribution of Power: any broad-franchise option (`law_universal_suffrage`, `law_census_voting`, `law_wealth_voting`)
- NOT `law_outlawed_dissent` (you can't sell the negotiated transition under censorship)

- Cost: 100 authority + influence with at least 2 GPs (representing buying allies for the controlled transition)
- Effect: convert up to 3 lowest-acceptance colonial states into vassals (verify the engine's vassal-conversion vocabulary against vanilla — `change_subject_type` or scripted-effect equivalent). Vassals pay tribute (gold-flow modifier) but don't count toward `colonial_state_count` for overstretch.
- Modifier `mandate_system_modifier`: small acceptance penalty in remaining holdings ("the world reads you as a managed-declinist"), +10% liberty desire on existing subjects.

Universal availability; AI drifting to liberal laws will sometimes take it (which is fine — that's the AI's negotiated-decline outcome). Player picking it is choosing the British informal-empire strategy.

### 7. Path-dependent successor laws/ideology `[L]`

Closes prior-review gap #8. In `apply_decolonization_path`, in addition to the existing legacy modifier, seed the successor's laws and IG clout based on the parent's path:

- **Commonwealth path** (high invest_months, success): `law_parliamentary_republic` or `law_monarchy` (Governance Principles), `law_census_voting` (Distribution of Power), `law_protected_speech`, `law_multicultural`, `law_minority_rights_indifference` or `law_minority_rights_protection`, weak `ig_landowners`; favored ideology `traditionalist` or `social_democrat`.
- **Iron Fist path** (garrison-dominant, success): `law_autocracy`, `law_ethnostate` or `law_national_supremacy`, `law_outlawed_dissent`, `law_minority_rights_discrimination` or `law_minority_rights_ghettoization` (the new state inherits the metropole's hard-line treatment of *its* minorities), strong `ig_armed_forces`. Often a junta state.
- **Negotiated Withdrawal** (invest+assimilate, failed): `law_landed_voting` or `law_wealth_voting`, `law_cultural_exclusion`, `law_minority_rights_indifference`, strong intelligentsia, favored ideology `social_democrat`.
- **Bloody Decolonization** (garrison-only, failed): `law_autocracy` or `law_single_party_state`, `law_command_economy` likely (revolutionary state), `law_minority_rights_violent_hostility` (revanchist state targeting the ex-metropole's loyalists), strong `ig_armed_forces`.

Implementation: extend `apply_decolonization_path` with a per-path `activate_law` cluster + IG-clout adjustments. Read `common/country_creation/` for prior art patterns to match.

### 8. Home-front pressure cluster `[M]`

Closes prior-review gap #6. Add 3 events to `events/decolonization_events.txt`, all firing on the metropole's domestic state, not the colony's:

- "The Treasury Tightens" — fires when colonial_state_count ≥ 8 AND country has budget surplus < 0; drains -8mo of bar, +5% landowner approval (they wanted the cuts), -5% intelligentsia
- "Mothers Against Empire" — fires when at war AND any colonial state had a violence-tier event in the last 5 years; -8mo bar, +radicalism in petite_bourgeoisie movements
- "The Universities Speak" — fires when intelligentsia is in opposition AND `je_colonial_empire` has been active >10 years; -6mo bar, +intelligentsia approval

Frequency: random_list weight 5 each, on the existing `decolonization_events_on_action`. ~3 events per playthrough on average.

These apply to AI and player uniformly but disproportionately bite the liberal-industrial profile (where intelligentsia is in opposition, where budget surplus is tighter under welfare-state spending) — the AI default profile.

### 9. GP stance for non-overlord AI majors `[S]`

Audit events 50–52 in `decolonization_events.txt` — the GP anti-/pro-colonial stance setters. Confirm a *non-overlord* AI GP (USSR, USA, post-1945 China) tends to pick anti-colonial stance with high weight. This compounds with #1: AI overlords on liberal profiles also collect more GP condemners stacking.

Tuning pass on existing event weights, not new mechanics.

### 10. Documented event-firing audit `[M]`

Closes prior-review gap #5. Run one careful pass over `decolonization_events_on_action` and the random_list weights for events 1–21. Targets: 6–10 events visible per JE arc, weighted toward thematic distribution (don't let "Trouble in [colony]" fire 5× while "Whose Language Do We Dream In?" never appears). Use existing `cooldown` and `valid` clauses; tighten the ones missing them. Document outcome inline.

---

## Critical files

In implementation order:

| File | Purpose |
|------|---------|
| `common/scripted_progress_bars/extra_progress_bars.txt` | Governance-coupled drift terms (#1); governance-scaled button effectiveness (#2); replace overstretch with metropole-scaled overreach (#1) |
| `common/script_values/colonial_empire_values.txt` | New `metropole_state_count`, `colonial_overreach_ratio` script values (#1) |
| `common/scripted_buttons/colonial_empire_buttons.txt` | Per-button cost retuning + `available` gates (#3); add Round Table mods if needed |
| `common/static_modifiers/extra_modifiers.txt` | Tuned `colonial_*_modifier` payloads (#3); new `colonial_assimilation_disruption_modifier` (state-side, #3); `imperial_federation_modifier`, `mandate_system_modifier` (#5, #6) |
| `common/journal_entries/je_colonial_empire.txt` | Add GDP-scaled treasury debit while Investment active (#3); `colonial_solidified_months` counter for IF Act gate (#5) |
| `common/scripted_effects/decolonization.txt` | Liberation contagion (#4); successor laws/ideology (#7); state-side assimilation disruption reapplication helper (#3) |
| `common/decisions/extra_decisions.txt` | Imperial Federation Act (Paths A & B, JE-completing capstone) + Mandate System decision (#5, #6) |
| `events/decolonization_events.txt` | IF Act capstone events 300 (Iron Fist) / 301 (Civilizing Mission) (#5); home-front cluster (#8); GP-stance reweight (#9); firing audit (#10) |
| `localization/english/te_*_l_english.yml` | All new tooltip + decision text; capstone event flavor; "Cultural Assimilation" reword (closes prior #10) |

Existing helpers to reuse, not rewrite:
- `apply_decolonization_path` — extend, don't replace
- `colonial_stability_positive_event` / `_negative_event` modifiers — reuse for liberation contagion
- `colonial_state_count`, `colonial_low_acceptance_count`, `colonial_high_acceptance_count` script values
- `is_overseas_colonial_state` and `is_overseas_from_capital` triggers

---

## Verification

**Static:**
- `POST /reload` and confirm warnings array is clean (no broken modifier names, no unknown triggers — `has_law = law_type:X` and `ig:X = { is_powerful = yes }` syntax verified pre-commit via `/engine-docs/triggers`)
- `python3 modifier_visibility_audit.py` — every new modifier value above threshold
- `curl -s http://localhost:8950/event-balance/<new_event_id>` for each home-front event
- `git grep "te_" localization/english/` to confirm new loc keys exist

**Dynamic (in-game):**
- Start a 1936 game as USA, observe-mode UK and France for 50 game years. Expectation: by ~1985, both have ≤25% of starting overseas states. JE has resolved (event 200/201/202/204) for both at least once. Resolutions should disproportionately route through 204 (Negotiated Withdrawal) and 201 (Empire Crumbles), with 203 (Iron Fist) rare.
- **Iron-Fist hold test.** Start as UK in 1936; lock in `law_colonial_exploitation`, `law_minority_rights_discrimination` (or worse), `law_national_supremacy`, `law_outlawed_dissent`, `law_autocracy` or `law_landed_voting`; keep Landowners + Armed Forces powerful; use Garrison rotation. Expectation: bar stabilizes despite high baseline drain (Garrison delivers +2.0+/mo); Authority budget tight but sustainable; infamy creeps up over decades. JE reaches Solidified band by ~1960; after 36 sustained months, IF Act Path A becomes available; taking it fires event 300 and completes the JE.
- **Civilizing-Mission hold test.** Start as UK in 1936; lock in `law_colonial_exploitation`, `law_minority_rights_affirmative_action`, `law_multicultural`, `law_protected_speech`, `law_universal_suffrage`; keep Industrialists powerful, Intelligentsia moderate; rely almost exclusively on Invest. Do NOT click Garrison (it goes negative). Expectation: bar drifts gently positive, stabilizes high; treasury under sustained pressure (~5% GDP/yr); industrialists chronically grumpy. IF Act Path B unlocks; taking it fires event 301.
- **Negative test.** Start as UK and *don't* steer — let the AI's natural law-progression run (drifts to `law_multicultural` + `law_universal_suffrage` while keeping `law_minority_rights_discrimination` and `law_colonial_exploitation`, then drifts further to `law_neocolonialism` by ~1955). Click Garrison passively. Expectation: profile is incoherent (cruel minority law + nice DP + neocolonial), tools deliver moderate offset but Garrison hits Authority shortfall and gets blocked, base drift crushes it. JE fails by ~1965.
- **Overreach scaling test.** Start as Belgium and Netherlands. Belgium (small empire, in proportion to metropole) should not fail naturally before ~1975 if buttons are clicked passively. Netherlands (large East Indies relative to small homeland) should fail in the early 1950s.
- **IF Act capstone test.** Verify that taking the IF Act removes the bar, removes all colonial buttons, and the country no longer triggers decolonization events. Verify event 300 / 301 fires correctly per path. Verify `imperial_federation_modifier` is permanent (not time-limited).
- Confirm liberation contagion: watch AI France's bar while AI UK loses India. Should visibly drop ~12 points over a year.
- Confirm successor states: when AI UK loses India via path-dominant Investment, India should spawn as a multiparty state, not a random-color autocratic monarchy.
