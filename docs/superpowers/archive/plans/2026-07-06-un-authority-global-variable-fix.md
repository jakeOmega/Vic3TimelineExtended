# Brief: Convert `un_authority` from a per-country variable to a global variable

**Status:** Not started. Written 2026-07-06 as a handoff for a separate session.
**Owner intent:** `un_authority` was always *meant* to be a single global value representing
the UN's authority in the world. It was implemented as a per-country variable by mistake.
This brief describes the bug and the conversion.

**Do this in its own session** — it is a systematic, ~10-file refactor and should not be mixed
with the diplomatic-principle-group work happening on `claude/diplomatic-principle-groups-4puwcu`.
(That work has a dependency on this fix; see "Downstream dependency" at the end.)

---

## The bug

`un_authority` is stored and mutated as a **country-scoped** variable (`set_variable` /
`change_variable` / read as `var:un_authority`). Every member country that runs
`je_united_nations` keeps its *own independent* authority number. Consequences:

- The monthly drift, championing/undermining toggles, war penalties, event shocks, and vote
  outcomes each move **only the acting country's own copy**, not a shared world value.
- "Is the UN strong?" is currently expressed as `any_country = { member; var:un_authority >= 60 }`
  — i.e., the world treats the UN as strong if *at least one* member happens to have high
  personal authority (usually the leader/a GP). That is not the intended semantics.
- Members' benefits (`un_membership_benefits_modifier`), high-authority infamy, NPT pressure,
  and non-member pariah status all scale off the *local* copy.

### Smoking gun that global was the original intent

`common/script_values/un_script_values.txt` already computes the drift factors as **global
aggregates** over `every_country`:

- `un_authority_drift_democracy` — sums +0.1/+0.2 for **every** GP with humanitarian_regs / limited_war
- `un_authority_drift_champion` — sums +0.3 (+0.2 if top-3) for **every** champion
- `un_authority_drift_undermine` — mirror, negative
- `un_authority_drift_wars` — sums −1 for **every** member at war with another member
- `un_authority_drift_total` = base + democracy + champion + undermine + wars

These were written for a single global authority. But the JE `on_monthly_pulse`
(`je_united_nations.txt` ~lines 277–342) applies only **ROOT's own** slice to **ROOT's own**
`var:un_authority`. So the display script values and the actual mechanic disagree.

---

## Desired behavior

One global `un_authority` in `[0,100]`, updated **once per month** by the aggregate drift
(`un_authority_drift_total`), plus discrete global shocks from events/buttons/votes. Every
reader keys off the single global value.

---

## Conversion strategy

1. **Storage → global.**
   - Replace the per-country init in `je_united_nations.txt` `immediate`
     (`set_variable = { name = un_authority value = 50 }`) — the global should be initialized
     **once, at UN founding**, next to `set_global_variable = un_founded`
     (`common/scripted_buttons/un_buttons.txt:43`): `set_global_variable = { name = un_authority value = 50 }`.
   - Per `docs/guides/scripting_best_practices.md` (global-var init timing, ~line 2324): anything
     that reads `global_var:un_authority` must be gated on `has_global_variable = un_authority`
     or guaranteed to run after founding. All current readers are already gated on membership /
     `un_founded`, so the founding anchor is sufficient — but audit for any `possible`/script-value
     reader that could fire earlier.

2. **Single monthly updater.** The drift block in the JE `on_monthly_pulse` currently runs
   per-member and must **collapse into one global update**. Move it to a place that runs exactly
   once per month — recommended: an `on_monthly_pulse` handler in
   `common/on_actions/un_on_actions.txt` guarded so it executes a single time (e.g. from the UN HQ
   host, or `random_country = { limit = { <is a member> } }`, or a dedicated global tick). The body
   becomes roughly:
   ```
   if = {
       limit = { has_global_variable = un_authority }
       change_global_variable = { name = un_authority add = un_authority_drift_total }
       # clamp 0..100 with set_global_variable
   }
   ```
   Because `un_authority_drift_total` already aggregates all members globally, the per-member
   drift/championing/war/law branches in `je_united_nations.txt` (~277–332) should be **deleted**
   (they are now double-counting duplicates of the drift script values). Keep the `un_authority_drift_base`
   toward-50 term, but change its `var:un_authority` read to `global_var:un_authority`.

3. **Reads → `global_var:un_authority`.** All ~80 `var:un_authority` reads become
   `global_var:un_authority`. Notable ones beyond the JE:
   - `common/static_modifiers/extra_modifiers.txt` — the `un_membership_benefits_modifier` and
     high-authority infamy multiplier blocks (`multiplier = { value = var:un_authority ... }`).
     Keep these modifiers **applied per-member** (each member still receives the modifier), but the
     multiplier now reads the shared global value.
   - `common/treaty_articles/extra_treaty_articles.txt` — the `nuclear_program_aid` NPT gate and
     any `any_country = { member; var:un_authority >= 60 }` checks **simplify** to a direct
     `global_var:un_authority >= 60` (drop the `any_country` iteration entirely).
   - `common/scripted_progress_bars/un_progress_bars.txt` — bar sync reads global.
   - `common/game_concepts/extra_concepts.txt`, loc `[...GetVariable('un_authority')...]` style refs
     → global equivalents.

4. **Writes → global, but review each site.** All `change_variable = { name = un_authority ... }`
   in `un_buttons.txt` (9), `un_events.txt` (~95), `un_vote_events.txt` (~24), and any in
   `un_on_actions.txt` become `change_global_variable`. **Critical review at each site:** if a write
   currently lives inside an `every_country` / per-member loop or an event that fires for many
   countries, converting it to a global write will apply N times per tick. Most UN events are
   HQ/global-driven and fire once, so a straight swap is usually correct — but confirm each is not
   multiplied. Clamp after batch shocks where needed.

5. **Clamp once, globally.** The 0/100 clamp currently in the JE pulse moves to the single global
   updater (and after large event shocks if they can overshoot).

6. **Save-game migration.** Existing saves carry per-country `un_authority` vars and no global one.
   Add a one-time migration (guarded `if = { limit = { NOT = { has_global_variable = un_authority } ... } }`)
   that seeds the global from a sensible source — recommend the UN HQ host's existing local value,
   else the max across members, else 50 — then optionally `remove_variable` the stale local copies.
   The JE already contains legacy-migration precedent (`je_united_nations.txt` SC-seat migration
   block) to mirror in style.

---

## File work list (reference counts from 2026-07-06)

| File | Refs | Work |
|---|---|---|
| `events/un_events.txt` | 129 | writes → global (review per-site for loops); reads → global |
| `common/journal_entries/je_united_nations.txt` | 42 | delete per-member drift block; init moves out; reads → global; clamp moves to updater |
| `events/un_vote_events.txt` | 26 | vote-outcome writes → global |
| `common/scripted_buttons/un_buttons.txt` | 24 | champion/undermine + event-button writes → global; add global init at founding (line 43) |
| `common/on_actions/un_on_actions.txt` | 21 | host the single monthly global updater; convert reads/writes |
| `common/script_values/un_script_values.txt` | 13 | `un_authority_drift_base` read → global; verify `_total` evaluates correctly from the updater scope |
| `common/static_modifiers/extra_modifiers.txt` | 3 | benefit/infamy multiplier reads → global |
| `common/scripted_progress_bars/un_progress_bars.txt` | 3 | bar reads → global |
| `common/treaty_articles/extra_treaty_articles.txt` | 2 | NPT/`any_country` checks → direct global read |
| `common/game_concepts/extra_concepts.txt` + loc yml | several | concept/loc var refs → global |

Localization files with `un_authority` refs (`te_concepts`, `te_journal_entries`,
`te_miscellaneous`, `te_un_button_effects`, `te_diplomacy`) use custom-loc `GetVariable`-style
reads that must point at the global; audit each.

---

## Gotchas

- **Variable writes are invisible to the player** (`scripting_best_practices.md` ~line 2754 calls
  out `un_authority` by name). Preserve any existing `custom_tooltip` / `show_as_tooltip` wrappers
  that surface the delta.
- **Don't double-apply** event/vote writes that sit in multi-country contexts (see step 4).
- **Init before read** — founding anchor + `has_global_variable` gates (step 1).
- **No dedicated UN test harness exists** (`test_tech_unlocks_lib.py` is unrelated). Consider adding
  a targeted parser/behavior test, or at minimum verify via `POST /reload` warnings + an in-game
  founding→drift→benefit smoke test.
- After edits: `python scripts/format_paradox_tabs.py <files>` on the brace files, then
  `curl -X POST 'http://localhost:8950/reload'` and check the `warnings` array +
  `docs/engine/*_report.md` audits.

---

## Downstream dependency

The Diplomatic **Multilateral Institutions** principle group (in design on
`claude/diplomatic-principle-groups-4puwcu`) has a Tier II that feeds a new
`country_un_authority_*` contribution modifier into UN authority and grants members an
authority-scaled benefit. That tier assumes a **single global** authority (rank-weighted
contributions summed into one value). It should be implemented **after** this fix lands, against
the global variable. The principle group's other tiers (I, III, IV, V) have no dependency on this.
