# Per-good snippet templates

Copy-paste-and-substitute templates for the verbose per-good blocks. Replace:
- `<GOOD>` → lowercase good ID (e.g. `small_arms`, `gold`)
- `<GOOD_DISPLAY>` → prose form (e.g. `Small Arms`, `Gold`)
- `<TECH>` → gating tech ID (e.g. `military_aviation`) — or remove the `has_technology_researched` line entirely if the good is always available

The templates assume tab indentation. Existing entries in the source files are the ground truth — when in doubt, grep for an existing good's name to see exact spacing.

---

## File 5: `common/script_values/st_res_script_values.txt`

Append the section below after the existing `--- TANKS ---` section (or whichever section is currently last). Then add the `_fill_pct` value at the very bottom alongside the existing `_fill_pct` entries.

### Main section (10 values)

```
# --- <GOOD_DISPLAY upper> ---
st_res_<GOOD>_decay_rate = {
	value = 0
	add = modifier:country_st_res_<GOOD>_decay_add
	divide = 52 # convert from per-year to per-week decay
	min = 0
	max = 1
}

st_res_<GOOD>_weekly_decay = {
	value = var:st_res_<GOOD>_stored
	multiply = st_res_<GOOD>_decay_rate
}

st_res_<GOOD>_actual_rate = {
	value = 0
	if = {
		limit = { var:st_res_hub_workforce_cached > 0.99 }
		add = var:st_res_<GOOD>_rate
	}
	add = st_res_<GOOD>_weekly_decay
}

st_res_<GOOD>_actual_rate_base_applied = {
	value = st_res_<GOOD>_actual_rate
	min = {
		value = 0
		subtract = st_res_weekly_base_rate_cap
	}
	max = st_res_weekly_base_rate_cap
}

st_res_<GOOD>_weekly_delta = {
	value = 0
	add = st_res_<GOOD>_actual_rate_base_applied
	subtract = st_res_<GOOD>_weekly_decay
}

st_res_<GOOD>_capacity = {
	value = 0
	add = modifier:country_st_res_<GOOD>_capacity_add
}

st_res_<GOOD>_good_mult = {
	value = 0
	if = {
		limit = {
			has_variable = st_res_<GOOD>_stored
			st_res_<GOOD>_actual_rate_base_applied > 0
		}
		add = st_res_<GOOD>_actual_rate_base_applied
	}
	else_if = {
		limit = { has_variable = st_res_<GOOD>_stored }
		subtract = st_res_<GOOD>_actual_rate_base_applied
	}
	# Compensate for throughput modifiers, so total rate equals desired rate
	divide = st_res_throughput_factor
}

st_res_<GOOD>_max_withdrawable = {
	value = 0
	add = var:st_res_<GOOD>_stored
	subtract = st_res_<GOOD>_weekly_decay
	multiply = -1
}

st_res_<GOOD>_max_storable = {
	value = 0
	add = st_res_<GOOD>_capacity
	subtract = var:st_res_<GOOD>_stored
	subtract = st_res_<GOOD>_weekly_decay
}

st_res_<GOOD>_sale_profit = {
	value = 0
	if = {
		limit = {
			has_variable = st_res_<GOOD>_stored
			st_res_<GOOD>_actual_rate_base_applied < 0
		}
		subtract = st_res_<GOOD>_actual_rate_base_applied
		g:<GOOD> = {
			multiply = base_price
		}
		multiply = {
			value = 1
			add = this.market.mg:<GOOD>.market_goods_pricier
		}
	}
}
```

### Fill-percentage value (at end, with siblings)

```
st_res_<GOOD>_fill_pct = {
	value = var:st_res_<GOOD>_stored
	divide = {
		value = st_res_<GOOD>_capacity
		min = 1
	}
	multiply = 100
}
```

---

## File 6: `common/scripted_effects/st_res_effects.txt`

The pattern: extend EVERY existing per-good enumeration to include `<GOOD>`, then add three new helpers.

### 6a. Extend `st_res_init_effect` (add a stored-var + rate-var pair, mirroring oil's pair)

```
	if = {
		limit = { NOT = { has_variable = st_res_<GOOD>_stored } }
		set_variable = { name = st_res_<GOOD>_stored value = 0 }
	}
	if = {
		limit = { NOT = { has_variable = st_res_<GOOD>_rate } }
		set_variable = { name = st_res_<GOOD>_rate value = 0 }
	}
```

### 6b. Extend `st_res_reset_vars_effect` (mirror oil's two `set_variable` lines)

```
	set_variable = { name = st_res_<GOOD>_stored value = 0 }
	set_variable = { name = st_res_<GOOD>_rate value = 0 }
```

### 6c. Extend `st_res_clamp_stockpiles_effect` (one stored-clamp line + two rate-clamp lines per good)

```
	clamp_variable = { name = st_res_<GOOD>_stored min = 0 max = st_res_<GOOD>_capacity }
```

```
	clamp_variable = { name = st_res_<GOOD>_rate min = st_res_neg_weekly_base_rate_cap max = st_res_weekly_base_rate_cap }
	clamp_variable = { name = st_res_<GOOD>_rate min = st_res_<GOOD>_max_withdrawable max = st_res_<GOOD>_max_storable }
```

### 6d. Extend `st_res_weekly_update_effect` (inside the `if = { limit = { any_scope_building = ... } }`)

```
		change_variable = { name = st_res_<GOOD>_stored add = st_res_<GOOD>_weekly_delta }
		clamp_variable = { name = st_res_<GOOD>_stored min = 0 max = st_res_<GOOD>_capacity }
```

### 6e. Extend `st_res_je_immediate_effect` AND `st_res_je_weekly_pulse_effect` (both files; same shape)

Add one `set_variable` line at the country-scope level:

```
	set_variable = { name = st_res_<GOOD>_fill_for_bar value = st_res_<GOOD>_fill_pct }
```

…and one `set_bar_progress` line inside `scope:journal_entry`:

```
		set_bar_progress = { name = st_res_<GOOD>_fill_bar value = ROOT.var:st_res_<GOOD>_fill_for_bar }
```

### 6f. Extend `st_res_reset_rates_effect`

```
	set_variable = { name = st_res_<GOOD>_rate value = 0 }
```

### 6g. Extend `st_res_refresh_hub_flow_effect` (the cached actual-rate writes)

```
	set_variable = { name = st_res_<GOOD>_actual_rate_cached value = st_res_<GOOD>_actual_rate }
```

### 6h. Extend `st_res_rebuild_hub_flow_modifiers_effect` (TWO places)

At the country-scope startup section:

```
	st_res_startup_good_setup_effect = { GOOD = <GOOD> }
```

Inside the `random_scope_building = { limit = { is_building_type = building_strategic_reserve_hub } ... }` block:

```
			st_res_rebuild_<GOOD>_flow_modifiers_effect = yes
```

### 6i. Extend `st_res_apply_sell_profit_effect`

```
	change_variable = { name = st_res_sell_profit add = st_res_<GOOD>_sale_profit }
```

### 6j. New wrapper effect (one per good)

```
st_res_rebuild_<GOOD>_flow_modifiers_effect = {
	st_res_rebuild_good_flow_modifiers_effect = { GOOD = <GOOD> }
}
```

### 6k. New rate-adjust effects (two per good)

```
st_res_increase_<GOOD>_rate_effect = {
	st_res_init_effect = yes
	change_variable = { name = st_res_<GOOD>_rate add = st_res_adjust_step_value }
	st_res_refresh_hub_flow_effect = yes
	st_res_clamp_stockpiles_effect = yes
}

st_res_decrease_<GOOD>_rate_effect = {
	st_res_init_effect = yes
	change_variable = { name = st_res_<GOOD>_rate subtract = st_res_adjust_step_value }
	st_res_refresh_hub_flow_effect = yes
	st_res_clamp_stockpiles_effect = yes
}
```

---

## File 7: `common/scripted_buttons/st_res_buttons.txt`

Two buttons. If the good has a tech gate, include the `has_technology_researched = <TECH>` line in the `visible` block; otherwise drop it (only `has_journal_entry = je_strategic_reserve` remains).

```
# ---------------- <GOOD_DISPLAY upper> RATE BUTTONS ----------------
st_res_increase_<GOOD>_rate_button = {
	name = "st_res_increase_<GOOD>_rate_button"
	desc = "st_res_increase_<GOOD>_rate_button_desc"
	visible = {
		has_journal_entry = je_strategic_reserve
		has_technology_researched = <TECH>
	}
	ai_chance = {
		value = 0
	}
	possible = {
		custom_tooltip = {
			text = "st_res_rate_adjustment_disabled"
			var:st_res_<GOOD>_rate < st_res_<GOOD>_max_storable
			var:st_res_<GOOD>_rate < st_res_weekly_base_rate_cap
		}
	}
	effect = {
		st_res_increase_<GOOD>_rate_effect = yes
	}
}

st_res_decrease_<GOOD>_rate_button = {
	name = "st_res_decrease_<GOOD>_rate_button"
	desc = "st_res_decrease_<GOOD>_rate_button_desc"
	visible = {
		has_journal_entry = je_strategic_reserve
		has_technology_researched = <TECH>
	}
	ai_chance = {
		value = 0
	}
	possible = {
		custom_tooltip = {
			text = "st_res_rate_adjustment_disabled"
			var:st_res_<GOOD>_rate > st_res_<GOOD>_max_withdrawable
			var:st_res_<GOOD>_rate > st_res_neg_weekly_base_rate_cap
		}
	}
	effect = {
		st_res_decrease_<GOOD>_rate_effect = yes
	}
}
```

---

## File 8: `common/scripted_progress_bars/st_res_progress_bars.txt`

```
st_res_<GOOD>_fill_bar = {
	name = "st_res_<GOOD>_fill_bar_name"
	desc = "st_res_<GOOD>_fill_bar_desc"

	default_green = yes

	start_value = 0
	min_value = 0
	max_value = 100
}
```

---

## File 9: `common/customizable_localization/st_res_custom_loc.txt`

```
st_res_<GOOD>_mode_text = {
	type = country
	random_valid = no

	text = {
		trigger = {
			var:st_res_<GOOD>_rate > 0
			var:st_res_<GOOD>_stored < st_res_<GOOD>_capacity
		}
		localization_key = st_res_mode_storing
	}
	text = {
		trigger = {
			var:st_res_<GOOD>_rate < 0
			var:st_res_<GOOD>_stored > 0
		}
		localization_key = st_res_mode_withdrawing
	}
	text = {
		trigger = { always = yes }
		localization_key = st_res_mode_idle
	}
}
```

---

## File 10: `common/journal_entries/je_strategic_reserve.txt`

Three insertions inside the `je_strategic_reserve = { ... }` body:

(a) progress bar declaration (next to the existing `scripted_progress_bar = st_res_oil_fill_bar`):

```
	scripted_progress_bar = st_res_<GOOD>_fill_bar
```

(b) two button declarations (next to the existing `scripted_button = st_res_increase_oil_rate_button`):

```
	scripted_button = st_res_decrease_<GOOD>_rate_button
	scripted_button = st_res_increase_<GOOD>_rate_button
```

(c) status_desc triggered_desc (next to the existing oil/aeroplanes/tanks lines). With tech gate:

```
		triggered_desc = {
			desc = je_strategic_reserve_<GOOD>_line
			trigger = { has_technology_researched = <TECH> }
		}
```

Without tech gate:

```
		triggered_desc = {
			desc = je_strategic_reserve_<GOOD>_line
			trigger = { always = yes }
		}
```

---

## Localization templates (files 11–14)

### te_modifiers_l_english.yml

```
 country_st_res_<GOOD>_capacity_add:0 "<GOOD_DISPLAY> Reserve Capacity"
 country_st_res_<GOOD>_capacity_add_desc:0 "Maximum <GOOD_DISPLAY lower> that can be held in the national strategic reserve."
 country_st_res_<GOOD>_decay_add:0 "<GOOD_DISPLAY> Reserve Decay"
 country_st_res_<GOOD>_decay_add_desc:0 "Fraction of the <GOOD_DISPLAY lower> stockpile lost to <REASON> per year."
```

`<REASON>` → "spoilage" for food, "corrosion and obsolescence" for arms, "airframe fatigue and obsolescence" for aeroplanes, "mechanical degradation and obsolescence" for tanks, etc. Match the existing voice.

### te_journal_entries_l_english.yml

One key per good (the JE status line). The format is verbose but mechanical — copy the existing oil line and substitute. Note: `Active` shows the *actual* gross flow (includes decay replenishment) which can differ from the player's *Rate Setting*.

```
 je_strategic_reserve_<GOOD>_line:0 "\n#bold <GOOD_DISPLAY>:#! [ROOT.GetCountry.MakeScope.Var('st_res_<GOOD>_stored').GetValue|0] / [ROOT.GetCountry.GetModifier.GetValueWithBreakdownFor('country_st_res_<GOOD>_capacity_add')]\n#bold Rate Setting:#! [ROOT.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|0] / week\n#bold Active:#! [ROOT.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_actual_rate')|0] / week\n#bold Status:#! [ROOT.GetCountry.GetCustom('st_res_<GOOD>_mode_text')]\n#bold Decay:#! [ROOT.GetCountry.GetModifier.GetValueWithBreakdownFor('country_st_res_<GOOD>_decay_add')]\n"
```

Also update `je_strategic_reserve_desc:0 "Manage the national stockpile of grain, ammunition, oil, ..."` to add the new good name in its comma list.

### te_miscellaneous_l_english.yml

```
 st_res_<GOOD>_fill_bar_name:0 "<GOOD_DISPLAY> Fill"
 st_res_<GOOD>_store_flow:0 "Strategic Reserve <GOOD_DISPLAY> Intake"
 st_res_<GOOD>_withdraw_flow:0 "Strategic Reserve <GOOD_DISPLAY> Release"
 st_res_increase_<GOOD>_rate_button:0 "Increase <GOOD_DISPLAY> Rate"
 st_res_decrease_<GOOD>_rate_button:0 "Decrease <GOOD_DISPLAY> Rate"
```

### te_concepts_l_english.yml

```
 st_res_<GOOD>_fill_bar_desc:0 "<GOOD_DISPLAY>: [ROOT.ScriptValue('st_res_<GOOD>_fill_pct')|1]% Full"
 st_res_<GOOD>_store_flow_desc:0 "This hub is purchasing <GOOD_DISPLAY lower> for the strategic reserve."
 st_res_<GOOD>_withdraw_flow_desc:0 "This hub is releasing <GOOD_DISPLAY lower> from the strategic reserve."
 st_res_increase_<GOOD>_rate_button_desc:0 "Increase the <GOOD_DISPLAY lower> reserve rate setting by [ROOT.GetCountry.MakeScope.ScriptValue('st_res_adjust_step_value')|0]. Positive values store <GOOD_DISPLAY lower>, negative values withdraw them. Current setting: [ROOT.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|0] / week."
 st_res_decrease_<GOOD>_rate_button_desc:0 "Decrease the <GOOD_DISPLAY lower> reserve rate setting by [ROOT.GetCountry.MakeScope.ScriptValue('st_res_adjust_step_value')|0]. Positive values store <GOOD_DISPLAY lower>, negative values withdraw them. Current setting: [ROOT.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|0] / week."
```

`organize_loc.py` will re-sort these on the next mod_state_server reload. Don't worry about exact insertion position — alphabetical-ish is enough for diff readability.

---

## Optional: per-tech decay reduction `INJECT:` blocks

In `common/technology/technologies/modified.txt`, add an INJECT for any tech that should reduce the new good's decay. Pattern:

```
INJECT:<tech_id> = {
	modifier = {
		country_st_res_<GOOD>_decay_add = -0.005
	}
}
```

Decay reduction values are small — typically 5-25% of the base decay rate per tech. For grain (base 0.25), `canneries` and friends reduce by 0.05 each. For ammunition (base 0.02), `dynamite` reduces by 0.005. Pick comparably.
