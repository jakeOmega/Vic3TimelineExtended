# Vanilla 1.15 migration: play-test checklist

What the next play-test of the vanilla 1.15 migration should look at. In-game checks don't gate the merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): the migration lands on the offline gate, and what only the game
can show is listed here. The engine questions a script can answer with no player watching are once-a-game probes,
`TE_PROBE_115` lines in `debug.log` ("Self-checks" below); what needs a player or a save is under "Not probed" and
"Panels and systems". Record each answer in `docs/audits/vanilla_1_15_prep.md` § 2 under its C-number (and in the
migration record that doc becomes), and an engine fact in `docs/guides/scripting_best_practices.md`.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **The probes** need nothing but time: any game, observer or played, new or loaded, for **four months of game time**.
  They run once a game on one AI major power, which picks itself within 14 days of the start (or of loading a save
  that has never run them), then take about three months. A game whose every major power is at war or held by a
  player never starts them.
- **Logs.** Read `debug.log`, not `error.log`: `grep TE_PROBE_115 debug.log`, or with the server
  `curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_PROBE_115"`. `debug.log` rolls over at
  512 KB, and a probe that fired once is gone after a few launches: copy the lines out right after the run
  (log-triage skill, 2026-09-27). Which line fired is the answer; none prints a figure.
- **At load**, check `debug.log` for `Unexpected token` or an unknown-field line on `disable_evaluation`,
  `fire_only_once_globally`, `scaling_modifiers_while_active`, `outcome` or the bar's `min_value` in the `te_probe_115` files. Two of
  those fields are in vanilla's readme and digest but no vanilla 1.15 script uses them; a load error there is itself
  an answer (the field doesn't exist) and explains a BROKEN below.
- **Re-arm** in a save that has run them by renaming the global `te_probe_115_claimed` (`_v2`) and giving events
  `te_probe_115.10` and `.11` new ids: a `fire_only_once` event that has fired never fires again.
- **Invisible?** No player country can take the entry (`is_ai = yes`), so nobody sees it unless a player switches to
  the probe country while it runs (the `TE_PROBE_115 start` line names it, via `debug_log_scopes`). Its two modifiers
  are the nuclear deterrent's display-only terms, whose types nothing reads.
- **Delete once answered**: `common/journal_entries/te_probe_115_probes.txt`, `common/scripted_effects/te_probe_115_effects.txt`,
  `common/scripted_effects/te_probe_115_c5_effects.txt`, `common/scripted_progress_bars/te_probe_115_bars.txt`,
  `events/te_probe_115_events.txt`, `test_te_probe_115.py`, the four loc keys `te_probe_115`, `te_probe_115_reason`,
  `te_probe_115_c5_bar_name` and `te_probe_115_c5_bar_text` (organize_loc files them in `te_miscellaneous_l_english.yml`),
  and the Self-checks section below.

## Self-checks (the te_probe_115 probes)

The probe's steps, in order: `TE_PROBE_115 start` (the country, then a scope dump), `TE_PROBE_115 step 1` to
`TE_PROBE_115 step 9` a week or more apart (C7's steps wait while it samples), then three days after the entry
concludes `TE_PROBE_115 done`. `TE_PROBE_115 timeout` means it stalled for two years: the last step line says where.
Each row's first answer is the expected one.

| Question | Line in `debug.log` | What each answer means | If it's the bad answer |
|---|---|---|---|
| C3: two outcomes true on the same update | `TE_PROBE_115 c3_precedence FIRST` / `SECOND` | FIRST: the first declared outcome concludes the entry (it has the failure look, so the look doesn't decide). SECOND: the last declared one does, or the completion look wins. | FIRST: declare each converted entry's outcomes in 1.14's order of precedence. SECOND, or to be safe either way: give outcomes that can be true together mutually exclusive triggers (the Space Race, the four social-movement entries with complete, fail and timeout). |
| C3: does the other one run too? | `TE_PROBE_115 c3_both ONE` / `BOTH` | ONE: only one outcome's effect runs. BOTH: every outcome true on the update runs its effect. | BOTH: mutually exclusive triggers on every entry whose outcomes can be true together. |
| C5: the root of a bar's script-value `min_value` | `TE_PROBE_115 c5_root OWNER` / `ENTRY` / `NONE` / `UNCLAMPED` / `OTHER` (step 3) | The probe's bar (`te_probe_115_c5_bar`) has a minimum of 40 when its root holds the probe country's variable, 20 when `journal_entry_age` answers, 5 when neither; step 2 adds 1 to a start of 0. OWNER: the minimum runs with the owning country as root and reads its variables. ENTRY: with the entry as root. NONE: it ran, in neither. UNCLAMPED: it never clamped (`add_progress` doesn't clamp, or the minimum isn't read). A load-time scope error on `has_variable` or `journal_entry_age` in `te_probe_115_bars.txt` names the scope the engine expects. | ENTRY: read the owner through `owner` in bar values. NONE: mirror the input into a global variable first. UNCLAMPED: clamp in script with `set_bar_progress`. |
| C5: clamped at activation? | `TE_PROBE_115 c5_at_activation 0` / `40` / `20` / `5` / `other` (step 2, before the add) | 0: the start value isn't clamped to the minimum when the entry activates. 40: it is, with the owner as root; 20: with the entry as root (step 3 then reads one more). 5: it is, but the root isn't told here: the clamp may run before the entry's `immediate` sets the owner's variable, so an owner root reads 5 too. Read `c5_root`. | — |
| C7: does a scaling modifier apply? | `TE_PROBE_115 c7_control OK` / `UNSCALED` / `ABSENT` / `OTHER` | OK: a constant value of 4 scales `nd_authority_terms_2` (launch credit reads 1). UNSCALED: the value is ignored. ABSENT: nothing reaches the country's `modifier:` read. | UNSCALED or ABSENT: § 4.2 of the prep doc is off; keep the dynamic-modifier pulse (`add_modifier` with `multiplier`). |
| C7: a value from a country-only read | `TE_PROBE_115 c7_positive seen after N days` / `NOT seen within 14 days` | seen: the value's root is the owning country (`is_ai` held) and the modifier follows it; N is how soon a `modifier:` read sees a change, `seen in the same effect` meaning at once. Expect N up to 4 (`JOURNAL_ENTRY_UPDATE_ACTIVE`). NOT seen with `c7_control OK`: the root is not the country. | Read the owner through `owner` (an event target from a journal entry) or `scope:journal_entry.owner`, or keep the pulse pattern. A large N: a reader must not expect the new value the same week. |
| C7: a negative value | `TE_PROBE_115 c7_negative seen after N days` / `NOT seen within 14 days` | seen: value -1 reads +6, so negatives work. NOT seen: clamped at 0, or not re-evaluated. | A second static modifier with the unit values negated, for the negative side. |
| C7: back to 0 | `TE_PROBE_115 c7_zero seen after N days` / `NOT seen within 14 days` | seen: the read returns to 0 after -1. The three N's together give the re-evaluation cadence. | NOT seen: a value can't be switched off by 0; remove it with the entry, or keep the pulse pattern. |
| C7: what a phase that never showed reads | `TE_PROBE_115 c7_read 0` / `-6` / `+6` / `other` | 0: the test modifier contributes nothing. -6: it applies at its own size (value ignored) or is stuck at 1. +6: stuck at -1. | As the row above it. |
| C7: does value 0 keep it on the entry? | `TE_PROBE_115 c7_zero_first PRESENT` / `ABSENT` (0 since activation), `TE_PROBE_115 c7_zero_after PRESENT` / `ABSENT` (0 after -1) | Whether `has_modifier` on the entry finds the test modifier at value 0. Read only if `c7_has_modifier_entry YES`. Whether the panel or the country's modifier list hides it is a play-test item (below). | PRESENT, if the panel then shows a row of zeros: § 4.2's policy switches can't use value 0 to hide a policy. |
| C7: how script tests a scaling modifier | `TE_PROBE_115 c7_has_modifier_entry YES` / `NO`, `TE_PROBE_115 c7_has_modifier_country YES` / `NO` | Whether `has_modifier` finds a scaling modifier on the entry (`je:<key> = { has_modifier = … }`, as the UN's membership check does for `modifiers_while_active`) and on the country. | Both NO: test the value's inputs (a variable), not the modifier. |
| C7: a value of 0 reads 0 | `TE_PROBE_115 c7_zero_first_read reads 0` / `reads non-zero` | Sanity: value 0 since activation reads 0. | non-zero: another source adds to the display type; the probe's C7 reads are void. |
| C19: a quoted `$ARG$` in `debug_log` | `TE_PROBE_115 c19_quoted_arg_a …`, `TE_PROBE_115 c19_quoted_arg_b …`, `TE_PROBE_115 c19_branch number=7` | Called once with N = 7, WORD = probe. `number=7 word=probe end` and `(kind probe)`: 1.15 substitutes inside quotes. `number7` and `wordprobe` each followed by a dollar sign, and `(kindprobe` with one: garbled as on 1.14.5. The argument names still in dollar signs: left alone. `c19_branch number=7` confirms the argument arrived. | Garbled or left alone: the rule in `scripting_best_practices.md` ("No `$PARAM$` inside the string") stands; branch on the argument and log literal lines. Substituted: the rule can be dropped for 1.15. |
| C20: `fire_only_once` on one country | `TE_PROBE_115 c20_once_here ONCE` / `NEVER` / `TWICE` | Tried with its trigger false (step 5), true (6) and true again (7). ONCE: a try whose trigger failed doesn't use it up, and a second firing is stopped. NEVER, with `c20_once_other FIRED`: the failed try used it up (it is marked on the try, not the firing). TWICE: not enforced. A `TE_PROBE_115 c20_once fired on the probe country` line straight after `step 5` means `trigger_event` ignored the event's `trigger`. | NEVER: fire a `fire_only_once` event only when its trigger holds. TWICE: keep variable cooldowns. |
| C20: per country or per game | `TE_PROBE_115 c20_once_other FIRED` / `NOT_FIRED` | FIRED: `fire_only_once` is per country (vanilla's commented test event calls it "Fire Only Once Country"). NOT_FIRED: once a game, or no other AI country was found. | NOT_FIRED: an event every country should see once needs a variable instead. |
| C20: `fire_only_once_globally` | `TE_PROBE_115 c20_globally ONCE` / `TWICE` / `NEVER` / `MORE` | Tried on the probe country twice and on one other. ONCE: once a game. TWICE: once per country. MORE: ignored (check the load lines). NEVER: never fired. | Keep a global variable marker. |
| C20: each firing | `TE_PROBE_115 c20_once fired on …`, `TE_PROBE_115 c20_globally fired on …` | One line per firing, on the probe country or the other one; the report lines above count them. | — |
| C21: activation of a one-country entry | `TE_PROBE_115 c21_activation_pass DUPE` (none expected) | One line per extra country that activated the entry on the claim's pass: the engine checks every inactive record before any activation's `immediate` runs, so an `immediate` can't stop a second country on the same pass. No line: one country only. | DUPE: any entry meant for one country (a world first) needs this guard: claim in `immediate`, end the extras through an invalid outcome. |
| C21: `scope:journal_entry` | `TE_PROBE_115 c21_pulse_scope OK` / `BROKEN`, `TE_PROBE_115 c21_outcome_scope OK` / `BROKEN` | Whether `scope:journal_entry` is set in an entry's `on_weekly_pulse` (and the scripted effects it calls) and in an outcome's `effect`. | BROKEN: reach the entry with `je:<key>`. |
| C21: inside an outcome's effect | `TE_PROBE_115 c21_outcome_effect_active YES` / `NO` | Whether `has_journal_entry` still holds while an outcome's effect runs. | NO: a helper an outcome calls must not gate on its own entry being active. |
| C21: a concluded entry | `TE_PROBE_115 c21_concluded_active YES` / `NO`, `TE_PROBE_115 c21_concluded_je YES` / `NO`, `TE_PROBE_115 c21_concluded_inactive YES` / `NO` | Three days after it concluded: whether `has_journal_entry`, `exists = je:<key>` and `has_inactive_journal_entry` find it. The engine docs call `has_journal_entry` active-only, so expect NO there; the other two are open. | Any YES: a script that tests a finished entry with these reads it as still there; test a variable the outcome sets instead (the mod's entries already set one). |
| C21: `disable_evaluation` | `TE_PROBE_115 c21_disable_evaluation REMOVED` / `KEPT` / `INCONCLUSIVE` | Seven weeks after the claim, on another AI country: REMOVED means `disable_evaluation` removed its inactive record (a cheap way to prune the 28 mod entries' records for countries that can never take them). KEPT: it didn't. INCONCLUSIVE: `has_inactive_journal_entry` is false even for an entry never activated, so it can't tell. | KEPT: no pruning that way; check the load lines for the field. |

## Not probed (needs a player or a save)

- **C5**, the rest: how a `progress_condition` factor of 0, and one read from a named script value, show in the
  panel's Advance and Retreat lists (open an entry that uses one, once one does).
- **C7**: whether a scaling modifier at value 0 shows a row of zeros in the journal entry panel and the country's
  modifier tooltip, or is hidden (open a mod entry that uses one, once § 4.2 builds one); whether a revolution's winner
  gets it back with the inherited entry (the civil-war harness, `docs/audits/civil_war_inheritance_audit.md`; the probe
  entry is `can_revolution_inherit = no`).
- **C20**: whether a fired `fire_only_once` event stays fired across a save and load, and for a revolution's winner
  (save before and after, `scripts/analysis/save_country_probe.py`).
- **C21**, contextless entries: `should_be_involved` re-checks, what `je:` and `JournalEntry.GetCountry` return for one,
  `effect_all_involved`. A contextless probe entry could show in a player's journal, so none was built.

## Panels and systems

<!-- The controller fills this from the other streams' play-test items. -->
