# UN GUI pass, round 1: design

**Status:** approved in conversation with the owner, 2026-09-28. Round 1 built the same day (plan `docs/superpowers/plans/2026-09-28-un-gui-pass.md`, commits `e6faf1f`..), branch `feat/banking-budget-tab`, PR #567. Not yet seen in game.

## Goal

The UN's panels are for a player who already knows the system and opens them to check status: am I in, how strong is the UN, who runs it, what has it built, did the credibility pillar go up. The dynamic parts get a visual and are open by default. The explanatory walls of text stay, collapsed by default, for players learning the mod. Nothing that exists today is lost: text an icon replaces moves into that icon's tooltip.

The same layout serves both hosts: the journal entry `je_united_nations` and the Diplomacy panel's UN tab (`gui/diplomatic_overview.gui`). Placeholder art is vanilla textures referenced by path, so real icons later change paths only.

**Round 2 (not in this spec):** one visual row per item for missions in the field, authorized mandates and the archive. Those live in global lists of script containers. Whether the GUI can read them through `GetGlobalList` is untested, so round 1 ships a probe (§6).

## 1. Layout and order

▼ open by default, ▶ collapsed by default.

```
OVERVIEW (always shown, not collapsible)
▼ General Assembly
    in session:  topic icon · tally bar · time bar · card text · vote buttons
                 ▶ Delegations
                 ▶ Recorded ballot
    otherwise:   "No resolution before the Assembly"
                 ▶ Table a resolution
▼ Why authority is moving     pillar bars; crisis panel, ladder, powers and ledger as today
▼ Missions in the field       text, as today
▼ Authorized mandates         text, as today
▼ Our obligations             text, as today
▼ Our exposure                text, as today
▼ Actions                     the entry's scripted buttons (tab only; the journal draws its own grid)
▼ Authority history           chart
▶ Archive of closed resolutions
▶ How international standing works
▶ How UN authority works
  [Open Journal Entry]        (tab only)
```

- Delegations, the recorded ballot and "Table a resolution" become subsections of General Assembly. The first two describe the resolution in session. Proposing is impossible while one is in session: every proposal requires `NOT = { has_global_variable = un_vote_active }`. So the two states never both apply. While a proposer event holds the lock with nothing in session, "Table a resolution" shows with every row greyed and the lock as the reason.
- The standing, council and membership text at the top of today's chamber moves into the overview's tooltips (§2).
- Collapse flags are renamed with an `_open` or `_closed` suffix to match each section's new default.

## 2. Overview

| Element | Visual | Data | Tooltip |
|---|---|---|---|
| Membership | one icon per state: member (check), permanent member (check with star), suspended with the seat carried (amber check), suspended (amber warning), can join (empty box), cannot join (cross), no UN (dash); plus a short label | new `un_disp_member_code` | today's status line for that state (`je_un_chamber_status_*` / `je_un_status_*`) |
| Tier | one icon per tier (moribund, contested, established, strong, supranational), plus the name | `global_var:un_tier` 0–4 through a display value; none while no UN | today's tier line (`je_un_tier_line_*`) |
| Crisis | red alert icon, only while the crisis is open | `un_crisis_is_open` | the crisis panel's text |
| Standing | small meter, 0–100 | `var:un_standing` | today's standing block (`un_standing_status_block`) |
| Authority | 0–100 bar with a target tick; "62 → 68 (+0.4)" | `un_disp_authority`, `un_disp_target`, `un_disp_step` | today's headline (`je_un_auth_tbl_headline`) |
| Pies ×3 | members' share of countries, of GDP, of population; `progresspie` over a background disc, % label | three new monthly snapshots (§4) | what each measures |
| Security Council | five slots: vanilla `small_flag` for each permanent member (country tooltip, click opens the country panel, right-click menu, map highlight); a "vacant" placeholder otherwise | `un_p5_seat_1..5` on each player's country (§4) | on the label: today's council text (`un_chamber_council_sgui`), including who is in line |
| Agencies ×11 | two rows of icons (WHO, UNESCO, ICJ, UNHRC, IAEA, UNEP, UNHCR, UNOOSA, ITLOS, ICC, CPPNM): full colour once founded, dimmed until then | 11 display values over the `un_agency_*` globals | name, what it does, founded or not |

**Target tick:** a transparent progressbar with a marker, the technique of Banking's policy-stance bar (works in game).

**Flags:** a country object in the GUI comes from a stored capital, `…MakeScope.Var('un_p5_seat_N').GetState.GetCountry`. The covert widget proves this route for names. Driving `small_flag` from it uses only calls vanilla already makes on countries, but has not been seen in game. Slot N is filled when `un_disp_p5_count >= N`, so no missing variable is ever read (gotcha #23).

## 3. Dynamic sections

**General Assembly, in session:**
- *Topic icon:* one placeholder per topic (18).
- *Tally bar:* spans `un_vote_eligible_member_count`, the member count the supermajority rule divides by. Three stacked left-to-right bars, the pie technique: red with value 1, grey with value (yes + not yet voted) ÷ members, green with value yes ÷ members. That draws green for yes, grey for not yet voted and red for no.
  - Expulsion and charter reform pass on two-thirds of all current members, so the bar shows a ⅔ mark for those two.
  - Every other topic passes on more yes than no votes. That point moves with turnout, so the label says "needs more yes than no" instead of drawing a mark.
- *Time bar:* `un_res_months` of 12.
- The card text and vote buttons stay as they are.

**Why authority is moving:**
- *Pillar rows:* base, participation, commitment, credibility, funding, order, delivery, then the target.
  - Each row has a label, a bar over the pillar's own range with a zero mark and a marker at the value, the value, and a trend of ▲/▼/– against last month, in green or red.
  - Ranges: participation 0–25, commitment −25–25, credibility −15–15, funding −10–10, order −20–0, delivery 0–10. Base is the constant 15 and has no bar.
  - Today's "reading" column moves into the row's tooltip, together with last month's value.
  - Bar positions are 0–1 fractions from script values, never `.gui` arithmetic.
- The crisis panel, the empty states and the other subsections (ladder, powers, ledger log) keep their text.

Missions, mandates, obligations and exposure keep today's text and open by default.

## 4. Script

- **`un_authority_monthly_update`, step 3** (`un_authority_effects.txt`):
  - Before the pillar snapshots are rewritten, copy each `un_pillar_<p>` to `un_pillar_<p>_prev`.
  - Snapshot `un_member_country_share`, `un_member_gdp_share` and `un_member_pop_share`, each 0–1. Members are countries whose `je:je_united_nations` carries `un_member_modifier`, measured against every country: count, `gdp`, `total_population`.
- **`un_p5_display_refresh`:** for every player country, clear `un_p5_seat_1..5`, then store the permanent members' capitals in prestige order.
  - It runs from the monthly update and from every effect that grants or removes `un_permanent_member_modifier`: `un_ladder_effects` (two sites), `un_membership_effects`, `un_seat_effects`, `un_state_effects` (restore), `events/un_vote_events.txt`, and the two debug effects in `te_debug_un_effects`. Otherwise a seat change would show up to a month late.
- **Display values** (`un_disp_*`, country scope, reading globals):
  - member code, tier code, P5 count;
  - the three shares;
  - each pillar's bar fraction and its change since last month;
  - the tally fractions, the months fraction and the supermajority flag;
  - the eleven agency flags.
- **Scope-free scripted GUIs**, used only as `visible` gates: session open, UN exists. The crisis gate reuses `un_authority_crisis_sgui`'s `is_shown`.

## 5. Files

- `gui/journal_entry_widgets/un_overview_widget.gui` (new): `te_un_overview_panel` and its small types, plus the named wrapper the journal attaches.
- `un_chamber_widget.gui`, `un_authority_widget.gui`: each section becomes a type. Two composing types:
  - `te_un_status_sections`: General Assembly through Exposure.
  - `te_un_reference_sections`: history chart, archive, the two how-it-works sections.
- `common/journal_entries/je_united_nations.txt` attaches four widgets:
  - overview in `custom_widget_container_1`, above the status text;
  - status in `_2`, above the button grid;
  - reference in `_3`, below it;
  - the bars-on-top marker in `_7`, so the overview's authority bar replaces the journal's bottom one.
- `gui/diplomatic_overview.gui`: the tab composes header → overview → status → Actions → reference → link. It drops `te_je_scripted_bars` and `te_je_status_desc`, because the overview covers both.

## 6. Round-2 probe

A line in the tab, shown only in debug mode, that sets `datamodel = "[GetGlobalList('un_mission_registry')]"` and prints its item count. If it counts, round 2 reads the global lists directly. If not, script mirrors each list onto the player's country, the covert widget's pattern. The line is removed in round 2.

## 7. Testing

- **New static tests:**
  - every site that grants or removes the permanent-member modifier also calls `un_p5_display_refresh`;
  - every agency in `un_agency_count` has a display value and an overview slot.
- **Existing tests:** the UN widget tests updated where rows move.
- **Offline checks:** the full suite, the CI checks, and the reload-only audits through a local ModState.
- **In game** (`te_debug_un.1` founds the UN and grants seats):
  - each overview element in each state;
  - flags open the country;
  - agencies light up;
  - pies and trend arrows after a month;
  - the session bars on both a simple-majority and a supermajority topic;
  - collapse defaults;
  - the journal is intact, with its bar drawn once;
  - the probe's count in debug mode.

The player guide is deferred with the rest of PR #567.
