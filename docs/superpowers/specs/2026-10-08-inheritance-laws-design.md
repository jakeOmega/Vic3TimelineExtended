# Inheritance: who inherits, what the community takes, and a generational clock — design

## Context

The Inheritance law group (`lawgroup_inheritance`) was added for France: Equal Inheritance's birth-rate penalty gives
France its early fall in fertility by default. Its four laws today (`common/laws/extra_laws.txt`):

| Law | Unlock | Effects |
|---|---|---|
| Primogeniture | start | Birth rate +5%, radicals from movements +10%, Landowners +10% clout, qualifications −10%, tax capacity −10%, bureaucracy cost −5% |
| Partible Inheritance | default (`common/history/extra_history.txt`) | None |
| Equal Inheritance | `egalitarianism` | Birth rate −10%, radicals −10%, Landowners −10% and Rural Folk +10% clout, education access +5%, migration quota +10%, tax capacity +10%, bureaucracy cost +5% |
| Non-Inheritable Usage Rights | Command Economy or Cooperative Ownership | Birth rate −10%, +200 authority, government dividends efficiency +5%, Bureaucrats +10% clout, bureaucracy cost +5% |

Starting laws: France Equal Inheritance; Britain, Russia and Japan Primogeniture; everyone else Partible.

Why the group felt dull:

- `ideological_opinion_impact = 0` (`common/law_groups/extra_law_groups.txt`), the same as vanilla's colonization.
  Interest groups react only while a change is being enacted, never to the law in force.
- The effects are instant. Event 77's own flavour text says equal division "dissolves the great houses in three
  generations"; the modifiers do it on the day the law passes.
- Partible Inheritance does nothing and is hard to tell from Equal Inheritance.
- There is one left option. Anarchists and communists share one stance list (`communal_inheritance` in
  `ideology_modifications.py`), and Usage Rights' authority and dividend package makes it a state-ownership law.
- Nothing past the 1930s.

## Decisions (owner, 2026-10-08)

| Question | Decision |
|---|---|
| Keep or cut | **Keep and rebuild.** France's demography stays systemic, and every country gets the lever |
| Laws | **Six** (§1): Primogeniture & Entail, Customary Inheritance, Forced Heirship, Freedom of Testation, State as Universal Heir, Possession by Use. The laws answer one question, who inherits |
| Estate Duties | **An amendment** on the four private-ownership laws, not a law (§2.1) |
| Birthright Endowment | **An amendment** too (§2.3): it says nothing about who receives the untaxed rest of an estate, so it fits any private-ownership law. It replaces Estate Duties instead of stacking on it, because the duty is what pays for it |
| Perpetual Dynastic Trusts | **An amendment** (§2.2) |
| Undivided Farm Succession | **An amendment** on Forced Heirship and Customary (§2.4): one heir takes the farm whole, the fix Germany, Austria and Norway used for fragmentation |
| Estate Duties' revenue | **None standing**; the duty works through the concentration score (§2.1) |
| Posthumous Title | **An event chain** off `mind_backups` (§6), not a law |
| The left | **Split by heir**: the communist wants the state to inherit, the anarchist wants nobody to |
| Systemic layer | Wealth-concentration score (§3), rural-scaled birth and migration effects (§4), generation events (§5), and law stances that bite while the law is in force (§8) |
| Migration | `state_migration_quota_mult` moves immigration and emigration together (owner correction), so it can't push a one-way flow. Equal Inheritance's +10% was not "the wrong way", just the wrong tool. §4 scales it by how rural a state is |

Numbers below (targets, rates, modifier sizes) are starting proposals for the balance pass, not decisions.

## 1. Laws

Keys stay where a law keeps its meaning, so saves keep their laws; only the display text changes.

| Key | Name | Unlock | Starts | Identity |
|---|---|---|---|---|
| `law_primogeniture` | Primogeniture & Entail | start | Britain, Japan | The eldest takes the estate, and entail stops him breaking it up. Great houses last; younger sons go into the army, the church, the colonies and the city |
| `law_partible` | Customary Inheritance | default | everyone else, Russia (§7) | Local custom decides. Blank baseline |
| `law_equal_inheritance` | Forced Heirship | `egalitarianism` | France | The Code Napoléon's reserved shares. Farms split each generation, peasants have fewer children so the plot survives, and they stay on the land |
| `law_free_testation` (new) | Freedom of Testation | start | USA (§7) | The owner chooses the heirs. Family firms survive intact; fortunes can be left to foundations |
| `law_state_universal_heir` (new) | State as Universal Heir | Command Economy | — | Saint-Simonians (1829), measure 3 of the Communist Manifesto. Estates go to the state. Takes today's Usage Rights package (+200 authority, dividends efficiency, Bureaucrats' clout) |
| `law_non_inheritable_usage_rights` | Possession by Use | Cooperative Ownership | — | Proudhon's possession against property; Bakunin put the abolition of inheritance before the International at Basel (1869). Holdings go back to the commune that uses them, not to the state: no authority bonus. Local, decentralised effects instead |

No law unlocks after the economic-system laws. The group's late content is the amendments (eras 9 and 10, §2) and the
era-12 event chain (§6), which arrive through events, so the law list itself looks the same in 2030 as in 1900.

What happens to today's static modifiers:

- **Landowner clout** (Primogeniture +10%, Equal −10%) moves to the concentration score (§3), so it arrives over a
  generation instead of on the day the law passes.
- **Birth rate and migration quota** move to the rural-scaled state effects (§4).
- The rest (radicals, qualifications, tax capacity, bureaucracy cost, education access, Rural Folk clout) stays on the
  laws for now.
- **Both left laws save less.** With no bequest to save for, State as Universal Heir and Possession by Use lower the
  upper and middle strata's investment-pool efficiency (`state_<pop>_investment_pool_efficiency_mult`).

Leaving Command Economy or Cooperative Ownership already drops State as Universal Heir or Possession by Use through the
law-consistency walk (`gen_law_consistency.py`), as it drops Usage Rights today.

## 2. Amendments

All four need a scripted way in (`scripting_best_practices.md` § `add_amendment` Requirements): a debate event in
the `on_law_checkpoint_debate` pool while a host law is being enacted (the `extra_law_events.87`/`.88` pattern), and an
amendment petition on a host law already in force (`events/amendment_petition_events.txt`, § Amendment Petitions in
`docs/systems/mod_systems.md`).

**A law's amendments leave with it.** Moving from Primogeniture to Forced Heirship drops Estate Duties or the
Endowment. The debate event during the new law's enactment should offer to carry it over, so reforming who inherits
doesn't quietly abolish the tax.

**Parents come from other law groups.** No inheritance law stands for taxing estates, so each amendment takes its IG
stances from the law elsewhere whose supporters backed it in history. Vanilla does this for 18 of its 67 amendments
(`amendment_homestead_acts` → `law_frontier_colonization`, `amendment_religious_workhouses` →
`law_charitable_health_system`). Repeal needs an IG in government that opposes the parent law.

### 2.1 Estate Duties (`amendment_estate_duties`)

- **Allowed on** Primogeniture & Entail, Customary Inheritance, Forced Heirship, Freedom of Testation: the laws with
  private estates to tax.
- **Unlock** (`possible`): `political_agitation` (era 4). Britain's progressive estate duty is 1894, the US federal
  estate tax 1916; both came with war or naval spending.
- **Effect**: lowers the concentration target (§3) by 25, floored at 0.
- **Parent**: `law_graduated_taxation`. The groups that want a progressive income tax want a progressive duty on
  estates.
- **Petition**: rolls higher during a war or with a reformist or social-democratic IG in government.
- **No standing revenue.** The duty works through the score. Inheritance and estate taxes raise about 0.5% of tax
  revenue across the OECD today, though they mattered more to Britain before the Second World War. One-off sums can
  come through its events (§5). This also keeps clear of the tax-code spec's rule against relabelling the dividend tax
  as an inheritance tax (`2026-09-29-legislated-tax-code-design.md` §2, §3).

### 2.2 Perpetual Dynastic Trusts (`amendment_perpetual_trusts`)

- **Allowed on** Freedom of Testation only. Entail already is a perpetual trust; the rule against perpetuities was
  invented to stop it.
- **Unlock**: `globalization` (era 9). South Dakota dropped the rule against perpetuities in 1983 and other states
  followed in the 1990s; offshore trusts came with the same wave.
- **Effect**: raises the concentration target by 30, capped at 100, and capitalists' investment-pool efficiency.
- **Parent**: `law_laissez_faire`, as vanilla's `amendment_extraterritoriality_rights` uses. It puts the trusts with
  the Industrialists and finance, who lobbied for them, rather than in the fight between traditionalists and liberals.
  `law_primogeniture` ("entail by another name") is the alternative (§9).
- **Petition**: under Freedom of Testation with powerful Industrialists.
- Can sit beside Estate Duties or the Endowment: the trusts exist largely to avoid the duty. Their targets add.

### 2.3 Birthright Endowment (`amendment_birthright_endowment`)

Paine's *Agrarian Justice* (1797): a duty on estates pays every young adult a capital stake. It says nothing about who
gets the untaxed rest, so it fits any law with private estates.

- **Allowed on** the same four laws as Estate Duties.
- **Unlock**: `universal_basic_income` (era 10).
- **It replaces Estate Duties; it doesn't stack on it.** The duty is how it's paid for, so one amendment both levies the
  duty and pays out the stake. A petition on a law carrying Estate Duties swaps one for the other; a law with neither
  can take the Endowment directly. Two separate amendments would break when the duty was repealed: the engine checks
  `possible` only when an amendment is added, so an Endowment that required the duty would outlive it. With one
  amendment, repealing it removes both, which is right: the fund is the duty. Estate Duties' `possible` excludes a law
  that has the Endowment.
- **Effect**: lowers the concentration target by 30 (it taxes the top and spreads capital at the bottom), plus
  qualifications, education access and lower-strata investment-pool efficiency
  (`state_laborers_investment_pool_efficiency_mult`, Farmers', Shopkeepers').
- **Parent**: `law_old_age_pension`. Paine's plan paired the stake at 21 with a pension from 50.
- **Petition**: on a law carrying Estate Duties, with a reformist or social-democratic IG in government.
- An Endowment funded from general revenue instead (Britain's Child Trust Fund, 2005) is a welfare programme, not
  inheritance policy, and is out of scope here.

### 2.4 Undivided Farm Succession (`amendment_undivided_farm_succession`)

One heir takes the family farm whole and pays the other heirs out. It is the remedy for the fragmentation that equal
division causes: northwest Germany's Höfeordnung (1947), Austria's Anerbengesetz (1958), Norway's odel and åsete rights;
even France lets one heir take the farm and buy out the rest. Single-heir farm custom already held in Westphalia,
Hanover and Bavaria in 1836. The Nazi Reichserbhofgesetz (1933) made such farms inalienable and open only to
"Aryan" farmers; the British zone's Höfeordnung replaced it with a register farmers could opt into.

- **Allowed on** Forced Heirship and Customary Inheritance. Primogeniture already keeps estates whole, and under
  Freedom of Testation an owner can leave the farm to one child.
- **Unlock**: none; available from the start.
- **Effect**: cancels Forced Heirship's rural birth-rate effect (§4), since peasants no longer need fewer children to
  keep the farm whole, and turns its migration effect around: the siblings who don't inherit leave the land, as under
  Primogeniture. Raises the concentration target by 10.
- **Parent**: `law_peasant_proprietorship`. Agrarians back it (Jeffersonian agrarians strongly), the hierarchic and
  oligarchic ideologies strongly oppose it.
- **Ways in**: a fourth option in Forced Heirship's Last Division event (§5), the debate event, and a petition when
  Rural Folk are powerful.

## 3. The concentration score

One country variable, `te_inh_concentration`, 0–100: how much of the nation's wealth sits in great family fortunes.

- **Target** set by the law plus amendments: Primogeniture & Entail 80, Freedom of Testation 60, Customary 50, Forced
  Heirship 25, State as Universal Heir 0, Possession by Use 0; Estate Duties −25, Birthright Endowment −30, Perpetual
  Trusts +30, Undivided Farm Succession +10.
- **Drift**: each year the score closes 3% of the gap to its target, so half the gap closes in about 23 years, one
  generation. A republic that abolishes entail in 1848 still has great houses in 1870.
- **Start**: each 1836 country starts at its law's target, so nothing drifts at game start.
- **Effects** come from the score through the dynamic-modifier pattern, refreshed in one place (the country's yearly
  pulse; the multiplier is a country variable, so a country pulse is correct):
  - `inh_great_fortunes`, multiplier (score − 50) / 50 above 50: Aristocrats' and Capitalists' clout up
    (`country_aristocrats_pol_str_mult`, `country_capitalists_pol_str_mult`), their investment-pool efficiency up,
    radicals from movements up.
  - `inh_dispersed_wealth`, multiplier (50 − score) / 50 below 50: Aristocrats' clout down, Farmers' and Shopkeepers'
    investment-pool efficiency up.
- **Revolutions**: the score is a variable, so a revolution's winner keeps it (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").
  The modifiers are reapplied by the next yearly pulse.
- **Shown** in the law group's tooltip or a concept, with its target and direction, so a player sees the clock.

## 4. Rural-scaled birth and migration

Le Play's mechanism is a peasant one: smallholders had fewer children so the farm would not be split. The effects
apply per state from `on_yearly_pulse_state`, multiplied by the state's agrarian share (Peasants plus Farmers):

| Law | Birth rate | Migration quota |
|---|---|---|
| Forced Heirship | Down | Down: peasants stay on their plots, which holds back the rural exodus |
| Primogeniture & Entail | Up | Up: younger sons leave the land |

Because the quota is symmetric, scaling it by rural share is what makes it work: a farm state rarely draws migrants,
so a lower quota there mostly holds people in, while France's industrial départements (where its late-century
immigrants went) are untouched. The target: France's lead in the fertility transition shows from 1836 to about 1880 and
fades by 1900 as it urbanises and other countries catch up. Undivided Farm Succession (§2.4) switches Forced Heirship's
rural effects off.

`pop_type_percent_state` is a trigger, not a value, so the multiplier is a few steps unless a script-value sum over the
state's pops works; check before building.

## 5. Generation events

One recurring event per law, rolled yearly from a sub-action (the amendment-petition idiom), once a country has held
the law for 20 years, with a 25-year cooldown. Each option moves the score, a pop group or a law-specific effect.

| Law | Event | Choices |
|---|---|---|
| Primogeniture & Entail | The Cadet Sons | Army, church, colonies or the city |
| Forced Heirship | The Last Division | Fewer children (the French path), emigrate (Württemberg and Baden, whose split farms sent thousands to America), sell to a neighbour (score up), or legislate undivided succession (adds §2.4) |
| Freedom of Testation | The Founder's Will | Endow a foundation (score down; Carnegie's *Gospel of Wealth*, 1889), found a dynasty (score up), or the heirs go to court |
| State as Universal Heir | The Hidden Estates | Crack down (authority, radicals) or look away (score creeps up under a law that says zero) |
| Possession by Use | The Empty Holding | The commune reallocates it or a family claims continuity |
| Birthright Endowment (amendment) | The First Cohort | Steer the stake into education or let it be spent |
| Estate Duties (amendment) | The Great Estates for Sale | The state buys them, the market takes them, or farms are exempted (a quarter of England changed hands in 1918–21) |

Customary Inheritance gets none. First wave: Primogeniture, Forced Heirship, Freedom of Testation, Estate Duties.

## 6. Posthumous Title (event chain)

From `mind_backups` (era 12). The first backed-up mind contests its own probate:

- **Recognise continuity of title**: backed-up minds keep their property. The score's target is pinned at its current
  value (nobody's estate passes on), with gerontocratic costs. A follow-up, *The Heirs Who Never Inherit*, brings a
  youth movement.
- **Declare legal death**: inheritance proceeds under the current law; the augmentation lobby is angered.

`biological_immortality` (era 12) can open the same chain: with nobody dying, inheritance stops either way.

## 7. Starting laws

- **France**: Forced Heirship (unchanged).
- **Britain**: Primogeniture & Entail (unchanged). Primogeniture governed intestate land until 1925.
- **Japan**: Primogeniture & Entail (unchanged): househead succession.
- **Russia**: Customary Inheritance, not Primogeniture. Anna repealed Peter's 1714 single-inheritance law in 1731, and
  nobles divided estates among their sons.
- **USA**: Freedom of Testation. Primogeniture and entail were gone by about 1800 and there are no forced shares.
- **Ottoman Empire**: Customary (open question, §9).

## 8. Ideology stances

Raise `ideological_opinion_impact` from 0 to **0.5**, so groups react to the law in force. France's landowners will
then dislike Forced Heirship from 1836, which matches the Legitimists (Villèle's 1826 bill to restore primogeniture,
rejected by the Chamber of Peers) but lowers France's starting approval; check it.

Stance sets in `ideology_modifications.py` (P C F T S U in §1's order; SA strongly approve, A approve, N neutral,
D disapprove, SD strongly disapprove). The amendments take their stances from their parents (§2), so they need no
column:

| Set | Ideologies | P | C | F | T | S | U |
|---|---|---|---|---|---|---|---|
| traditional | paternalistic, traditionalist, papal and Shinto moralists, Confucian, the three patriarchs, legitimist, bakufu, traditionalist movements | SA | N | D | D | SD | SD |
| moderate | liberal, meritocratic, individualist, hindu moralist | D | N | N | SA | SD | SD |
| reform | reformer, social democrat, buddhist and sikh moralists, orleanist, republican leader, agrarian, Jeffersonian agrarian | D | A | A | N | D | D |
| bonapartist | bonapartist | D | N | SA | N | D | D |
| progressive | proletarian | SD | N | A | D | A | A |
| communist (was communal) | communist, communist and proletarian movements | SD | D | N | SD | SA | D |
| anarchist (new) | anarchist | SD | D | N | SD | D | SA |

The hand-written blocks in `common/ideologies/extra_ideologies.txt` name the two new laws too (the
`ideology_lawgroup_audit` rule). Islamic Inheritance: P D, C A, F A, T D (testation is capped at a third), S D, U D.
Where a custom-religion economy approves Usage Rights for its state-ownership side (socialist, imperial cult,
theocratic), the approval moves to State as Universal Heir and Possession by Use drops to disapprove.

## 9. Open questions

- **Amendment parents** (§2): Perpetual Trusts on `law_laissez_faire` or `law_primogeniture`. Check that the
  vanilla stances on graduated taxation, old-age pensions and peasant proprietorship give sensible backers for the
  duty, the Endowment and the farm amendment.
- **The Endowment swap.** Whether `add_amendment` sees an Estate Duties removal made earlier in the same effect block.
  If not, the swap removes the duty and adds the Endowment in two steps.
- **Ottoman start.** Islamic law is forced heirship in substance, but Ottoman fertility stayed high. On Customary it
  avoids the French effect; the Islamic Inheritance IG can still enact Forced Heirship later.
- **Values**: targets, the 3% drift, modifier sizes, the rural steps, the 0.5 opinion impact.

## 10. Existing content to update

- Events `extra_law_events.17`, `.53`, `.77` trigger on enacting Equal Inheritance or Usage Rights; extend them to the
  new laws. Event 17 uses `digital_privacy_screen.dds`, which doesn't suit an 1830s estate dispute.
- Loc renames (`te_laws_l_english.yml`) and the German translation memory (`i18n/german/tm/te_laws.json`).
- Icons for the two new laws; Possession by Use keeps the Usage Rights icon.
- `gen_law_consistency.py` regenerates `extra_law_consistency_generated.txt` for the new laws on the next reload.
- Player guide: the Inheritance row in `06-politics.md`, Islamic Inheritance's row there, and the petition list in
  `20-appendix-reference-lists.md`.
