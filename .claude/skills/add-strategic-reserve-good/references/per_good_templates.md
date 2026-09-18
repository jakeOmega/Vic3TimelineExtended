# Per-good snippet templates

Copy-paste-and-substitute templates for the verbose per-good blocks. Replace:
- `<GOOD>` → lowercase good ID (e.g. `small_arms`, `gold`)
- `<GOOD_DISPLAY>` → prose form (e.g. `Small Arms`, `Gold`)
- `<TECH>` → gating tech ID (e.g. `military_aviation`) — or use `always = yes` if the good is always available

The templates assume tab indentation. Existing entries in the source files are the ground truth — when in doubt, grep for an existing good's name to see exact spacing.

> **Since the reserve inventory widget landed**, a good no longer needs a scripted progress bar, a pair of scripted buttons or a journal-entry status line. It needs an unlock trigger, a scripted GUI, a widget row and two custom-loc blocks instead. The numbering below matches the table in `SKILL.md`.

---

## File 5: `common/script_values/st_res_script_values.txt`

Append the main section after the existing `--- TANKS ---` section (or whichever section is currently last). Then add `_fill_pct` and `_last_net` at the bottom alongside their siblings.

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
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_stored }
		value = var:st_res_<GOOD>_stored
		multiply = st_res_<GOOD>_decay_rate
	}
}

# Decay-add must stay INSIDE the workforce gate: an undermanned hub cannot
# auto-replenish decay loss, and pulling it out would make weekly_delta read 0
# while the stockpile is actually shrinking.
st_res_<GOOD>_actual_rate = {
	value = 0
	if = {
		limit = {
			has_variable = st_res_hub_workforce_cached
			var:st_res_hub_workforce_cached > 0.99
			has_variable = st_res_<GOOD>_rate
		}
		add = var:st_res_<GOOD>_rate
		add = st_res_<GOOD>_weekly_decay
	}
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
	divide = st_res_throughput_factor
	subtract = 1  # compensate for PM base 1-unit (see grain block for rationale)
}

# Bounds for the rate clamp in st_res_clamp_stockpiles_effect — pure storage room.
# Decay is already netted out in weekly_delta; subtracting it again here would pull
# the rate variable below zero at full capacity and silently flip Status to "Withdrawing".
st_res_<GOOD>_max_withdrawable = {
	value = 0
	add = var:st_res_<GOOD>_stored
	multiply = -1
}

st_res_<GOOD>_max_storable = {
	value = 0
	add = st_res_<GOOD>_capacity
	subtract = var:st_res_<GOOD>_stored
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

### Widget accessors (two more, in their own sibling groups near the bottom)

**Both MUST be `has_variable`-guarded.** The inventory widget evaluates them every frame, including on a save made before the good existed; an unguarded `var:` read there raises script-system errors.

```
st_res_<GOOD>_fill_pct = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_stored }
		value = var:st_res_<GOOD>_stored
		divide = {
			value = st_res_<GOOD>_capacity
			min = 1
		}
		multiply = 100
	}
}
```

```
st_res_<GOOD>_last_net = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_last_delta }
		value = var:st_res_<GOOD>_last_delta
	}
}
```

---

## File 6: `common/scripted_triggers/st_res_triggers.txt` (unlock trigger)

The single source of truth for "is this good available yet". The scripted GUI reads it and the widget row's visibility flows from there — **never duplicate the tech condition anywhere else.**

```
st_res_<GOOD>_unlocked_trigger = {
	has_technology_researched = <TECH>
}
```

No tech gate:

```
st_res_<GOOD>_unlocked_trigger = {
	always = yes
}
```

---

## File 7: `common/scripted_effects/st_res_effects.txt`

Most of the per-good work is now one line added to an existing `$GOOD$`-parameterized list. Only the wrapper effects are genuinely new.

### 7a. Add one line to each per-good call list

```
	st_res_init_good_effect          = { GOOD = <GOOD> }  # in st_res_init_effect
	st_res_reset_good_vars_effect    = { GOOD = <GOOD> }  # in st_res_reset_vars_effect
	st_res_startup_good_setup_effect = { GOOD = <GOOD> }  # in st_res_rebuild_hub_flow_modifiers_effect (country half)
	st_res_apply_weekly_good_effect  = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (hub branch)
	st_res_mark_good_no_hub_effect   = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (else branch)
	st_res_set_good_status_effect    = { GOOD = <GOOD> }  # at the END of st_res_refresh_hub_flow_effect
```

Inside the `random_scope_building = { limit = { is_building_type = building_strategic_reserve_hub } … }` block of `st_res_rebuild_hub_flow_modifiers_effect`:

```
			st_res_rebuild_<GOOD>_flow_modifiers_effect = yes
```

### 7b. Extend `st_res_clamp_stockpiles_effect` (one stored clamp + two rate clamps)

```
	clamp_variable = { name = st_res_<GOOD>_stored min = 0 max = st_res_<GOOD>_capacity }
```

```
	clamp_variable = { name = st_res_<GOOD>_rate min = st_res_neg_weekly_base_rate_cap max = st_res_weekly_base_rate_cap }
	clamp_variable = { name = st_res_<GOOD>_rate min = st_res_<GOOD>_max_withdrawable max = st_res_<GOOD>_max_storable }
```

### 7c. Extend `st_res_reset_rates_effect`

```
	set_variable = { name = st_res_<GOOD>_rate value = 0 }
```

### 7d. Extend `st_res_refresh_hub_flow_effect` (the cached actual-rate writes)

Must come **before** the `st_res_set_good_status_effect` calls — the status derivation reads this cached value to detect flow-cap clipping.

```
	set_variable = { name = st_res_<GOOD>_actual_rate_cached value = st_res_<GOOD>_actual_rate }
```

### 7e. Extend `st_res_apply_sell_profit_effect`

```
	change_variable = { name = st_res_sell_profit add = st_res_<GOOD>_sale_profit }
```

### 7f. New wrapper effects (four one-liners per good)

```
st_res_rebuild_<GOOD>_flow_modifiers_effect = {
	st_res_rebuild_good_flow_modifiers_effect = { GOOD = <GOOD> }
}
```

```
st_res_increase_<GOOD>_rate_effect  = { st_res_increase_rate_base = { GOOD = <GOOD> } }
st_res_decrease_<GOOD>_rate_effect  = { st_res_decrease_rate_base = { GOOD = <GOOD> } }
st_res_stop_<GOOD>_rate_effect      = { st_res_stop_rate_base     = { GOOD = <GOOD> } }
```

---

## File 8: `common/scripted_guis/st_res_scripted_gui.txt`

One scripted GUI per good. The three row controls share it and pass the action in a `dir` saved scope. **The `dir` mapping is an implicit contract with the widget — `0` decrease, `1` stop, `2` increase.** Player-only, matching the `ai_chance = { value = 0 }` that every Strategic Reserve button has always carried.

The `custom_tooltip` texts are phrased as **conditions**, not complaints: `ScriptedGui.IsValidTooltip` renders them with a tick when valid and a cross when not.

```
st_res_adjust_<GOOD>_sgui = {
	scope = country
	saved_scopes = { dir }

	is_shown = {
		has_journal_entry = je_strategic_reserve
		st_res_<GOOD>_unlocked_trigger = yes
	}

	ai_is_valid = {
		always = no
	}

	is_valid = {
		trigger_if = {
			limit = { scope:dir = 0 }
			custom_tooltip = {
				text = "st_res_rate_adjustment_possible"
				var:st_res_<GOOD>_rate > st_res_<GOOD>_max_withdrawable
				var:st_res_<GOOD>_rate > st_res_neg_weekly_base_rate_cap
			}
		}
		trigger_else_if = {
			limit = { scope:dir = 2 }
			custom_tooltip = {
				text = "st_res_rate_adjustment_possible"
				var:st_res_<GOOD>_rate < st_res_<GOOD>_max_storable
				var:st_res_<GOOD>_rate < st_res_weekly_base_rate_cap
			}
		}
		trigger_else = {
			custom_tooltip = {
				text = "st_res_rate_stop_possible"
				NOT = { var:st_res_<GOOD>_rate = 0 }
			}
		}
	}

	effect = {
		if = {
			limit = { scope:dir = 0 }
			st_res_decrease_<GOOD>_rate_effect = yes
		}
		else_if = {
			limit = { scope:dir = 2 }
			st_res_increase_<GOOD>_rate_effect = yes
		}
		else = {
			st_res_stop_<GOOD>_rate_effect = yes
		}
	}
}
```

---

## File 9: `common/customizable_localization/st_res_custom_loc.txt`

Two blocks per good, **both driven by `st_res_<GOOD>_last_status`** (written by `st_res_set_good_status_effect`). Never re-derive the state from rates or stockpiles here — that is exactly what makes the label and the bookkeeping drift apart.

Status codes: `0` Idle, `1` Storing, `2` Withdrawing, `3` Storing (flow-capped), `4` Withdrawing (flow-capped), `5` Full, `6` Empty, `7` Understaffed, `8` No hub.

Every branch is `has_variable`-guarded: customizable localization is evaluated for countries that never opened the journal entry.

```
st_res_<GOOD>_mode_text = {
	type = country
	random_valid = no

	text = {
		trigger = {
			has_variable = st_res_<GOOD>_last_status
			OR = {
				var:st_res_<GOOD>_last_status = 1
				var:st_res_<GOOD>_last_status = 3
			}
		}
		localization_key = st_res_mode_storing
	}
	text = {
		trigger = {
			has_variable = st_res_<GOOD>_last_status
			OR = {
				var:st_res_<GOOD>_last_status = 2
				var:st_res_<GOOD>_last_status = 4
			}
		}
		localization_key = st_res_mode_withdrawing
	}
	text = {
		trigger = {
			has_variable = st_res_<GOOD>_last_status
			var:st_res_<GOOD>_last_status >= 5
		}
		localization_key = st_res_mode_blocked
	}
	text = {
		trigger = { always = yes }
		localization_key = st_res_mode_idle
	}
}
```

```
st_res_<GOOD>_reason_text = {
	type = country
	random_valid = no

	text = {
		trigger = {
			has_variable = st_res_<GOOD>_last_status
			var:st_res_<GOOD>_last_status = 8
		}
		localization_key = st_res_reason_no_hub
	}
	# … repeat one block per code, highest first:
	#   7 -> st_res_reason_unstaffed          3 -> st_res_reason_cap_store
	#   6 -> st_res_reason_empty              2 -> st_res_reason_on_target_withdraw
	#   5 -> st_res_reason_full               1 -> st_res_reason_on_target_store
	#   4 -> st_res_reason_cap_withdraw
	text = {
		trigger = { always = yes }
		localization_key = st_res_reason_idle
	}
}
```

The nine `st_res_reason_*` and four `st_res_mode_*` keys are **shared across all goods** — they already exist, don't add new ones.

---

## File 10: `gui/journal_entry_widgets/strategic_reserve_widget.gui`

One row instance, appended to the root `widget_je_strategic_reserve_inventory` flowcontainer in the same order as the other goods. Nothing in the row `type` needs to change: the three control buttons read the inherited `ScriptedGui` datacontext, so they are identical for every good.

```
	widget_je_st_res_inventory_row = {
		datacontext = "[GetScriptedGui('st_res_adjust_<GOOD>_sgui')]"
		visible = "[ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'dir', MakeScopeValue( '(CFixedPoint)1' ) ).End )]"
		tooltip = "st_res_row_<GOOD>_tooltip"

		blockoverride "row_name" { text = "st_res_row_<GOOD>_name" }
		blockoverride "row_amount" { text = "st_res_row_<GOOD>_amount" }
		blockoverride "row_status" { text = "st_res_row_<GOOD>_status" }
		blockoverride "row_flow" { text = "st_res_row_<GOOD>_flow" }
		blockoverride "row_bar_value" {
			value = "[FixedPointToFloat(GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).ScriptValue('st_res_<GOOD>_fill_pct'))]"
		}
	}
```

**`.gui` files need a UTF-8 BOM** — `bom_normalizer` adds one on the next reload, but keep it if you rewrite the file wholesale.

---

## File 11: `common/journal_entries/je_strategic_reserve.txt`

**Nothing to add per good.** The journal entry no longer declares per-good progress bars, buttons or status lines — the widget covers all of it. Only update `je_strategic_reserve_desc` (below) so the good is named in the prose list.

---

## Localization templates

### te_modifiers_l_english.yml

```
 country_st_res_<GOOD>_capacity_add:0 "<GOOD_DISPLAY> Reserve Capacity"
 country_st_res_<GOOD>_capacity_add_desc:0 "Maximum <GOOD_DISPLAY lower> that can be held in the national strategic reserve."
 country_st_res_<GOOD>_decay_add:0 "<GOOD_DISPLAY> Reserve Decay"
 country_st_res_<GOOD>_decay_add_desc:0 "Fraction of the <GOOD_DISPLAY lower> stockpile lost to <REASON> per year."
```

`<REASON>` → "spoilage" for food, "corrosion and obsolescence" for arms, "airframe fatigue and obsolescence" for aeroplanes, "mechanical degradation and obsolescence" for tanks, etc. Match the existing voice.

### te_journal_entries_l_english.yml

No per-good key any more. Just update the prose list:

```
 je_strategic_reserve_desc:0 "Manage the national stockpile of grain, ammunition, oil, …, and <GOOD_DISPLAY lower>. …"
```

### te_miscellaneous_l_english.yml (widget row cells + flow modifier names)

All row expressions use `JournalEntry.GetCountry…`, **not** `ROOT…` — the widget's data context is the journal entry, not a scripted button.

```
 st_res_<GOOD>_store_flow:0 "Strategic Reserve <GOOD_DISPLAY> Intake"
 st_res_<GOOD>_withdraw_flow:0 "Strategic Reserve <GOOD_DISPLAY> Release"
 st_res_row_<GOOD>_name:0 "@<GOOD>! #bold <GOOD_DISPLAY>#!"
 st_res_row_<GOOD>_amount:0 "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_stored').GetValue|0] / [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_capacity')|0]"
 st_res_row_<GOOD>_status:0 "[JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_mode_text')]"
 st_res_row_<GOOD>_flow:0 "#bold [concept_st_res_rate_setting]:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|+0]  #bold Last wk:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_last_net')|+=1]/wk"
```

`@<GOOD>!` is the goods texticon — confirm it exists with `grep -n "icon = <GOOD>$" "$VIC3/game/gui/goods_texticons.gui"` (a mod-only good needs an entry in `gui/zzz_extra_goods_texticons.gui` instead).

### te_concepts_l_english.yml (row tooltip + flow modifier descs)

```
 st_res_<GOOD>_store_flow_desc:0 "This hub is purchasing <GOOD_DISPLAY lower> for the strategic reserve."
 st_res_<GOOD>_withdraw_flow_desc:0 "This hub is releasing <GOOD_DISPLAY lower> from the strategic reserve."
 st_res_row_<GOOD>_tooltip:0 "#header @<GOOD>! <GOOD_DISPLAY> Reserve#!\n#bold Stored:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_stored').GetValue|0] / [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_capacity')|0] ([JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_fill_pct')|1]%)\n#bold [concept_st_res_rate_setting]:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|+0] / week\n#bold [concept_st_res_active_rate]:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_actual_rate')|+1] / week\n#bold Net movement last week:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_last_net')|+=1] / week\n#bold Weekly decay:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_weekly_decay')|1] / week\n#bold Hub flow cap:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_weekly_base_rate_cap')|0] / week per good\n#bold Hub staffing:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_hub_staffing')|%0]\n\n#bold Status:#! [JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_mode_text')] — [JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_reason_text')]"
```

The three control-button tooltips (`st_res_row_decrease_tooltip`, `st_res_row_stop_tooltip`, `st_res_row_increase_tooltip`) are shared across all goods — they already exist.

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
