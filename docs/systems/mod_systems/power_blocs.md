# Power Blocs

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

The mod's power bloc content outside this file: principle slots 5 to 8 and their game rule (`common/script_values/te_power_bloc_principle_slot_values.txt`, `docs/systems/mod_systems/game_rules.md`, `test_pb_principle_slots.py`), the identity and principle groups (`common/power_bloc_identities/`, `common/power_bloc_principles/`, `common/power_bloc_principle_groups/`), and the panel override (`gui/power_bloc_panel.gui`, `docs/guides/gui_modding_guide.md`). The player guide's account is `docs/player_guide/09-diplomacy.md` § "Power bloc principles and identities".

## Power Bloc Summits (`te_pb_summit.1`)

A use for mandates other than principles (#1442), for a bloc whose slots are full. A leader spends one mandate on one initiative the whole bloc carries for ten years. It replaced the Mandate Reserve (+3 cohesion a year per unspent mandate, up to +12), a 1.14.5 stand-in from when script couldn't spend a mandate; a bonus for holding mandates would pull against spending them. The reserve's modifier is retired, kept defined for old saves and stripped yearly (`te_unused_mandate_reserve_on_action`; checklist in `common/scripted_effects/legacy_modifier_cleanup.txt`).

**Files.** `events/te_power_bloc_summit_events.txt` (the event), `common/static_modifiers/te_power_bloc_summit_modifiers.txt`, `common/scripted_effects/te_power_bloc_summit_effects.txt` (`te_pb_summit_pay`, `te_pb_summit_grant_bloc_initiative`), `common/scripted_triggers/te_power_bloc_summit_triggers.txt` (`te_pb_summit_can_pay`, `te_pb_summit_has_open_borders`), `common/on_actions/te_power_bloc_summit_on_actions.txt` (the AI), `te_pb_summit_sgui` in `common/scripted_guis/te_power_bloc_sguis.txt` and its button in `gui/power_bloc_panel.gui`; `test_pb_summit.py`. Play-test items: `docs/testing/vanilla-1-15-playtest.md` § "Power bloc mandates".

**The button.** Convene a Summit sits beside the leader's mandate count (vanilla's AVAILABLE MANDATES row, shown only to the leader). `is_valid` is `te_pb_summit_can_pay` under a custom tooltip, so the button greys with its reason while the bloc holds no mandate. It spends nothing: it fires the event with `popup = yes`, and closing the event costs nothing.

**The options.** Each initiative calls `te_pb_summit_pay` (`add_power_bloc_mandate = -1` under the cost line `te_pb_summit_cost_tt`, plus a `TE_PB_SUMMIT <kind> by=ai|player` log line) and lasts `long_modifier_time`. The bloc's are granted by `te_pb_summit_grant_bloc_initiative`, which removes a running copy first, unseen, since a same-name `add_modifier` stacks.

| Option | Modifier (scope) | Effect | Offered |
|---|---|---|---|
| a | `te_pb_summit_rally` (bloc) | `add_cohesion_percent = 0.2` at once, `power_bloc_cohesion_add = 10` | Always, for the immediate cohesion |
| b | `te_pb_summit_recruitment` (bloc) | `power_bloc_invite_acceptance_add = 25` | While not running |
| c | `te_pb_summit_leverage` (bloc) | `power_bloc_leverage_generation_mult = 0.25` | While not running |
| e | `te_pb_summit_open_borders` (bloc) | `power_bloc_allow_port_access_bool`, `power_bloc_allow_wider_migration_area_bool` | While not running, and not when Navy III+ and Freedom of Movement III+ give both |
| g | `te_pb_summit_home` (leader) | `country_legitimacy_base_add = 10`, `country_authority_add = 50` | While not running |
| h | none | Adjourn; the default option | Always |

Every option but Adjourn also needs `te_pb_summit_can_pay`, since the event can wait while the mandate goes on a principle; with none in hand the description says the summit can only adjourn. Magnitudes sit against vanilla's: principles move cohesion by 5 to 20 and the UN's bloc vacuum gives +10; Sovereign Empire's invitation penalty is −30; the UN's dissolution vacuum gives +20% leverage. A spend is worth less than a principle tier (ten years, not permanent), so a bloc with an open slot still buys principles first.

**The AI.** The engine AI spends mandates on principles and never clicks a scripted GUI (`ai_is_valid = { always = no }`). `te_pb_summit_ai_on_action` (on `on_monthly_pulse_country`) gives an AI leader holding two or more mandates a monthly chance to fire the event: 3%, 6%, 10% and 25% at two, three, four and five (`MAX_MANDATES`), about 31%, 52%, 72% and 97% a year (owner, 2026-11-06: from two, rising with the count, since AI leaders fill their slots quickly). At the cap, progress is wasted, so the summit comes within months. The event's `ai_chance` picks the initiative: Common Purpose 10, +30 below 50% cohesion and +30 more below 25%; Recruitment 5, +10 under five members; Leverage 10; Open Borders 5; Mandate at Home 5, +15 below 50 legitimacy; Adjourn 0.

## Mandates in Script (1.15)

Probed with the power bloc test console's mandate options (`te_debug_pb.1` options g and h, verdict in `te_debug_pb.2`), 2026-11-06: `add_power_bloc_mandate = -1` removes a mandate, and the count drops within the same effect (the `straight_after` reading), so a spend can check and deduct in one click. `power_bloc.num_mandates` reads the count as a value from country scope and matches the `num_mandates` trigger. Not probed: whether a negative value takes the count below 0 (every spend gates on `num_mandates >= 1`, so it doesn't matter yet), and whether `add_power_bloc_mandate` above the cap of 5 is clamped as the docs say.
