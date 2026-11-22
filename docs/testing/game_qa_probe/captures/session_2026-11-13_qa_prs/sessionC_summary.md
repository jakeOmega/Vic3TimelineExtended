Restore: restored (58 files put back, 0 removed).

- Permission: owner in this session, 2026-11-12 23:07 MST: 'You will be able to run the game to test but I would like this to be as late in the process as possible - do what you can first, please.' Offline work done first.
- Snapshot: 20261113T084215Z
- Save: te_qa_fixture_c6498ca4f4c4_d18360329
- Country: FRA
- Overlay removed: True

## Self-checks

1 BROKEN, 1 START (no verdict was logged after it), 30 OK.

- Session: 0 TE_SELF_CHECK lines in /mnt/d/vic3_qa_backups/runs/20261113T084215Z/debug.log. The game writes its log in blocks, so a line logged after the last verb may be missing.
- The run that made the fixture: 140 lines kept from snapshot 20261113T083721Z, 35 of them TE_SELF_CHECK (/mnt/d/vic3_qa_backups/fixtures/c6498ca4f4c4_d18360329/lines.log).

| Check | Verdict | From | Line |
|---|---|---|---|
| delayed_state_event | BROKEN | fixture | events/te_debug_demog_events.txt:1298: TE_SELF_CHECK BROKEN delayed_state_event (a state event triggered with days = 7 never ran: move the delayed calls of te_demog_events.4, monument_events.30 and .31 to a country event) date=January 16, 1836 |
| cm_census_yearly | START | fixture | common/scripted_effects/te_culture_merge_selfcheck_effects.txt:171: TE_SELF_CHECK START cm_census_yearly year=1836 (the verdict follows at the next census, a year on; a START with no verdict after that means the calendar-year guard never lets a second census through) |
| decentralized_law_baseline | OK | fixture | common/on_actions/te_decentralized_laws_selfcheck_on_actions.txt:46: TE_SELF_CHECK OK decentralized_law_baseline (no decentralized nation holds any of the five placeholder laws after history: the history baseline reached them) |
| primate_state_flag | OK | fixture | common/scripted_effects/te_demog_place_effects.txt:253: TE_SELF_CHECK OK primate_state_flag tag=GBR city=Home Counties self=1 states=1 date=January 1, 1836 |
| monument_piece_rejoins | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1952: TE_SELF_CHECK OK monument_piece_rejoins (the Parthenon's marbles read as a piece of the Parthenon in Attica) |
| monument_artifact_stands_apart | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1965: TE_SELF_CHECK OK monument_artifact_stands_apart (the Luxor Obelisk reads as apart from the Obelisks of Karnak) |
| ch_board_rows | OK | fixture | common/scripted_effects/cultural_hegemony_effects.txt:162: TE_SELF_CHECK OK ch_board_rows ranked=99 (the board store lists the leader's row with its capital) date=January 2, 1836 |
| covert_can_research_current | OK | fixture | common/on_actions/te_covert_tech_selfcheck_on_actions.txt:54: TE_SELF_CHECK OK covert_can_research_current held=38 can_research=38 (can_research holds for every country's current production or military research whose prerequisites it holds) date=January 2, 1836 |
| pop_workforce_read | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:745: TE_SELF_CHECK OK pop_workforce_read wf_engine=0.250 date=January 2, 1836 |
| gm_occupation_read | OK | fixture | common/scripted_effects/gm_trophy_effects.txt:836: TE_SELF_CHECK OK gm_occupation_read (a state at peace counts 96 provinces and its owner holds half of them, so an occupier can be found) |
| fptp_major_parties | OK | fixture | common/scripted_effects/te_fptp_effects.txt:301: TE_SELF_CHECK OK fptp_major_parties (two largest of parties=3 marked; second's clout=0.26) |
| metro_world_market_hub | OK | fixture | common/scripted_effects/te_demog_metro_effects.txt:150: TE_SELF_CHECK OK metro_world_market_hub hubs=243 port_states=242 hubs_without_port=91 ports_not_hub=90 countries=291 first=Corsica date=January 4, 1836 |
| conscription_term_read | OK | fixture | events/te_debug_demog_events.txt:854: TE_SELF_CHECK OK conscription_term_read added=0.012 expected=0.012 date=January 11, 1836 |
| workforce_ratio_scale | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:936: TE_SELF_CHECK OK workforce_ratio_scale wf_engine=0.256 per_people=0.255 per_dependents=0.203 (near per_people: the engine's ratio is workforce over people, as the census's rates in the game's units assume) date=January 5, 1836 |
| primogeniture_scaled | OK | fixture | events/te_debug_demog_events.txt:583: TE_SELF_CHECK OK primogeniture_scaled added=0.0683 expected=0.0683 date=January 14, 1836 |
| unemployment_share_read | OK | fixture | common/scripted_effects/te_unemployment_effects.txt:110: TE_SELF_CHECK OK unemployment_share_read state=Mecklenburg-Strelitz conv=0.192 exact=0.192 read=0.048 per_people=0.048 wf_share=0.249 prev_wf_share=0.249 workforce=21239 (the engine's figure is the idle workforce over all the state's people, so te_state_unemployment_share is the share of the workforce the mod's readers mean) date=January 8, 1836 |
| famine_reserves_absorbed | OK | fixture | events/te_debug_demog_events.txt:777: TE_SELF_CHECK OK famine_reserves_absorbed absorbed=-0.200 walk=-0.200 country=-0.200 (powerful Landowners: the trait's -0.1 doubled reads -0.2) state=Malabar date=January 9, 1836 |
| workforce_lines_net | OK | fixture | events/te_debug_demog_events.txt:664: TE_SELF_CHECK OK workforce_lines_net remainder=0.000 date=January 9, 1836 |
| working_conditions_read | OK | fixture | events/te_debug_demog_events.txt:823: TE_SELF_CHECK OK working_conditions_read read=0.100 expected=0.100 scale=1.00 state=Cuba Oriental (the read carries the table at the building's scale: the walk's group reads count working conditions once) date=January 10, 1836 |
| fl_neighbours_read | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:1556: TE_SELF_CHECK OK fl_neighbours_read foreign=11 own=0 (own above 0: the iterator returns the country's own states too, which the step leaves out) date=January 21, 1836 |
| neighbouring_state_reads | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:1590: TE_SELF_CHECK OK neighbouring_state_reads land=1 strait=1 (strait=1: the practices spread across straits too, so the harness's replay takes demographics_adjacency's straits; strait=0: islands spread only through their own conditions) date=January 21, 1836 |
| archaeology_site_region | OK | fixture | common/scripted_effects/gm_archaeology_effects.txt:182: TE_SELF_CHECK OK archaeology_site_region (a site's stored state region finds its states) |
| gm_world_base | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1896: TE_SELF_CHECK OK gm_world_base (world GDP 401485346 is within a tenth of the 1836 constant 404100000) |
| monument_least_grandeur | OK | fixture | common/scripted_effects/gm_monument_effects.txt:2126: TE_SELF_CHECK OK monument_least_grandeur state=Transjordan least=15.00 expected=15.00 primary=25.00 (the least grand monument here reads right, so Clear Away shows on it) |
| cm_definition_inject | OK | fixture | common/scripted_effects/te_culture_merge_selfcheck_effects.txt:811: TE_SELF_CHECK OK cm_definition_inject date=February 1, 1836 (GER's definition lists North German and cm_german) |
| hq_found | OK | fixture | common/scripted_effects/te_journal_map_effects.txt:87: TE_SELF_CHECK OK hq_found states=6 date=February 1, 1836 (the store found company headquarters by building group) |
| hq_profit | OK | fixture | common/scripted_effects/te_journal_map_effects.txt:128: TE_SELF_CHECK OK hq_profit states=6 nonzero=6 date=February 1, 1836 |
| measure_country_types | OK | fixture | events/te_debug_demog_events.txt:734: TE_SELF_CHECK OK measure_country_types added=0.0500 expected=0.0500 date=February 14, 1836 |
| banking_entry_everywhere | OK | fixture | events/te_debug_banking_events.txt:21: TE_SELF_CHECK OK banking_entry_everywhere (every country under the rule holds je_banking_cycle, none added by the safety net) date=February 20, 1836 |
| row_standing_on_creation | OK | fixture | common/scripted_effects/rules_of_war_effects.txt:88: TE_SELF_CHECK OK row_standing_on_creation path=other country=GUA standing=0 (a country made mid-game ran its first Rules of War law's on_activate with no standing, and was charged nothing for it) date=March 1, 1836 |
| gm_education_reaches_states | OK | fixture | common/scripted_effects/gm_policy_effects.txt:80: TE_SELF_CHECK OK gm_education_reaches_states (Public Education's modifier on the journal entry reached the capital: its education access rose by 0.276, the steps give 0.026) |
| dp_esc_pause | OK | fixture | common/scripted_effects/dp_escalation_effects.txt:187: TE_SELF_CHECK OK dp_esc_pause now=16 mark=9 days=7 week=0 date=March 11, 1836 (a play kept its mark and the escalation ladder read it: days is the engine's rise since the last tick, 7 a week unpaused) |

| # | Verb | Outcome |
|---|---|---|
| 1 | held | none |
| 2 | overlay | built |
| 3 | fixture | found |
| 4 | snapshot | ok |
| 5 | launch | ok |
| 6 | window | ok |
| 7 | console_ready | ok |
| 8 | tag | ok |
| 9 | debugger | ok |
| 10 | start | ok |
| 11 | read | ok |
| 12 | console_after_start | ok |
| 13 | reattach | ok |
| 14 | tag | ok |
| 15 | enter_game | ok |
| 16 | advance | ok |
| 17 | selfchecks | ok |
| 18 | kill | ok |
| 19 | restore | restored |
| 20 | stop | restored |
