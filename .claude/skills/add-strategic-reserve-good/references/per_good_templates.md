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

### Main section (11 values)

`_annual_decay_rate` is the single derivation site for the good's decay: the weekly bookkeeping divides it by 52, and the widget row's *Decay: X%/yr* cell shows it as-is. It reads only a modifier, so it needs no `has_variable` guard.

```
# --- <GOOD_DISPLAY upper> ---
st_res_<GOOD>_annual_decay_rate = {
	value = 0
	add = modifier:country_st_res_<GOOD>_decay_add
	min = 0
}

st_res_<GOOD>_decay_rate = {
	value = st_res_<GOOD>_annual_decay_rate
	divide = 52 # convert from per-year to per-week decay
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

### Panel display values (three more, in the "Panel display values" group after the accessors)

Display only: the row's policy icon and the two markers on its fill bar. No script reads them. **Guard every read**, for the same every-frame reason as the accessors. `_disp_target` and `_disp_floor` must use the same policy codes the evaluator does (target while the policy can buy, 1 and 3; protected while it can sell, 2 and 3), and sit at the bar's ends (100 / 0) otherwise, where the widget hides the marker. `test_strategic_reserve_layout.py` checks all three.

```
st_res_<GOOD>_disp_policy = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_policy }
		value = var:st_res_<GOOD>_policy
	}
}
```

```
st_res_<GOOD>_disp_target = {
	value = 100
	if = {
		limit = {
			has_variable = st_res_<GOOD>_policy
			has_variable = st_res_<GOOD>_ceil_pct
			OR = {
				var:st_res_<GOOD>_policy = 1
				var:st_res_<GOOD>_policy = 3
			}
		}
		value = var:st_res_<GOOD>_ceil_pct
	}
}
st_res_<GOOD>_disp_floor = {
	value = 0
	if = {
		limit = {
			has_variable = st_res_<GOOD>_policy
			has_variable = st_res_<GOOD>_floor_pct
			OR = {
				var:st_res_<GOOD>_policy = 2
				var:st_res_<GOOD>_policy = 3
			}
		}
		value = var:st_res_<GOOD>_floor_pct
	}
}
```

---

### Reserve-policy values (ten more, appended after the main section)

These back the price-triggered policies. `_price_rel` is the signed premium against base price on the country's own market; do **not** collapse it into a bare `market_goods_pricier` read — the double `min = 0` construction is what keeps it correct whether the engine clamps `pricier`/`cheaper` at zero or returns them as signed mirrors. `_price_signal` is what the evaluator and the widget actually read: the running average kept by `st_res_policy_track_price_effect`, falling back to the live price until the first weekly tick seeds it. The four `_limit` values exist because a Paradox trigger needs a `var:` on its left side, so the sgui cannot compare a gap script value to a constant directly. `_policy_budget_max` is per-good because the budget stepper's ceiling is priced in that good: a full week at the shared flow ceiling, decay replacement included, at today's price.

```
# --- <GOOD_DISPLAY upper> ---
st_res_<GOOD>_price_up = {
	value = 0
	market = {
		mg:<GOOD> = {
			add = market_goods_pricier
		}
	}
	min = 0
}

st_res_<GOOD>_price_down = {
	value = 0
	market = {
		mg:<GOOD> = {
			add = market_goods_cheaper
		}
	}
	min = 0
}

# Signed premium against base price, as a fraction (+0.20 = 20% above base).
st_res_<GOOD>_price_rel = {
	value = st_res_<GOOD>_price_up
	subtract = st_res_<GOOD>_price_down
}

# The price signal the policies act on, in percentage points: the running
# average, or the live price until the first weekly tick has seeded it.
# `has_variable`-guarded because the inventory widget reads it every frame.
st_res_<GOOD>_price_signal = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_price_avg }
		add = var:st_res_<GOOD>_price_avg
	}
	else = {
		add = st_res_<GOOD>_price_rel
		multiply = 100
	}
}

# Current market price of one unit, in GBP. `min = 1` keeps the budget division safe.
st_res_<GOOD>_unit_price = {
	value = 1
	g:<GOOD> = {
		multiply = base_price
	}
	multiply = {
		value = 1
		add = st_res_<GOOD>_price_rel
	}
	min = 1
}

st_res_<GOOD>_policy_buy_up_limit = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_sell_thr }
		add = var:st_res_<GOOD>_sell_thr
	}
	subtract = st_res_policy_min_gap
	subtract = st_res_policy_thr_step
}

st_res_<GOOD>_policy_sell_down_limit = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_buy_thr }
		add = var:st_res_<GOOD>_buy_thr
	}
	add = st_res_policy_min_gap
	add = st_res_policy_thr_step
}

st_res_<GOOD>_policy_floor_up_limit = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_ceil_pct }
		add = var:st_res_<GOOD>_ceil_pct
	}
	subtract = st_res_policy_stock_min_gap
	subtract = st_res_policy_pct_step
}

st_res_<GOOD>_policy_ceil_down_limit = {
	value = 0
	if = {
		limit = { has_variable = st_res_<GOOD>_floor_pct }
		add = var:st_res_<GOOD>_floor_pct
	}
	add = st_res_policy_stock_min_gap
	add = st_res_policy_pct_step
}

st_res_<GOOD>_policy_budget_max = {
	value = st_res_policy_flow_max
	add = st_res_<GOOD>_weekly_decay
	multiply = st_res_<GOOD>_unit_price
	divide = st_res_policy_budget_step
	ceiling = yes
	multiply = st_res_policy_budget_step
	min = st_res_policy_budget_max_base
}
```

The shared `st_res_policy_*` constants at the bottom of the file are **not** per-good — don't touch them when adding a good.

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

Also add the good's line to `st_res_reserve_filling_up` further down the same file, the silo's AI storage signal:

```
		st_res_<GOOD>_fill_pct >= 75
```

---

## File 7: `common/scripted_effects/st_res_effects.txt`

Most of the per-good work is now one line added to an existing `$GOOD$`-parameterized list. Only the wrapper effects are genuinely new.

### 7a. Add one line to each per-good call list

```
	st_res_init_good_effect          = { GOOD = <GOOD> }  # in st_res_init_effect
	st_res_reset_good_vars_effect    = { GOOD = <GOOD> }  # in st_res_reset_vars_effect
	st_res_startup_good_setup_effect = { GOOD = <GOOD> }  # in st_res_rebuild_hub_flow_modifiers_effect (country half)
	st_res_refresh_preset_magnitudes_effect = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (hub branch, BEFORE the apply loop)
	st_res_apply_weekly_good_effect  = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (hub branch)
	st_res_policy_tick_good_effect = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (hub branch, AFTER the apply loop)
	st_res_mark_good_no_hub_effect   = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (else branch)
	st_res_policy_tick_good_effect = { GOOD = <GOOD> }  # in st_res_weekly_update_effect (else branch too — see below)
	st_res_set_good_status_effect    = { GOOD = <GOOD> }  # at the END of st_res_refresh_hub_flow_effect
	st_res_switch_to_manual_base     = { GOOD = <GOOD> }  # in st_res_reset_rates_effect
	st_res_ai_seed_good_effect       = { GOOD = <GOOD> POLICY = 3 }  # in st_res_ai_seed_policies_effect; every good is on Stabilize Prices
```

`st_res_policy_tick_good_effect` goes in **both** branches of the weekly pulse. That is not redundancy: it advances the good's running price average and then runs `st_res_policy_evaluate_good_effect`, the single derivation site for `st_res_<GOOD>_policy_status`, whose no-hub branch is what writes status 9. Drop the else-branch call and a policy's explanation goes stale the moment the hub is destroyed. Never call the tick from a click path — the price average must advance once a week, not once per click.

Its position in the hub branch matters too — after `st_res_apply_weekly_good_effect` (so last week's movement is booked first) and before the shared `st_res_refresh_hub_flow_effect` / `st_res_clamp_stockpiles_effect` tail (so the rate it picks is the one the hub trades on next week). The tail still runs **once**, not once per good.

For `st_res_ai_seed_good_effect`, pick the AI's policy: `3` (Stabilize Prices) for a civilian good whose price the AI should smooth, `1` (Buy When Cheap) for war materiel. Grain and `fertilizer` (Chemicals) are the only `3`s today.

The twelve per-good policy settings need **no** new init code — `st_res_init_good_effect` seeds them behind its two `has_variable` guards, and `st_res_reset_good_vars_effect` resets them (and removes the running price average so it re-seeds from the live price), all already `$GOOD$`-parameterized.

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

### 7g. The good's history series (`common/scripted_effects/te_history_strategic_reserve_effects.txt`)

One block in `te_history_record_strategic_reserve_samples`, after the other goods', gated on the good's unlock trigger like them. It records the good's fill (0–100) once a month from the journal entry's `on_monthly_pulse`, for the chart in its expanded row.

```
		if = {
			limit = { st_res_<GOOD>_unlocked_trigger = yes }
			te_history_record_sample = { METRIC = st_res_<GOOD> VALUE = st_res_<GOOD>_fill_pct }
		}
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

### The policy scripted GUI (second sgui per good)

A good also needs an `st_res_policy_<GOOD>_sgui`, in the lower half of the same file. It is long but entirely mechanical: **copy the `st_res_policy_grain_sgui` block and replace every `grain` with `<GOOD>`.** Nothing else changes — the op codes are identical for every good, and the file header carries the op-code table.

Do not hand-write it from the table; the `is_valid` chain has twenty-four branches and the relative-bound branches (ops 21, 22, 27, 28) reference that good's `_policy_*_limit` script values and the budget branches (ops 31, 51, 71 in `is_valid`; 30/31, 50/51, 70/71 in `effect`) its `_policy_budget_max`, which is exactly where a hand copy goes wrong.

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

### Policy custom loc (two more blocks)

`st_res_<GOOD>_policy_text` (4 branches on `st_res_<GOOD>_policy`) and `st_res_<GOOD>_policy_reason_text` (10 branches on `st_res_<GOOD>_policy_status`). Copy the grain pair and swap the good name; every branch keeps its `has_variable` guard for the same reason the existing pair does. The `localization_key` values are shared across goods — no new loc keys are needed for these two.

---

## File 10: `gui/journal_entry_widgets/strategic_reserve_widget.gui`

One `te_st_res_good_row` instance, added inside the `te_st_res_sec_inventory` type after the other goods' rows, in the order of `st_res_triggers.txt`. **Copy an existing good's row and swap the good's name; nothing else changes.** `test_strategic_reserve_layout.py` fails if any row differs from the first beyond the good's name, if the rows are out of order, or if a row reads a script value, scripted GUI or loc key that does not exist. No `type` needs to change: the three rate buttons read the inherited `ScriptedGui` datacontext, and the policy panel's op codes are the same for every good.

```
	te_st_res_good_row = {
		datacontext = "[GetScriptedGui('st_res_adjust_<GOOD>_sgui')]"
		visible = "[ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'dir', MakeScopeValue( '(CFixedPoint)1' ) ).End )]"
		tooltip = "st_res_row_<GOOD>_tooltip"

		blockoverride "row_toggle" {
			onclick = "[GetVariableSystem.Toggle('st_res_row_<GOOD>_open')]"
			tooltip = "st_res_row_collapse_tooltip"
		}
		blockoverride "row_open" {
			visible = "[GetVariableSystem.Exists('st_res_row_<GOOD>_open')]"
		}
		blockoverride "row_closed" {
			visible = "[Not(GetVariableSystem.Exists('st_res_row_<GOOD>_open'))]"
		}
		blockoverride "row_name" { text = "st_res_row_<GOOD>_name" }
		blockoverride "row_status" { text = "st_res_row_<GOOD>_status" }
		blockoverride "row_fill" {
			value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_fill_pct') )]"
		}
		blockoverride "row_target_marker" {
			visible = "[LessThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_disp_target'), '(CFixedPoint)100' )]"
			value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_disp_target') )]"
		}
		blockoverride "row_floor_marker" {
			visible = "[GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_disp_floor'), '(CFixedPoint)0' )]"
			value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_disp_floor') )]"
		}
		blockoverride "row_auto" {
			visible = "[GreaterThan_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_disp_policy'), '(CFixedPoint)0' )]"
		}
		blockoverride "row_stored" { text = "st_res_row_<GOOD>_amount" }
		blockoverride "row_rate" { text = "st_res_row_<GOOD>_flow" }
		blockoverride "row_last" { text = "st_res_row_<GOOD>_last" }
		blockoverride "row_decay" { text = "st_res_row_<GOOD>_decay" }
		blockoverride "row_price" { text = "st_res_row_<GOOD>_price" }
		blockoverride "row_policy" { text = "st_res_row_<GOOD>_policy" }
		blockoverride "row_policy_reason" { text = "st_res_row_<GOOD>_policy_reason" }
		blockoverride "row_history" {
			te_history_chart = {
				blockoverride "chart_title" {
					text = "st_res_hist_title"
				}
				blockoverride "chart_legend" {
					text = "st_res_hist_legend"
				}
				blockoverride "marker_pips" {}
				blockoverride "bar_tooltip" {
					tooltip = "st_res_hist_tt_<GOOD>"
				}
				blockoverride "bar_body" {
					te_history_bar_unsigned = {
						visible = "[ScriptContainer.HasVariable( 'te_hist_v_st_res_<GOOD>' )]"
						blockoverride "values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)2', ScriptContainer.GetVariableValue( 'te_hist_v_st_res_<GOOD>' ) ) )]"
						}
						blockoverride "cover_values" {
							min = 0
							max = 100
							value = "[FixedPointToFloat( Max_CFixedPoint( '(CFixedPoint)0', Subtract_CFixedPoint( ScriptContainer.GetVariableValue( 'te_hist_v_st_res_<GOOD>' ), '(CFixedPoint)4' ) ) )]"
						}
					}
				}
			}
		}
		blockoverride "row_settings_toggle" {
			onclick = "[GetVariableSystem.Toggle('st_res_policy_<GOOD>_open')]"
		}
		blockoverride "row_settings_open" {
			visible = "[GetVariableSystem.Exists('st_res_policy_<GOOD>_open')]"
		}
		blockoverride "row_settings_closed" {
			visible = "[Not(GetVariableSystem.Exists('st_res_policy_<GOOD>_open'))]"
		}
		blockoverride "row_settings_shown" {
			visible = "[Or( GetVariableSystem.Exists('st_res_row_<GOOD>_open'), GetVariableSystem.Exists('st_res_policy_<GOOD>_open') )]"
		}
		blockoverride "row_policy_panel" {
			widget_je_st_res_policy_panel = {
				blockoverride "policy_panel_context" {
					datacontext = "[GetScriptedGui('st_res_policy_<GOOD>_sgui')]"
				}
				blockoverride "policy_value_buy_thr" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_buy_thr').GetValue|+0]"
				}
				blockoverride "policy_value_sell_thr" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_sell_thr').GetValue|+0]"
				}
				blockoverride "policy_value_max_flow" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_max_flow').GetValue|0]"
				}
				blockoverride "policy_value_floor_pct" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_floor_pct').GetValue|0]"
				}
				blockoverride "policy_value_ceil_pct" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_ceil_pct').GetValue|0]"
				}
				blockoverride "policy_value_budget" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_budget').GetValue|0]"
				}
				blockoverride "policy_value_price_memory" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_price_memory').GetValue|0]"
				}
				blockoverride "policy_value_ramp" {
					text = "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_ramp').GetValue|0]"
				}
			}
		}
	}
```

What each part does:

- `row_toggle` / `row_open` / `row_closed` share one GUI-only key, `st_res_row_<GOOD>_open`: clicking the good's name shows or hides its figures and Policy Settings, and swaps the chevron beside the name. The key is absent until the first click, so a new good's row starts collapsed like the others. `st_res_row_collapse_tooltip` is shared.
- `row_fill` drives the fill bar; `row_target_marker` / `row_floor_marker` place the two markers and hide each at its end of the bar (the display values above put it there when the policy does not use that bound).
- `row_auto` shows the lit policy icon over the always-drawn dimmed one.
- `row_stored` … `row_policy_reason` are the expanded figures, one loc key each (file 14).
- `row_history` is the good's fill-by-month chart (`te_history_chart`, shown inside the expanded row): its bars read `te_hist_v_st_res_<GOOD>`, which `te_history_record_strategic_reserve_samples` records (file 7g), and its bar tooltip is `st_res_hist_tt_<GOOD>` (file 14). The tooltip key may read only `ScriptContainer` (gotcha #24; `test_history_chart_tooltip_context.py`).
- `row_settings_toggle` / `row_settings_open` / `row_settings_closed` share `st_res_policy_<GOOD>_open`, the Policy Settings subsection, collapsed until opened. `row_settings_toggle` is also the policy icon's click, so the icon opens the settings from the table line; `row_settings_shown` shows the subsection under an expanded row, or under a collapsed one while it is open.
- `row_policy_panel` nests the shared `widget_je_st_res_policy_panel` with the good's `st_res_policy_<GOOD>_sgui` as its datacontext and its eight value cells. The value cells put their data function inline in `text` rather than behind a loc key, which is why adding a good needs no per-setting localization.

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
 st_res_row_<GOOD>_status:0 "[JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_mode_text')]"
 st_res_row_<GOOD>_amount:0 "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_stored').GetValue|0] / [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_capacity')|0] ([JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_fill_pct')|0]%)"
 st_res_row_<GOOD>_flow:0 "[JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|+0]/wk"
 st_res_row_<GOOD>_last:0 "[JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_last_net')|+=1]/wk"
 st_res_row_<GOOD>_decay:0 "[JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_annual_decay_rate')|%1]/yr ([JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_weekly_decay')|1]/wk)"
 st_res_row_<GOOD>_tooltip:0 "#header @<GOOD>! <GOOD_DISPLAY> Reserve#!\n#bold Stored:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_stored').GetValue|0] / [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_capacity')|0] ([JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_fill_pct')|1]%)\n#bold [concept_st_res_rate_setting]:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_rate').GetValue|+0] / week\n#bold [concept_st_res_active_rate]:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_actual_rate')|+1] / week\n#bold Net movement last week:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_last_net')|+=1] / week\n#bold Decay rate:#! [JournalEntry.GetCountry.GetModifier.GetValueWithBreakdownFor('country_st_res_<GOOD>_decay_add')] of the stockpile per year\n#bold Weekly decay:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_weekly_decay')|1] / week\n#bold Hub flow cap:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_weekly_base_rate_cap')|0] / week per good\n#bold Hub staffing:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_hub_staffing')|%0]\n\n#bold Status:#! [JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_mode_text')] — [JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_reason_text')]\n\n#bold Reserve policy:#! [JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_policy_text')]\n[JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_policy_reason_text')]\n#bold National market price:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_price_rel')|%0] against base price (this is the market the hub's purchases and sales clear on)\n#bold Averaged price:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_price_signal')|+0]% against base ([JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_price_memory').GetValue|0]-week average — the figure the policy acts on)\n#bold Response ramp:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_ramp').GetValue|0] points past each threshold (0 = full flow at the threshold)\n#bold Price signal at the last review:#! [JournalEntry.GetCountry.MakeScope.Var('st_res_<GOOD>_policy_price').GetValue|+0]%\n\n#italic Click the good's name to expand this row for stock, flow, decay and policy details; click it again to collapse it.#!"
```

`amount`, `flow`, `last` and `decay` are **value cells** of the expanded row: the labels beside them (Stored, Rate Setting, Last Week, Decay) are shared keys (`st_res_row_label_*`), so these carry only the figure. `st_res_row_<GOOD>_decay`'s `%N` is per good: enough decimals to show the good's finest decay step, and no more. Grain moves in 5 pp steps (`%0`), oil and Chemicals in 0.05–0.25 pp steps (`%2`), everything else in 0.1–0.7 pp steps (`%1`, as above). Too few decimals and a tech's cut rounds away on the row. The row tooltip's *Decay rate* line carries the exact figure with a hoverable per-source breakdown.

`@<GOOD>!` is the goods texticon — confirm it exists with `grep -n "icon = <GOOD>$" "$VIC3/game/gui/goods_texticons.gui"` (a mod-only good needs an entry in `gui/zzz_extra_goods_texticons.gui` instead).

### te_miscellaneous_l_english.yml — policy row cells (three more keys)

```
 st_res_row_<GOOD>_price:0 "[JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_price_rel')|%0] (averaged [JournalEntry.GetCountry.MakeScope.ScriptValue('st_res_<GOOD>_price_signal')|+0]%)"
 st_res_row_<GOOD>_policy:0 "[JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_policy_text')]"
 st_res_row_<GOOD>_policy_reason:0 "[JournalEntry.GetCountry.GetCustom('st_res_<GOOD>_policy_reason_text')]"
```

`price` and `policy` are value cells like `amount` (labels Market Price and Reserve Policy); `policy_reason` is the line under the figures.

### te_miscellaneous_l_english.yml — the history chart's bar tooltip (two more keys)

```
 st_res_hist_tt_<GOOD>:0 "$te_hist_tt_date$\n[SelectLocalization( ScriptContainer.HasVariable('te_hist_v_st_res_<GOOD>'), 'st_res_hist_tt_<GOOD>_row', 'te_hist_tt_missing' )]"
 st_res_hist_tt_<GOOD>_row:0 "Filled: #v [ScriptContainer.GetVariableValue('te_hist_v_st_res_<GOOD>')|0]%#!"
```

A bar tooltip renders with only the month's `ScriptContainer` as its context, so these must not read `JournalEntry` (gui_modding_guide.md gotcha #24). The chart's title and legend (`st_res_hist_title`, `st_res_hist_legend`) are shared.

Everything else the policy panel shows — policy names, preset names, settings labels, all the tooltips and all ten explanations — is shared across goods and already exists.

---

### te_concepts_l_english.yml (flow modifier descs)

```
 st_res_<GOOD>_store_flow_desc:0 "This hub is purchasing <GOOD_DISPLAY lower> for the strategic reserve."
 st_res_<GOOD>_withdraw_flow_desc:0 "This hub is releasing <GOOD_DISPLAY lower> from the strategic reserve."
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
