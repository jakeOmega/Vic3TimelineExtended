# Bureaucracy laws: machine administration, machine rule, and what follows — design

## Context

The owner's proposal splits two ideas the mod had merged into one law:

- **Bureaucracy** — who administers the state and implements its laws.
- **Distribution of Power** — who sets the state's objectives and has final political authority.

Before this change, `law_algorithmic_governance` (Distribution of Power, `machine_learning`, era 10) carried both:
administrative effects (+100% institution size change speed, −25% decree cost, +15% population bureaucracy cost) and
political ones. A democracy that wanted machines to run its offices had to hand them the state. The split lets any
government delegate administration to machines without surrendering sovereignty, and reserves Algorithmic Governance for
the state that does surrender it.

The work lands in two PRs. **PR 1** (this one) adds Automated Bureaucracy and reworks Algorithmic Governance. **PR 2**
adds the other two bureaucracy laws and the Spoils System amendment (the last section).

## Decisions (owner, 2026-10-01)

| Question | Decision |
|---|---|
| Name | **Automated Bureaucracy** (`law_automated_bureaucracy`). "Algorithmic Administration" was dropped: too close to Algorithmic Governance, the confusion the split removes |
| Unlock | **Generative AI** (era 10) |
| Strength | A late-game law should be strong. −20% institution bureaucracy cost stands even though it is four times Elected Bureaucrats' net −5% (vanilla −15%, the mod's +10%) |
| Tax capacity | **None.** By era 10 a country has spare tax capacity; cheap institutions are the prize, and the clout changes are a tradeoff, not a bonus |
| Algorithmic Governance's unlock | **Artificial Intelligence** (era 12). It requires Programmable Matter (also era 12), so this is among the last laws in the game, and it should be very strong |
| Coupling the two laws | **Install and lock.** Algorithmic Governance enacts Automated Bureaucracy, and no other bureaucracy law can be enacted while it holds. Not a prerequisite (see §3) |
| `INJECT:` into a list vanilla already declares | **Appends.** Works for every one of the mod's 99 PMG INJECTs; the old doc warning was about trigger blocks |
| Company slots on Algorithmic Governance | **Keep +2**: vanilla's Technocracy gives one, and this is the further step |
| Banking momentum on Algorithmic Governance | **Drop.** It reads as machine rule taking over the central bank's job, which makes the monetary laws moot |
| `pm_ai_governance` | Keeps its key; displayed as **AI Agent Networks**, a machinery name like the group's Teletype and Internet Communications |
| Contracted / Communal Administration | **Wanted, in PR 2.** They give a neocameral, privatized state and a devolved anarchist society a bureaucracy law that fits. Their overlap with Neocameralism and Devolution is consistency, not duplication |
| Professional Civil Service, Party Bureaucracy laws | **Not added.** Appointed Bureaucrats already is a professional service (+25% tax capacity, +25% bureaucrat clout), and a party bureaucracy is Single-Party State with Appointed Bureaucrats |

## 1. Automated Bureaucracy (`common/laws/extra_laws.txt`)

| Field | Value |
|---|---|
| Group, unlock | `lawgroup_bureaucracy`, `generative_ai` |
| `country_bureaucracy_investment_cost_factor_mult` | −0.2 |
| `country_institution_size_change_speed_mult` | +0.5 |
| `country_bureaucrats_pol_str_mult` / `country_engineers_pol_str_mult` | −0.25 / +0.15 |
| `country_legislative_override_capacity_add` | +1 (Appointed's value: an apparatus without discretion carries out what it is told) |
| Progressiveness | −10 (§3) |
| `on_enact` | Appointed Bureaucrats' two IG-shift tooltips: pop IG weights key on Elected and Hereditary, so leaving either for this law moves the same pops |
| AI weight | 10, +25 while bureaucracy is negative |
| Icon | `automated_bureaucracy.dds`: a ministry building crowned by a processor chip (`draw_building_ministry_circuit`, `scripts/image_pipeline/gen_law_icons.py`) |

**Staffing PM** `pm_automated_casework` (`extra_pms.txt`), in vanilla's `pmg_government_administration_bureaucrat_professionalism`
beside Hereditary and Professional Bureaucrats: 150 bureaucrats and 100 engineers a level instead of 500 bureaucrats, plus
5 Digital Access and 5 Digital Assets. At wage weights 4 and 3 that saves about 1,100 wage units a level against about
1,100 of goods at base prices: cheaper where wages are high, dearer where they are low. It replaces Professional
Bureaucrats while the law holds (`disallowing_laws` INJECTed on `pm_professional_bureaucrats`), the way vanilla's
Hereditary Bureaucrats PM replaces it under that law. No `required_input_goods`: under the law it is the group's only PM.
`pm_ai_governance` (era 12) stays the base-group upgrade beyond it.

**Ideology stances.** Only on ideologies whose entry `apply_ideologies` already REPLACEs (any other vanilla ideology would
need its raw text, §5) and on the mod's own:

| Stance | Ideologies |
|---|---|
| Strongly approve | `ideology_positivist`, `ideology_positivist_movement`, `ideology_optimist_transhumanist`, `ideology_custom_religion_technocratic_governance` |
| Approve | `ideology_vanguardist`, `ideology_despotic_utopian`, `ideology_custom_religion_corporate_governance` |
| Neutral (explicit) | `ideology_custom_religion_republican_governance` |
| Disapprove | `ideology_paternalistic`, `ideology_republican_paternalistic`, `ideology_junker_paternalistic`, `ideology_papal_paternalistic`, `ideology_hindu_moralist`, `ideology_jacksonian_democrat`, `ideology_absolutist_movement`, `ideology_populist`, `ideology_anarchist`, the aristocratic, imperial-cult and theocratic custom-religion governance ideologies |
| Strongly disapprove | `ideology_scholar_paternalistic` (the examination-selected official class is exactly what is replaced) |

## 2. Algorithmic Governance (`common/laws/extra_laws.txt`)

Supreme political authority vested in AI; human institutions advise and execute.

- **Unlock** `artificial_intelligence`. Saves where a country holds it through Machine Learning keep it:
  `gen_law_consistency` checks laws' `unlocking_laws` and `disallowing_laws`, not their technologies.
- **Removed:** +100% institution size change speed and the +15% population bureaucracy cost (Automated Bureaucracy
  carries the administration now), banking momentum, and `country_legitimacy_govt_leader_clout_add = 10`.
- **Kept:** +2 companies, +50% enactment speed, −25% stall, −30% ideological incoherence, doubled radicals and loyalists
  from SoL change, −25% decree cost (directing policy, not administering it), +10% research, the academic, engineer and
  Intelligentsia clout, +2 Legislative Override Capacity.
- **Added: legitimacy from results.** `algorithmic_mandate` (`sol_expectations_modifiers.txt`) carries
  `country_legitimacy_base_add = 1` and is re-applied each month with multiplier `algorithmic_mandate_value`
  (`extra_script_values.txt`): 5 × `var:sol_expectations_gap_cached`, capped at ±25. The gap is
  `average_sol + country_sol_expectations_target_add − average_expected_sol`; it returns to zero once expectations catch
  up, so the mandate pays for living standards that outrun expectations and costs for ones that fall behind, not for a
  level of wealth. `te_refresh_algorithmic_mandate` (`sol_expectations_effects.txt`) runs from
  `sol_expectations_monthly_on_action` right after the update caches the gap: the modifier's only refresh site. The law's
  `on_deactivate` removes it at once. The 5 and the cap are first values to tune in play.
- **Net, for a country that holds it:** it gains −20% institution cost (through Automated Bureaucracy) and the mandate,
  and loses half its resize speed and the flat +10 legitimacy.
- Parties still dissolve on activation. Algorithmic Directorate and Algorithmic Commons (`amendment_collective_algorithmic_commons`) already describe machine rule and are unchanged.

## 3. Install and lock, and the consistency walk

`gen_law_consistency.py` replaces any law whose `unlocking_laws` / `disallowing_laws` no longer hold with the
nearest-progressiveness valid law, every month and on every law change, Distribution of Power before Bureaucracy.

- **Why not a prerequisite.** `unlocking_laws = { law_automated_bureaucracy }` on Algorithmic Governance would make the
  walk evict the governing law whenever the bureaucracy changed, and every existing save holding Algorithmic Governance
  with Appointed Bureaucrats would lose it the month after the update.
- **What ships.** Algorithmic Governance's `on_activate` enacts Automated Bureaucracy (in place of the old
  Elected→Appointed swap) and its `on_enact` says so (`ALGORITHMIC_GOVERNANCE_TT_INSTALLS_AUTOMATED_BUREAUCRACY`).
  `law_appointed_bureaucrats`, `law_hereditary_bureaucrats` and `law_crownland_diets` get
  `disallowing_laws = { law_algorithmic_governance }` (`common/laws/modified.txt`); Elected already needs a voting law.
  An old save holding Algorithmic Governance with Appointed Bureaucrats moves to Automated Bureaucracy once it has
  Generative AI, and until then stays as it is.
- **Progressiveness −10.** At 0 (Appointed's value) the ideology tiebreak sent a country losing Elected Bureaucrats (50)
  to Automated Bureaucracy. At −10 it goes to Appointed, as before. Hereditary Bureaucrats (−50) under a Council
  Republic does go to Automated Bureaucracy once Generative AI is researched; that case is rare.

## 4. Events

| Event | Change |
|---|---|
| `society_technology_events.27` (now "Administration by Algorithm") | Fires with Generative AI (was Artificial Intelligence) unless the country holds Automated Bureaucracy. Its modifiers read "Automated Administration Pilot / Rejected" |
| `post_scarcity_events.3` "AI Replaces Bureaucrats" | Skipped once the country holds Automated Bureaucracy |
| `extra_law_events.83` "Tech First or Human Oversight First?" | Automated Bureaucracy's enactment event. Who has the last word over the machines is that law's question; under machine rule the machines do |
| `extra_law_events.23`, `.59` | Fire for either law; text names the law being enacted |
| `society_technology_events.26` | Its "a government AI system" text counts either law |

## 5. Generated files without the game

This PR was built in a container without Victoria 3, where `apply_ideologies` and `gen_law_consistency` cannot run
(they read raw vanilla files). Both outputs were produced with their own code and checked byte-for-byte against the
committed files before any change:

- `gen_law_consistency` ran against a synthetic vanilla tree serialized from `vanilla_parsed/` (laws, ideologies). The
  baseline run reproduced `extra_law_consistency_generated.txt` exactly.
- `apply_ideologies` copies raw vanilla text, so its edit was replayed with the generator's own insert-or-replace logic
  over the committed REPLACE bodies, keeping trailing comments as the real run does. The baseline replay reproduced
  `common/ideologies/modified.txt` exactly. This is why new stances only go on already-REPLACEd ideologies.
- `pm_costs`' annotation ran on `extra_pms.txt` with prices from `vanilla_parsed/` and the mod's goods; only the new PM
  changed.

The owner's next `/reload` on a machine with the game should leave all three files unchanged.

## 6. In-game checks

- Enacting Algorithmic Governance from Appointed Bureaucrats switches the bureaucracy to Automated, and the Appointed and
  Hereditary laws then show as disallowed.
- `law_hereditary_bureaucrats` still lists Council Republic among its disallowing laws (the INJECTed list appended).
- A Government Administration under Automated Bureaucracy offers Automated Casework and not Professional Bureaucrats; under
  any other law the PM is hidden.
- The Algorithmic Mandate line appears in the legitimacy breakdown, and its size is sensible against the SoL trend.

## PR 2: the remaining bureaucracy laws (scope)

Every new bureaucracy law follows PR 1's checklist: `disallowing_laws = { law_algorithmic_governance }` (or
Algorithmic Governance evicts it); a progressiveness that keeps Appointed as Elected Bureaucrats' fallback, confirmed in
the generated cascade; Legislative Override Capacity; Appointed's IG-shift `on_enact` tooltips; ideology stances (only on
REPLACEd or mod ideologies unless the game is available); AI weights; loc; an icon; the player guide.
Each law's identity comes from **who staffs the administration**, through its own PM in the professionalism slot and
clout, not from Devolution's or Neocameralism's levers (decree cost, institution impact, separatism, wealth-based
clout), so stacking them does not double up.

### Contracted Administration (`law_contracted_administration`)

Private firms run substantial state functions under contract (the New Public Management era).

- **Staffing PM:** fewer bureaucrats plus a Services input, so the state buys contractors' work and the money flows to
  private service businesses. That is the dependence on contracted services.
- **Clout:** industrialists up, bureaucrats down.
- **Unlock:** an era 8–9 technology (candidates `computer_networks`, `supply_chain_management`), with
  `unlocking_laws` Laissez-Faire or Interventionism (Neocameralism's pair); disallowed under Command Economy and Council
  Republic.
- **Open:** the tradeoff (contract overruns as institution cost, or tax capacity lost to contractor margins);
  whether Private Military Contractors' barracks-PM TODO uses the same pattern.

### Communal Administration (`law_communal_administration`)

Local assemblies and recallable delegates administer services and local affairs; communities take part directly rather
than electing officials to act for them (Elected Bureaucrats).

- **Staffing PM:** bureaucrats replaced in part by clerks, the rotating delegates.
- **Clout and politics:** trade unions or rural folk up, bureaucrats down; lower movement radicalism.
- **Cost:** weaker central coordination, e.g. lower tax capacity.
- **Unlock:** `unlocking_laws` Council Republic, Anarchy or Collective Governance (`law_direct_democracy`), the way
  Elected Bureaucrats needs a voting law; no later than era 4 technology.
- **Progressiveness:** above Elected's 50 reads right, but then a country losing Elected under Anarchy or a Council
  Republic falls back here rather than to Appointed. That is probably correct; confirm in the cascade.

### Spoils System amendment (`amendment_spoils_system`)

Ordinary administrative posts handed to political supporters. It fits the 1836 start (civil-service reform came in 1883),
so no technology.

- `parent = law_appointed_bureaucrats` (the parent sets IG stances); allowed under Appointed Bureaucrats, possibly
  Elected.
- Sponsor gains political strength (+10–15%, Preserved Bureaucratic Caste gives +15%); the country pays in tax capacity
  or bureaucracy.
- A name distinct from the existing `decree_political_patronage`.
- Vanilla has no equivalent: none of its 67 amendments is a spoils system. `amendment_preserved_bureaucratic_caste`
  (parent Hereditary, allowed under all three vanilla bureaucracy laws, sponsored only by Landowners) is the nearest
  precedent. Whether the new laws join its `allowed_laws` is open.
- A party-membership requirement amendment, for stronger party control, stays a later idea.

### Not planned

IG pop-affinity shifts for the new laws (vanilla's Elected Bureaucrats moves bureaucrats into the Petty Bourgeoisie):
those weights live in generator-owned `common/interest_groups/00_*.txt` (`ig_feminism.py`) and need the game files.
