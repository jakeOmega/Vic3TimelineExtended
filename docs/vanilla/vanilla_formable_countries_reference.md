# Vanilla Formable Countries Reference (Victoria 3)

A primer on the **base game's** country-formation mechanics — minor unification, major unification (with leadership and unification plays), special unifications, and the formation event. The full enumerated list of formable countries (with primary cultures, tier requirements, required state percentages) lives in `common/country_formation/`; this doc explains the *system* the catalog runs on.

> **Last verified against vanilla:** 1.13.5 (Hotfix to "The Great Wave"). Wiki source dates this article 1.12. The Federation of the Andes major formable was added in 1.13 (Colossus of the South); other major-unification mechanics (leadership plays, unification plays) have been stable since 1.5.
>
> **This doc captures concepts, not the country list.** The vanilla list of formable countries (~70 entries with required cultures, tiers, regions, state percentages) is in `common/country_formation/00_formable_countries.txt` and `common/country_formation/00_major_formables.txt`; the mod adds more in `common/country_formation/extra_*`. **For "what formables exist" or "what's required to form X"** — query the source or use the mod's `add-formable-country` skill (`.claude/skills/add-formable-country/SKILL.md`), which has the canonical patterns for adding new entries.

## 1. Two paths to forming a country

A formable country is one that can be created mid-game (or re-formed if it ceased to exist). Vanilla distinguishes:

- **Minor formable** — control-based formation. Requires owning a percentage of target state regions directly (or via subjects). Typical of regional unifications (Spain, Mexico, Algeria, Pakistan).
- **Major formable** — candidacy-based formation. Multiple potentially-eligible great powers compete for the right to form via leadership plays; the winner can then form by direct control or by a unification play. Used for large multi-cultural unifications: Germany, Italy, Scandinavia, Yugoslavia, Federation of the Andes.

A few **special unifications** layer journal-entry / decision / unique-wargoal mechanics on top of the basic patterns: Iberia, China, Arabia, Ethiopia, India, Indonesia, Romania, Peru-Bolivia, Canada, Australia, North/South German Federation.

## 2. Minor unification — the basic case

Requirements (minimum set; specific countries add more):

- **Country does not currently exist.**
- **Has at least one of the required primary cultures** (which become the new country's primary cultures on formation).
- **Country tier is *lower* than the formable's tier** — a Hegemony cannot form a Kingdom because the rank gate is downward-only. (Same-tier formation requires a Major formable; see § 3.)
- **Controls a certain percentage of target states** — either listed explicitly (state IDs) or "cultural homelands" (any state region where any required primary culture has homeland presence).

When all requirements are met, a button appears on the Culture tab. Pressing it changes the country: updated primary cultures, updated flag, updated tier, the formation event fires (§ 5).

### 2.1 Subjects count toward formation

Dominions, personal unions, puppets, and vassals **count toward state-region control** for formation purposes (tributaries and protectorates do not). Indirect subjects of these types also count.

On formation:

- Subjects that share a primary culture of the formable are **fully annexed** (whether they own any required states or not).
- Subjects with other primary cultures are not annexed but **cede target state regions** to the unifying overlord.
- Indirect subjects become subjects of the unifier (rather than annexing through layers).

This is the mechanism by which a small overlord with a strong subject network can punch above its weight in formation: a unifier holding many same-culture subjects effectively pre-positions for a large pop on formation day.

## 3. Major unification — candidacy and plays

Major formables share the minor base but add:

- **Same-tier countries can form** them (no rank-down requirement).
- A formable doesn't require **direct** control of all target states. Instead, candidates accumulate **support** from same-cultured countries.

### 3.1 Candidacy

Up to **three candidates** at a time, drawn from the most-prestigious eligible great powers. If no great powers are eligible, major powers; for Scandinavia and Italy, minor powers if no major-power candidates exist. **Subjects can only support their direct overlord.**

Each non-candidate eligible country supports **one or none** of the candidates; AI countries pick based on relations + attitude scoring. Once a candidate is disqualified (lost a leadership play, backed down, etc.), they can no longer become a candidate, *but* they can still form via direct-control minor unification.

### 3.2 Leadership plays

While multiple candidates exist, none can form. Each candidate can launch a **leadership play** to force another candidate to renounce. Supporters auto-back their candidate. The defeated/backed-down candidate is disqualified.

This is the "who gets to be Germany" mechanic: a Prussian Germany vs. an Austrian Germany leadership play resolves which candidate the rest of Germany supports going forward, and the loser is locked out of further candidacy.

### 3.3 Unification plays

When **only one candidate remains** and any required state is held by a non-supporter / non-ally, that candidate can launch a **unification play**:

- All target-region states held by non-supporters become primary demands.
- Opposing side gets `Cut Down to Size` as their counter-wargoal.
- **Backing down or losing** restores the auto-annexed supporters.

Critical asymmetry: a successful unification play **does not generate infamy** for the unifying candidate. This is the high-risk-high-reward path — succeed and unify cleanly; fail and lose your supporter network (cut down to size).

A unification play is **not strictly required**. If the sole candidate already controls (with supporters and allies' help) enough states, the formation can happen without one.

### 3.4 What unification does to supporters

When the unification play **launches**, the candidate **immediately annexes all supporters** (for Germany, Italy, Scandinavia specifically). Subject relationships transfer to the candidate. If the play fails, those annexations *reverse*. So the cost of supporter-failure is not a permanent loss — but the candidate's diplomatic position during the play is dramatically different from the pre-launch state.

## 4. Special unifications

Several formables layer additional mechanics on top of minor / major patterns. The recurring patterns:

### 4.1 Journal-entry-driven assists

- **Iberia** has *The Iberian Union* JE.
- **Italy** has its unification JE that allows annexing minor / insignificant powers in customs union, subject status, or neighbor with claim.
- **Peru-Bolivia** is formed only by Bolivia, via the *Peru-Bolivian Confederation* JE (which establishes a personal-union step before the merge).
- **Romania** is formed by Moldavia or Wallachia via JEs that establish a personal union first.

### 4.2 Federation steps

The **North German Federation** and **South German Federation** can be formed via a JE for North-/South-German countries. On completion, the federation auto-converts (for Principality and Kingdom tier countries; great powers exempted), AI same-culture countries in the customs union or supporting Germany are annexed, and other same-culture countries receive an annex-or-claim event.

### 4.3 Special annexation plays

A subset of formables have a **special annexation play** (separate from the regular unification play) requiring `Pan-nationalism` (except China and Ethiopia, which don't): Arabia, China, Ethiopia, India, Indonesia. These plays are how "annex everyone in the cultural sphere" works without making the formable a major-unification candidacy contest.

### 4.4 Colonial-merge unifications

**Canada** and **Australia** can be merged either by their shared overlord (Great Britain) or by the colonies themselves through a special decision. The final formation step still follows the regular formable rules.

## 5. The formation event

Most formations trigger an event the first time the country forms (or re-forms, if it existed at start). Many formables have country-specific events with flavor text and bespoke modifiers; the rest receive the **generic unification event** (`formation.17` in `events/formation_events.txt`).

The generic event grants:

- A **decaying 20-year `unification_prestige` modifier**.
- **Claims on all unowned homelands** of the new primary cultures.
- If all homelands are already owned/claimed, **5% loyalist generation** in pops as a fallback.

Country-specific override events vary widely — many add additional law changes, ideology shifts, or unique modifiers. The exempt list (countries with non-generic events) lives at the top of `events/formation_events.txt`.

## 6. Mod implications

- **Use the `add-formable-country` skill.** The skill at `.claude/skills/add-formable-country/SKILL.md` has the canonical patterns for adding new formable countries — including dynamic-name government-conditional variants, conversion of minor formables to major, and the candidacy / leadership-play / unification-play setup. Don't write a formable country from scratch by guessing the file structure.
- **Mind the tier gate.** A country whose tier matches the formable's cannot use the minor unification path — must be a major formable. Mod content that adds a "Hegemony" tier formable for cultural-superpower formations needs the major-unification scaffolding.
- **Subject annexation behavior is non-obvious.** Same-culture subjects auto-annex on formation; non-same-culture subjects cede the target states only. If a mod-added formable should preserve a particular subject relationship, the annex behavior may need overriding via scripted effects.
- **Re-form events use the same code path as first-form.** A country that exists at game start (Russia, France, etc.) and ceases to exist mid-game can be re-formed; the first-form vs. re-form distinction is per-event, not per-formation.
- **Power-bloc identity overrides exist.** Some major formations (Germany, Italy, Scandinavia) interact with power-bloc identity changes — verify against `common/scripted_effects/` to see what bloc-side state mutates on formation.

## 7. Cross-references

- **Diplomatic plays (general)**: `vanilla_diplomacy_reference.md` § 11. Leadership and unification plays are special cases.
- **Subject types and annexation cascade**: `vanilla_diplomacy_reference.md` § 10.
- **Politics (the new primary cultures' IGs and ideologies)**: `vanilla_politics_reference.md` § 7.
- **State-level effects of new homelands**: `vanilla_states_reference.md` § 1, § 2.
- **Add-formable-country skill (canonical patterns)**: `.claude/skills/add-formable-country/SKILL.md`.
- **Vanilla data**:
  - `common/country_formation/00_formable_countries.txt` (minor formables).
  - `common/country_formation/00_major_formables.txt` (major formables; `is_major_formation = yes`).
  - `common/diplomatic_plays/00_diplomatic_plays.txt` (leadership/unification plays — `dp_unify*`, `dp_leadership*`).
  - `events/formation_events.txt` (formation events incl. `formation.17` generic).
  - `common/journal_entries/` for unification-assist JEs.

## 8. Maintenance protocol

1. **On every vanilla patch**: revisit if new formables are added or candidacy/play mechanics change. Federation of the Andes was added in 1.13; future DLC may add more major formables.
2. **Don't reproduce the formable list.** It's long and drift-prone. The `common/country_formation/` files are authoritative.
3. **Special unification mechanics live across data files.** A change to the China formation JE doesn't automatically invalidate this doc — the JE-driven assist pattern is durable. Update only if the *category* of mechanic changes.
4. **The mod's `add-formable-country` skill is the lookup for "how do I add one"** — refresh it after a vanilla bump if the file structure changes (it has been stable since 1.5).
