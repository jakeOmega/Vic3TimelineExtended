Restore: restored (51 files put back, 0 removed).

- Permission: (the owner's go-ahead, given in the conversation; their words are not kept here)
- Snapshot: 20261111T104103Z
- Save: te_qa_fixture_ee2c4bd30adc
- Country: FRA
- Overlay removed: True

| # | Verb | Outcome |
|---|---|---|
| 1 | held | none |
| 2 | overlay | built |
| 3 | fixture | made |
| 4 | snapshot | ok |
| 5 | launch | ok |
| 6 | window | ok |
| 7 | console_ready | ok |
| 8 | tag | ok |
| 9 | debugger | ok |
| 10 | start | ok |
| 11 | read | ok |
| 12 | run_setup | ok |
| 13 | read | ok |
| 14 | console | ok |
| 15 | events | ok |
| 16 | pick | ok |
| 17 | events | ok |
| 18 | read | ok |
| 19 | shot | ok |
| 20 | run_setup | ok |
| 21 | console | ok |
| 22 | events | ok |
| 23 | read | ok |
| 24 | pick | ok |
| 25 | read | ok |
| 26 | run_setup | ok |
| 27 | console | ok |
| 28 | events | ok |
| 29 | read | ok |
| 30 | pick | ok |
| 31 | read | ok |
| 32 | try_event | ok |
| 33 | enter_game | not_entered |
| 34 | shot | ok |
| 35 | read | no_stop |
| 36 | shot | ok |
| 37 | console | ok |
| 38 | events | ok |
| 39 | run_setup | ok |
| 40 | console | ok |
| 41 | events | ok |
| 42 | pick | ok |
| 43 | kill | ok |
| 44 | restore | restored |
| 45 | stop | restored |

## try-event minor_events_timelineextended.3 (setup clean)

State is shared between options: each ran on the game the one before left, the setup re-run first; console `event` ignores the trigger and the cooldown.

| Option | Fired | Before | After | Picked | New errors |
|---|---|---|---|---|---|
| 0 | yes | has_modifier = nation_building_investment_modifier = no; has_modifier = foreign_investment_dependency_modifier = no; c:FRA.gdp = 22558288.43996 | has_modifier = nation_building_investment_modifier = yes; has_modifier = foreign_investment_dependency_modifier = no; c:FRA.gdp = 22558288.43996 | option 0 | 0 |
| 1 | yes | has_modifier = nation_building_investment_modifier = no; has_modifier = foreign_investment_dependency_modifier = no; c:FRA.gdp = 22558288.43996 | has_modifier = nation_building_investment_modifier = no; has_modifier = foreign_investment_dependency_modifier = yes; c:FRA.gdp = 22558288.43996 | option 1 | 0 |

Every option fired and was picked.
