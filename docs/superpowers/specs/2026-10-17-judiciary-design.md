# Judiciary: who checks power, and how far the courts are trusted — design

## Context

The owner asked (2026-10-17) for a law group on the court system. Stronger courts should raise baseline legitimacy and
credit standing and lower Legislative Override Capacity, and the group needs options that fit an 1836 start (Qajar
Persia was the example). Neither vanilla nor the mod models courts today. The nearest groups stay as they are:

- **Criminal Justice** (`lawgroup_criminal_justice`, mod): what follows a conviction (prisons, rehabilitation, labour
  camps). This group is about who checks the government, not sentencing. Criminal Justice's description says it covers
  "laws, courts, and law enforcement agencies"; it loses "courts" (§ 11).
- **Internal Security** (vanilla): what home affairs may investigate. Guaranteed Liberties already carries −2 override.
- **State Power** (mod): centralization.

Three existing mechanics take the group's effects with no new plumbing:

- **Legislative Override Capacity** (`country_legislative_override_capacity_add`, about 40 sources;
  `common/laws/legislative_override_capacity.txt` for the vanilla laws). The Forceful Legislation event
  (`minor_events_timelineextended.2`, fired from `on_law_enactment_started`) offers its options at 0, 2 and 4; the tax
  code's Force Through needs 2 (`te_tax_can_force_through`). A court law adds or subtracts like any other source.
- **Credit standing** (`country_credit_standing_add`, `common/modifier_type_definitions/banking_cycle_modifier_types.txt`).
  A **positive** value raises the structural risk premium. The premium is floored at 0.5pp (`te_mon_standing_floor`),
  moved by `country_credit_standing_floor_add` (Central Bank Independence −0.25pp). Rank alone adds +0.5pp for a great
  power, +2pp for a minor power, +8pp for an unrecognized power and +10pp for a decentralized one
  (`common/country_ranks/te_monetary_rank_injections.txt`), so a great power already sits on the floor and standing
  earned below it is wasted (§ 4.3). For scale: the gold standard is −1pp and Central Bank Independence −0.5pp.
- **Legitimacy.** Vanilla's distribution-of-power laws grant tens of points through `country_legitimacy_headofstate_add`
  and the clout and vote terms. The mod's laws and amendments use ±5 to ±10 of `country_legitimacy_base_add`.

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| Laws | Six: Executive Tribunals, **Religious Courts** (added to the original five for the 1836 Islamic world), Statutory Courts, Constitutional Review, Judicial Supremacy, Algorithmic Jurisprudence |
| Names | **Judicial Supremacy**, not "Judicial Activism", which is a partisan label (interest groups may still say "activism" in event text). **Statutory Courts**, not "Legislative Supremacy", which implies a legislature: the name covers Prussia's code-bound judges under a king as well as Britain's under Parliament |
| Judicial Supremacy's description | Must make clear that the courts don't take day-to-day decisions. They decide the cases brought to them. If they governed, it would be a Distribution of Power law |
| Judicial Independence | A slowly built score patterned on the Tradition of Free Elections (§ 3) |
| Effects kept | Less radicalism from enactment disapproval and dearer suppression (owner: yes). Capitalist investment (owner: maybe), kept because it scales by itself with how much of the economy is in private hands, so the courts matter more in a market economy (§ 3.2) |
| Effects left out | A pro-minority radicalism effect: a constitution can as easily thwart protections as extend them (Dred Scott, 1857; the Civil Rights Cases, 1883), so the courts' rights effect is neutral entrenchment instead (§ 3.4). Migration attraction: the owner is unsure, so it stays out of v1 |
| Defying the court; the overhaul shock | In: the shock in phase 1 (§ 3.5), the court challenge in phase 2 (§ 10) |
| Landmark cases | v2. Each case's trigger must be keyed to game state, never a date or a tag, since the alternate timeline may lack the context by the 20th century |
| Amendments | In, phase 3 (§ 10) |
| First PR | This spec and the phase 1 plan only |

**Awaiting the owner.** Five proposals in this spec have not been ruled on: Judicial Supremacy's legitimacy (§ 2.5),
how Judicial Independence is shown (§ 3.6), the credit floor (§ 4.3), Constitutional Review's technology and Judicial
Supremacy's transition gate (§ 2.4, § 2.5). § 12 lists them. The values throughout are first proposals, to be tuned in
the phase 1 play-test.

## 1. The law group

```
lawgroup_judiciary = {
	law_group_category = power_structure
	ideological_opinion_impact = 0.5
	affected_by_regime_change = yes
}
```

`affected_by_regime_change`: courts were imposed with regimes (the constitutional courts of West Germany, 1951, and
postwar Japan, 1947). Impact 0.5: interest groups care about the courts in force, as they do about the inheritance law,
not only during enactment.

The laws live in a new file, `common/laws/te_judiciary_laws.txt`, **Executive Tribunals first**: the first law in the
file is what an unseeded country and an old save get (`docs/systems/mod_systems.md` § Resource Transition).

## 2. The laws

The laws carry what the courts **can do** (their powers); Judicial Independence (§ 3) carries how far they are
**trusted**. A law's flat modifiers hold override capacity, entrenchment, suppression cost, authority, staffing,
interest-group clout and the credit cost of arbitrary justice. The legitimacy, the credit standing and its floor,
capitalist investment and the radicalism damping all scale with the score. Each law sets the score's **ceiling**.

| Law | Key | Progressiveness | Unlock and gates | Ceiling | Flat modifiers |
|---|---|---|---|---|---|
| Executive Tribunals | `law_executive_tribunals` | −50 | None; first in file | 10 | Override +1; authority +50; suppression cost −10%; credit standing +1pp |
| Religious Courts | `law_religious_courts` | −20 | Not under Total Separation or State Atheism (`disallowing_laws`) | 40 | Devout +15% political strength; population bureaucracy cost −5%; credit standing +0.5pp |
| Statutory Courts | `law_statutory_courts` | 0 | `rationalism` | 70 | Suppression cost +10%; population bureaucracy cost +5% |
| Constitutional Review | `law_constitutional_review` | 50 | `human_rights` (proposal, § 2.4) | 100 | Override −2; suppression cost +25%; population bureaucracy cost +5%; entrenchment (§ 3.4) |
| Judicial Supremacy | `law_judicial_supremacy` | 75 | `civil_rights_movement`; from Constitutional Review only (proposal, § 2.5) | 100 | Override −3; suppression cost +40%; population bureaucracy cost +5%; wider entrenchment; legitimacy −3; credit standing +0.3pp; ideological incoherence penalty −25%; movement radicalism −5%, movement pop attraction +5% |
| Algorithmic Jurisprudence | `law_algorithmic_jurisprudence` | 25 | `generative_ai` | 60 | Population bureaucracy cost −10%; override +2 while Algorithmic Governance is in force (§ 2.6) |

Modifier keys: `country_legislative_override_capacity_add`, `country_authority_add`, `country_suppression_cost_mult`,
`country_credit_standing_add` (0.01 = 1pp; the modifier displays one decimal place), `interest_group_ig_devout_pol_str_mult`,
`state_bureaucracy_population_base_cost_factor_mult` (the privacy laws' lever, ±0.05 to ±0.1),
`country_legitimacy_base_add`, `country_legitimacy_ideological_incoherence_mult` (vanilla uses −0.25 to +0.5),
`political_movement_radicalism_add`, `political_movement_pop_attraction_mult`. All are vanilla or already registered by
the mod.

Progressiveness orders the consistency walk (`gen_law_consistency.py`: the nearest valid law by progressiveness
replaces an invalid one). A country holding Religious Courts that enacts Total Separation or State Atheism drops to
Statutory Courts (20 away) when it has Rationalism, else to Executive Tribunals (30 away), never to Algorithmic
Jurisprudence (45 away, and gated by its technology). Executive Tribunals has no gate, so it is the group's terminal
fallback. Total Separation's tooltip can't preview the change (`scripting_best_practices.md`, the cascade preview
note), so Religious Courts' description says so.

### 2.1 Executive Tribunals

The officials who govern also judge, and judges serve at the ruler's pleasure: the Qing county magistrate, the Russian
governor's chancery before 1864, the bakufu's magistrates. Override +1 and authority +50 make it the early-game tool of a
ruler consolidating power. Suppression is cheaper, since nobody frees a dissident on a writ. Lenders charge for justice
the ruler can bend: +1pp.

1836: Russia, Qing China, Japan, Korea, Austria, Siam, and most unrecognized countries.

### 2.2 Religious Courts

Clerical judges apply religious law in most civil and criminal matters, alongside whatever the ruler decrees: the
qadi courts of the Ottoman Empire and Egypt, the mujtahids' courts of Qajar Persia, the ecclesiastical tribunals of the
Papal States. The ceiling is 40 because these judges did not answer to the ruler. The Persian ulama led the Tobacco
Protest of 1891–92 against the shah. But they answered to the faith, not to the state's law. The Devout gain clout. The
courts cost less administration, since clergy staff them on fees and endowments. Foreign lenders charge +0.5pp: these
courts heard commercial disputes with foreigners poorly enough that the Ottomans opened commercial courts in 1840 and
Egypt mixed courts in 1875 (both phase 3 amendments, § 10).

1836: the Ottoman Empire, Persia, Egypt, Morocco, Tunisia, Afghanistan, Bukhara, Khiva, the Papal States.

**Persia.** Persia starts here, with Judicial Independence at 10: half its ceiling, which Autocracy halves from 40 to 20
(§ 3.1). It has a historical path out. The 1905 protesters' first demand was an *adalatkhaneh*, a house of justice,
and the Ottoman path ran through the Nizamiye courts (1864) and the Mecelle code (1869–76) to Statutory Courts. Both
make good event hooks for v2.

### 2.3 Statutory Courts

Judges hold office for life or by career and cannot be dismissed for their rulings, but they apply the law as written.
Whoever makes the law, a parliament or a king in council, has the last word: no court strikes a statute down. Britain
(judges' tenure from the Act of Settlement, 1701), France (the Code civil), Prussia (the General Code of 1794; "there
are still judges in Berlin"), the Netherlands, Belgium, Sweden. Taff Vale (1901), where the Lords made unions liable for
strike losses and Parliament reversed them by statute in 1906, is the law's whole idea. It costs no override and buys a
ceiling of 70.

### 2.4 Constitutional Review

Courts may strike down laws that breach a written constitution. 1836: the United States (Marbury v. Madison, 1803).
Later adopters: Mexico's *amparo* (1847), Norway (1866), Austria's Constitutional Court (1920), West Germany (1951),
Italy (1956). Override −2, dearer suppression and entrenchment (§ 3.4) pay for the highest ceiling.

**Proposal: unlock at Human Rights (era 3), not Democracy (era 1).** The obstacle in 19th-century Europe was the
doctrine of parliamentary sovereignty, not technology. At era 1, Britain and France would have it from day one and the
AI's liberal groups would push it in the 1840s. The United States holds it from history, which ignores unlock
technologies.

### 2.5 Judicial Supremacy

Courts claim the final word on what the constitution means. They read it broadly, to rights it does not name, and
sometimes rule on constitutional amendments themselves (India's basic structure doctrine, Kesavananda Bharati, 1973).
Other examples: the Warren Court (1953–69), Israel's "constitutional revolution" (1992–95), Colombia's court after
1991.

**Description requirement (owner).** The law's description must say the courts do not govern. A draft:

> The courts decide only the cases brought before them, and the government still governs. But the courts' reading of
> the constitution binds the legislature, reaches rights the text does not name, and no ordinary law can overturn it.

**Does overriding parliament make courts more legitimate? Proposal: no, so legitimacy peaks at Constitutional Review.**
Research on public support for courts finds that it rests on the court being seen as a legal body rather than a
political one. It falls when rulings look partisan: confidence in the US Supreme Court fell to 25% in Gallup's 2022
poll after Dobbs. So Judicial Supremacy keeps the full ceiling (an old, independent court is still trusted) but pays a
flat −3 legitimacy as a contested court, netting +7 at full independence against Constitutional Review's +10.

What it offers instead is the reason politicians empower such courts. Divisive questions go to the court, so a
coalition of groups that disagree can govern (Mark Graber, "The Nonmajoritarian Difficulty", 1993). That is a −25%
ideological incoherence penalty. Movements litigate: radicalism −5%, pop attraction +5%. They win more in court and
riot less. The costs are override −3, the widest entrenchment, suppression +40% and +0.3pp credit standing, since
lenders can't predict policy made by rulings.

**Proposal: enacted only from Constitutional Review** (`unlocking_laws = { law_constitutional_review }`). This is a
transition gate from the law's own group, which the consistency walk treats as a gate, not a standing requirement
(the Legacy Slavery precedent in `gen_law_consistency.py`). Supremacy grows out of review. It is not a leap from
magistrates' courts.

### 2.6 Algorithmic Jurisprudence

Models decide routine cases and draft the rest; human judges sign. China's "smart courts" and the Hangzhou Internet
Court (2017) are the start of it. Risk-scoring tools such as COMPAS (ProPublica, 2016) are the warning. The ceiling is 60.
The machine can't be leaned on case by case, but whoever trains it decides what it rules. It is cheap: population
bureaucracy cost −10%.

**The capture.** With Algorithmic Governance also in force, the same system writes the law and judges it: override +2,
from a separate modifier (`te_jud_algorithmic_capture`, § 3.2's refresh). That's on top of the paper-court halving of
the ceiling (§ 3.1, 60 → 30). Combined, the two algorithmic laws become an override tool rather than a check.

## 3. Judicial Independence

### 3.1 The score

- `var:te_judicial_independence` on the country, 0–100.
- **Ceiling**: the law's (§ 2), halved under a **paper court**, a regime whose executive answers to nobody:
  Autocracy and its variants (`has_law_or_variant = law_type:law_autocracy`), Single-Party State and Algorithmic
  Governance. This is the soft cap for strong courts under autocracy. Constitutional Review stays enactable there,
  but a court the autocrat can ignore earns half the trust.
- **Yearly** (`on_yearly_pulse_country`): below the ceiling +4, stopping at it; above the ceiling −10, stopping at it. From
  0, a Constitutional Review court reaches 100 in 25 years. A court that moved up from Statutory (70) gets there in 8.
- Patterned on the Tradition of Free Elections: earned slowly, and carried across a change of law. A country that leaves
  a strong court keeps its score above the new ceiling, losing 10 a year, so coming back within a few years recovers
  most of it (the owner's no-micromanagement default: progress isn't erased the moment the law changes).
- State lives in variables only, so a revolution's winner inherits the score and the refresh rebuilds the modifier
  (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").

### 3.2 What it does

One static modifier, `te_judicial_independence`, applied with `multiplier = var:te_jud_modifier_mult` (score ÷ 100;
the variable is kept, never removed, since the engine re-reads it). Values at 100:

| Modifier | At 100 | Why |
|---|---|---|
| `country_legitimacy_base_add` | +10 | Trusted courts lend the state their authority |
| `country_credit_standing_add` | −0.005 (−0.5pp) | Contracts and debts are enforced (North and Weingast, "Constitutions and Commitment", 1989) |
| `country_credit_standing_floor_add` | −0.001 (−0.1pp) | Proposal, § 4.3 |
| `state_capitalists_investment_pool_efficiency_mult` | +0.10 | Property is safe. Under Command Economy the investment pool is disabled (vanilla `country_disable_investment_pool_bool`), so this is worth nothing there; it is worth most where capitalists hold most of the wealth (Laissez-Faire). No condition is needed for courts to matter more in a market economy |
| `political_movement_radicalism_from_enactment_disapproval_mult` | −0.20 | Losers accept an outcome a trusted court can review ("losers' consent", Anderson et al., 2005) |

**Refresh.** One writer: `te_jud_refresh`, from `on_monthly_pulse_country` (ROOT = the country), the modifier's
only refresh site. It sets the multiplier variable, removes and re-adds the modifier, and adds or removes
`te_jud_algorithmic_capture`. The score changes yearly and when spent (§ 3.3), so the modifier lags a change by at most
a month.

### 3.3 Spending it

| What | Cost |
|---|---|
| Forceful Legislation, "Expedite" (option b) | −5 |
| Forceful Legislation, "Push decisively" (option c) | −10 |
| Forceful Legislation, "Force it through" (option e) | −20 |
| Tax code Force Through (`te_tax_force_into`, which applies option c's modifiers) | −10 |
| Phase 2: defying a ruling, packing the court (§ 10) | to be set |

The score is floored at 0. Each option shows its cost in a `custom_tooltip` (the silent-variable rule). The costs apply
under every court law: under Executive Tribunals the score is near 0, so they cost almost nothing, as they should.

### 3.4 Entrenchment

Under Constitutional Review or Judicial Supremacy, and not under a paper court, starting the enactment of a law in a
**protected group** adds an enactment modifier (`add_enactment_modifier`, at `on_law_enactment_started`; the
Forceful Legislation event uses the same call at the same hook):

| Court | Protected groups | Enactment modifier |
|---|---|---|
| Constitutional Review | Distribution of Power, Governance Principles, Church and State, Citizenship, Free Speech, Internal Security, State Power, Judiciary | `te_jud_constitutional_challenge`: enactment success −10% |
| Judicial Supremacy | The above, plus Rights of Women, Slavery, Minority Rights, LGBTQ+ Rights, Privacy Rights | `te_jud_supremacy_challenge`: enactment success −15% |

It is **neutral by design**: the court defends whatever constitution is in force, so a progressive reform pays the same
as a reactionary one. Dred Scott and Brown v. Board both came from courts. The Judiciary group protects itself
(Israel's court struck down the 2023 reasonableness amendment in 2024), which makes court-curbing slow and is phase 2's
reason to pack instead. Constitutional Review's rule also stands in for the vanilla per-law modifiers
(`country_enactment_success_chance_law_autocracy_add` and its siblings) for every group at once.

**Trigger.** `currently_enacting_law ?= { type = { OR = { is_same_law_group_as = law_type:<one law per group> … } } }`
(`currently_enacting_law` is a country → law link, `type` a law → law type link, `is_same_law_group_as` a law type
trigger: `docs/engine/event_targets_summary.txt`, `triggers_summary.txt`). Whether the link resolves at this hook is
unread. The once-a-game self-check (§ 9) reports it.

### 3.5 The overhaul shock

When any law that sets the ceiling is activated (the six court laws, Autocracy and its variants, Single-Party State,
Algorithmic Governance), a hidden country event checks the gap between the score and the new ceiling. At 20 or more it
applies `te_jud_court_overhaul` for 5 years, decaying, with `multiplier` = gap ÷ 100:

| Modifier | At a gap of 100 |
|---|---|
| `country_risk_premium_add` | +0.02 (+2pp, cyclical: added after the floor, so it always bites) |
| `country_legitimacy_base_add` | −10 |

At a gap of 40 or more it also adds middle-strata radicals (`add_radicals = { value = small_radicals strata = middle }`),
the protests. One rule covers a court downgrade (Constitutional Review at 90 → Executive Tribunals: gap 80) and a
self-coup that turns the court into a paper court (Constitutional Review at 90 → Autocracy: ceiling 50, gap 40).
Historical anchors: Moody's lowered Israel's outlook in April 2023, citing the judicial overhaul; the EU withheld funds
from Poland over its 2015–23 court changes.

`on_law_activated` runs with ROOT = the law, and script values that read country variables fail there
(`scripting_best_practices.md`). The on-action only matches the law type and fires `te_judiciary_events.1` on `owner`.
The event does the arithmetic with ROOT = the country, so the multiplier resolves correctly. It needs `te_jud_seeded`,
so seeding (§ 6) never shocks. A revolution's winner doesn't inherit the shock (no modifiers are inherited); that's
accepted.

### 3.6 How it is shown (proposal)

The owner is torn. **Proposal: visible, without a journal entry.** The score is something the player invests in for
decades and spends at decision time ("Judicial Independence −10" must mean something when it's offered), and the house
style puts dynamic content in the open (`docs/guides/gui_style_guide.md` rule 1). But a journal entry is for a system
the player works through, and phase 1 has nothing to press. The Inheritance concentration score is the precedent:

- a game concept, `concept_judicial_independence`, whose description explains the score and ends with
  "Now #v X#!, heading for #v Y#!." (`te_jud_display`, `te_jud_ceiling`), as `concept_inheritance_concentration_desc`
  does;
- the scaled `te_judicial_independence` modifier in the country's modifier list, showing what the score buys now;
- each court law's `on_enact` tooltip naming its ceiling;
- each spending option naming its cost.

If phase 2's court challenges make the score something the player manages, a small section in an existing panel can
follow.

## 4. Balance

### 4.1 At full independence, with no paper court

| Law | Score | Legitimacy | Credit standing | Floor | Override | Other |
|---|---|---|---|---|---|---|
| Executive Tribunals | 10 | +1 | +0.95pp | −0.01pp | +1 | Authority +50, cheaper suppression |
| Religious Courts | 40 | +4 | +0.30pp | −0.04pp | 0 | Devout clout, cheaper administration |
| Statutory Courts | 70 | +7 | −0.35pp | −0.07pp | 0 | — |
| Constitutional Review | 100 | +10 | −0.50pp | −0.10pp | −2 | Entrenchment, suppression +25% |
| Judicial Supremacy | 100 | +7 | −0.20pp | −0.10pp | −3 | Incoherence −25%, wider entrenchment, suppression +40% |
| Algorithmic Jurisprudence | 60 | +6 | −0.30pp | −0.06pp | 0 (+2) | Administration −10% |

Investment efficiency and the radicalism damping scale with the score the same way (+10% and −20% at 100).

### 4.2 Why each law gets chosen

The table is deliberately not monotone, so there is no "just climb":

- **Executive Tribunals:** authority and override are what a consolidating ruler is short of in 1836.
- **Religious Courts:** the Devout's price, with cheap administration. The Islamic world's status quo.
- **Statutory Courts:** most of the trust at no cost in override. The 19th-century liberal default.
- **Constitutional Review:** the most legitimacy and credit, paid for in override (no medium Forceful Legislation tier,
  no tax Force Through), dearer suppression and slower constitutional change.
- **Judicial Supremacy:** broad coalitions and quieter movements, for less legitimacy than Review.
- **Algorithmic Jurisprudence:** cheap and middling on its own; with Algorithmic Governance, a captured court.

### 4.3 Credit standing and the floor (proposal)

A great power's rank puts it on the 0.5pp floor already, so the −0.5pp of a trusted court is invisible to Britain or
France. It matters to minor and unrecognized countries, which is historically apt: small states bought cheap credit
with credible institutions. **Proposal:** the score also moves the floor, up to −0.1pp at 100. That is a quarter of
Central Bank Independence's −0.25pp and stacks with it (`te_mon_standing_floor` clamps at 0). A great power then
feels its courts, but only after decades. The alternative is to leave the floor alone and let the benefit go to the
smaller countries.

### 4.4 Override totals

A mature democracy ends below 0 under Constitutional Review: Universal Suffrage −3, Guaranteed Liberties −2 and the court
−2 make −7. No Forceful Legislation option appears and tax Force Through is closed. That is intended: those are exactly
the shortcuts a constitutional court exists to stop.

## 5. Starting laws (1836)

In `common/history/extra_history.txt`, after vanilla history, through one scripted effect,
`te_jud_assign_court_by_rule`, which § 6's old-save seeding also calls (history already calls scripted effects:
`gm_com_seed`):

1. **Religious Courts:** Theocracy; or a Sunni, Shia or Ibadi state religion (`country_has_state_religion`; the three
   religions with `heritage_islamic`) under State Religion or a variant (`has_law_or_variant`) or Freedom of
   Conscience.
2. **Statutory Courts:** a voting law (Landed, Wealth or Census Voting, Universal Suffrage).
3. Otherwise Executive Tribunals, the first law in the file.

Then, in the country blocks history already has: the United States → Constitutional Review; Britain, France, Prussia,
the Netherlands, Sweden and Belgium → Statutory Courts, whatever their 1836 franchise.

**Starting score:** half the effective ceiling, set at game start (§ 6), except where history sets it first:
Britain 70, the United States 60, the Netherlands 50, Sweden 50, Belgium 40, Prussia 35, France 35.

## 6. Seeding, old saves and new countries

- **New game:** `on_game_started` runs `te_jud_seed_score` on every country: the score is half the ceiling unless
  history set it, and `te_jud_seeded` is set. It applies no modifier, so ROOT = none there does no harm (the
  inheritance system needs an event only because it applies multipliers); the first monthly refresh adds the
  modifier. It also sets the global `te_jud_world_seeded`.
- **Old save** (no `te_jud_world_seeded`): every country holds Executive Tribunals, the first law in the file. On the
  first `on_monthly_pulse`, every country runs `te_jud_assign_court_by_rule` once, then the score's seeding, and the
  global is set. Laws activated there don't shock: the shock event either runs before `te_jud_seeded` is set or finds
  the score at half the new ceiling.
  This is an old-save repair (`common/on_actions/te_old_save_repairs.txt`, with its removal marker).
- **A new country mid-game** (release, secession) without `te_jud_seeded`: the monthly pulse seeds its score from the
  law it holds. Its law isn't changed.
- **A revolution's winner** inherits the variables, so nothing is reseeded.

## 7. Ideology stances

The stances live in named lists in `ideology_modifications.py` (`JUDICIARY_LISTS`, keyed by the names below, and
`JUDICIARY_STANCES`, ideology → list). Every list names all six laws, as the
`ideology_lawgroup` audit requires. `apply_ideologies.py` writes the vanilla ideologies (an INJECT, since vanilla has no
block for the group, which `scripts/generators/regen_ideologies_offline.py` can produce without the game). The mod's
own ideologies get hand-written blocks in `common/ideologies/extra_ideologies.txt`.

| List | Executive | Religious | Statutory | Constitutional | Supremacy | Algorithmic |
|---|---|---|---|---|---|---|
| absolutist | ++ | 0 | − | −− | −− | 0 |
| traditional | + | 0 | + | − | −− | − |
| religious | 0 | ++ | − | − | −− | −− |
| liberal | −− | − | + | ++ | 0 | − |
| anticlerical | −− | −− | + | ++ | 0 | − |
| market | − | − | + | ++ | − | + |
| rights | −− | −− | 0 | + | ++ | − |
| labour | − | − | ++ | 0 | − | 0 |
| populist | 0 | 0 | ++ | − | −− | − |
| vanguard | ++ | −− | − | −− | −− | + |
| technocratic | − | −− | + | + | − | ++ |

Labour's distrust of strong courts is historical: Taff Vale, Lochner v. New York (1905) and the labour injunctions.
Populists want the people's representatives to have the last word, as Jackson did over Worcester v. Georgia (1832).

| Ideologies | List |
|---|---|
| `ideology_loyalist`, `ideology_authoritarian`, `ideology_military_absolutist`, `ideology_reactionary`, `ideology_reactionary_movement`, `ideology_royalist_movement`, `ideology_absolutist_movement` | absolutist |
| `ideology_paternalistic`, `ideology_hierarchic`, `ideology_patriarchal`, `ideology_patriotic`, `ideology_jingoist`, `ideology_royalist`, `ideology_legitimist`, `ideology_bonapartist` | traditional |
| `ideology_pious`, `ideology_moralist`, `ideology_theocrat`, the `*_moralist` and `*_patriarch` variants, `ideology_papal_paternalistic`, `ideology_islamic_inheritance` (mod) | religious |
| `ideology_liberal`, `ideology_liberal_leader`, `ideology_republican`, `ideology_republican_leader`, `ideology_individualist`, `ideology_constitutionalist`, `ideology_liberal_movement` | liberal |
| `ideology_anti_clerical` | anticlerical |
| `ideology_laissez_faire`, `ideology_plutocratic`, `ideology_market_liberal`, `ideology_corporate` (mod) | market |
| `ideology_liberal_modern`, `ideology_egalitarian_modern`, `ideology_humanitarian`, `ideology_feminist`, `ideology_multicultural` (mod) | rights |
| `ideology_proletarian`, `ideology_egalitarian`, `ideology_socialist`, `ideology_social_democrat`, `ideology_socialist_movement` | labour |
| `ideology_populist`, `ideology_agrarian`, `ideology_jacksonian_democrat` | populist |
| `ideology_communist`, `ideology_vanguardist`, `ideology_fascist`, and their `_movement` ideologies | vanguard |
| `ideology_technocratic`, `ideology_positivist`, `ideology_meritocratic`, `ideology_optimist_transhumanist` (mod) | technocratic |

Custom-religion ideologies (mod): `theocratic_governance` and `theocratic_society` → religious,
`technocratic_governance` → technocratic, `republican_governance` → liberal, `aristocratic_governance` → traditional,
`corporate_governance` → market, `imperial_cult_governance` → absolutist. Everything else stays neutral. Every key
named here exists in `vanilla_parsed/common/ideologies.json` or `extra_ideologies.txt` (checked 2026-10-17).

The early-game effect in the Islamic world: the Devout (pious, moralist) back Religious Courts, and the Intelligentsia
(liberal, anti-clerical) push for Statutory Courts. That's the Tanzimat's argument.

## 8. AI

Enactment follows the stances. Each law carries the mod's standard `ai_enact_weight_modifier` (10, +750 under
`ai_has_enact_weight_modifier_journal_entries`). Nothing else in phase 1. The play-test watches for an AI that flips
between court laws chasing approval: the 10-a-year decay and the overhaul shock should make that costly.

## 9. Engine facts to verify

Per the in-game checks rule (`CLAUDE.md`): ship the preferred version, log a once-a-game `TE_SELF_CHECK` line and list
the rest for the play-test (`docs/testing/judiciary-playtest.md`, new).

| Fact | Check |
|---|---|
| `currently_enacting_law` resolves at `on_law_enactment_started` | `TE_SELF_CHECK OK judiciary_enacting_law_scope` (or `BROKEN`), once a game, logged the first time any country under Constitutional Review or Judicial Supremacy starts an enactment (`enacting_any_law = yes` holds, so a missing link can't pass as OK) |
| `add_enactment_modifier` from an on-action effect applies | Play-test: the enactment panel lists "Constitutional Challenge" for a Distribution of Power law under Constitutional Review. Fallback: move the call into a hidden event, as Forceful Legislation runs |
| A scripted effect runs from history | Play-test: the lobby shows the United States with Constitutional Review and Persia with Religious Courts |
| The concept renders the live score | `loc_render_audit` offline; play-test reads it |

## 10. Later phases

Each later phase gets its own plan once phase 1 has been play-tested, since their details depend on how the score
behaves.

- **Phase 2: defying the court.** Under Constitutional Review or Judicial Supremacy (not a paper court), taking a
  Forceful Legislation option opens a challenge. Some months later the court rules:
  - **comply**: legitimacy, and the forced law's gains are clawed back;
  - **defy**: a larger score loss and the overhaul shock's credit term;
  - **pack the court**: an authority cost, a score loss, and a later event offering a drop to Statutory Courts.

  The open engine question is whether a variable can hold the replaced law's type, so that compliance can restore it.
  If not, compliance costs the forced law's legitimacy instead of reversing it. An overhaul-protest event replaces the
  bare radicals of § 3.5.
- **Phase 3: amendments.** Every amendment has a scripted way in (an event or a petition), per the mod's rule:
  - **Suspension of Habeas Corpus** (Statutory or Constitutional; an Armed Forces petition in wartime, with a sunset;
    Lincoln, 1861);
  - **Judicial Elections** (Statutory or Constitutional; Jacksonian Democrats; Mississippi 1832, New York 1846);
  - **Mixed Commercial Courts** (Religious or Executive; better credit standing; the Industrialists; Ottoman 1840,
    Egypt 1875);
  - **Jury Trials** (Statutory or Constitutional; Russia's 1864 reform);
  - **Military Tribunals for Civilians** (Executive or Statutory; the Armed Forces);
  - **People's Tribunals** (Executive under Single-Party State; vanguard ideologies);
  - **Human-in-the-Loop Appeals** (Algorithmic; legitimacy for efficiency).
- **Phase 4 (v2): landmark cases.** Events keyed to game state, never dates or tags:
  - a slavery ruling under Constitutional Review while slavery is legal and an abolition movement is active (Dred Scott);
  - a court that refuses the government's demand for an execution under diplomatic pressure (the Ōtsu Incident, 1891);
  - labour laws struck down under Judicial Supremacy (Lochner, and the 1937 court-packing plan);
  - a court that voids the ruler's election (Allahabad, 1975, and the Emergency that followed);
  - a court that validates a coup (Pakistan's "doctrine of necessity", 1955 and 1958);
  - Persia's *adalatkhaneh* and the Ottoman Nizamiye courts as reform paths out of Religious Courts.

## 11. Existing content to update

- `lawgroup_criminal_justice_desc` (`localization/english/te_laws_l_english.yml`): drop "courts".
- `concept_legislative_override_capacity_desc`: name the court laws among the sources.
- `docs/guides/scripting_best_practices.md` (the override sources list) and `docs/systems/tax_code_schema.md` § 7.4
  (Force Through's costs).
- `docs/systems/mod_systems.md`: a new § Judiciary.
- Player guide: `06-politics.md` (the law group table, the Forceful Legislation sources and costs, a short paragraph on
  Judicial Independence) and `04-banking.md` (a credit standing source), at the depth of their peers; rebuild the PDF.

## 12. Open questions for the owner

1. **Judicial Supremacy's legitimacy** (§ 2.5): −3 flat, so it nets +7 against Constitutional Review's +10, with
   incoherence −25% as its draw?
2. **Showing the score** (§ 3.6): a concept with the live value plus the scaled modifier, no journal entry?
3. **The credit floor** (§ 4.3): −0.1pp at full independence, or leave the floor alone?
4. **Constitutional Review's technology** (§ 2.4): Human Rights (era 3) or Democracy (era 1)?
5. **Judicial Supremacy only from Constitutional Review** (§ 2.5)?
