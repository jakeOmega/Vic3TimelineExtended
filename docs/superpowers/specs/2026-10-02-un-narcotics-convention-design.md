# UN Single Convention on Narcotic Drugs — approved design

**Status:** approved by the owner on 2026-10-04; implemented in PR #658. A follow-up to drugs phase 2
(#656), which the owner asked for on 2026-10-02.
**Why:** phase 2's plantation penalties cut only the enacting country's own opium
plantations. India, Persia and the other exporters rarely enact them and keep exporting until
Pharmaceutical Industries undercut them on price. A UN convention modelled on the 1961
Single Convention on Narcotic Drugs is the one hook that reaches exporters: they cut their
own plantations by ratifying it.

Read first: the convention survey below, `docs/systems/journal_entry_systems.md` §
"Adding a convention" (CRLF file), `test_un_convention_registry.py` (the executable
checklist) and `docs/player_guide/09-united-nations.md` § "UN conventions and agencies".

## Convention architecture (updated for implementation)

- **Fourteen conventions** are in `CONVENTIONS`. Each has an agency flag (`un_agency_<x>`),
  a member modifier carried by parties (×E, the enforcement multiplier), a chamber op, a proposer event
  in `un_events`, a refusal modifier, optional regime terms and an optional game rule.
- **The AI reaches a convention only through the docket.** Conventions have no
  journal-entry buttons. A situation (a docket item code) or the Assembly's agenda
  (`agenda = True`, picked at random among open topics) offers it to a qualifying member,
  human first.
- **Phase 7's nine other topics are not conventions** (they have no parties). There is no
  lighter path for a treaty members ratify.
- **The pandemic convention (WHO) is the closest template.** It is agenda-raised, needs
  authority 20 and a major-power proposer with a tech, and its lean reads two laws.
- **Scale:** a convention touches about 38 files and 60+ sites (the registry docstring's
  "thirty sites, twenty files" undercounts). Sites the registry doesn't check are listed under
  [Build notes](#build-notes).

## Approved implementation

### Identity

| Field | Proposed | Note |
|---|---|---|
| key | `narcotics` | topic `un_topic_narcotics`, propose key `un_propose_narcotics_*` |
| agency | `un_agency_incb` (International Narcotics Control Board) | short name `incb` |
| member modifier | `un_narcotics_control_modifier`, **country** scope | a journal-entry modifier is lost when a revolution wins; the six country-scoped conventions are country-scoped |
| op | 29 | ops 20–28 are phase 7's charter decisions; relax `test_ops_follow_the_member_topics` to "contiguous except the charter-decision block" rather than renumber 20–28 |
| proposer event | `un_events.39` | refusal reason 1391 (100 × event + 1) |
| refusal modifier | `un_narcotics_refusal_modifier` | bars the refuser from tabling it |
| agenda | yes, gated by world state in `topic_open` (the CPPNM pattern) | cheaper than a new docket item code |
| game rule | none | |

### Terms for parties (`un_narcotics_control_modifier`, × E)

The convention licenses production for medical use and quotas the rest.

| Field | Proposed | Why |
|---|---|---|
| `building_opium_plantation_throughput_add` | −0.15 | Production quotas: the convention's point, and the lever that reaches exporters. Sums with the health-law penalties. |
| `building_synthetics_plant_opium_throughput_add` | +0.05 | Licensed manufacture for medicine: parties' Pharmaceutical Industries gain a little, so ratifying shifts supply rather than only cutting it. Approved by the owner. |
| `country_prestige_mult` | +0.03 | The pattern every convention follows (+2% to +5%). |

### Regime terms

None. The owner dropped the additional exporter inspection penalty.

### When it comes up (`un_docket_topic_open_narcotics`)

- Not in force, no cooldown, UN authority ≥ 20 (the pandemic convention's threshold).
- **World-state gate:** some member has researched `antibiotic_mass_production` (era 7), so
  the convention arrives in the 1950s–60s, when Healthcare demand starts to matter. The
  historical 1961 date fits.
- **Proposer (`un_propose_narcotics_qualifies`):** a member, major power or above, that has
  researched `pharmaceuticals`, isn't a party and doesn't carry the refusal modifier.

### The AI's lean (`un_lean_interests`)

| Input | Lean | Why |
|---|---|---|
| Has Pharmaceutical Industries and no opium plantations | +15 | A medicine producer gains and loses nothing. |
| Opium plantation levels ≥ 10 | −20 | Exporters resist quotas. |
| Opium plantation levels ≥ 30 | −15 more | Large exporters resist harder. |
| Public Health Insurance | +10 | The government already regulates medicine. |
| Laissez-Faire | −10 | Opposes quotas on principle. |

### The proposer event (`un_events.39`)

As `un_events.17`:
- **A (default), table it.** Intelligentsia +3, Devout +3, Landowners −3.
- **B, pass the offer on.**
- **C, refuse.** The refusal modifier, ledger reason 1391, Landowners +3.

AI weights: A base 4, +3 with Public Health Insurance; C base 2, +4 with opium plantation
levels ≥ 10. In `un_vote.3`, a no voter refuses ratification more often (+20 in option C)
when its Landowners are powerful.

## Build notes

- **Add the `CONVENTIONS` row first.** Its failures are the checklist.
- **Sites the registry doesn't check:**
  - `un_agency_count`.
  - `un_disp_agency_incb`, the overview tile and `je_un_ov_agency_incb_tt`.
  - `un_disp_res_topic_code` and the topic icon in `un_layout_widget.gui`.
  - The Our Obligations line, `je_un_chamber_conv_narcotics` and `je_un_conv_name_narcotics`.
  - The per-convention weights in `un_vote.3`.
  - `te_debug_un_effects.txt`.
  - The guide's "thirteen agencies" counts.
  - The hard-coded lists in `test_un_layout.py` (`range(29)`, `MEMBER_MODIFIERS`, `CONV_KEYS`) and `test_un_overview_data.py` (`TOPIC_ICONS`, `AGENCY_KEYS`).
- **Two icons:** `gfx/interface/icons/un_icons/topic_narcotics.dds` and `agency_incb.dds`.
  These come from the icon pipeline, or a placeholder reused from the pandemic convention
  until then (question 6).
- **Engine-silent traps:**
  - Add the member modifier only through `un_convention_country_on` with `un_convention_multiplier`, never at ×0.
  - Pass loc keys literally, not built from `$PARAM$`, or `organize_loc` files them as unused.
  - Use month counters, not timed variables, on resolution containers (#457).
  - The proposer event needs an `event_image`.
- **Player guide:** a row in `09-united-nations.md`'s conventions table, the agency
  counts, a line in `02-timeline.md`'s Pharmaceutical Industries section, and a PDF rebuild.

## Owner decisions (2026-10-04)

1. Use the real Single Convention on Narcotic Drugs and INCB.
2. Keep the Antibiotic Mass Production world-state gate.
3. Include both −15% plantation throughput and +5% Pharmaceutical Industries throughput, plus +3% prestige.
4. Drop the additional exporter regime penalty.
5. Keep the proposed AI lean table and proposer/ratification weights.
6. Reuse pandemic and WHO art as placeholder topic/agency icons under the new filenames.
