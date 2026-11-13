Restore: restored (52 files put back, 0 removed).

- Permission: owner in this session, 2026-11-12 23:07 MST: 'You will be able to run the game to test but I would like this to be as late in the process as possible - do what you can first, please.' Offline work done first.
- Snapshot: 20261113T085554Z
- Save: te_qa_fixture_c6498ca4f4c4
- Country: FRA
- Overlay removed: True

## Self-checks

2 START (no verdict was logged after it), 16 OK.

- Session: 8 TE_SELF_CHECK lines in /mnt/d/vic3_qa_backups/runs/20261113T085554Z/debug.log. The game writes its log in blocks, so a line logged after the last verb may be missing.
- The run that made the fixture: 113 lines kept from snapshot 20261113T080524Z, 10 of them TE_SELF_CHECK (/mnt/d/vic3_qa_backups/fixtures/c6498ca4f4c4/lines.log).

| Check | Verdict | From | Line |
|---|---|---|---|
| conscription_term_read | START | fixture | common/scripted_effects/te_debug_demog_effects.txt:1196: TE_SELF_CHECK START conscription_term_read term=0.012 before=-0.100 (the verdict follows in a week; none means the state changed hands first) date=January 4, 1836 |
| conscription_term_read | START | session | common/scripted_effects/te_debug_demog_effects.txt:1196: TE_SELF_CHECK START conscription_term_read term=0.012 before=-0.100 (the verdict follows in a week; none means the state changed hands first) date=January 4, 1836 |
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
| fptp_major_parties | OK | session | common/scripted_effects/te_fptp_effects.txt:301: TE_SELF_CHECK OK fptp_major_parties (two largest of parties=3 marked; second's clout=0.25) |
| workforce_ratio_scale | OK | session | common/scripted_effects/te_debug_demog_effects.txt:936: TE_SELF_CHECK OK workforce_ratio_scale wf_engine=0.256 per_people=0.255 per_dependents=0.203 (near per_people: the engine's ratio is workforce over people, as the census's rates in the game's units assume) date=January 5, 1836 |

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
| 11 | run_setup | ok |
| 12 | shot | ok |
| 13 | country_click | no_country_selected |
| 14 | console_after_start | ok |
| 15 | reattach | ok |
| 16 | tag | ok |
| 17 | enter_game | ok |
| 18 | read | ok |
| 19 | kill | ok |
| 20 | restore | restored |
| 21 | stop | restored |
