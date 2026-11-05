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
  A **positive** value raises the structural risk premium. The premium is floored at 0.5pp (`te_mon_standing_floor`).
  Rank alone adds +0.5pp for a great power, +2pp for a minor power, +8pp for an unrecognized power and +10pp for a
  decentralized one (`common/country_ranks/te_monetary_rank_injections.txt`), so a great power already sits on the
  floor and standing earned below it is wasted (§ 4.3). For scale: the gold standard is −1pp and Central Bank
  Independence −0.5pp.
- **Legitimacy.** Vanilla's distribution-of-power laws grant tens of points through `country_legitimacy_headofstate_add`
  and the clout and vote terms. The mod's laws and amendments use ±5 to ±10 of `country_legitimacy_base_add`.

## Decisions (owner, 2026-10-17)

| Question | Decision |
|---|---|
| Laws | Six: Executive Tribunals, **Religious Courts** (added to the original five for the 1836 Islamic world), Statutory Courts, Constitutional Review, Judicial Supremacy, Algorithmic Jurisprudence |
| Names | **Judicial Supremacy**, not "Judicial Activism", which is a partisan label (interest groups may still say "activism" in event text). **Statutory Courts**, not "Legislative Supremacy", which implies a legislature: the name covers Prussia's code-bound judges under a king as well as Britain's under Parliament |
| Judicial Supremacy's description | Must make clear that the courts don't take day-to-day decisions. They decide the cases brought to them. If they governed, it would be a Distribution of Power law |
| Judicial Supremacy's numbers | Legitimacy −5 (+5 net at full independence, against Constitutional Review's +10); movement radicalism −10%, pop attraction +10% |
| Judicial Supremacy's gate | **None.** From Statutory Courts it is a legislature legislating itself out of supremacy. Had it to follow Constitutional Review only, it would be an amendment to that law instead |
| Statutory Courts | A small thematic bonus, by who makes the law: legitimacy from votes under an elected government, authority without one (§ 2.3) |
| Tooltips | Every rule a player plans around is on the law's tooltip, as a script-only modifier line the script reads (§ 2.7). No player should be surprised that a law is hard to change under Constitutional Review |
| Constitutional Review's technology | Human Rights (era 3). The United States holds the law from history before it has the technology, a pattern the mod already has |
| Credit floor | **No.** The score doesn't move the floor; the credit benefit goes to the countries below it (§ 4.3) |
| Judicial Independence | A slowly built score patterned on the Tradition of Free Elections (§ 3) |
| Effects kept | Less radicalism from enactment disapproval and dearer suppression (owner: yes). Capitalist investment (owner: maybe), kept because it scales by itself with how much of the economy is in private hands, so the courts matter more in a market economy (§ 3.2) |
| Effects left out | A pro-minority radicalism effect: a constitution can as easily thwart protections as extend them (Dred Scott, 1857; the Civil Rights Cases, 1883), so the courts' rights effect is neutral entrenchment instead (§ 3.4). Migration attraction: the owner is unsure, so it stays out of v1 |
| Defying the court; the overhaul shock | In: the shock in phase 1 (§ 3.5), the court challenge in phase 2 (§ 10) |
| Landmark cases | v2. Each case's trigger must be keyed to game state, never a date or a tag, since the alternate timeline may lack the context by the 20th century |
| Amendments | In, phase 3 (§ 10) |
| A tab for national modifiers | The owner wants one: a Timeline Extended window tab for scores such as Judicial Independence and Legislative Override Capacity, with the country panel's modifier list hiding them. A separate spec (§ 13) |
| First PR | This spec and the phase 1 plan only |

The values throughout are first proposals, to be tuned in the phase 1 play-test.

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
interest-group clout and the credit cost of arbitrary justice. The legitimacy, the credit standing, capitalist
investment and the radicalism damping all scale with the score. Each law sets the score's **ceiling**. Every
conditional rule is a tooltip line (§ 2.7).

| Law | Key | Progressiveness | Unlock and gates | Ceiling | Flat modifiers |
|---|---|---|---|---|---|
| Executive Tribunals | `law_executive_tribunals` | −50 | None; first in file | 10 | Override +1; authority +50; suppression cost −10%; credit standing +1pp |
| Religious Courts | `law_religious_courts` | −20 | Not under Total Separation or State Atheism (`disallowing_laws`) | 40 | Devout +15% political strength; population bureaucracy cost −5%; credit standing +0.5pp |
| Statutory Courts | `law_statutory_courts` | 0 | `rationalism` | 70 | Suppression cost +10%; population bureaucracy cost +5%; with an elected government +10 legitimacy from votes, without one +25 authority |
| Constitutional Review | `law_constitutional_review` | 50 | `human_rights` | 100 | Override −2; suppression cost +25%; population bureaucracy cost +5%; constitutional laws' enactment success −10% (§ 3.4) |
| Judicial Supremacy | `law_judicial_supremacy` | 75 | `civil_rights_movement` | 100 | Override −3; suppression cost +40%; population bureaucracy cost +5%; constitutional and rights laws' enactment success −15%; legitimacy −5; credit standing +0.3pp; ideological incoherence penalty −25%; movement radicalism −10%, movement pop attraction +10% |
| Algorithmic Jurisprudence | `law_algorithmic_jurisprudence` | 25 | `generative_ai` | 60 | Population bureaucracy cost −10%; override +2 while Algorithmic Governance is in force (§ 2.6) |

Modifier keys: `country_legislative_override_capacity_add`, `country_authority_add`, `country_suppression_cost_mult`,
`country_credit_standing_add` (0.01 = 1pp; the modifier displays one decimal place), `interest_group_ig_devout_pol_str_mult`,
`state_bureaucracy_population_base_cost_factor_mult` (the privacy laws' lever, ±0.05 to ±0.1),
`country_legitimacy_base_add`, `country_legitimacy_ideological_incoherence_mult` (vanilla uses −0.25 to +0.5),
`political_movement_radicalism_add`, `political_movement_pop_attraction_mult`, and the script-only lines of § 2.7. All
are vanilla, already registered by the mod, or registered by this group.

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

**The bonus follows whoever makes the law** (owner). Under an elected government (a voting law or Anarchy, which the
mod counts as electoral) the legislature's word is final, and the government elected to make it gains standing: +10
legitimacy from votes (`country_legitimacy_govt_total_votes_add`, Presidential Republic's figure). Without one, the
crown's word is final: +25 authority, half of Executive Tribunals' +50, which keeps its override and cheap
suppression. Both show on the law's tooltip as conditional lines (§ 2.7); `te_jud_refresh` applies whichever holds.

### 2.4 Constitutional Review

Courts may strike down laws that breach a written constitution. 1836: the United States (Marbury v. Madison, 1803).
Later adopters: Mexico's *amparo* (1847), Norway (1866), Austria's Constitutional Court (1920), West Germany (1951),
Italy (1956). Override −2, dearer suppression and entrenchment (§ 3.4) pay for the highest ceiling.

It unlocks at **Human Rights** (era 3, owner). The obstacle in 19th-century Europe was the doctrine of parliamentary
sovereignty, not technology: at Democracy (era 1), Britain and France would have it from day one and the AI's liberal
groups would push it in the 1840s. The United States holds it from history, which ignores unlock technologies.

### 2.5 Judicial Supremacy

Courts claim the final word on what the constitution means. They read it broadly, to rights it does not name, and
sometimes rule on constitutional amendments themselves (India's basic structure doctrine, Kesavananda Bharati, 1973).
Other examples: the Warren Court (1953–69), Israel's "constitutional revolution" (1992–95), Colombia's court after
1991.

**Description requirement (owner).** The law's description must say the courts do not govern:

> The courts decide only the cases brought before them, and the government still governs. But the courts' reading of
> the constitution binds the legislature, reaches rights the text does not name, and no ordinary law can overturn it.

**Legitimacy peaks at Constitutional Review.** Research on public support for courts finds that it rests on the court
being seen as a legal body rather than a political one, and it falls when rulings look partisan: confidence in the US
Supreme Court fell to 25% in Gallup's 2022 poll after Dobbs. Judicial Supremacy keeps the full ceiling (an old,
independent court is still trusted) but pays a flat −5 legitimacy as a contested court, netting +5 at full
independence against Constitutional Review's +10 (owner).

What it offers instead is the reason politicians empower such courts. Divisive questions go to the court, so a
coalition of groups that disagree can govern (Mark Graber, "The Nonmajoritarian Difficulty", 1993). That is a −25%
ideological incoherence penalty. Movements litigate: radicalism −10%, pop attraction +10% (owner). They win more in
court and riot less. The costs are override −3, the widest entrenchment, suppression +40% and +0.3pp credit standing,
since lenders can't predict policy made by rulings.

**Reachable from any court** (owner). From Statutory Courts it is a legislature legislating itself out of supremacy,
as Israel's Knesset did with its 1992 Basic Laws. Had it to follow Constitutional Review only, it would be an amendment
to that law rather than a law of its own.

### 2.6 Algorithmic Jurisprudence

Models decide routine cases and draft the rest; human judges sign. China's "smart courts" and the Hangzhou Internet
Court (2017) are the start of it. Risk-scoring tools such as COMPAS (ProPublica, 2016) are the warning. The ceiling is 60.
The machine can't be leaned on case by case, but whoever trains it decides what it rules. It is cheap: population
bureaucracy cost −10%.

**The capture.** With Algorithmic Governance also in force, the same system writes the law and judges it: override +2.
That's on top of the paper-court halving of the ceiling (§ 3.1, 60 → 30). Combined, the two algorithmic laws become an
override tool rather than a check.

### 2.7 Every rule on the tooltip

The owner's rule: a player must be able to read every rule they plan around from the tooltips. The banking dials are
the pattern (`banking_cycle_modifier_types.txt`): the law carries the number as a `script_only` modifier line, so its
own tooltip states the rule and the engine renders the breakdown, and script reads the sum and applies the effect.
A later law, technology or amendment moves the same dial without a script edit.

| Line (`common/modifier_type_definitions/judiciary_modifier_types.txt`) | On | Read by |
|---|---|---|
| `country_judicial_independence_ceiling_add` | Each court law: 10, 40, 70, 100, 100, 60 | `te_jud_ceiling` |
| `country_judicial_independence_ceiling_mult` | The paper courts (§ 3.1): −50% | `te_jud_ceiling` |
| `country_court_challenges_ignored_bool` | The paper courts | `te_jud_paper_court` (§ 3.4) |
| `country_constitutional_law_enactment_success_add` | Constitutional Review −10%, Judicial Supremacy −15% | `te_jud_enactment_started` (§ 3.4) |
| `country_rights_law_enactment_success_add` | Judicial Supremacy −15% | `te_jud_enactment_started` |
| `country_legitimacy_from_votes_if_elected_add` | Statutory Courts +10 | `te_jud_refresh` (§ 2.3) |
| `country_authority_if_unelected_add` | Statutory Courts +25 | `te_jud_refresh` |
| `country_override_with_algorithmic_governance_add` | Algorithmic Jurisprudence +2 | `te_jud_refresh` (§ 2.6) |

Each line's name says when it applies ("Legitimacy from Votes, with an Elected Government") and its description lists
the law groups or laws involved. So Constitutional Review's tooltip shows "Enactment Success of Constitutional Laws
−10%" before the player enacts it, and Autocracy's shows "Judicial Independence Ceiling −50%" and "Courts Can’t
Challenge the Government". The paper-court lines are INJECTed into Autocracy, Bakufu, Neo-Absolutism and Single-Party
State (`common/laws/te_judiciary_law_injections.txt`; INJECTed modifier blocks add to a law's own) and written inline in
Algorithmic Governance.

Where the engine needs a named modifier, the line picks it. Entrenchment's enactment modifiers come in two tiers, −10%
and −15%, and every enactment-success line must be one of them (`test_judiciary.py`). The ceiling and the conditional
lines need no tiers: they are read as numbers.

## 3. Judicial Independence

### 3.1 The score

- `var:te_judicial_independence` on the country, 0–100.
- **Ceiling** (`te_jud_ceiling`): the court law's ceiling line times the paper court's. A **paper court** is a regime
  whose executive answers to nobody: Autocracy and its variants, Single-Party State and Algorithmic Governance. They
  carry −50% on the ceiling. This is the soft cap for strong courts under autocracy: Constitutional Review stays
  enactable there, but a court the autocrat can ignore earns half the trust.
- **Yearly** (`on_yearly_pulse_country`): below the ceiling +4, stopping at it; above the ceiling −10, stopping at it.
  From 0, a Constitutional Review court reaches 100 in 25 years. A court that moved up from Statutory (70) gets there in
  8.
- Patterned on the Tradition of Free Elections: earned slowly, and carried across a change of law. A country that leaves
  a strong court keeps its score above the new ceiling, losing 10 a year, so coming back within a few years recovers
  most of it (the owner's no-micromanagement default: progress isn't erased the moment the law changes).
- State lives in variables only, so a revolution's winner inherits the score and the refresh rebuilds the modifiers
  (`scripting_best_practices.md` § "What a Civil War's Winner Inherits").
- **Modifier sums lag a law change.** The ceiling is read from them, so nothing reads it on the day a law changes:
  scores are first seeded at a monthly pulse (§ 6), and the shock waits a week (§ 3.5).

### 3.2 What it does

One static modifier, `te_judicial_independence`, applied with `multiplier = var:te_jud_modifier_mult` (score ÷ 100;
the variable is kept, never removed, since the engine re-reads it). Values at 100:

| Modifier | At 100 | Why |
|---|---|---|
| `country_legitimacy_base_add` | +10 | Trusted courts lend the state their authority |
| `country_credit_standing_add` | −0.005 (−0.5pp) | Contracts and debts are enforced (North and Weingast, "Constitutions and Commitment", 1989) |
| `state_capitalists_investment_pool_efficiency_mult` | +0.10 | Property is safe. Under Command Economy the investment pool is disabled (vanilla `country_disable_investment_pool_bool`), so this is worth nothing there; it is worth most where capitalists hold most of the wealth (Laissez-Faire). No condition is needed for courts to matter more in a market economy |
| `political_movement_radicalism_from_enactment_disapproval_mult` | −0.20 | Losers accept an outcome a trusted court can review ("losers' consent", Anderson et al., 2005) |

**Refresh.** One writer: `te_jud_refresh`, from `on_monthly_pulse_country` (ROOT = the country), the only refresh site
of the four scaled modifiers: the score's, Statutory Courts' two conditional ones (`te_jud_votes_legitimacy`,
`te_jud_unelected_authority`, one unit each times the law's line) and the capture (`te_jud_algorithmic_capture`). The
score changes yearly and when spent (§ 3.3), so the modifier lags a change by at most a month.

### 3.3 Spending it

| What | Cost |
|---|---|
| Forceful Legislation, "Expedite" (option b) | −5 |
| Forceful Legislation, "Push decisively" (option c) | −10 |
| Forceful Legislation, "Force it through" (option e) | −20 |
| Tax code Force Through (`te_tax_force_into`, which applies option c's modifiers) | −10 |
| Phase 2: defying a ruling (§ 14.1) | −20 |
| Phase 2: packing the court (§ 14.1) | −15 |
| Phase 4: the landmark cases' answers (§ 14.3) | −5 to −30 |

The score is floored at 0. Each option shows its cost in a `custom_tooltip` (the silent-variable rule). The costs apply
under every court law: under Executive Tribunals the score is near 0, so they cost almost nothing, as they should.

### 3.4 Entrenchment

Under a court whose tooltip carries an enactment-success line, and not under a paper court, starting the enactment of
a law in a **protected group** adds an enactment modifier (`add_enactment_modifier`, at `on_law_enactment_started`; the
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

The player reads it in three places: the court law's tooltip before enacting it (§ 2.7), the enactment's own modifier
list once a protected law is under way, and the concept.

**Trigger.** `currently_enacting_law ?= { type = { OR = { is_same_law_group_as = law_type:<one law per group> … } } }`
(`currently_enacting_law` is a country → law link, `type` a law → law type link, `is_same_law_group_as` a law type
trigger: `docs/engine/event_targets_summary.txt`, `triggers_summary.txt`). Whether the link resolves at this hook is
unread. The once-a-game self-check (§ 9) reports it.

### 3.5 The overhaul shock

When any law that moves the ceiling is activated (the six court laws, Autocracy and its variants, Single-Party State,
Algorithmic Governance), a hidden country event checks the gap between the score and the new ceiling a week later. At
20 or more it applies `te_jud_court_overhaul` for 5 years, decaying, with `multiplier` = gap ÷ 100:

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
(`scripting_best_practices.md`). The on-action only matches the law type and fires `te_judiciary_events.1` on `owner`,
seven days on, once the new law's modifier sums are in place. The event does the arithmetic with ROOT = the country, so
the multiplier resolves correctly. It needs `te_jud_seeded`, so seeding (§ 6) never shocks. A revolution's winner
doesn't inherit the shock (no modifiers are inherited); that's accepted.

### 3.6 How it is shown

Phase 1 shows the score without a journal entry, the Inheritance concentration score's way:

- a game concept, `concept_judicial_independence`, whose description explains the score and ends with
  "Now #v X#!, heading for #v Y#!." (`te_jud_display`, `te_jud_ceiling`), as `concept_inheritance_concentration_desc`
  does;
- the scaled `te_judicial_independence` modifier in the country's modifier list, showing what the score buys now;
- each court law's tooltip lines (§ 2.7);
- each spending option naming its cost.

The national modifiers tab (§ 13) then gives the score a row of its own and takes the modifier out of the country
panel's list.

## 4. Balance

### 4.1 At full independence, with no paper court

| Law | Score | Legitimacy | Credit standing | Override | Other |
|---|---|---|---|---|---|
| Executive Tribunals | 10 | +1 | +0.95pp | +1 | Authority +50, cheaper suppression |
| Religious Courts | 40 | +4 | +0.30pp | 0 | Devout clout, cheaper administration |
| Statutory Courts | 70 | +7, and +10 from votes if elected | −0.35pp | 0 | +25 authority if unelected |
| Constitutional Review | 100 | +10 | −0.50pp | −2 | Entrenchment, suppression +25% |
| Judicial Supremacy | 100 | +5 | −0.20pp | −3 | Incoherence −25%, movements calmer but stronger, wider entrenchment, suppression +40% |
| Algorithmic Jurisprudence | 60 | +6 | −0.30pp | 0 (+2) | Administration −10% |

Investment efficiency and the radicalism damping scale with the score the same way (+10% and −20% at 100). The votes
term is a coefficient on the government's share of the vote, as vanilla's voting laws' are, so it pays a government
with a strong mandate more.

### 4.2 Why each law gets chosen

The table is deliberately not monotone, so there is no "just climb":

- **Executive Tribunals:** authority and override are what a consolidating ruler is short of in 1836.
- **Religious Courts:** the Devout's price, with cheap administration. The Islamic world's status quo.
- **Statutory Courts:** most of the trust at no cost in override, plus a mandate for whoever makes the law. The
  19th-century liberal default, and a codifying monarch's.
- **Constitutional Review:** the most legitimacy and credit, paid for in override (no medium Forceful Legislation tier,
  no tax Force Through), dearer suppression and slower constitutional change.
- **Judicial Supremacy:** broad coalitions and quieter movements, for half the legitimacy of Review.
- **Algorithmic Jurisprudence:** cheap and middling on its own; with Algorithmic Governance, a captured court.

### 4.3 Credit standing and the floor

A great power's rank puts it on the 0.5pp floor already, so the −0.5pp of a trusted court is invisible to Britain or
France. It matters to minor and unrecognized countries, which is historically apt: small states bought cheap credit
with credible institutions. The owner ruled against moving the floor (2026-10-17), so the benefit stays with the
smaller countries.

### 4.4 Override totals

A mature democracy ends below 0 under Constitutional Review: Universal Suffrage −3, Guaranteed Liberties −2 and the court
−2 make −7. No Forceful Legislation option appears and tax Force Through is closed. That is intended: those are exactly
the shortcuts a constitutional court exists to stop.

## 5. Starting laws (1836)

In `common/history/extra_history.txt`, after vanilla history, through one scripted effect,
`te_jud_assign_court_by_rule`, which § 6's old-save repair also calls (history already calls scripted effects:
`gm_com_seed`):

1. **Religious Courts:** Theocracy; or a Sunni, Shia or Ibadi state religion (`country_has_state_religion`; the three
   religions with `heritage_islamic`) under State Religion or a variant (`has_law_or_variant`) or Freedom of
   Conscience.
2. **Statutory Courts:** a voting law (Landed, Wealth or Census Voting, Universal Suffrage).
3. Otherwise Executive Tribunals, the first law in the file.

Then, in the country blocks history already has: the United States → Constitutional Review; Britain, France, Prussia,
the Netherlands, Sweden and Belgium → Statutory Courts, whatever their 1836 franchise.

**Starting score:** half the effective ceiling, set at the first monthly pulse (§ 6), except where history sets it
first: Britain 70, the United States 60, the Netherlands 50, Sweden 50, Belgium 40, Prussia 35, France 35.

## 6. Seeding, old saves and new countries

- **New game:** `on_game_started` only sets the global `te_jud_world_seeded`. The first monthly pulse seeds each
  country's score (`te_jud_seed_score`: half the ceiling unless history set it, then `te_jud_seeded`), by when the
  laws' modifier sums are certainly in place, and the refresh adds the modifiers.
- **Old save** (no `te_jud_world_seeded`): every country holds Executive Tribunals, the first law in the file. An
  old-save repair (`common/on_actions/te_old_save_repairs.txt`, with its removal marker) runs on `on_monthly_pulse`: in
  the first month every country runs `te_jud_assign_court_by_rule`; in the second the repair sets
  `te_jud_world_seeded`, and the monthly pulse seeds each score from the new law's ceiling. The laws it activates
  never shock, since the shock event needs `te_jud_seeded`.
- **A new country mid-game** (release, secession) without `te_jud_seeded`: the monthly pulse seeds its score from the
  law it holds. Its law isn't changed.
- **A revolution's winner** inherits the variables, so nothing is reseeded.

## 7. Ideology stances

The stances live in named lists in `ideology_modifications.py` (`JUDICIARY_LISTS`, keyed by the names below, and
`JUDICIARY_STANCES`, ideology → list). Every list names all six laws, as the `ideology_lawgroup` audit requires.
`apply_ideologies.py` writes the vanilla ideologies (an INJECT, since vanilla has no block for the group, which
`scripts/generators/regen_ideologies_offline.py` can produce without the game). The mod's own ideologies get
hand-written blocks in `common/ideologies/extra_ideologies.txt`.

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
| `currently_enacting_law` resolves at `on_law_enactment_started` | `TE_SELF_CHECK OK judiciary_enacting_law_scope` (or `BROKEN`), once a game, logged the first time a country whose court challenges starts an enactment (`enacting_any_law = yes` holds, so a missing link can't pass as OK) |
| `add_enactment_modifier` from an on-action effect applies | Play-test: the enactment panel lists "Constitutional Challenge" for a Distribution of Power law under Constitutional Review. Fallback: move the call into a hidden event, as Forceful Legislation runs |
| A scripted effect runs from history | Play-test: the lobby shows the United States with Constitutional Review and Persia with Religious Courts |
| The laws' modifier sums are in place a month after game start and a week after a law change | Play-test: the concept reads Britain's ceiling as 70 in February 1836; a court downgrade's shock is sized by the new ceiling |
| The concept renders the live score | `loc_render_audit` offline; play-test reads it |

## 10. Later phases

Each later phase was to get its own plan once phase 1 had been play-tested, since their details depend on how the
score behaves. The owner asked for all three on 2026-10-25, before that play-test; § 14 records what was built and the
calls made without the owner, and the play-test list carries what only the game can show.

- **Phase 2: defying the court.** Under Constitutional Review or Judicial Supremacy (not a paper court), taking a
  Forceful Legislation option opens a challenge. Some months later the court rules:
  - **comply**: legitimacy, and the forced law's gains are clawed back;
  - **defy**: a larger score loss and the overhaul shock's credit term;
  - **pack the court**: an authority cost, a score loss, and a later event offering a drop to Statutory Courts.

  The open engine question is whether a variable can hold the replaced law's type, so that compliance can restore it.
  If not, compliance costs the forced law's legitimacy instead of reversing it. An overhaul-protest event replaces the
  bare radicals of § 3.5.
- **Phase 3: amendments.** Every amendment has a scripted way in (an event or a petition), per the mod's rule, and
  moves the § 2.7 lines where it changes a rule (Judicial Elections lowering the ceiling, for one):
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
- `law_algorithmic_governance` (`common/laws/extra_laws.txt`): the two paper-court lines (§ 2.7).
- `docs/guides/scripting_best_practices.md` (the override sources list) and `docs/systems/tax_code_schema.md` § 7.4
  (Force Through's costs).
- `docs/systems/mod_systems.md`: a new § Judiciary.
- Player guide: `06-politics.md` (the law group table, the Forceful Legislation sources and costs, a short paragraph on
  Judicial Independence) and `04-banking.md` (a credit standing source), at the depth of their peers; rebuild the PDF.

## 12. Rulings

The five proposals of the first draft were ruled on in the owner's second review (2026-10-17): Judicial Supremacy's
legitimacy went further down, to +5 net, with stronger movement terms; the credit floor stays where it is;
Constitutional Review unlocks at Human Rights; Judicial Supremacy has no gate; and how the score is shown moves to the
national modifiers tab (§ 13), with phase 1's concept and modifier in the meantime. The review also added Statutory
Courts' conditional bonus and the rule that every rule shows on a tooltip (§ 2.3, § 2.7).

## 13. Hand-off: a tab for national modifiers

The owner wants a Timeline Extended window tab for the national scores the mod tracks in modifiers and variables
(Judicial Independence, Legislative Override Capacity and their like), seen and explained in one place, with the
country panel's modifier list hiding them as the state panel already hides its bookkeeping modifiers. It is
cross-cutting, so it gets its own spec. What this spec settles for it:

- The Judiciary needs nothing from the tab to work, and phase 1 doesn't wait for it. The tab then takes over: a
  Judicial Independence row (score, ceiling, what it buys), and `te_judicial_independence` hidden from the list.
- Where the list is: vanilla's `country_panel.gui` (owner's upload, 2026-10-17). The country panel's Information tab
  (`country_panel_information_content`) ends with a "MODIFIERS" header and a `flowcontainer` over
  `Country.GetTimedModifiers` (icon, name, remaining duration), shown for the local player. Its Modifiers tab
  (`modifier_list`) is a different view, the summed modifier types with their breakdowns, where the § 2.7 lines
  belong and should stay. Hiding works as in `gui/states_panel.gui` (`gui_modding_guide.md` gotcha #40): match
  `TimedModifier.GetName` against `Localize('<key>')`, with `ignoreinvisible = yes` on the flowcontainer, and a count
  script value for the header's `IsDataModelEmpty` test.
- Hidden is not gone: the breakdown tooltips (legitimacy's, the Modifiers tab's) still name the source.
- Only standing scores move to the tab. A timed consequence with a duration (the Court Overhaul) stays in the list,
  where the player expects to find what just happened to them.

## 14. Phases 2–4 as built (2026-10-25)

Built together, at the owner's request, ahead of the phase 1 play-test. What § 10 left open was settled as below. The
calls marked **(call)** were made without the owner and are listed for review in § 14.4. Play-test items:
`docs/testing/judiciary-playtest.md` § Phases 2–4.

### 14.1 Phase 2: defying the court

- **Who reviews.** A new tooltip line, `country_court_reviews_forced_laws_bool` ("Courts Review Forced Laws"), sits on
  Constitutional Review and Judicial Supremacy. `te_jud_court_can_strike_laws` reads it and excludes a paper court,
  and a packed court counts as one (below).
- **Opening a challenge.** Forceful Legislation's three bypass options call `te_jud_open_challenge = { TIER }` under
  such a court, in a `custom_tooltip` that states the rule. It stores the law being forced and the law in force in its
  group as law types (`te_jud_challenge_law`, `te_jud_replaced_law`), and which option was taken. The tax code's Force
  Through opens none **(call)**: a tax bill is not a law the court sees enacted.
- **Filing.** The monthly country pulse (`te_jud_challenge_monthly`) files the case once the enactment is over and
  `has_law` reads the forced law, one case at a time, by copying the variables to `te_jud_case_*`. A law that failed is
  forgotten. All of this runs in country scope; `te_jud_law_activated` still reads no variable (ROOT is the law there).
- **The ruling** comes 180 days after filing (`te_judiciary_events.2`, hidden). The court strikes the law down when the
  score is at least `te_jud_strike_threshold`: **90 after Expedite, 60 after Push decisively, 30 after Force it
  through (call)**. That is deterministic, so the line's description and each option's tooltip can say it; a mature
  court strikes down most forced laws, which is the check this phase exists for. Otherwise the court upholds the act
  (`.4`, +3 legitimacy for two years, decaying).
- **Struck down** (`.3`):
  - **Comply** restores the replaced law (`activate_law`) and adds +5 legitimacy for five years, decaying, and +5 to
    the score. If no replaced law was recorded, the forced law stays and costs −10 legitimacy instead, § 10's
    fallback.
  - **Defy** costs 20 of the score and five years of `te_jud_ruling_defied`: +1pp risk premium, the overhaul shock's
    credit term at a gap of 50, and −5 legitimacy. The Intelligentsia disapprove, and some of the middle strata
    radicalize.
  - **Pack the court** (`te_jud_pack_court`) costs 15 of the score, takes 150 authority fading over five years, and
    adds ten years of `te_jud_court_packed`. That modifier carries the paper-court line (so the packed court
    challenges and reviews nothing), −30% on the ceiling and −5 legitimacy. A year later The Enlarged Bench (`.5`)
    offers the drop to Statutory Courts (activated directly, and it ends the packing), keeping the bench, or
    restoring the old one (+5 legitimacy and +5 to the score).
- **The engine question** (§ 10) is answered in the preferred way, with a self-check:
  `TE_SELF_CHECK OK|BROKEN judiciary_law_type_variable`, logged once a game when the first challenge opens. BROKEN
  means a variable can't hold a law type, so no case is ever filed. The fallback, named in the play-test list, is to
  file from the forced law's own `on_law_activated` and let compliance cost legitimacy.
- **Lawyers in the Streets** (`.6`) replaces § 3.5's bare radicals at a gap of 40 or more. Letting them march gives the
  old middle-strata radicals. Clearing the streets takes 100 authority over two years and gives fewer radicals, with
  the Armed Forces pleased and the Intelligentsia not. Promising the judges their tenure adds 10 to the score and a
  few loyalists, and costs the governing groups 1 approval for two years.

### 14.2 Phase 3: the amendments

`common/amendments/te_judiciary_amendments.txt`. Every amendment has a petition on a court law in force
(`amendment_petition_events.21`–`.27`). Three also have a debate event while a host law is being enacted
(`te_judiciary_events.20`–`.22`, in `on_law_checkpoint_debate`). Courts for a New Code (§ 14.3) is a second way in for
the commercial courts. The parents (**calls**) were picked from vanilla stances so that the right groups back each
amendment:

| Amendment | Allowed on | Parent | Effects | Ways in |
|---|---|---|---|---|
| Suspension of Habeas Corpus | Statutory, Constitutional | Secret Police | suppression −25%, ceiling −20%, legitimacy −5; wartime only, and it lapses at peace (`country_amendment_lapses_at_peace_bool`, lifted by `te_jud_amendment_upkeep`) | petition `.21`, Armed Forces, at war, 25% |
| Judicial Elections | Statutory, Constitutional | Universal Suffrage | ceiling −20, legitimacy +5; elected government only | debate `.20`; petition `.22`, a strong group led by a Jacksonian Democrat or populist, 5% |
| Mixed Commercial Courts | Religious, Executive | Free Trade | credit standing −0.5pp, ceiling +10, Devout clout −5%; not under Isolationism | petition `.23`, strong Industrialists or Petty Bourgeoisie, 2.5%; Courts for a New Code |
| Jury Trials | Statutory, Constitutional | Guaranteed Liberties | ceiling +10, suppression +10%, legitimacy +3 | debate `.21`; petition `.24`, strong Intelligentsia, 2.5% |
| Military Tribunals for Civilians | Executive, Statutory | Outlawed Dissent | suppression −15%, Armed Forces clout +10%, ceiling −20% | petition `.25`, unrest and strong Armed Forces, 10% |
| People's Tribunals | Executive | Single-Party State | suppression −20%, loyalists from movements +10%, credit standing +0.5pp; Single-Party State only, lifted without it | petition `.26`, a governing group led by a vanguardist or fascist, 5% |
| Human-in-the-Loop Appeals | Algorithmic | Strong Privacy Rights | legitimacy +5, population bureaucracy cost +5%, ceiling +10, and −2 on the capture line, so Algorithmic Governance's captured court gives no override | debate `.22`; petition `.27`, legitimacy under 50 or strong Intelligentsia or Trade Unions, 5% |

`possible` is read only when an amendment is added, so the two standing conditions are enforced monthly by
`te_jud_amendment_upkeep`.

### 14.3 Phase 4: landmark cases

Each case is keyed to game state, never to a date or a tag, and comes once per country (`te_jud_heard_<case>`, a
variable, so a revolution's winner doesn't hear it again) **(call)**. Each rolls yearly from its own sub-action in the
petitions' idiom, except where noted.

| Event | When | Answers |
|---|---|---|
| `.30` The Free Soil Case | a court that can strike laws, score 30+, slavery legal, an abolition movement at 5%+; 5% a year | property in persons upheld (ten years of abolition support +25% and movement radicals +10%; Landowners pleased); at score 60+, free soil (ten years of +15% enactment success for Slavery Banned; +5 score; aristocrat radicals); or a question for the legislature (−5 score) |
| `.31` The Ōtsu Case | not a paper court, score 30+, not a great power, an AI great power at worse than cordial relations; 2.5% | the law sets the sentence (+10 score, +5 legitimacy decaying, relations −20) or the sentence they demand (−15 score, −5 legitimacy, relations +20) |
| `.32` Freedom of Contract | Judicial Supremacy, score 40+, a labour law, strong Industrialists; 5% | accept (ten years: Trade Unions −10%, Industrialists +10%, labour movement +25%); pack the court (as § 14.1); or lean on the court (−5 score) |
| `.33` The Voided Election | elected government, not a paper court, score 50+; 10% of `on_election_campaign_end` | respect it (+5 score, +10 legitimacy decaying; the strongest governing group angry) or declare an emergency (−30 score; three years with the paper-court line, suppression −25%, legitimacy −15) |
| `.34` The Doctrine of Necessity | a fortnight after a paper-court law is activated, score still 30+ | necessity knows no law (−20 score, +10 legitimacy decaying) or the judges resign (−10 legitimacy decaying, middle-strata radicals) |
| `.35` A House of Justice | Religious Courts, Rationalism, unrest, no enactment; 10% | grant it (`start_enactment` of Statutory Courts, middle-strata loyalists, Devout angry) or the clergy's courts suffice |
| `.36` Courts for a New Code | Religious Courts, Rationalism, strong Intelligentsia or a modernizer movement at 5%+; 2.5% | courts beside the religious ones (attaches Mixed Commercial Courts), codify (`start_enactment` of Statutory Courts), or keep the religious courts |

The Ōtsu Case picks an AI great power only **(call)**, so no player is blamed for a demand it never made
(`event_context_audit`'s rule).

### 14.4 Calls made without the owner

For review; each is a number or a choice the owner may want to move:

1. The strike-down thresholds (90, 60, 30) and their being deterministic rather than a roll.
2. The ruling's delay (180 days after the law is in force) and one case at a time.
3. The tax code's Force Through opens no challenge.
4. The sizes in § 14.1 (defy −20 and +1pp, pack −15, 150 authority and ten years at −30% ceiling, comply +5 and +5).
5. The seven amendments' parents, sizes, hosts and petition chances (§ 14.2), and which three get a debate event.
6. Landmark cases once per country, and their triggers and chances (§ 14.3).
7. A House of Justice and Courts for a New Code start the enactment of Statutory Courts (`start_enactment`) rather
   than adding a modifier to it; whether that effect starts an enactment from an event option is a play-test item.
