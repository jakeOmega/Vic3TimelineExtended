# In-game QA harness results: 2026-11-12, `add-setup`, a switched game rule, and the harness's open checks

The first live runs of `python3 -m game_qa add-setup` (#1600) and `start --switch-rule` (#1599), on the branch
that adds them, then five short sessions the same day for what those showed and for #1598 and #1588. Session 1
is written up first; the later sessions follow under "Sessions 2 to 6".

**Game:** Victoria 3 1.15.1. **Build:** the deployed mod folder as it stood (the main checkout was at `215fa63bc`; not compared with the folder).
**Playset:** this mod only (session 4: the owner's current playset, four mods). **Launches:** six sessions and
two unattended runs that made fresh saves, each on the owner's go-ahead: the first on "You can have the GPU
now!" (asked for one session of about 25 minutes), four more on "All, incl. foreground" (asked which further
sessions to run), the last on "Yes, one more now". Every stop restored the owner's files (`outcome: restored`,
51 files put back, nothing held) and left no overlay; `player/game_rules/presets.txt` was never touched.

**Run folders** (under the backup root): `runs/20261112T075854Z/` (session 1), `…082309Z/`, `…083507Z/`,
`…084824Z/`, `…090111Z/`, `…090755Z/`. The small evidence files (each session's `steps.jsonl` and
`summary.md`, session 1's log lines, the setups) are copied to
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
| How long a reload takes | **About 90 seconds, twice, in this session** (the effects file rewritten at 08:00:46 and 08:04:03 UTC; the game answered again at about 08:02:15 and 08:05:33); 66 s once the wait read the debugger's connection (session 3). The design's probes of 2026-11-10 measured 40 |
| What the game does meanwhile | **Its window does not respond at all.** The console calls a window silent for 10 s `game_gone`, so both `add-setup` calls, and a `run-setup` and a `read` made during a reload, were refused `game_gone` with nothing typed, while `watch` showed the game up. **Fixed on the branch after the session** (the wait tries again while the window still exists, looks first after 20 s, allows five minutes) and, after session 2, made to read the debugger's connection before each look; that version answered `loaded: true` by itself in session 3. In this session the setups were run by waiting for the log to go quiet and calling `run-setup`, which looked for the new revision, attached the debugger and ran them |
| A delayed event queued before a reload | Seen once: the self-check verdict event, which is queued with `days = 14`, ran on 17 January, so it was queued on the 3rd and outlived the reload made on the 6th. Not tested further |

## Sessions 2 to 6

| Session | What it was for | Result |
|---|---|---|
| 2 (`…082309Z`) | The fixed `add-setup` wait | **Failed, and showed the real cause.** The wait gave up after five minutes (19 looks, the window not responding each time) although the reload's log burst had ended after 67 s. The next `read` then worked at once. Between them nothing read the debugger's connection |
| 3 (`…083507Z`) | The wait again, now reading the debugger's connection before each look; what Esc does to a law window | **`add-setup` OK by itself**: `loaded: true` after 4 looks and 65.6 s, no debugger stop reported; `run-setup` logged the setup's line and its variable read 7. **Esc probe**: one `activate_law` of State as Universal Heir on the country-select screen raised two windows in turn ("We now have State as Universal Heir!", then "We now have Forced Heirship!", "changed from" the first: something put the law back at once). After `press esc` the first was gone; after a second, both; no menu opened; `enter-game` then entered. The view had moved between the shots |
| 4 (`…084824Z`) | A fresh save under the owner's current playset (#1588); `enter-game` past a law window | **Playset OK**: the save was made (`te_qa_fixture_e8ac82a3afab`, 38 rule settings, the playset's `headlines_all_minor_events` among them), loaded and read (`c:USA.gdp`, two `has_game_rule`). **Window not closed**: `enter-game`, which then pressed Esc when a click selected nothing, pressed three times and the window stayed; two more `press esc` by hand and the Enter of a console probe left it up as well. The cursor was on the window after the click each time, unlike in session 3. The lobby's side panel was read as unchanged every time, which is right. The view had moved off the country, over open sea |
| 5 (`…090111Z`) | The console taking the foreground back (#1588) | **OK, by inference.** The owner put their terminal in front of the game and left the machine alone; the next `read` was typed and answered, taking 7 s where the five reads timed that day with the game already in front and the console open took 1 to 2 s. The console types only into a game in front and waits two quiet three-second gaps before it brings it forward, which is the difference. The session does not record the focus call itself. **Then `enter-game` failed `not_entered`**: by the time it ran the lobby's view was at the top edge of the map, so the country click selected nothing (the side panel read as changed all the same, because it is translucent and the map behind it had moved) |
| 6 (`…090755Z`) | `enter-game`'s panel check on an ordinary lobby | **OK.** A country was selected, 19.1% of the side panel's pixels changed (the threshold is 1%; a covered lobby gave 0.0% in session 4), Start was clicked and the date moved from 2 to 6 January |

What these settle:

- **The game freezes after a reload until its debugger connection is read.** Not a debugger stop: none was
  reported once the connection was read before each look. The game streams every error-log line to the
  debugger, and a reload writes tens of thousands. `add-setup` now reads the connection before each look.
  With that the reload took 66 s; the "about 90 s" of session 1 included the time until another verb happened
  to read it.
- **No key is known to close a "We now have <law>!" window once the country click has landed on it.** What
  closed the two windows in session 3 is not established (Esc with the cursor elsewhere, or something the
  console typed). `enter-game` therefore presses nothing: it compares the side panel before and after the
  country click and, when no country was selected, refuses `no_country_selected` before Start is clicked. The
  session is then as it was (in session 4 `read`, `press` and `shot` all worked after the refusal). The rule
  stays: run a setup that changes a law after `enter-game`.
- **The panel check has a blind side.** The panel is translucent, so a view that moves between the two shots
  reads as a change, and the click goes on to Start as it did before the check existed (session 5).
- **What moves the lobby's view.** A console probe typed while the console is closed goes to the game, where
  its letters are camera keys: every verb after a `press` does this once. And in session 5 the view ran to the
  top of the map while the game sat in front between two verbs; the mouse resting on a screen edge would do
  that, but it was not checked. `enter-game` clicks wherever the view is, so either can make it miss.
- **State as Universal Heir, activated by a setup on the country-select screen, was replaced at once.** A
  second window, "We now have Forced Heirship!" (`law_equal_inheritance`), said "changed from State as
  Universal Heir" (sessions 3 and 4), and after entering `has_law = law_type:law_state_universal_heir` read no.
  Which law the USA then had was not read with a form that must say yes. The mod's generated law-consistency
  effect has a cascade for that law (`extra_law_consistency_generated.txt`), which would explain it; not
  checked. The 2026-11-11 note "laws changed there were not read afterwards" may have this cause.

**A lead from the owner, not verified** (2026-11-12, "fairly confident, not certain"): the Back button at the
bottom left of the country-select screen takes you back into the game as the current country, not to the main
menu; and Esc may not close a window while that screen (with its Back button) is up. If Back does enter the
game as the tagged country, one click on it would be a better `enter-game` than the click on whatever country
the view is over, since it would not depend on the view. Neither was tried: the shots above show only that Esc
never left the lobby (five presses in session 4, two in session 3), so Esc is not Back there.

## Self-checks in the runs

Session 1: 27 `TE_SELF_CHECK` lines: 22 OK, 4 START, and one BROKEN, `delayed_state_event`, which has read BROKEN
in every new game since 2026-11-08 (`demographics-playtest.md`). Sessions 3 and 6, which entered the game for a
few days, logged 8 lines each and no BROKEN; the others logged none.

## What stays in the owner's folder

`save games/te_qa_fixture_1fa1972f80f6.v3` (this mod only), its copy with the Tax Code switched off,
`te_qa_fixture_1fa1972f80f6_s20977745.v3`, and `te_qa_fixture_e8ac82a3afab.v3` (the current playset), 133 MB each,
kept on purpose. The two fixtures of 2026-11-11 were pruned.
