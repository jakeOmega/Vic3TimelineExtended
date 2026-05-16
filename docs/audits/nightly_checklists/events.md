# Nightly audit — events

For each event file selected, walk every event and apply these checks. Skip checks already covered by procedural audits (modifier visibility, magnitude, kill_character guards, loc presence, accessor chains, concept refs) — only flag if you find something a procedural audit would miss.

## Checks

- **AI weights.** Every option has an explicit `ai_chance` block with a `base` and at least one `modifier` tilt, or an in-comment reason it doesn't. (`docs/guides/event_creation_guide.md` § AI Weights in Events)
- **IG approval direction.** When an option bumps IG approval, the change matches the IG's prior stance per vanilla's rule: an IG approves passage of a law only when its prior stance was disapproved or neutral. Same logic for approval bumps on event outcomes. (`docs/vanilla/vanilla_politics_reference.md`)
- **Narrative-mechanical alignment.** The option title and tooltip describe the outcome the effect block actually produces — no drift between flavor and effect.
- **Modifier read-after-write.** Where `add_modifier` / `remove_modifier` is followed by a read of `modifier:X` in the same effect block, the read uses a stored prior-contribution variable, not the post-change `modifier:X`. (`docs/guides/scripting_best_practices.md`)
- **Asset usage.** Videos and icons are drawn from the documented available sets in `docs/guides/event_creation_guide.md`.
- **Option dominance.** For multi-option events, no option is strictly dominated by another. Pure-positive vs pure-negative is fine if competitive — the rule is non-dominance, not forced-tradeoff. (`docs/guides/event_creation_guide.md` § Option Tradeoff Principles)
- **Authority / resource-spending option AI.** When an option costs authority (or any resource), the AI block follows the three rules: gate on `authority` not `produced_authority`, incremental weight ramp (not single-threshold cliff), default option base ≥ 2–3. (`docs/guides/event_creation_guide.md` § Authority-Spending Options)
- **Pulse-fired narrative coherence.** For events fired from `on_yearly_pulse` / `on_monthly_pulse` / similar pulses: the narration is plausible given the player's actions — no "the veto worked" without a veto having been cast. (`docs/audits/open_issues.md` M_NEW2 #2)
- **Event-chain context.** For events that follow from a prior choice (backfires, sequels): the description references the prior event or otherwise reorients the player. (`docs/audits/open_issues.md` M_NEW2 #3)
- **Flavor-character guards.** When an event creates a throwaway character for flavor-text attribution, the pattern uses `place_character_in_void = 6` plus an `exists = scope:X` guard on `kill_character`. (`docs/guides/event_creation_guide.md` § Attributed fictional quotes — the procedural `kill_character_audit` catches the guard, but only this check verifies the design intent is "flavor name, not real character".)
- **Modifier value direction = in-fiction reception.** A "rehabilitation" modifier that grants positive reception when the in-fiction setup is fake contrition should be negative. Read the event's framing and ask whether the modifier sign matches how the world receives the outcome. (memory: narrative reception)
- **Toggle vs cooldown.** For policy-style choices reflecting long-term strategic orientation: prefer toggle pattern (enable/disable button pair) over cooldown one-shot. Flag cooldown patterns where toggle would fit. (`docs/guides/event_creation_guide.md` § Toggle vs Cooldown)
