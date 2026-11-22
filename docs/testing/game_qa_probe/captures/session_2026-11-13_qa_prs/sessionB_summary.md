Restore: restored (52 files put back, 0 removed).

- Permission: owner in this session, 2026-11-12 23:07 MST: 'You will be able to run the game to test but I would like this to be as late in the process as possible - do what you can first, please.' Offline work done first.
- Snapshot: 20261113T081657Z
- Save: te_qa_fixture_c6498ca4f4c4_se711b3ac
- Country: FRA
- Overlay removed: True

## Self-checks

1 BROKEN, 3 START (no verdict was logged after it), 30 OK.

- Session: 26 TE_SELF_CHECK lines in /mnt/d/vic3_qa_backups/runs/20261113T081657Z/debug.log; lines were lost to the log's rotation (2 times), and a verdict logged then is not here. The game writes its log in blocks, so a line logged after the last verb may be missing.
- The run that made the fixture: 113 lines kept from snapshot 20261113T080524Z, 10 of them TE_SELF_CHECK (/mnt/d/vic3_qa_backups/fixtures/c6498ca4f4c4/lines.log).

| Check | Verdict | From | Line |
|---|---|---|---|
| delayed_state_event | BROKEN | session | events/te_debug_demog_events.txt:1298: TE_SELF_CHECK BROKEN delayed_state_event (a state event triggered with days = 7 never ran: move the delayed calls of te_demog_events.4, monument_events.30 and .31 to a country event) date=January 17, 1836 |
| conscription_term_read | START | fixture | common/scripted_effects/te_debug_demog_effects.txt:1196: TE_SELF_CHECK START conscription_term_read term=0.012 before=-0.100 (the verdict follows in a week; none means the state changed hands first) date=January 4, 1836 |
| cm_census_yearly | START | session | common/scripted_effects/te_culture_merge_selfcheck_effects.txt:171: TE_SELF_CHECK START cm_census_yearly year=1836 (the verdict follows at the next census, a year on; a START with no verdict after that means the calendar-year guard never lets a second census through) |
| measure_country_types | START | session | common/scripted_effects/te_debug_demog_effects.txt:817: TE_SELF_CHECK START measure_country_types before=0.0000 (the verdict follows in a week; none means the state changed hands first) date=February 7, 1836 |
| decentralized_law_baseline | OK | fixture | common/on_actions/te_decentralized_laws_selfcheck_on_actions.txt:46: TE_SELF_CHECK OK decentralized_law_baseline (no decentralized nation holds any of the five placeholder laws after history: the history baseline reached them) |
| primate_state_flag | OK | fixture | common/scripted_effects/te_demog_place_effects.txt:253: TE_SELF_CHECK OK primate_state_flag tag=GBR city=Home Counties self=1 states=1 date=January 1, 1836 |
| monument_piece_rejoins | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1952: TE_SELF_CHECK OK monument_piece_rejoins (the Parthenon's marbles read as a piece of the Parthenon in Attica) |
| monument_artifact_stands_apart | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1965: TE_SELF_CHECK OK monument_artifact_stands_apart (the Luxor Obelisk reads as apart from the Obelisks of Karnak) |
| ch_board_rows | OK | fixture | common/scripted_effects/cultural_hegemony_effects.txt:162: TE_SELF_CHECK OK ch_board_rows ranked=99 (the board store lists the leader's row with its capital) date=January 2, 1836 |
| covert_can_research_current | OK | fixture | common/on_actions/te_covert_tech_selfcheck_on_actions.txt:54: TE_SELF_CHECK OK covert_can_research_current held=34 can_research=34 (can_research holds for every country's current production or military research whose prerequisites it holds) date=January 2, 1836 |
| pop_workforce_read | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:745: TE_SELF_CHECK OK pop_workforce_read wf_engine=0.250 date=January 2, 1836 |
| gm_occupation_read | OK | fixture | common/scripted_effects/gm_trophy_effects.txt:836: TE_SELF_CHECK OK gm_occupation_read (a state at peace counts 96 provinces and its owner holds half of them, so an occupier can be found) |
| metro_world_market_hub | OK | fixture | common/scripted_effects/te_demog_metro_effects.txt:150: TE_SELF_CHECK OK metro_world_market_hub hubs=243 port_states=242 hubs_without_port=91 ports_not_hub=90 countries=291 first=Corsica date=January 4, 1836 |
| ch_board_rows | OK | session | common/scripted_effects/cultural_hegemony_effects.txt:162: TE_SELF_CHECK OK ch_board_rows ranked=98 (the board store lists the leader's row with its capital) date=January 3, 1836 |
| covert_can_research_current | OK | session | common/on_actions/te_covert_tech_selfcheck_on_actions.txt:54: TE_SELF_CHECK OK covert_can_research_current held=65 can_research=65 (can_research holds for every country's current production or military research whose prerequisites it holds) date=January 3, 1836 |
| pop_workforce_read | OK | session | common/scripted_effects/te_debug_demog_effects.txt:745: TE_SELF_CHECK OK pop_workforce_read wf_engine=0.277 date=January 3, 1836 |
| gm_occupation_read | OK | session | common/scripted_effects/gm_trophy_effects.txt:836: TE_SELF_CHECK OK gm_occupation_read (a state at peace counts 30 provinces and its owner holds half of them, so an occupier can be found) |
| metro_world_market_hub | OK | session | common/scripted_effects/te_demog_metro_effects.txt:150: TE_SELF_CHECK OK metro_world_market_hub hubs=243 port_states=242 hubs_without_port=91 ports_not_hub=90 countries=291 first=Corsica date=January 4, 1836 |
| conscription_term_read | OK | session | events/te_debug_demog_events.txt:854: TE_SELF_CHECK OK conscription_term_read added=0.012 expected=0.012 date=January 11, 1836 |
| fptp_major_parties | OK | session | common/scripted_effects/te_fptp_effects.txt:301: TE_SELF_CHECK OK fptp_major_parties (two largest of parties=3 marked; second's clout=0.25) |
| workforce_ratio_scale | OK | session | common/scripted_effects/te_debug_demog_effects.txt:936: TE_SELF_CHECK OK workforce_ratio_scale wf_engine=0.256 per_people=0.255 per_dependents=0.203 (near per_people: the engine's ratio is workforce over people, as the census's rates in the game's units assume) date=January 5, 1836 |
| primogeniture_scaled | OK | session | events/te_debug_demog_events.txt:583: TE_SELF_CHECK OK primogeniture_scaled added=0.0683 expected=0.0683 date=January 14, 1836 |
| unemployment_share_read | OK | session | common/scripted_effects/te_unemployment_effects.txt:110: TE_SELF_CHECK OK unemployment_share_read state=Mecklenburg-Strelitz conv=0.192 exact=0.192 read=0.048 per_people=0.048 wf_share=0.250 prev_wf_share=0.249 workforce=21238 (the engine's figure is the idle workforce over all the state's people, so te_state_unemployment_share is the share of the workforce the mod's readers mean) date=January 8, 1836 |
| workforce_lines_net | OK | session | events/te_debug_demog_events.txt:664: TE_SELF_CHECK OK workforce_lines_net remainder=0.000 date=January 10, 1836 |
| working_conditions_read | OK | session | events/te_debug_demog_events.txt:823: TE_SELF_CHECK OK working_conditions_read read=0.100 expected=0.100 scale=1.00 state=Cuba Oriental (the read carries the table at the building's scale: the walk's group reads count working conditions once) date=January 10, 1836 |
| famine_reserves_absorbed | OK | session | events/te_debug_demog_events.txt:777: TE_SELF_CHECK OK famine_reserves_absorbed absorbed=-0.200 walk=-0.200 country=-0.200 (powerful Landowners: the trait's -0.1 doubled reads -0.2) state=Sindh date=January 10, 1836 |
| fl_neighbours_read | OK | session | common/scripted_effects/te_debug_demog_effects.txt:1556: TE_SELF_CHECK OK fl_neighbours_read foreign=11 own=0 (own above 0: the iterator returns the country's own states too, which the step leaves out) date=January 21, 1836 |
| neighbouring_state_reads | OK | session | common/scripted_effects/te_debug_demog_effects.txt:1590: TE_SELF_CHECK OK neighbouring_state_reads land=1 strait=1 (strait=1: the practices spread across straits too, so the harness's replay takes demographics_adjacency's straits; strait=0: islands spread only through their own conditions) date=January 21, 1836 |
| archaeology_site_region | OK | session | common/scripted_effects/gm_archaeology_effects.txt:182: TE_SELF_CHECK OK archaeology_site_region (a site's stored state region finds its states) |
| gm_world_base | OK | session | common/scripted_effects/gm_monument_effects.txt:1896: TE_SELF_CHECK OK gm_world_base (world GDP 401012622 is within a tenth of the 1836 constant 404100000) |
| monument_least_grandeur | OK | session | common/scripted_effects/gm_monument_effects.txt:2126: TE_SELF_CHECK OK monument_least_grandeur state=Transjordan least=15.00 expected=15.00 primary=25.00 (the least grand monument here reads right, so Clear Away shows on it) |
| cm_definition_inject | OK | session | common/scripted_effects/te_culture_merge_selfcheck_effects.txt:811: TE_SELF_CHECK OK cm_definition_inject date=February 1, 1836 (GER's definition lists North German and cm_german) |
| hq_found | OK | session | common/scripted_effects/te_journal_map_effects.txt:87: TE_SELF_CHECK OK hq_found states=6 date=February 1, 1836 (the store found company headquarters by building group) |
| hq_profit | OK | session | common/scripted_effects/te_journal_map_effects.txt:128: TE_SELF_CHECK OK hq_profit states=6 nonzero=6 date=February 1, 1836 |

| # | Verb | Outcome |
|---|---|---|
| 1 | held | none |
| 2 | overlay | built |
| 3 | fixture | found |
| 4 | switch_rules | ok |
| 5 | snapshot | ok |
| 6 | launch | ok |
| 7 | window | ok |
| 8 | console_ready | ok |
| 9 | tag | ok |
| 10 | debugger | ok |
| 11 | start | ok |
| 12 | read | ok |
| 13 | console_after_start | ok |
| 14 | reattach | ok |
| 15 | tag | ok |
| 16 | enter_game | ok |
| 17 | shot | ok |
| 18 | read | ok |
| 19 | advance | ok |
| 20 | read | ok |
| 21 | kill | ok |
| 22 | restore | restored |
| 23 | stop | restored |
