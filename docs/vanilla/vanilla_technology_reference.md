# Vanilla Technology Reference (Victoria 3)

A primer on how the **base game's** technology system works — the three trees, the era-and-prerequisite gating, innovation generation and capacity, technology spread, and the strategic shape of "ahead-of-time" research. This doc covers vanilla mechanics; mod-specific technologies live in their own folders alongside vanilla in `common/technology/technologies/` (see `docs/auto_generated_files.md` for ownership).

> **Last verified against vanilla:** 1.13.4 (Hotfix to "The Great Wave"). Wiki source for this article is dated 1.10; tree contents change every major patch (1.11–1.13 added several Era-V techs and reshuffled some prerequisites). **Verify specific technology IDs against the live game** via `/raw/Technology/<id>` or `docs/engine/technologies.txt` before quoting prerequisites in code.
>
> **This doc captures concepts, not the per-tech catalog.** The full enumerated list (eras, prerequisites, descriptions) is auto-generated to `docs/engine/technologies.txt` on every `/reload`; that file is the source of truth for "what techs exist in vanilla and what unlocks what". This doc explains the *system* the catalog runs on.
>
> **Numbers describe mechanism, not balance.** Era costs, ahead-of-time penalty coefficients, innovation-cap multipliers per literacy point, and tech-spread modifier values drift each patch. The *shape* — three trees, five eras, era-cost-grows-with-era, ahead-of-time-cost-grows-with-unresearched-prior-tech, literacy-bounds-innovation-cap — is durable.

## 1. Three trees

There are three independent technology trees:

- **Production** — building yields, automation, new goods (rubber, electricity, automobiles), railways, financial primitives. Concrete-invention-flavored.
- **Military** — weapons, doctrines, organizational schemes; ship types (most of the naval tree); civilian-port upgrades that touch supply.
- **Society** — politics, finance, diplomacy, ideology unlocks, institution caps, decree unlocks, formable-country gates. The "soft-tech" tree.

Each tree has two starter technologies (free to start). Every other technology has one or more prerequisite techs that must be researched first; clicking a tech with unresearched prereqs queues them in order.

Many techs have no direct effect — they exist purely to **unlock** something: a building, a PM, a law, a unit type, a journal entry, a decree, a leader-ideology generation, a formable-country candidacy. Other techs (especially society / military) carry direct modifiers (army offense, loan-interest cuts, increased authority/influence, institution-level caps).

There are 178 vanilla technologies (177 across the trees plus 1 exclusive — Sericulture). Most countries start with 20–30 already researched, representing the country's historical state at 1836.

## 2. Eras

Five eras (I–V) bin technologies by historical period:

- **Era I** — pre-1836 widely-known.
- **Era II** — First Industrial Revolution.
- **Era III** — late 19th-century stabilization / standardization.
- **Era IV** — Second Industrial Revolution / turn-of-the-century.
- **Era V** — early 20th-century transformative ideas.

Eras serve two purposes:

- **Base innovation cost rises with era**. Later-era technologies are intrinsically more expensive than earlier-era ones (the rough shape: a couple-thousand-point delta per era, current values in the wiki source and `common/technology/era/00_eras.txt`).
- **Ahead-of-time penalty**. For each unresearched technology in an *earlier* era of the same tree, the cost of any later-era technology is **inflated by a fixed fraction of its base era cost**. The penalty scales with the era difference — researching an Era-V technology while still missing many Era-II techs costs substantially more than the Era-V base.

This is what prevents rushing late-game tech: you can technically research Era-V techs from a 1836 start, but until you fill in Era I–IV in the same tree, the per-tech cost balloons. The game softens this with **technology spread** (§ 4).

### 2.1 Era cost penalty mechanics

The full formula (current as of 1.10; verify in `common/defines/00_defines.txt` for any drift):

```
tech_cost = base_era_cost
          + (count_unresearched_in_earlier_eras_same_tree
             × era_difference × era_cost_penalty_coefficient × base_era_cost)
```

**Practical effect**: each missing earlier-era tech in the *same tree* adds a quarter of the target era's base cost per era of separation. An Era-III tech with two unresearched Era-II techs in its tree costs roughly 50% more than its base. An Era-V tech with five unresearched Era-II techs in its tree costs more than 2× its base.

The penalty respects tree boundaries — unresearched military techs do not penalize society research, and vice versa. This is why heavy specialization in one tree is viable early-game.

### 2.2 Power-bloc principle: Advanced Research

The bloc principle `Advanced Research` (Internal/Society side) reduces the ahead-of-time penalty by a percentage per level of the **Education institution**. With the Education institution at level 5, the penalty drops substantially. This is the mechanical reason why an education-heavy bloc leader has structural advantages on tech rushes: it directly cuts the cost of researching out-of-era technologies.

## 3. Innovation — the per-week resource

### 3.1 Innovation generation

Each country has an **innovation generation** value, applied weekly to the currently-researched tech. Sources:

- **Base** — every country starts with a base innovation value (≈ 50). Independent of building stock.
- **Universities** — fully-staffed universities produce 2–4 innovation per level depending on PM and throughput. Dominant scaling source.
- **IG happy traits** — Industrialists' *Engines of Progress*, Armed Forces' *Veteran Consultation*, Intelligentsia's *Avant-garde* each add tree-specific research speed (Production / Military / Society respectively); doubled when the IG is powerful.
- **Event modifiers** — JE-driven temporary research speeds.
- **Companies** — many companies' prosperity bonuses add direct innovation or research speed.
- **Power-bloc principle** — *Advanced Research* (per level of Education) raises max innovation investment.

### 3.2 Maximum innovation investment

The amount of innovation that can be applied to *directed research* per week is capped:

```
max_innovation_investment = base + national_literacy × literacy_coefficient
                            + (Philips company bonus, Advanced Research, etc.)
```

National literacy is the average literacy across pops in **incorporated** states only (uninc states don't count toward the cap). Cap base ≈ 50; literacy coefficient ≈ 1.5 per percentage point of national literacy. So a country at 80% national literacy has roughly a 170-point innovation investment cap (base 50 + 120 from literacy); add Education-driven and company bonuses.

### 3.3 Spillover into technology spread

Generated innovation **above** the max-investment cap doesn't disappear — it flows into **technology spread** at reduced efficiency. Countries that out-generate their cap effectively trade directed-research overflow for spread-rate growth.

This is the strategic asymmetry of high-literacy small economies vs. low-literacy large economies: a small high-literacy country sees innovation efficiently invested into directed research; a large low-literacy country generates more total innovation but caps out earlier and pushes the rest into spread (which only works for techs *other countries already have*, so it's only useful when behind).

### 3.4 Research speed modifiers

A separate set of **research speed** multipliers applies on top of innovation per week. They can push points-applied past the max-investment cap and are tree-specific or general:

- IG happy traits per tree (above).
- Law `Industry Banned` cuts production research speed substantially.
- Free Speech laws affect tech spread (§ 4).
- Various event/JE modifiers (often temporary).
- Power-bloc principles affecting specific trees.

## 4. Technology spread — the catch-up mechanism

### 4.1 What spread does

If any country in the world has researched a technology, every other country eligible to research it gets a slow trickle of innovation toward it. **Each country can have one technology spreading per tree** at a time, chosen automatically (the tech currently spreading "to" a country is the most-researched-globally tech the country lacks but could research).

### 4.2 Spread rate

The shape (current in 1.10; spread coefficient values in `common/defines/`):

```
spread_per_week = (base + spillover_factor × unspent_innovation
                        + literacy_factor × national_literacy)
                  × sum(modifiers) × random(0.5, 1.5)
```

Spread is a stochastic process per week — base trickle + a coefficient applied to the *unspent* innovation (innovation generated above the directed-research cap that's not chosen for current research) + a coefficient applied to literacy. Multiplied by all spread modifiers and a per-week random factor.

The dominant input is **literacy** (consistent with everything else research-related), with the secondary factor being unspent innovation. A country that doesn't pick a directed-research target sends *all* its innovation into spread.

### 4.3 Spread modifiers

The modifiers stack:

- **Free Speech laws** — `Outlawed Dissent` and `Censorship` reduce; `Right of Assembly` neutral; `Protected Speech` boosts.
- **Trade Policy** — `Isolationism` cuts.
- **Economic System** — `Industry Banned` cuts (production tree only).
- **Recognition status** — unrecognized countries take a graded penalty (Major / Regional / Insignificant).
- **IG traits** — Rural Folk's *Old Ways* unhappy trait (and Jewish Devout's *Traditsye*) cuts spread (doubled when powerful).
- **Ruler trait** — `Innovative` boosts.
- **Power-bloc principle** — `Advanced Research` adds per Education level.
- **Events / companies** — various.

### 4.4 The slingshot strategy

A non-obvious gameplay pattern: **deliberately not researching a tech that's currently spreading to you**, while researching a different desired tech, lets the spread run free in the background. By the time the spreading tech finishes, the alternate tech is far enough along that it can be picked up next with the spread-driven head start carrying over to a new spread choice.

The mechanism that makes this work: spread continues as long as you don't *select* the spreading tech for directed research. Selecting it merges directed innovation into the spread progress. Letting it complete on its own buys spread-time on the next tech that the engine auto-selects.

The slingshot is a player-side optimization, not a balance lever. Mod work shouldn't try to defeat it — it's a feature of how spread interacts with directed selection.

## 5. Querying the catalog

The auto-generated `docs/engine/technologies.txt` lists every vanilla technology with its era, prerequisites, and description (whatever's in the loca file). Regenerate via `POST /reload`.

For runtime queries:
- `/raw/Technology/<id>` — full definition.
- `/modifier-search?q=` to find research-speed modifiers (`country_*_research_speed_mult`, `country_*_innovation_*`).
- `/engine-docs/origin/<modifier>` to verify a modifier name is real before referencing in script.

The mod's tech-balance audit lives in `docs/audits/mod_only_tech_modifier_baseline.md` and is regenerated by `tech_balance_audit.py` against the cached `docs/data/tech_modifier_baseline.json`. When mod tech-tree work needs a baseline anchor (typical median modifier value at a given era), refresh the cache via `tech_balance_audit.py --refresh-baseline` after a vanilla bump.

## 6. Mod implications

A handful of authoring rules that bite hard if missed:

- **Validate prerequisites against the live tree.** The wiki and old Reddit threads frequently quote stale prereqs (1.7-era `Atmospheric Engine` prereqs aren't the same as 1.13). Always read `/raw/Technology/<id>` before basing a new tech's prereq on a vanilla one.
- **Era cost balloons unresearched prior-era techs.** A mod-added Era-V tech that requires vanilla Era-IV prereqs will be substantially harder to research than its base era cost suggests because most countries reach Era V with several Era-IV techs still missing. Set the unlock thresholds with this in mind.
- **Unlocking ideologies, JEs, formable countries via tech is tracked but invisible.** Many vanilla techs unlock leader ideologies or unification candidacies but don't display this in the tech-detail UI. The mod's `gen_event_inventory` and `engine_coverage_report` audits surface these; check there before assuming a tech is "purely modifier".
- **Tech-modifier registration**: tech effects that use parametric modifier patterns (`building_*_throughput_add`, `goods_output_*_mult`) require the relevant axis combinations to be registered in `common/modifier_type_definitions/`. See `docs/guides/scripting_best_practices.md` § dynamic modifier validation.

## 7. Cross-references

- **Per-tech catalog**: `docs/engine/technologies.txt` (auto-gen on every reload).
- **Tech balance audit**: `docs/audits/mod_only_tech_modifier_baseline.md`.
- **Production / military / society building unlocks**: `vanilla_economy_reference.md` (PMs/buildings), `vanilla_war_reference.md` (units/doctrines), `vanilla_politics_reference.md` (ideology/law/JE unlocks).
- **Literacy mechanics on innovation cap**: `vanilla_pops_reference.md` § Literacy.
- **Power-bloc Advanced Research principle**: `vanilla_diplomacy_reference.md` § 9.
- **Mod's tech-tree modifier polarity overrides**: `docs/data/tech_modifier_polarity.yml`.
- **Tech-modifier pattern overrides**: `docs/data/tech_modifier_pattern_overrides.yml`.

## 8. Maintenance protocol

1. **On every vanilla patch**: revisit per the patch runbook. The catalog (era/cost/prereqs) shifts most often; the *system* (three trees, five eras, ahead-of-time cost penalty, spread mechanism) is durable.
2. **Era cost values** belong in `common/technology/era/00_eras.txt`; don't hardcode them here.
3. **Per-tech unlocks** (which tech unlocks which building / ideology / JE / formable) belong in the tech file itself; this doc is the system, not the catalog.
4. **The spread coefficient** is in defines; reproducing it here would drift. Point at the file.
