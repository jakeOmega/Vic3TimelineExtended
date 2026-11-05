# Grand Monuments & Colonial Empire — GUI & localization audit

> Part of the 2026-10-27 GUI and localization audit; the index, the cross-cutting findings and the owner questions are in [`../gui_localization_audit.md`](../gui_localization_audit.md). Line numbers are as of the audit and drift as files change; search by key or type name. "Quick fixes" below means the loc-only edits this PR applied.

Scope read: `gui/journal_entry_widgets/grand_monuments_widget.gui`, `gui/gm_archaeology_widgets.gui`,
`gui/gm_trophy_widgets.gui`, the Grand Monument / site / trophy cards in `gui/te_state_panel_widgets.gui`
(instanced at `gui/states_panel.gui:1458-1463`), `gui/journal_entry_widgets/colonial_empire_widget.gui`, the two
tabs in `gui/te_systems_window.gui:754-875`, the GM and CE scripted GUIs, `je_grand_monuments.txt`,
`je_colonial_empire.txt`, the scripted effects/values their tooltips call, and every loc key those render
(374 GM keys extracted from the markup: none missing).

Both tabs in the Timeline Extended window are clean: they compose the journal entry's own types
(`te_gm_overview_panel` / `te_gm_status_sections` / `te_gm_reference_sections`, and the `te_ce_*` equivalents) and
end with Open Journal Entry, so nothing is reachable in only one host. All findings below therefore apply to both
the journal entry and its tab.

Already in good shape: Our Monuments, Awaiting Dedication, the digs, the open sites, Trophies, Held Abroad and the
state card's trophy and "Also Standing Here" lists are all datamodels over script lists. Every Colonial Empire
control (Release, Dominion, Open Talks, the programme steppers, Planned Full Decolonization) greys out with
`IsValidTooltip` + `ExecuteTooltip`. Colonial Empire's overview (band icon, lit programmes, the layered stability bar,
completion clocks, pie) follows rules 1, 4 and 5 closely.

## Top priorities

- **Colonial Holdings and International Pressure are the slice's two "should be lists"**: territories and subjects
  are 8 copy-pasted fixed slots each with a "+N more" hover, and the pressure roster is a script-concatenated text
  block. Datamodels over variable lists built in the existing monthly refresh would replace both (CE-1, CE-2).
- **Grand Monuments renders no modifier through the engine**: boons, unique dedications and policies are all
  hand-written effect prose. The 15 boon tooltips can switch to `[GetStaticModifier('gm_boon_x').GetDesc]` today as
  a loc-only edit (GM-1, Quick fixes). The policies need `script_only` modifier types (GM-2).
- **What needs a decision is at the bottom of the Grand Monuments page.** The overview flags "Contested N" in red,
  but the three choices sit in Our Monuments, after the opportunity, digs and dozens of National Effects rows. The
  policy buttons are at the foot of National Effects too (GM-3). The three choices themselves say what happens in
  prose with no figures (GM-4).
- **Colony / territory / colonial-subject definitions are written out in five tooltips, and they have drifted
  apart** (CE-4). Three concepts would replace them. The live list captions also restate the column-head hovers
  (CE-3, Quick fixes).
- **Stale or contradictory text**: How it Works says an opportunity asks for "5 levels" (the target is 5 grandeur,
  as the guide says); the trophy summaries say "half the levels" (a test already forbids that in their siblings);
  the "Undedicated" texts describe the pre-sites model; `concept_decolonization_system_desc` still counts "three
  decolonization decisions" (GM-7, GM-9, GM-12, CE-10, Quick fixes).
- **Repeated per-row facts** (rule 6): the world-wealth level rate on every site row, the same IG-approval paragraph
  on every IG row, the "ways home" paragraph on every Held Abroad row, the band rule on every subject's liberty
  desire, and "the bar spans X to Y; the figure beside it is exact" on eight pillar rows (GM-5, GM-10, GM-13, CE-5,
  CE-9).

## Findings

### Grand Monuments

### GM-1. Opportunity boons hand-write their modifier instead of rendering it
- **Status:** done (2026-10-27, #1210): no further change needed: the 15 boon hovers render `[GetStaticModifier('gm_boon_x').GetDesc]` since the loc pass (#1202); GM-16 gives their months a unit.
- **Category:** style
- **Where:** `gui/journal_entry_widgets/grand_monuments_widget.gui:2616-2760` (Opportunities Seized rows); loc
  `gm_je_tt_boon_*` (`te_miscellaneous_l_english.yml:3264-3278`), e.g. `gm_je_tt_boon_reign` (`:3270`), and
  `gm_je_tt_boon_homecoming` (`:3268`, also used by Trophies, `gui/gm_trophy_widgets.gui:2380`). Each is a flat
  static modifier (`common/static_modifiers/gm_modifiers.txt:175-251`, added unscaled by `gm_add_boon`).
- **Now:** `#b $gm_boon_reign$#!\n$gm_boon_reign_effect$, for #v 34#! more months.\n$gm_boon_reign_desc$`, where
  `gm_boon_reign_effect` is the typed string `#G +10%#! [concept_authority]`. GM has no
  `GetStaticModifier(...)` in any loc key.
- **Proposed:** render the modifier: `#b $gm_boon_reign$#!, for #v N#! more months\n[GetStaticModifier('gm_boon_reign').GetDesc]\n$gm_boon_reign_desc$`
  (all 15 in Quick fixes). Keep the `_effect` keys: `gm_com_boon_effect` (the offer event) and
  `test_grand_monument_registry.py:2536-2558` use them. The athletic boon's `state_death_cause_chr_mult` line is the
  "label beside it" the owner asked for (2026-10-22), so GetDesc prints it as intended.
- **Effort:** quick (loc-only)
- **Confidence:** high

### GM-2. Monument policies are prose. Their shared boilerplate is repeated on four buttons
- **Status:** done (2026-10-27, #1210): each policy is a display-only static modifier (`gm_policy_<p>_display`) built from five `script_only` modifier types (`gm_policy_modifier_types.txt`), so the buttons and the overview hover print modifier lines; the shared timing is said once, on the Monument Policy subheader's hover; the history-share clause stays a line after GetDesc.
- **Category:** style / over-explaining
- **Where:** policy buttons `grand_monuments_widget.gui:2816-2852` (tooltips call `gm_policy_*_sgui`, whose
  `effect` is `custom_tooltip = { text = gm_policy_*_effect_tt ... }`, `common/scripted_guis/gm_sguis.txt:292-425`);
  loc `gm_policy_open_effect_tt` (`:3855`), `gm_policy_ceremonial_effect_tt` (`:3838`), `gm_policy_culture_effect_tt`
  (`:3841`), `gm_policy_culture_prestige_effect_tt` (`:3842`), `gm_policy_education_effect_tt` (`:3847`); overview
  hover `gm_je_ov_policy_tt` → custom loc `gm_policy_effects_*` (`:3848-3852`).
- **Now:** each button: "The monument policy becomes **X**. Tourism output from each monument ×1.5, from one
  dedicated To History ×1.25. The other policies' effects stop. National effects change at once, each monument's own
  at the start of next month. After this, the policy cannot change for 60 months; a first choice starts no wait."
  The last three sentences are identical on all four. The 60-month lock is also the IsValidTooltip line
  (`gm_policy_wait_tt`) and in `gm_je_how_policy`.
- **Proposed:** (a) give each policy a static modifier `gm_policy_<p>_display` built from `script_only = yes` modifier
  types (`gm_monument_tourism_mult = 0.5`, `gm_monument_cultural_pull_mult = 0.5`,
  `gm_monument_legitimacy_share_add = 0.25`, `gm_monument_education_access`…; loc in `te_modifiers_l_english.yml`).
  The button's effect then reads `#b X#!\n[GetStaticModifier('gm_policy_<p>_display').GetDesc]`, and the overview
  hover reads the same, so the four policies show as coloured, bulleted lines. (b) Say the shared timing once, as
  the `gm_je_sub_policy` subheader's tooltip ("A change applies to national effects at once and to each monument's
  own at the start of next month. After a change the policy is locked for 60 months; a first choice starts no
  wait."), and drop it from the four buttons (rule 6). (c) The ×1.25 history-share clause is the one figure modifiers
  can't carry. Keep it as a line after GetDesc. `test_grand_monument_registry.py:4512-4523` needs
  `$pm_monument_historic$` in each.
- **Effort:** medium (modifier types + loc). (b) alone is quick (a subheader tooltip and four loc trims).
- **Confidence:** high

### GM-3. What needs a decision is far below the overview that flags it
- **Status:** done (2026-10-27, #1210): as approved (owner, 2026-10-27): Awaiting a Decision (`te_gm_sec_decisions`, contested rows of both lists, shown while any is) straight after the Opportunity, Awaiting Dedication beside it, then Archaeology; the policy subheader and buttons open National Effects; Our Monuments lists only the rest.
- **Category:** spread-out/redundant
- **Where:** composer `te_gm_status_sections` (`grand_monuments_widget.gui:3139-3158`): Opportunity → Archaeology →
  National Effects → Awaiting Dedication → Our Monuments → Trophies → Held Abroad. Contested choices are in
  `gm_monument_row` (`:1846-1867`), inside Our Monuments. The policy buttons are at the foot of National Effects
  (`:2816-2852`).
- **Now:** the overview shows `#R Contested 2` (`gm_je_ov_contested_some`), whose tooltip says "Decide with the
  buttons on its row under Our Monuments". To reach them the player scrolls past every National Effects row in force
  (up to 11 totals, 15 unique dedications, 8 IG rows, 2 ledgers, 14 boons and 5 held specials) and then through all
  upheld rows, which are mixed with the contested ones. The same applies to the policy line in the overview and its
  buttons.
- **Proposed:** follow the owner's own Awaiting Dedication precedent (2026-10-18). Add **"Awaiting a Decision"**, a
  section shown only while `gm_disp_count_contested > 0`, placed straight after the Opportunity. Its datamodel is the
  same `gm_states` list filtered on `gm_status_code = 4`, plus `gm_monuments_held` filtered on `gm_mon_status_code = 4`,
  each row with its three choices. Our Monuments then lists only the rest. Move Awaiting Dedication up beside it, so
  both "act now" sections come before the readout. Move the Monument Policy subheader and its buttons to the top of
  National Effects, directly under the overview line they act on. Update `STATUS` in
  `test_grand_monuments_layout.py` and `test_held_specials_under_the_boons` (`:1033`, which wants the held specials
  before the policy subheader). This doesn't reverse an owner decision: the owner placed Awaiting Dedication above
  Our Monuments, not relative to National Effects.
- **Effort:** medium
- **Confidence:** high

### GM-4. The three contested choices say what happens in prose, with no figures
- **Status:** done (2026-10-27, #1210): each choice's hover gives its figures from preview values the monthly refresh computes (`gm_preview_choices`, marker-guarded against the tooltip walk): the legitimacy and approval steps a tear-down or a rededication moves, the grandeur kept or lost, and Preserve's no-change; the effects' `custom_tooltip` wrapping stays, as the real effects are ledgers.
- **Category:** hidden info / style
- **Where:** `gm_tear_down_sgui` / `gm_rededicate_sgui` / `gm_preserve_sgui` (`gm_sguis.txt:11-100`) →
  `gm_state_choose_*` (`common/scripted_effects/gm_effects.txt:1676-1695`), each a `custom_tooltip` wrapping the real
  effect. Loc `gm_tear_down_tt` (`:4215`), `gm_rededicate_tt` (`:3864`), `gm_preserve_tt` (`:3863`); the secondaries'
  `gm_mon_tear_down_tt` (`:3736`) etc.
- **Now:** "Pull it down. The new order gains legitimacy that fades over about five years, and **Devout** approve;
  **Landowners** resent it. All of its grandeur is lost." Only Rededicate shows a number (its cost). The player
  compares three irreversible options without seeing how much legitimacy, how much approval and how much grandeur
  each moves.
- **Proposed:** add preview script values at state scope (`gm_state_preview_teardown_legitimacy`: the ledger's first
  step from this monument's grandeur; `gm_state_preview_ig_approval`; and Rededicate's halved levels and grandeur) and
  print them as "Label: value" lines. Better still, render the immediate parts as modifier lines: a `script_only`
  "Old Order Torn Down" legitimacy line with the figure, and the IG approval as the vanilla `ig_approval` line. The
  effect would no longer hide them in a `custom_tooltip`, the same problem as `custom_tooltip = { text = X
  add_modifier = {...} }`.
- **Effort:** medium-large (preview values for a fading ledger)
- **Confidence:** medium (the ledger maths lives in `gm_state_ledger_ig` / `gm_init_ledgers`; check that a one-step
  preview is meaningful)

### GM-5. The world-wealth level rate sits in National Effects and repeats on every site row
- **Status:** done (2026-10-27, #1210): the world-wealth rate is the first line of Awaiting Dedication and stays on the state's site card; it left National Effects and every site row. Revised 2026-10-28: Awaiting Dedication shows only while a site stands, so the panel lost the rate before the first level was built; it is now the overview's last line, under the policy, and still said once.
- **Category:** spread-out/redundant
- **Where:** `gm_je_world_rate` as National Effects' first line (`grand_monuments_widget.gui:2147-2151`, loc `:3368`);
  `gm_site_row_rate` on every Awaiting Dedication row (`:1687-1689`, loc `:3943`); `gm_site_card_rate` on the state's
  site card (`te_state_panel_widgets.gui:640-650`).
- **Now:** "A Grand Monument level built this year adds 0.420 grandeur (5 in 1836)" opens a section about what
  monuments *give*. The same figure, which is the same for every site, is printed again under each site.
- **Proposed:** state it once, where building is decided: as the first line of Awaiting Dedication, above its rows
  (rule 6), and on the state's site card, which is one site. Drop it from National Effects and from `gm_site_row`.
  National Effects keeps its "none in force" line as its first line. Tests reference both keys
  (`test_grand_monument_registry.py`, `test_grand_monuments_layout.py`). Update them with the move.
- **Effort:** medium (GUI move, test update)
- **Confidence:** high

### GM-6. Contested is explained in five places, two of them on the same row
- **Status:** done (2026-10-27, #1210): the badge and cell hover are the concept plus one line; the contest line's hover is the row's own: who wants it kept, who resents it and the grandeur that counts against their approval (a standing subtraction, not a monthly one, so no monthly figure).
- **Category:** over-explaining
- **Where:** `gm_je_status_contested_tt` (`:3252`: overview cell, row status badge, secondary status line);
  `gm_row_contest_tt` (`:3869`: the row's "Old Supporters · Resented By" line); `gm_state_contest_tt` (`:4158`);
  `concept_contested_monument_desc` (`te_concepts_l_english.yml:771`); `gm_je_how_contested` (`:3156`).
- **Now:** a contested row shows the badge hover ("It honours something this government is not. It keeps its
  tourism and its effect in its state but gives nothing else, and the group that objected… resents it every month…
  Decide with the buttons on its row") and, one line lower, the contest line's hover, which says nearly the same
  thing. Neither gives the monthly cost of leaving it undecided.
- **Proposed:** badge/cell tooltip: `#b [concept_contested_monument]#!\nNo prestige, legitimacy or approval while it
  stands undecided.` The contest line's tooltip then carries the row-specific part: who resents it and the approval
  it costs them each month (a new `gm_state_disp_resent` value). Keep "It honours something this government is not"
  in `gm_row_contest_tt`, which `test_grand_monuments_layout.py:207` pins.
- **Effort:** quick (loc) for the trim, medium for the monthly figure
- **Confidence:** high

### GM-7. "Undedicated", "Being Built", "under construction", "construction site", "Awaiting Dedication": one icon, stale text
- **Status:** done (2026-10-27, #1210): "Construction Site" for sites (cell "Sites", row titles "Construction site in X"), "Undedicated" only for a finished building; the two stale texts rewritten; a finished undedicated monument is counted on the Our Monuments cell's hover (`gm_disp_count_undedicated`).
- **Category:** style / other (accuracy)
- **Where:** overview cell `gm_je_ov_undedicated` "Being Built N" counts construction sites (`gm_disp_count_undedicated`
  = `gm_state_has_site`, `common/script_values/gm_values.txt:1542`). The row badge "Undedicated"
  (`gm_status_undedicated`) marks a *finished* building on `pm_monument_undedicated` (`gm_status_code` 1,
  `gm_values.txt:245-266`). Both use `status_undedicated.dds`. Loc `gm_je_status_undedicated_tt` (`:3254`),
  `gm_je_how_counts_other` (`:3158`), `gm_je_ov_building_tt` (`:3240`), `gm_site_row_detail_tt` (`:3942`).
- **Now:** `gm_je_status_undedicated_tt`: "…every level built on it joins it until its Dedicate button holds its
  ceremony". `gm_je_how_counts_other`: "An undedicated one gives prestige, cultural pull and tourism, and waits for
  its Dedicate button". But the Dedicate button is a *site's* (`gm_dedicate_button` shows on
  `gm_state_disp_awaiting`), a site "has no effects until it is dedicated" (`gm_site_row_detail_tt`), and building on
  a finished monument's state starts a new site (`gm_je_how_grandeur`). A finished undedicated monument is counted by
  no overview cell (`gm_disp_count_upheld` needs `gm_state_is_dedicated`).
- **Proposed:** one term per thing. "Construction Site" (cell label "Sites N", section "Awaiting Dedication", row
  title "Construction site in X") for sites. "Undedicated" only for the finished building left undedicated. Rewrite
  the two stale texts: `gm_je_status_undedicated_tt` → "Finished but not dedicated: it gives prestige, cultural pull
  and tourism, and nothing for its dedication until its ceremony is held again." (Check against
  `monument_events.2` how a re-dedication is reached.) In `gm_je_how_counts_other`, the last sentence → "A
  construction site gives nothing until its Dedicate button holds its ceremony." Fold status 1 into the Upheld cell's
  count, or give it a fifth state of the cell tooltip. `test_grand_monument_registry.py:7462-7463` only forbids "asks
  again".
- **Effort:** quick (loc) + medium (cell count)
- **Confidence:** medium (how a status-1 monument is re-dedicated should be confirmed in `monument_events.2`)

### GM-8. Every upheld row carries three naming buttons, one usually greyed
- **Status:** done, the quick form (2026-10-27, #1210): Clear Name shows only while the monument has a typed name. The single Name… button was not built: a per-state client flag has no precedent in the mod, and with the gate most rows carry two buttons.
- **Category:** spread-out/redundant (list compactness)
- **Where:** `gm_monument_row`, `grand_monuments_widget.gui:1821-1842` (Rename / Name It / Clear Name, shown on
  `gm_state_can_rename`); `gm_clear_name_sgui` is invalid without a typed name (`gm_sguis.txt:579-605`).
- **Now:** ten upheld monuments mean thirty buttons in Our Monuments. Clear Name is greyed on every row that has no
  typed name, which is most of them, and naming is a rare action.
- **Proposed:** show Clear Name only while `gm_state_has_typed_name = 1` (the value the title already switches on).
  Better: replace the trio with one small "Name…" button (or a pen `button_icon_*`) beside the title. It reveals the
  three on click through a client-side `GetVariableSystem` flag per state, the way the trophy card's view buttons
  work.
- **Effort:** quick (visible gate) / medium (single button)
- **Confidence:** medium

### GM-9. Trophy tooltips: stale "half the levels", and the same sentence on every hover of the state card
- **Status:** done (2026-10-27, #1210): the loc part in #1202; `gm_state_tr_summary_tt` and `gm_mon_row_value_tt` lose the repeated carry-off rule; `gm_tr_take_site_tt` takes the rows' wording.
- **Category:** over-explaining / other (accuracy)
- **Where:** `gm_je_tr_summary_tt` (`:3261`), `gm_state_tr_summary_tt` (`:4192`), `gm_tr_take_site_tt` (`:4325`)
  versus `gm_tr_row_value_tt` / `gm_tr_row_site_value_tt` / `gm_mon_take_tt`, which say "half the grandeur… its
  levels and its years". `test_grand_monument_registry.py:5565-5571` forbids "half the levels" in those three only.
  "A country whose armies hold half the state in a war can carry them off" appears in `gm_state_tr_header_tt`
  (`:4188`), `gm_state_tr_summary_tt`, `gm_state_mon_header_tt` (`:4178`) and `gm_mon_row_value_tt` (`:3728`), all on
  the state view's monument and trophy cards.
- **Now:** the Trophies summary hover says a trophy counts for "half the levels carried off". The rows beneath it
  say "half the grandeur carried off, its levels and its years". On the state view, the header, the summary and each
  secondary row repeat the carry-off rule.
- **Proposed:** `gm_je_tr_summary_tt` takes the rows' wording (Quick fixes). `gm_state_tr_summary_tt`: same wording,
  and drop its last sentence, since the card's header hover says it. It is in Findings only because
  `test_grand_monument_trophies.py:644` asserts four words in it, all of which survive. `gm_mon_row_value_tt`: drop
  its last sentence, since `gm_state_mon_header_tt` and `gm_je_how_trophies` say it. `gm_tr_take_site_tt`: "half its
  levels" → confirm whether a re-taken trophy counts for half its current or its original grandeur, then use the
  rows' wording.
- **Effort:** quick
- **Confidence:** high (wording drift), medium (re-take semantics)

### GM-10. Held Abroad repeats the section's "ways home" paragraph on every row; Trophies does the same with "what it counts for"
- **Status:** done (2026-10-27, #1210): the Held Abroad row's hover is row-specific (at war with the holder or not, so whether Carry It Off is open); `gm_tr_row_value_tt` is cut to its one row-specific sentence.
- **Category:** spread-out/redundant (rule 6)
- **Where:** `gm_tr_row_abroad`'s "Held by" line tooltip `gm_tr_row_held_by_tt` (`:4298`) is word for word
  `gm_je_abroad_ways_tt` (`:3122`), the section summary's tooltip (`gui/gm_trophy_widgets.gui:2229-2231, 2432-2434`).
  `gm_tr_row_value_tt` (`:4306`) on every held row restates `gm_je_tr_summary_tt`.
- **Now:** hovering any Held Abroad row gives the same three ways home as the line above the rows.
- **Proposed:** make the row hover row-specific: are we at war with the holder (Carry It Off possible)? Is the
  Return Cultural Property article open to us against them? Use the treaty article's own `possible` as an
  IsValidTooltip-style check, or a small `gm_tr_disp_*` value. If that's too much, remove the row's tooltip and
  `#tooltippable` and leave the summary's. Trim `gm_tr_row_value_tt` to its one row-specific sentence ("If it goes
  home, all its levels are rebuilt and its years come back with it.").
- **Effort:** quick (remove/trim) / medium (row-specific checks)
- **Confidence:** high

### GM-11. Carrying off a trophy on display or a secondary monument hides its infamy cost
- **Status:** done (2026-10-27, #1210): container-scope `gm_tr_disp_take_infamy` / `gm_mon_disp_take_infamy` print the infamy in both hovers.
- **Category:** hidden info / style
- **Where:** `gm_tr_take_site_tt` (`:4325`) and `gm_mon_take_tt` (`:3735`): "We gain [concept_infamy]…", no figure.
  The primary's `gm_tr_take_occupation_tt` (`:4322`) shows `#R [THIS.GetState.MakeScope.ScriptValue('gm_state_tr_infamy')|1]#!`.
  The amount is `gm_tr_infamy` (2 + 1 per 5 grandeur, at most 8, doubled under UNESCO;
  `common/script_values/gm_trophy_values.txt:111`).
- **Now:** three Carry It Off buttons, and only one says how much infamy.
- **Proposed:** add container-scope twins of `gm_state_tr_infamy` (`gm_tr_disp_take_infamy`,
  `gm_mon_disp_take_infamy`) and print `#R N#! [concept_infamy]` in both tooltips. Or render the effect's own
  `change_infamy` line by moving it outside the `custom_tooltip`.
- **Effort:** medium
- **Confidence:** high

### GM-12. Opportunity section: the levels still needed are hidden, the How text says levels where the panel says grandeur, and two hovers repeat each other
- **Status:** done (2026-10-27, #1210): the loc part in #1202; a Levels to Go row under the bar (`gm_disp_com_levels_to_go`).
- **Category:** hidden info / other (accuracy) / over-explaining
- **Where:** `te_gm_sec_commission` (`grand_monuments_widget.gui:2018-2114`). Loc `gm_je_com_progress_tt` (`:3140`),
  `gm_je_com_ask_tt` (`:3130`), `gm_je_how_commissions` (`:3154`). Target set to `5` grandeur in `gm_com_begin`
  (`common/scripted_effects/gm_commission_effects.txt:139`); levels to go `gm_com_levels_to_go`
  (`gm_commission_values.txt:155`) appear only in the Raise It hover (`gm_button_com_raise_where`, `:2869`).
- **Now:** the bar reads "Grandeur Added 0.84 / 5.0". How many levels that is at today's rate (the number the
  player builds) is only in Raise It's tooltip. `gm_je_how_commissions` says "Each asks for 5 levels of its
  dedication", while the panel and the player guide (`02-timeline.md:958`, "asks for 5 grandeur") say grandeur.
  `gm_je_com_ask_tt` explains what counts and where, which the next line (`gm_je_com_where_line`) and the bar's hover
  (`gm_je_com_progress_tt`) also say.
- **Proposed:** in Quick fixes, add "About N more levels at today's rate" to the bar's hover, fix "5 levels" → "5
  [concept_grandeur]" in How (with GM-15's bullets), and trim `gm_je_com_ask_tt` to its one unique sentence. Larger:
  put the levels in the bar row's value ("0.84 / 5.0 · 9 lv"; the 86 value cell needs widening, or a second
  `gm_value_row` "Levels to Go: 9").
- **Effort:** quick (loc) + medium (row)
- **Confidence:** high

### GM-13. All eight IG approval rows share one generic paragraph and none says where its total comes from
- **Status:** done (2026-10-27, #1210): the shared paragraph is the Approval subheader's hover; each IG row's hover gives its own parts (approves of, objects to, resents while contested, past decisions), summed per IG in `gm_compute_ig`.
- **Category:** over-explaining / hidden info (rule 6)
- **Where:** `grand_monuments_widget.gui:2502-2589`, every row `tooltip = "gm_je_tt_ig"` (loc `:3281`).
- **Now:** hovering Landowners +2 or Devout −1 gives the same explanation of how totals work. Which monuments the
  group likes or resents isn't shown anywhere.
- **Proposed:** move `gm_je_tt_ig` to the `gm_je_sub_approval` subheader (said once, above the rows). Give each row a
  per-IG hover: "From monuments it approves of: +G grandeur · it objects to: −G · contested it resents: −G · past
  decisions: ±G". The monthly pass already sums these per IG for `gm_display_ig_*`, so storing the parts as
  `gm_display_ig_<ig>_pos/_neg/_ledger` is small.
- **Effort:** quick (move) / medium (breakdown)
- **Confidence:** medium (the per-IG sums must exist separately in `gm_country_refresh`)

### GM-14. Archaeology has no How subsection, its mechanics sit in a live hover, and its terms aren't hoverable
- **Status:** done (2026-10-27, #1210): an Archaeology subsection in How Grand Monuments Work, the summary cut to one line, a subheading over each list gated on its count, and hovers on the two Abroad lines (the article, and Foreign Scholarship's GetDesc).
- **Category:** over-explaining / hidden info / list
- **Where:** `gui/gm_archaeology_widgets.gui:170-242`. `gm_je_arch_summary_tt` (`:3126`) is the system's only
  explanation; `te_gm_sec_how` (`grand_monuments_widget.gui:3013-3132`) has no archaeology heading (no `gm_je_how_*`
  key mentions digs). Row lines `gm_arch_row_abroad_permit` / `_concession` / `gm_arch_row_dig_permit` (`:2601-2606`)
  name "Excavation Concession", "Excavation Permit" (treaty articles, `te_concepts_l_english.yml:336, 1375`) and
  "Foreign Scholarship" (static modifier `gm_arch_scholarship`) as plain text. The digs list and the open-sites list
  follow each other with no heading.
- **Now:** "Archaeological Expeditions": a summary line, then dig rows and site rows in one run.
- **Proposed:** add "Archaeology" to How Grand Monuments Work (new `gm_je_how_sub_archaeology` +
  `gm_je_how_archaeology`, taking the second half of `gm_je_arch_summary_tt` and the three methods' one-line
  comparison now on each button). Cut `gm_je_arch_summary_tt` to one line ("Digs under way and buried sites we may
  dig"). Put a `gm_subheader` over each list ("Digs Under Way", "Open Sites"), each gated on its count. Give the two
  "Abroad" lines a tooltip: the article name and, for the permit, `[GetStaticModifier('gm_arch_scholarship').GetDesc]`.
  A datamodel row's tooltip may read GetStaticModifier, which is global.
- **Effort:** medium
- **Confidence:** high

### GM-15. How it Works: a nine-item list written as one sentence, and the step rules told twice and inconsistently
- **Status:** done (2026-10-27, #1210): the loc part in #1202; the unique dedications are bullets too, and the step families are three lines in `concept_grandeur_desc` only.
- **Category:** list / over-explaining (duplication within How)
- **Where:** `gm_je_how_commissions` (`:3154`), `gm_je_how_signatures` (`:3166`); `gm_je_how_grandeur` (`:3159`)
  versus `concept_grandeur_desc` (`te_concepts_l_english.yml:818`).
- **Now:** the opportunity moments are one 90-word comma list. The unique dedications are another. The step
  schedule ("first step of 5, then 10, 15… complete at 5, 15, 30, 50, 75… twice the one before… 5, 15, 35, 75,
  155… Legitimacy and cultural pull take steps of 10") is in both How and the concept. In both, cultural pull is named
  in the 5-step family and then again in the 10-step one.
- **Proposed:** bullets for the moments (Quick fixes) and for the shared unique dedications. Keep the step schedule
  only in `concept_grandeur_desc`, as three lines ("Local effects and prestige: steps of 5, 10, 15… / Cultural pull
  and legitimacy: steps of 10, 20, 30… / Other national effects and approval: each twice the last, up to 8"). Check
  each against `gm_set_steps_*` in `gm_effects.txt:950-990`. `gm_je_how_grandeur` keeps the site/dedication story and
  links `[concept_grandeur]`. `test_grand_monument_registry.py:1899` wants no "+5" in `gm_je_how_grandeur`.
- **Effort:** quick (bullets) / medium (de-duplicate after verifying the step families)
- **Confidence:** high (structure), medium (which family legitimacy is in)

### GM-16. Smaller items in National Effects and the row
- **Status:** done (2026-10-27, #1210): "Opportunities Seized" with "mo" on the months; the no-ceiling sentence dropped from three hovers; `gm_row_frozen_tt` cut; `gm_tr_row_site_value_tt` names the tab only (its test updated).
- **Category:** style
- **Where / Now / Proposed:**
  - `gm_je_sub_boons` "Opportunities Seized (Months Left)" (`:3257`) heads both the boons (value = months) and the
    held unique dedications (`gm_je_val_sig_held_*` = "×2", a count). Rename it to "Opportunities Seized" and give the
    months their unit in the value (`#v 34#! mo`, as CE's "/mo").
  - The "There is no ceiling: each step takes N grandeur more than the one before." sentence closes
    `gm_je_tt_prestige`, `gm_je_tt_culture` and `gm_je_tt_education` (`:3279-3285`), and is in `concept_grandeur_desc`.
    Drop it. These keys are partly pinned (`test_grand_monument_registry.py:1896-1899, 3317-3323, 4484`), but not
    that sentence.
  - `gm_row_frozen_tt` (`:3873`) re-teaches ageing on every finished row. Cut it to "Finished at N levels: nothing
    built later joins it. It ages by 2% of its starting grandeur a year while its message stands or it is kept as
    heritage." (keeps the phrase `test_grand_monuments_layout.py:974` pins) and leave the rest to
    `gm_je_how_grandeur_age`.
  - `gm_tr_row_site_value_tt` (`:4303`) ends "…can be viewed in the Grand Monuments tab of the Timeline Extended window
    or in the Journal Entry". Rule 9 says name the tab only, but `test_grand_monument_trophies.py:642` pins "Journal
    Entry". Leave it, or update the test.
- **Effort:** quick
- **Confidence:** high

### GM-17. Type sizes below the house ladder
- **Status:** done (2026-10-27, #1210): `gm_fontsize_row` / `_heading` / `_overview` (17/20/16) through all three GM files, cells resized from the longest label, `LabelBudgetTest` reads each template.
- **Category:** style
- **Where:** `gm_step_row`, `gm_value_row`, `gm_text`, `gm_row_line`, `gm_tr_line`, `gm_arch_line` use
  `fontsize_medium` (14, OpenSans). Buttons (`gm_choice_button`, `gm_policy_button`, `gm_arch_button`,
  `gm_tr_button`, `gm_dedicate_button`) and the overview cell labels (`gm_ov_cell`) use `fontsize_small` (12).
- **Now:** rows at 14 and overview words at 12, where rule 3 (owner, 2026-10-17) asks 17 for rows, values, buttons
  and notes, and 16 for the overview.
- **Proposed:** add panel font templates (`gm_fontsize_row` / `_heading` / `_overview`, as Banking's) and size the
  label columns from the longest label first. `test_grand_monuments_layout.LabelBudgetTest` budgets 25 medium-font
  characters in the 240 label column, so the 4 + 240 + 8 + 130 + 8 + 86 split needs redoing (e.g. a narrower
  bar). This predates the 2026-10-17 rule, so bring it in line when the panel is next reworked.
- **Effort:** medium
- **Confidence:** high

### Colonial Empire

### CE-1. Colonial Holdings: territories and subjects are 8 fixed slots plus a "+N more" hover. Make them datamodels
- **Status:** done (2026-10-27, #1210): datamodels over `colonial_empire_blocs` and `colonial_empire_subject_capitals`, every row with its buttons; the slots, the "+N more" hovers and their sguis are gone; row hovers read `GetPlayer`. `State.GetCountry` from a datamodel item is unproven, so the first subject row logs `TE_SELF_CHECK OK|BROKEN ce_subject_row` once a game (play-test list: `docs/testing/colonial-holdings-playtest.md`).
- **Category:** list
- **Where:** `colonial_empire_widget.gui:2179-2269` (eight `te_ce_territory_row` instances on
  `Var('colonial_empire_territory_1..8')`, then `je_colonial_empire_territories_more` with
  `colonial_empire_territories_sgui`, which prints positions 8-23 and a tail at 24). `:2287-2369` holds eight
  `te_ce_subject_row` on `colonial_empire_subject_1..8` and `colonial_empire_subjects_sgui` (up to 40). Wars: three
  slots, `:2127-2148`. Built in `colonial_empire_refresh_display`
  (`common/scripted_effects/colonial_empire_display_effects.txt:202-253`).
- **Now:** the ninth territory onward exists only as a line in a hover, with no figures, no colony icon and no
  Release button. A player with twelve blocs can release only eight from the panel.
- **Proposed:** in the same monthly refresh, after `colonial_empire_mark_release_blocs`, build
  `clear_variable_list = colonial_empire_blocs` and
  `ordered_scope_state = { limit = { has_variable = colonial_bloc_seed } order_by = colonial_bloc_disp_gdp max = 99
  add_to_variable_list = { name = colonial_empire_blocs target = this } }`. Build `colonial_empire_subject_capitals`
  the same way from `ordered_subject_or_below = { limit = { is_qualifying_colonial_subject = yes } order_by = gdp …
  capital = { add_to_variable_list … } }`. Countries go through their capital, per gui_modding_guide gotcha 15, as
  the rows already do. Then one row each:
  `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('colonial_empire_blocs')]"`, item
  `te_ce_territory_row = { datacontext = "[Scope.GetState]" }`, the Demographics States pattern. The rows' cells
  already read only `State.*` and pass `State.MakeScope` to their buttons, so their bodies don't change. Tooltips
  inside the row that read `JournalEntry` (`je_colonial_empire_territory_primary_tt` reads the national thresholds)
  must switch to `GetPlayer`, the overview's own workaround (gotcha 24). Delete the two "+N more" sguis and keys, and
  the 16 `remove_variable` slots. Wars stay three slots (the script caps three wars). Update
  `test_colonial_empire_layout.py:965-985`, which pins the eight slots.
- **Effort:** large (script list + GUI + tests), but mechanical
- **Confidence:** high

### CE-2. International Pressure is a script-built text block. Make it a table of great powers
- **Status:** done (2026-10-27, #1210): a table, one script container per great power (`colonial_empire_gp_rows`: flag, name, stance, prestige, stability a month), the escalations in force under it; the per-power factors and escalation losses are named values the bar's terms use, so the rows add up to its row. The two share lines went with the roster.
- **Category:** list / spread-out/redundant
- **Where:** `te_ce_sec_pressure` (`colonial_empire_widget.gui:1926-1954`), whose only child is a
  `colonial_empire_text` (fontsize_large) printing `colonial_empire_pressure_sgui`'s ExecuteTooltip
  (`common/scripted_guis/colonial_empire_sguis.txt`, the `every_country` loops). Loc
  `je_colonial_empire_pressure_scaling_tt` (`:267`), `_share_tt`, `_support_share_tt`, `_condemner_entry_tt` (`:174`),
  `_supporter_entry_tt`.
- **Now:** "Our prestige: 1,240 / Condemners' share: 41% / Supporters' share: 12% / Condemning — France (prestige
  980) / Supporting — Russia (prestige 1,500)…" at 20 pt. The two shares repeat the overview pie's legend. What each
  power costs or gives a month (its prestige weight ×0.25–×2 against ours, times −0.6 or +0.3,
  `colonial_gp_condemnation_weight`, `colonial_empire_values.txt:155`) is shown nowhere, though it's the number a
  player acts on diplomatically.
- **Proposed:** build `colonial_empire_gp_stances` (the capitals of great powers with `gp_anti_colonial_stance` or
  `gp_pro_colonial_stance`, condemners first) in `colonial_empire_refresh_display`. Draw a head row and one row per
  power: vanilla `tiny_flag` (name on hover, opens the country) | name | stance word (`#R Condemning` / `#G Supporting`)
  | prestige | "−0.84/mo". The weight is relative to *our* prestige, so a value on the GP's own scope can't compute
  it. The robust route is the one the trophy and dig rows use: the refresh creates one script container per stance,
  holding the GP's capital (`var:ce_gp_capital`) and its signed monthly weight (`var:ce_gp_weight`, the
  `colonial_gp_condemnation_weight` term for that one power). The datamodel then runs over those containers
  (`Scope.GetScriptContainer`; flag through `ScriptContainer.MakeScope.Var('ce_gp_capital').GetState.GetCountry`, as
  the covert rows do). Keep "No great power is pressing us" as the empty line. Drop the two share lines, which the
  overview legend shows. Rows at the panel's row size, not 20.
- **Effort:** medium-large
- **Confidence:** high (structure), medium (the per-row weight route)

### CE-3. The live lists open with #lore captions that restate their own column-head hovers
- **Status:** done (2026-10-27, #1210): the territories and subjects captions are gone; the wars caption's mechanic is in `je_colonial_empire_holdings_wars_tt` and How it Works.
- **Category:** over-explaining
- **Where:** `je_colonial_empire_territories_caption` (`te_journal_entries_l_english.yml:311`, shown at
  `colonial_empire_widget.gui:2175`), `je_colonial_empire_subjects_caption` (`:306`, at `:2283`),
  `je_colonial_empire_wars_caption` (`:357`, at `:2125`).
- **Now:** territories: "Largest GDP first. A territory shares its row with the states one release would take with
  it (+N). A lit icon: a colony among them. A red figure: the test that makes it one. Hover a name for the states,
  the people who would form the new nation and the weight on stability. Release opens a decision on that row
  alone." Each sentence is already a hover one cell away: `…_head_gdp_tt` ("The list runs from the largest down"),
  `…_head_name_tt` ("+N after the name"), `…_territory_colony_tt`, `…_head_primary_tt` / `…_head_sol_tt` ("Red when…"),
  the name's own hover, and `CE_RELEASE_STATE_TT`.
- **Proposed:** remove the territories and subjects captions (GUI: drop the two `colonial_empire_list_text`). As a
  loc-only first step, cut them to "Largest GDP first; hover any cell for its details." (Quick fixes). The wars
  caption's first sentence ("Holding their land does not end a war of independence: only their capitulation, or a
  peace, does") is the one mechanic said nowhere else. Move it into `je_colonial_empire_holdings_wars_tt` and a How
  line, and drop the caption.
- **Effort:** quick (loc) / quick-medium (GUI removal)
- **Confidence:** high

### CE-4. The definitions of territory, colony and colonial subject are written out five times, and have drifted
- **Status:** done (2026-10-27, #1210): `concept_colonial_territory`, `concept_overseas_colony` (vanilla has `concept_colony`, for colonization) and `concept_colonial_subject`, each with its thresholds read from script; the five hovers and `CE_STATE_IS_ELIGIBLE` (and the two `IS_*_STATE_TT` requirement lines) link them. The territory test is the strict one: the distinct-people share is part of it, and the colony adds the unincorporated, indigenous or living-standards test.
- **Category:** over-explaining / style (consistency)
- **Where:** `je_colonial_empire_ov_held_tt` (`:242`), `je_colonial_empire_holdings_territories_tt` (`:210`),
  `je_colonial_empire_territory_head_name_tt` (`:322`), `je_colonial_empire_holdings_subjects_tt` (`:208`),
  `je_colonial_empire_territory_colony_tt`, and the button condition `CE_STATE_IS_ELIGIBLE`
  (`te_miscellaneous_l_english.yml:207`).
- **Now:** the "more than X% a people sharing no heritage with ours" test is part of *territory eligibility* in
  `holdings_territories_tt` and `territory_head_name_tt`. In `ov_held_tt` it is part of the *colony* test
  ("…more than X% of the people and poorly accepted"). `CE_STATE_IS_ELIGIBLE` doesn't mention it at all. A player
  can't tell which is right, and each hover is 80-120 words.
- **Proposed:** three concepts in `extra_concepts.txt` (names in `te_miscellaneous`, descs in `te_concepts`):
  `concept_colonial_territory` (overseas, not a homeland, ≥ N people, not settled land),
  `concept_colony` (a colonial territory meeting the indigenous, the living-standards or the unincorporated test) and
  `concept_colonial_subject`. Concept descs can read thresholds through `GetPlayer.MakeScope.ScriptValue(...)`, as
  `je_colonial_empire_ov_heading_tt` does. Then:
  `ov_held_tt` → "It runs while we hold a [concept_colony] or a [concept_colonial_subject]; it ends without penalty
  once we hold neither."; `holdings_territories_tt` → "Every [concept_colonial_territory] we hold, one row per release.
  A lit icon marks a [concept_colony]."; `head_name_tt` → "[concept_colonial_territory]; +N: the states one release
  takes with it."; `holdings_subjects_tt` → keep only its second half (no stability effect; liberty desire in
  Strained and below). First check which version of the indigenous test `is_decolonization_eligible_state` and
  `is_overseas_colonial_state` actually use. `test_colonial_empire_layout.py:620-623, 1029` pin threshold reads in
  `ov_held_tt` and `territory_head_name_tt`. Move those asserts to the concept descs.
- **Effort:** medium
- **Confidence:** high (duplication), medium (which text is right)

### CE-5. Pillar-row tooltips end in the same two boilerplate lines
- **Status:** done (2026-10-27, #1210): both boilerplate lines gone from the eight hovers; How it Works says once that each bar spans its term's usual range.
- **Category:** over-explaining
- **Where:** `je_colonial_empire_drift_*_tt` (`te_journal_entries_l_english.yml:183-200`). Eight end "#lore The bar
  spans A to B; the figure beside it is exact.#!", and three add "Updated monthly." The rows are at
  `colonial_empire_widget.gui:1700-1905`.
- **Now:** every term's hover spends a line on how the bar is drawn.
- **Proposed:** say once in `je_colonial_empire_how_moves`: "Each row's bar spans that term's usual range; the figure
  beside it is exact. Overreach, great-power pressure and acceptance are counted at the monthly assessment." The last
  part is already there. Drop both lines from the rows. The ranges are design detail a returning player doesn't act
  on, so they're the one thing lost. This isn't a quick fix for that reason.
- **Effort:** quick (loc, nine keys)
- **Confidence:** medium (whether the owner wants the ranges kept)

### CE-6. Programme rows: a 12-pt cost line packs four figures, the stability figure appears three times, and the hover's prose repeats its own modifier lines
- **Status:** done (2026-10-27, #1210): the row is short name, level, stability a month and the stepper at the row size; costs (Upkeep / One-off lines) and what a level adds on the hover; the garrison's infamy is a named value.
- **Category:** style / spread-out/redundant / over-explaining
- **Where:** `colonial_empire_policy_row` (`colonial_empire_widget.gui:920-991`, `row_cost` at `fontsize_small`,
  `:950`). Loc `je_colonial_empire_cost_invest` / `_garrison` / `_assimilation` (`:176-178`), `je_colonial_empire_tt_*`
  (`:339-341`), `CE_*_BODY` (`te_miscellaneous_l_english.yml:161, 185, 191`).
- **Now:** under each name: "Upkeep @£1.2k/wk (@£400 a level), one-off @£25k a step · stability +0.42/mo (+0.14 a
  level)" in small #lore type, which is decision input below rule 3's floor. The hover repeats "Bar contribution:
  +0.42 a month at level 1 of 3. Each level adds +0.14", and the Programmes pillar row shows the total. The hover
  opens with a three-sentence BODY ("A one-off payment… ongoing bureaucracy and authority costs… accelerates
  assimilation and conversion… accelerating radicalism") that the `GetDesc` lines below it already show:
  `colonial_cultural_assimilation_modifier` carries bureaucracy, authority cost, assimilation, conversion and
  radicals. The plus button's ExecuteTooltip already shows the one-off payment and the start-up IG disapproval, which
  are left visible in `colonial_programme_invest_up`.
- **Proposed:** row = name | level as three pips or "1 / 3" | stability "+0.42/mo" (green) | − +, all at row size.
  The costs move into the row hover, as a two-line "Upkeep: … · One-off: … a step" table. Trim the BODY keys to their
  flavour sentence (Quick fixes).
- **Effort:** quick (BODY) / medium (row)
- **Confidence:** high

### CE-7. The overview carries an explanatory note, and the same rule is written four times
- **Status:** done (2026-10-27, #1210): the note is gone; each legend line carries what its share does, and the pie has its own hover.
- **Category:** over-explaining
- **Where:** `je_colonial_empire_ov_legend_note` (`:250`, `fontsize_small`, `colonial_empire_widget.gui:1626-1635`).
  The same rule is in `je_colonial_empire_pressure_share_note` (`:268`), `…_support_share_note`, `…_how_pressure`
  (`:220`) and the isolation/consensus hovers.
- **Now:** under the pie legend, in the always-open overview: "Isolation and consensus count only the condemning
  share."
- **Proposed:** remove the note (rule 1: no explanations in live sections). Put the sentence on the Supporting legend
  row's tooltip ("Support adds to stability every month but does not offset isolation or consensus."), where the
  question arises. Once CE-2 lands, drop the two `_share_note`s with their share lines.
- **Effort:** quick-medium (GUI)
- **Confidence:** high

### CE-8. The Release button's hover repeats the row name's hover
- **Status:** done (2026-10-27, #1210): no further change needed: the loc part in #1202 was the whole fix.
- **Category:** over-explaining
- **Where:** `CE_RELEASE_STATE_TT` (`te_miscellaneous_l_english.yml:203`, via `colonial_empire_effect_release_state`,
  `decolonization.txt:1679`) versus the name cell's `colonial_empire_bloc_sgui` hover (`je_colonial_empire_bloc_people`,
  `_bloc_states`).
- **Now:** "…The new nation would be its largest people whose homeland it is or, if none of them lives there, its
  largest people other than ours, and it would leave with every neighbouring state of ours where they are at home…"
  The name hover beside it gives this row's actual answer ("Released, it forms a nation of its Malay people. It takes
  with it… these 3 states").
- **Proposed:** cut to the decision and its safety (Quick fixes). The general rule stays in
  `je_colonial_empire_how_decolonization`.
- **Effort:** quick
- **Confidence:** high

### CE-9. Every subject row repeats the band rule in its liberty-desire hover
- **Status:** done (2026-10-27, #1210): no further change needed: the loc part in #1202 was the whole fix.
- **Category:** over-explaining (rule 6)
- **Where:** `je_colonial_empire_subject_ld_tt` (`:298`).
- **Now:** after the row's own figures: "In the Strained band and below, every colonial subject of ours gains more of
  it each month." The same sentence is in the section's subheader hover (`je_colonial_empire_holdings_subjects_tt`),
  `concept_colonial_band_desc` and `je_colonial_empire_how_bar_2`.
- **Proposed:** drop the sentence (Quick fixes).
- **Effort:** quick
- **Confidence:** high

### CE-10. Stale text: the decolonization concept and both tab tooltips
- **Status:** done (2026-10-27, #1210): no further change needed: the loc part in #1202 was the whole fix.
- **Category:** other (accuracy) / hidden info
- **Where:** `concept_decolonization_system_desc` (`te_concepts_l_english.yml:789`); `te_window_tab_colonial_empire_tt`
  (`te_miscellaneous_l_english.yml:8561`); `te_window_tab_grand_monuments_tt` (`:8564`).
- **Now:** the concept says "Three colonial programmes and three decolonization decisions allow colonial powers to
  manage the transition". For a player, the decisions are now a Release button per territory and subject plus
  Planned Full Decolonization (the three scripted buttons are AI-only). The concept also doesn't name the tab
  (rule 9). The CE tab tooltip lists everything but Colonial Holdings, the first section. The GM tab tooltip ("Your
  Grand Monuments, their national effects and any that are contested") leaves out opportunities, digs, construction
  sites and trophies.
- **Proposed:** see Quick fixes.
- **Effort:** quick
- **Confidence:** high

### CE-11. Smaller style points
- **Status:** done (2026-10-27, #1210): `colonial_empire_fontsize_row` / `_heading` / `_overview` (17/20/16), every cell resized and held by `WidthBudgetTest`; Stable reads green; the heading hover is the projection; How links `[concept_colonial_band]` instead of repeating it. Spelling left for the separate pass. The overview is four `te_banking_ov_cell` cells (owner, 2026-10-27).
- **Category:** style
- **Where / Now / Proposed:**
  - Type sizes: pillar rows, list cells and the decision row are `fontsize_medium` (14). Column heads, programme costs,
    the overview words (`te_ce_ov_icon_label`) and the legend note are `fontsize_small` (12). The pressure roster is
    `fontsize_large` (20, `colonial_empire_text`). Rule 3 wants 17 / 16. The same remedy as GM-17 applies
    (`test_colonial_empire_layout.py` width budgets).
  - Band colour vs status phrase: the Stable band reads `#G Stable#!` (`je_colonial_empire_band_stable`, `:157`), but
    the band hover's status sentence opens `#Y Colonial holdings are stable.#!` (`je_colonial_empire_status_stable`,
    `:285`). Use `#G` to match.
  - `je_colonial_empire_ov_heading_tt` (`:240`) explains the bar's drawing ("The green stretch… the red stretch…"),
    which `je_colonial_empire_how_bar_2` covers. Cut it to the projection and "assessed again every month". The key
    is test-referenced (`test_colonial_empire_layout.py:268-275`: it must contain `GetPlayer.`), so it isn't in Quick
    fixes.
  - `je_colonial_empire_how_bar_2` (`:215`) and `concept_colonial_band_desc` (`te_concepts:762`) share their last two
    sentences word for word. Keep them in the concept and link `[concept_colonial_band]` from How.
  - Spelling is mixed British/American ("programme", "neighbouring", "politicises" beside "radicalize",
    "radicalizes"). Low priority: noted once for the whole slice.
- **Effort:** quick-medium
- **Confidence:** high

## Applied in this PR

29 loc-only edits from this slice were applied (text rewritten in place, keys unchanged). The pre-edit text is in git history; the finding each serves is named above. Keys:

`CE_CULTURAL_ASSIMILATION_BODY`, `CE_INVEST_IN_DEVELOPMENT_BODY`, `CE_MILITARY_GARRISON_BODY`, `CE_RELEASE_STATE_TT`, `concept_decolonization_system_desc`, `gm_je_com_ask_tt`, `gm_je_com_progress_tt`, `gm_je_how_commissions`, `gm_je_tr_summary_tt`, `gm_je_tt_boon_centenary`, `gm_je_tt_boon_defeat`, `gm_je_tt_boon_faith`, `gm_je_tt_boon_great_power`, `gm_je_tt_boon_homecoming`, `gm_je_tt_boon_regime`, `gm_je_tt_boon_reign`, `gm_je_tt_boon_ruler_death`, `gm_je_tt_boon_space`, `gm_je_tt_boon_tech_artistic`, `gm_je_tt_boon_tech_athletic`, `gm_je_tt_boon_tech_industrial`, `gm_je_tt_boon_tech_naturalist`, `gm_je_tt_boon_tech_scientific`, `gm_je_tt_boon_victory`, `je_colonial_empire_subject_ld_tt`, `je_colonial_empire_subjects_caption`, `je_colonial_empire_territories_caption`, `te_window_tab_colonial_empire_tt`, `te_window_tab_grand_monuments_tt`
