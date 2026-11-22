Restore: restored (51 files put back, 0 removed).

- Permission: owner in the conversation 2026-11-11, asked 'May I launch Victoria 3 now for the in-game test session?', answered 'Launch now, retries OK' (up to three launches in total today)
- Snapshot: 20261111T181801Z
- Save: te_qa_fixture_81677a2162d5
- Country: USA
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
| 12 | read | ok |
| 13 | run_setup | ok |
| 14 | read | ok |
| 15 | run_setup | ok |
| 16 | read | ok |
| 17 | run_setup | ok |
| 18 | read | ok |
| 19 | run_setup | ok |
| 20 | read | ok |
| 21 | run_setup | ok |
| 22 | read | ok |
| 23 | run_setup | ok |
| 24 | read | ok |
| 25 | run_setup | ok |
| 26 | read | ok |
| 27 | read | ok |
| 28 | events | ok |
| 29 | run_setup | ok |
| 30 | read | ok |
| 31 | events | ok |
| 32 | shot | ok |
| 33 | pick | ok |
| 34 | read | ok |
| 35 | events | ok |
| 36 | run_setup | ok |
| 37 | read | ok |
| 38 | events | ok |
| 39 | pick | ok |
| 40 | read | ok |
| 41 | run_setup | ok |
| 42 | read | ok |
| 43 | events | ok |
| 44 | read | ok |
| 45 | run_setup | ok |
| 46 | console | ok |
| 47 | events | ok |
| 48 | read | ok |
| 49 | pick | ok |
| 50 | read | ok |
| 51 | run_setup | ok |
| 52 | console | ok |
| 53 | events | ok |
| 54 | read | ok |
| 55 | pick | ok |
| 56 | read | ok |
| 57 | try_event | ok |
| 58 | read | ok |
| 59 | console | ok |
| 60 | events | ok |
| 61 | read | ok |
| 62 | pick | ok |
| 63 | read | ok |
| 64 | try_event | ok |
| 65 | tag | ok |
| 66 | read | ok |
| 67 | console | ok |
| 68 | events | ok |
| 69 | shot | ok |
| 70 | pick | ok |
| 71 | read | ok |
| 72 | tag | ok |
| 73 | run_setup | ok |
| 74 | read | ok |
| 75 | console_after_start | ok |
| 76 | reattach | ok |
| 77 | tag | ok |
| 78 | enter_game | not_entered |
| 79 | read | ok |
| 80 | read | ok |
| 81 | read | ok |
| 82 | read | ok |
| 83 | read | ok |
| 84 | kill | ok |
| 85 | restore | restored |
| 86 | stop | restored |

## try-event inheritance_events.14 (setup inh_heir)

State is shared between options: each ran on the game the one before left, the setup re-run first; console `event` ignores the trigger and the cooldown.

| Option | Fired | Before | After | Picked | New errors |
|---|---|---|---|---|---|
| 0 | yes | has_modifier = inh_estates_audited = no; has_modifier = inh_estates_overlooked = no; root.capital.var:te_dg_wc = 54.5539; root.var:te_inh_concentration = 66.37251 | has_modifier = inh_estates_audited = yes; has_modifier = inh_estates_overlooked = no; root.capital.var:te_dg_wc = 51.5539; root.var:te_inh_concentration = 63.37251 | option 0 | 0 |
| 1 | yes | has_modifier = inh_estates_audited = yes; has_modifier = inh_estates_overlooked = no; root.capital.var:te_dg_wc = 51.5539; root.var:te_inh_concentration = 63.37251 | has_modifier = inh_estates_audited = yes; has_modifier = inh_estates_overlooked = yes; root.capital.var:te_dg_wc = 56.5539; root.var:te_inh_concentration = 68.37251 | option 1 | 0 |

Every option fired and was picked.

## try-event minor_events_timelineextended.10

State is shared between options: each ran on the game the one before left; console `event` ignores the trigger and the cooldown.

| Option | Fired | Before | After | Picked | New errors |
|---|---|---|---|---|---|
| 0 | yes | has_modifier = failed_state_modifier = no; has_modifier = inh_estates_overlooked = yes | has_modifier = failed_state_modifier = no; has_modifier = inh_estates_overlooked = yes | option 0 | 0 |

Every option fired and was picked.
