Restore: restored (49 files put back, 0 removed).

- Permission: owner in this session, 2026-11-12 23:07 MST: 'You will be able to run the game to test but I would like this to be as late in the process as possible - do what you can first, please.' Offline work done first.
- Snapshot: 20261113T080833Z
- Save: te_qa_fixture_c6498ca4f4c4_se711b3ac
- Country: (none)
- Overlay removed: True

## Self-checks

1 START (no verdict was logged after it), 9 OK.

- Session: 0 TE_SELF_CHECK lines in /mnt/d/vic3_qa_backups/runs/20261113T080833Z/debug.log. The game writes its log in blocks, so a line logged after the last verb may be missing.
- The run that made the fixture: 113 lines kept from snapshot 20261113T080524Z, 10 of them TE_SELF_CHECK (/mnt/d/vic3_qa_backups/fixtures/c6498ca4f4c4/lines.log).

| Check | Verdict | From | Line |
|---|---|---|---|
| conscription_term_read | START | fixture | common/scripted_effects/te_debug_demog_effects.txt:1196: TE_SELF_CHECK START conscription_term_read term=0.012 before=-0.100 (the verdict follows in a week; none means the state changed hands first) date=January 4, 1836 |
| decentralized_law_baseline | OK | fixture | common/on_actions/te_decentralized_laws_selfcheck_on_actions.txt:46: TE_SELF_CHECK OK decentralized_law_baseline (no decentralized nation holds any of the five placeholder laws after history: the history baseline reached them) |
| primate_state_flag | OK | fixture | common/scripted_effects/te_demog_place_effects.txt:253: TE_SELF_CHECK OK primate_state_flag tag=GBR city=Home Counties self=1 states=1 date=January 1, 1836 |
| monument_piece_rejoins | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1952: TE_SELF_CHECK OK monument_piece_rejoins (the Parthenon's marbles read as a piece of the Parthenon in Attica) |
| monument_artifact_stands_apart | OK | fixture | common/scripted_effects/gm_monument_effects.txt:1965: TE_SELF_CHECK OK monument_artifact_stands_apart (the Luxor Obelisk reads as apart from the Obelisks of Karnak) |
| ch_board_rows | OK | fixture | common/scripted_effects/cultural_hegemony_effects.txt:162: TE_SELF_CHECK OK ch_board_rows ranked=99 (the board store lists the leader's row with its capital) date=January 2, 1836 |
| covert_can_research_current | OK | fixture | common/on_actions/te_covert_tech_selfcheck_on_actions.txt:54: TE_SELF_CHECK OK covert_can_research_current held=34 can_research=34 (can_research holds for every country's current production or military research whose prerequisites it holds) date=January 2, 1836 |
| pop_workforce_read | OK | fixture | common/scripted_effects/te_debug_demog_effects.txt:745: TE_SELF_CHECK OK pop_workforce_read wf_engine=0.250 date=January 2, 1836 |
| gm_occupation_read | OK | fixture | common/scripted_effects/gm_trophy_effects.txt:836: TE_SELF_CHECK OK gm_occupation_read (a state at peace counts 96 provinces and its owner holds half of them, so an occupier can be found) |
| metro_world_market_hub | OK | fixture | common/scripted_effects/te_demog_metro_effects.txt:150: TE_SELF_CHECK OK metro_world_market_hub hubs=243 port_states=242 hubs_without_port=91 ports_not_hub=90 countries=291 first=Corsica date=January 4, 1836 |

| # | Verb | Outcome |
|---|---|---|
| 1 | held | none |
| 2 | overlay | built |
| 3 | fixture_lines | kept |
| 4 | fixture | made |
| 5 | switch_rules | ok |
| 6 | fixture_lines | dropped |
| 7 | snapshot | ok |
| 8 | launch | ok |
| 9 | window | ok |
| 10 | console_ready | not_foreground |
| 11 | kill | ok |
| 12 | restore | restored |
| 13 | stop | restored |
