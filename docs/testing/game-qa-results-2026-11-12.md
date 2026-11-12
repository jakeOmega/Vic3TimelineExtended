# In-game QA harness results: 2026-11-12, `add-setup` and a switched game rule

The first live run of `python3 -m game_qa add-setup` (#1600) and `start --switch-rule` (#1599), on the branch
that adds them.

**Game:** Victoria 3 1.15.1. **Build:** the deployed mod folder as it stood (the main checkout was at `215fa63bc`; not compared with the folder).
**Playset:** this mod only. **Launches:** one session, plus the unattended run that made its fresh save, on the
owner's go-ahead ("You can have the GPU now!", after being asked for one session of about 25 minutes). It took
12 minutes, restored the owner's files (`outcome: restored`, 51 files put back, nothing held), and left no
overlay; `player/game_rules/presets.txt` was not touched.

**Run folder** (under the backup root): `runs/20261112T075854Z/`. The small evidence files are copied to
`docs/testing/game_qa_probe/captures/session_2026-11-12_add_setup_switch_rule/`.

## The fresh save and the switched rule

| Check | Result |
|---|---|
| The fixture key follows the owner's last applied rules | A new fixture was made (`te_qa_fixture_1fa1972f80f6`): the key now takes the `LastAppliedRules` list, so the fixtures of 2026-11-11 no longer matched |
| The game loads a copy with a rule switched | **OK.** `start --switch-rule te_tax_code_rule=te_tax_code_disabled` wrote `te_qa_fixture_1fa1972f80f6_s20977745` (six bytes longer than the fixture, the header's length rewritten) and the game loaded it to a usable console |
| The game reports the switched setting | **OK.** As the USA: `has_game_rule = te_tax_code_disabled` yes, `has_game_rule = te_tax_code_light` no |
| The other rules are as the owner last applied them | **OK.** `has_game_rule = culture_merges_enabled` yes and `culture_merges_disabled` no (the default is disabled); `has_game_rule = no_fantastical_content` yes. This is the live confirmation that an unattended new game takes `LastAppliedRules`, not the defaults |
| The mod reads the switch as a rule changed mid-game | **OK for the Tax Code.** After `enter-game` and 37 days, `te_tax_on_actions.txt`'s rule-off branch had logged `TE_TAX rule_off left the code` once for each of 291 countries, on their monthly pulses from 3 to 30 January 1836; `te_tax_code_on = yes` and `te_tax_code_light_on = yes` read no |

Not looked at: the rest of the rule-off row in `rules-off-midgame-playtest.md` ("Light code": the entry closes
within a week, the relief and reaction modifiers are gone, the taxation law is unchanged). The variable
`te_tax_light_level` was still set on the USA and Britain on 12 February; whether the teardown should clear it
is that row's question, not answered here. Only the Tax Code was switched: another rule's reaction to an edited
save is not shown by this.

## `add-setup`

| Check | Result |
|---|---|
| A setup added on the country-select screen runs | **OK, after a fix.** `run-setup probe_a` logged the setup's own line and `root.var:te_qa_probe_a` read 7 |
| A setup added in an entered game runs | **OK, after a fix.** `run-setup probe_b`: `root.var:te_qa_probe_b` read 11; `te_qa_probe_a` still read 7 after entering |
| A read still stops after a reload | **OK.** Reads worked after each reload, once the debugger was attached again (the verb does that) |
| How long a reload takes | **About 90 seconds, twice** (the effects file rewritten at 08:00:46 and 08:04:03 UTC; the game answered again at about 08:02:15 and 08:05:33). The design's probes of 2026-11-10 measured 40 |
| What the game does meanwhile | **Its window does not respond at all.** The console calls a window silent for 10 s `game_gone`, so both `add-setup` calls, and a `run-setup` and a `read` made during a reload, were refused `game_gone` with nothing typed, while `watch` showed the game up. **Fixed on the branch after the session**: the wait now tries again while the window still exists, the first look comes after 20 s, and the wait allows five minutes. The fixed wait has only run against the fakes; in this session the setups were run by waiting for the log to go quiet and calling `run-setup`, which looked for the new revision, attached the debugger and ran them |
| A delayed event queued before a reload | Seen once: the self-check verdict event, which is queued with `days = 14`, ran on 17 January, so it was queued on the 3rd and outlived the reload made on the 6th. Not tested further |

## Self-checks in the run

27 `TE_SELF_CHECK` lines: 22 OK, 4 START, and one BROKEN, `delayed_state_event`, which has read BROKEN in every
new game since 2026-11-08 (`demographics-playtest.md`).

## What stays in the owner's folder

`save games/te_qa_fixture_1fa1972f80f6.v3` and `te_qa_fixture_1fa1972f80f6_s20977745.v3` (133 MB each), kept on
purpose, beside `te_qa_fixture_81677a2162d5.v3` from 2026-11-11; the older `te_qa_fixture_ee2c4bd30adc.v3` was
pruned.
