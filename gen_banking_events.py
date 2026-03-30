"""
Generate 25 new banking cycle events (events 21-45), their modifiers,
scripted-effect entries, and localization.

Writes patches/appends to existing mod files.
Run: python gen_banking_events.py
"""

import os, sys

# Path constants
MOD = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(MOD, "events", "banking_cycle_events.txt")
MODIFIERS_FILE = os.path.join(MOD, "common", "static_modifiers", "extra_modifiers.txt")
EFFECTS_FILE = os.path.join(MOD, "common", "scripted_effects", "banking_cycle_effects.txt")
EVENTS_LOC = os.path.join(MOD, "localization", "english", "te_events_l_english.yml")
MISC_LOC = os.path.join(MOD, "localization", "english", "te_miscellaneous_l_english.yml")
JE_LOC_FILE = os.path.join(MOD, "localization", "english", "aaaaa_extra_l_english.yml")

# ============================================================================
# NEW EVENTS 21-45
# ============================================================================

EVENTS = r"""

# ============================================================================
# NEW BANKING CYCLE EVENTS 21-45
# Added to increase variety across all cycle phases and tech eras.
# ============================================================================


# ==========================================================================
# EARLY ERA ADDITIONS (no extra tech beyond stock_exchange)
# ==========================================================================

# --------------------------------------------------------------------------
# 21. Merchant Bank Prosperity
# Fires during stable/expansion. A respected merchant bank reports
# record profits, boosting confidence in the financial sector.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.21 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.21.t
	desc = banking_cycle_events.21.d
	flavor = banking_cycle_events.21.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.21.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		add_modifier = {
			name = banking_event_merchant_prosperity
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 60
		}
	}

	option = {
		name = banking_cycle_events.21.b
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		add_loyalists = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 40
		}
	}
}

# --------------------------------------------------------------------------
# 22. New Provincial Exchange
# Fires during expansion+. A provincial city opens its own stock exchange.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.22 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.22.t
	desc = banking_cycle_events.22.d
	flavor = banking_cycle_events.22.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.22.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_4_DESC"
			change_variable = { name = bubble_pressure add = 4 }
		}
		add_modifier = {
			name = banking_event_provincial_exchange
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.22.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 23. Banking Scandal
# Fires in any phase. A prominent banker is caught embezzling.
# NEGATIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.23 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.23.t
	desc = banking_cycle_events.23.d
	flavor = banking_cycle_events.23.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.23.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		add_modifier = {
			name = banking_event_scandal_fallout
			days = short_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			strata = lower
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.23.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_5_DESC"
			change_variable = { name = finance_cycle_value add = -5 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 24. Warehouse Receipts Fraud
# Fires during expansion/boom/frenzy with bubble >= 20.
# Fraudulent warehouse receipts circulate in the lending market.
# NEGATIVE, 3 options
# --------------------------------------------------------------------------
banking_cycle_events.24 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.24.t
	desc = banking_cycle_events.24.d
	flavor = banking_cycle_events.24.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.24.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_5_DESC"
			change_variable = { name = finance_cycle_value add = -5 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_8_DESC"
			change_variable = { name = bubble_pressure add = -8 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_2_DESC"
			change_variable = { name = finance_cycle_momentum add = -2 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
			modifier = { add = 15 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.24.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.24.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_5_DESC"
			change_variable = { name = bubble_pressure add = 5 }
		}
		ai_chance = {
			base = 20
		}
	}
}

# --------------------------------------------------------------------------
# 25. Trade Bill Innovation
# Fires during stable+, not at war. New instruments improve commerce.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.25 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.25.t
	desc = banking_cycle_events.25.d
	flavor = banking_cycle_events.25.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.25.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		add_modifier = {
			name = banking_event_trade_bills
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 60
		}
	}

	option = {
		name = banking_cycle_events.25.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		add_modifier = {
			name = banking_event_trade_bills
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 40
		}
	}
}


# ==========================================================================
# MID ERA ADDITIONS (central_banking / investment_banks / mutual_funds)
# ==========================================================================

# --------------------------------------------------------------------------
# 26. Pension Fund Growth
# Fires during expansion+. Requires mutual_funds.
# Growing pension funds provide stable, long-term capital.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.26 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.26.t
	desc = banking_cycle_events.26.d
	flavor = banking_cycle_events.26.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.26.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_pension_stability
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.26.b
		custom_tooltip = {
			text = "CYCLE_VALUE_5_DESC"
			change_variable = { name = finance_cycle_value add = 5 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_4_DESC"
			change_variable = { name = bubble_pressure add = 4 }
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
			modifier = { add = -15 banking_cycle_bubble_risk_high = yes }
		}
	}
}

# --------------------------------------------------------------------------
# 27. Telegraph Banking Revolution
# Fires during expansion+. Requires central_banking.
# Telegraph enables faster interbank settlements and arbitrage.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.27 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.27.t
	desc = banking_cycle_events.27.d
	flavor = banking_cycle_events.27.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.27.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		add_modifier = {
			name = banking_event_telegraph_settlement
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.27.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 28. Interbank Lending Freeze
# Fires during stagnation/downturn. Requires central_banking.
# Banks refuse to lend to each other, threatening a liquidity crisis.
# NEGATIVE, COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.28 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.28.t
	desc = banking_cycle_events.28.d
	flavor = banking_cycle_events.28.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.28.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_5_DESC"
			change_variable = { name = finance_cycle_value add = -5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_2_DESC"
			change_variable = { name = finance_cycle_momentum add = -2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_5_DESC"
			change_variable = { name = bubble_pressure add = -5 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 30
		}
	}

	option = {
		name = banking_cycle_events.28.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_interbank_guarantee
			multiplier = banking_event_expense_medium
			days = short_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 45
		}
	}

	option = {
		name = banking_cycle_events.28.c
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_6_DESC"
			change_variable = { name = bubble_pressure add = 6 }
		}
		ai_chance = {
			base = 25
		}
	}
}

# --------------------------------------------------------------------------
# 29. Agricultural Cooperative Banking
# Fires during stable+. Requires central_banking.
# Rural cooperatives pool savings to form lending institutions.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.29 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.29.t
	desc = banking_cycle_events.29.d
	flavor = banking_cycle_events.29.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.29.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_cooperative_growth
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = very_small_radicals
			strata = lower
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.29.b
		custom_tooltip = {
			text = "CYCLE_VALUE_5_DESC"
			change_variable = { name = finance_cycle_value add = 5 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		add_loyalists = {
			value = very_small_radicals
			strata = lower
		}
		add_loyalists = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 30. Foreign Debt Arbitrage
# Fires during expansion+. Requires investment_banks.
# Investors exploit interest rate differences between countries.
# MIXED, COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.30 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.30.t
	desc = banking_cycle_events.30.d
	flavor = banking_cycle_events.30.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.30.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_8_DESC"
			change_variable = { name = bubble_pressure add = 8 }
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 35
			modifier = { add = -25 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.30.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.30.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 25
			modifier = { add = 20 banking_cycle_bubble_risk_high = yes }
		}
	}
}

# --------------------------------------------------------------------------
# 31. Bank Holiday Proposal
# Fires during downturn/panic. Requires central_banking.
# Close all banks temporarily to halt a panic.
# COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.31 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.31.t
	desc = banking_cycle_events.31.d
	flavor = banking_cycle_events.31.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.31.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_5_DESC"
			change_variable = { name = finance_cycle_value add = 5 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_10_DESC"
			change_variable = { name = bubble_pressure add = -10 }
		}
		add_modifier = {
			name = banking_event_bank_holiday
			days = short_modifier_time
			is_decaying = yes
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 50
		}
	}

	option = {
		name = banking_cycle_events.31.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_8_DESC"
			change_variable = { name = finance_cycle_value add = -8 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_3_DESC"
			change_variable = { name = finance_cycle_momentum add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_5_DESC"
			change_variable = { name = bubble_pressure add = -5 }
		}
		add_radicals = {
			value = medium_radicals
			strata = lower
		}
		ai_chance = {
			base = 30
		}
	}

	option = {
		name = banking_cycle_events.31.c
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		add_modifier = {
			name = banking_event_interbank_guarantee
			multiplier = banking_event_expense_small
			days = short_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 35
		}
	}
}

# --------------------------------------------------------------------------
# 32. Trust Company Failure
# Fires during boom/frenzy. Requires mutual_funds. RARE.
# A major trust company spectacularly collapses.
# NEGATIVE, COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.32 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.32.t
	desc = banking_cycle_events.32.d
	flavor = banking_cycle_events.32.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.32.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_8_DESC"
			change_variable = { name = finance_cycle_value add = -8 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_3_DESC"
			change_variable = { name = finance_cycle_momentum add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_10_DESC"
			change_variable = { name = bubble_pressure add = -10 }
		}
		add_modifier = {
			name = banking_event_trust_collapse
			days = normal_modifier_time
			is_decaying = yes
		}
		add_radicals = {
			value = medium_radicals
			strata = upper
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.32.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_5_DESC"
			change_variable = { name = bubble_pressure add = -5 }
		}
		add_modifier = {
			name = banking_event_interbank_guarantee
			multiplier = banking_event_expense_large
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.32.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_8_DESC"
			change_variable = { name = bubble_pressure add = 8 }
		}
		ai_chance = {
			base = 20
		}
	}
}

# --------------------------------------------------------------------------
# 33. Commercial Paper Market
# Fires during stable/expansion. Requires investment_banks.
# Short-term business lending instruments become popular.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.33 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.33.t
	desc = banking_cycle_events.33.d
	flavor = banking_cycle_events.33.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.33.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		add_modifier = {
			name = banking_event_commercial_paper
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.33.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_5_DESC"
			change_variable = { name = bubble_pressure add = 5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		add_modifier = {
			name = banking_event_commercial_paper
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
			modifier = { add = -15 banking_cycle_bubble_risk_high = yes }
		}
	}
}

# --------------------------------------------------------------------------
# 34. Deposit Insurance Debate
# Fires during stagnation+. Requires central_banking.
# Should the government guarantee ordinary deposits?
# MIXED, COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.34 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	title = banking_cycle_events.34.t
	desc = banking_cycle_events.34.d
	flavor = banking_cycle_events.34.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.34.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_5_DESC"
			change_variable = { name = bubble_pressure add = -5 }
		}
		add_modifier = {
			name = banking_event_deposit_insurance
			days = long_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			strata = lower
		}
		add_radicals = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
		}
	}

	option = {
		name = banking_cycle_events.34.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.34.c
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		add_modifier = {
			name = banking_event_deposit_insurance
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 35
		}
	}
}

# --------------------------------------------------------------------------
# 35. Joint-Stock Company Boom
# Fires during expansion+. Requires corporate_management.
# Joint-stock companies multiply, fueling investment.
# POSITIVE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.35 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.35.t
	desc = banking_cycle_events.35.d
	flavor = banking_cycle_events.35.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.35.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_6_DESC"
			change_variable = { name = bubble_pressure add = 6 }
		}
		add_modifier = {
			name = banking_event_joint_stock_boom
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 50
			modifier = { add = -20 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.35.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		ai_chance = {
			base = 50
			modifier = { add = 15 banking_cycle_bubble_risk_rising = yes }
		}
	}
}


# ==========================================================================
# LATE ERA ADDITIONS (keynesian / modern_financial / consumer_credit)
# ==========================================================================

# --------------------------------------------------------------------------
# 36. Fintech Disruption
# Fires during expansion+. Requires modern_financial_instruments.
# New technology firms challenge traditional banking.
# POSITIVE/MIXED (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.36 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_industry.dds"

	title = banking_cycle_events.36.t
	desc = banking_cycle_events.36.d
	flavor = banking_cycle_events.36.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.36.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_6_DESC"
			change_variable = { name = bubble_pressure add = 6 }
		}
		add_modifier = {
			name = banking_event_fintech_growth
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 40
			modifier = { add = -20 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.36.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.36.c
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		add_loyalists = {
			value = very_small_radicals
			strata = lower
		}
		ai_chance = {
			base = 20
		}
	}
}

# --------------------------------------------------------------------------
# 37. Mortgage-Backed Securities
# Fires during boom/frenzy. Requires consumer_credit.
# Banks bundle mortgages into tradeable securities.
# MIXED/DANGEROUS (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.37 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.37.t
	desc = banking_cycle_events.37.d
	flavor = banking_cycle_events.37.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.37.a
		default_option = yes
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_12_DESC"
			change_variable = { name = bubble_pressure add = 12 }
		}
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		add_modifier = {
			name = banking_event_mbs_boom
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 30
			modifier = { add = -25 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.37.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_5_DESC"
			change_variable = { name = bubble_pressure add = 5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		ai_chance = {
			base = 45
		}
	}

	option = {
		name = banking_cycle_events.37.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_2_DESC"
			change_variable = { name = finance_cycle_momentum add = -2 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 25
			modifier = { add = 20 banking_cycle_bubble_risk_high = yes }
		}
	}
}

# --------------------------------------------------------------------------
# 38. Microfinance Initiative
# Fires during stable+. Requires keynesian_economics.
# Small loans to entrepreneurs and the urban poor.
# POSITIVE, SIMPLE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.38 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.38.t
	desc = banking_cycle_events.38.d
	flavor = banking_cycle_events.38.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.38.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_microfinance
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			strata = lower
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.38.b
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		add_loyalists = {
			value = very_small_radicals
			strata = lower
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 39. Quantitative Easing Debate
# Fires during downturn/panic. Requires keynesian_economics.
# The central bank proposes buying government bonds.
# COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.39 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	title = banking_cycle_events.39.t
	desc = banking_cycle_events.39.d
	flavor = banking_cycle_events.39.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.39.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_5_DESC"
			change_variable = { name = finance_cycle_value add = 5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_3_DESC"
			change_variable = { name = finance_cycle_momentum add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_8_DESC"
			change_variable = { name = bubble_pressure add = 8 }
		}
		add_modifier = {
			name = banking_event_qe_stimulus
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			strata = lower
		}
		ai_chance = {
			base = 45
			modifier = { add = 15 banking_cycle_is_panic = yes }
		}
	}

	option = {
		name = banking_cycle_events.39.b
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.39.c
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		add_radicals = {
			value = small_radicals
			strata = lower
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 20
		}
	}
}

# --------------------------------------------------------------------------
# 40. Credit Rating Agency Failure
# Fires during boom/frenzy. Requires modern_financial_instruments.
# Rating agencies gave top marks to worthless securities.
# NEGATIVE, COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.40 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.40.t
	desc = banking_cycle_events.40.d
	flavor = banking_cycle_events.40.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.40.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_5_DESC"
			change_variable = { name = finance_cycle_value add = -5 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_8_DESC"
			change_variable = { name = bubble_pressure add = -8 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_2_DESC"
			change_variable = { name = finance_cycle_momentum add = -2 }
		}
		add_modifier = {
			name = banking_event_rating_crackdown
			days = normal_modifier_time
			is_decaying = yes
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
		}
	}

	option = {
		name = banking_cycle_events.40.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.40.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_5_DESC"
			change_variable = { name = bubble_pressure add = 5 }
		}
		ai_chance = {
			base = 20
		}
	}
}

# --------------------------------------------------------------------------
# 41. Student Loan Burden
# Fires during expansion+. Requires consumer_credit.
# Rising education costs create a generation of indebted graduates.
# NEGATIVE (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.41 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_trade.dds"

	title = banking_cycle_events.41.t
	desc = banking_cycle_events.41.d
	flavor = banking_cycle_events.41.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.41.a
		default_option = yes
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_4_DESC"
			change_variable = { name = bubble_pressure add = 4 }
		}
		add_modifier = {
			name = banking_event_student_debt_relief
			days = normal_modifier_time
			is_decaying = yes
		}
		add_modifier = {
			name = banking_event_student_debt_relief_cost
			multiplier = banking_event_expense_small
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = small_radicals
			pop_type = academics
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.41.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		add_radicals = {
			value = small_radicals
			pop_type = academics
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.41.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		add_loyalists = {
			value = small_radicals
			pop_type = academics
		}
		ai_chance = {
			base = 25
		}
	}
}

# --------------------------------------------------------------------------
# 42. Green Bond Initiative
# Fires during stable+. Requires keynesian_economics.
# Bonds financing environmental and infrastructure projects.
# POSITIVE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.42 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_scales.dds"

	title = banking_cycle_events.42.t
	desc = banking_cycle_events.42.d
	flavor = banking_cycle_events.42.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.42.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_3_DESC"
			change_variable = { name = finance_cycle_value add = 3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_green_bonds
			days = normal_modifier_time
			is_decaying = yes
		}
		add_loyalists = {
			value = very_small_radicals
			pop_type = academics
		}
		ai_chance = {
			base = 55
		}
	}

	option = {
		name = banking_cycle_events.42.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_3_DESC"
			change_variable = { name = bubble_pressure add = 3 }
		}
		add_loyalists = {
			value = very_small_radicals
			strata = upper
		}
		ai_chance = {
			base = 45
		}
	}
}

# --------------------------------------------------------------------------
# 43. Venture Capital Boom
# Fires during expansion/boom. Requires modern_financial_instruments.
# Venture capital funds pour money into innovative new firms.
# POSITIVE (2 options)
# --------------------------------------------------------------------------
banking_cycle_events.43 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_industry.dds"

	title = banking_cycle_events.43.t
	desc = banking_cycle_events.43.d
	flavor = banking_cycle_events.43.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.43.a
		default_option = yes
		custom_tooltip = {
			text = "MOMENTUM_2_DESC"
			change_variable = { name = finance_cycle_momentum add = 2 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_6_DESC"
			change_variable = { name = bubble_pressure add = 6 }
		}
		add_modifier = {
			name = banking_event_venture_boom
			days = normal_modifier_time
			is_decaying = yes
		}
		ai_chance = {
			base = 50
			modifier = { add = -20 banking_cycle_bubble_risk_high = yes }
		}
	}

	option = {
		name = banking_cycle_events.43.b
		custom_tooltip = {
			text = "MOMENTUM_1_DESC"
			change_variable = { name = finance_cycle_momentum add = 1 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_2_DESC"
			change_variable = { name = bubble_pressure add = 2 }
		}
		ai_chance = {
			base = 50
			modifier = { add = 15 banking_cycle_bubble_risk_rising = yes }
		}
	}
}

# --------------------------------------------------------------------------
# 44. Predatory Lending Scandal
# Fires during boom/frenzy. Requires consumer_credit.
# Abusive lending practices targeting the poor exposed.
# NEGATIVE (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.44 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_fire.dds"

	title = banking_cycle_events.44.t
	desc = banking_cycle_events.44.d
	flavor = banking_cycle_events.44.f

	duration = 3
	is_popup = yes

	immediate = {
	}

	option = {
		name = banking_cycle_events.44.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_5_DESC"
			change_variable = { name = bubble_pressure add = -5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		add_modifier = {
			name = banking_event_predatory_crackdown
			days = normal_modifier_time
			is_decaying = yes
		}
		add_radicals = {
			value = small_radicals
			strata = upper
		}
		add_loyalists = {
			value = small_radicals
			strata = lower
		}
		ai_chance = {
			base = 50
		}
	}

	option = {
		name = banking_cycle_events.44.b
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_radicals = {
			value = small_radicals
			strata = lower
		}
		ai_chance = {
			base = 30
		}
	}

	option = {
		name = banking_cycle_events.44.c
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_4_DESC"
			change_variable = { name = bubble_pressure add = 4 }
		}
		add_radicals = {
			value = medium_radicals
			strata = lower
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 15
		}
	}
}

# --------------------------------------------------------------------------
# 45. International Bailout Request
# Fires during downturn/panic. Requires keynesian_economics.
# A trading partner asks for emergency financial assistance.
# COMPLEX (3 options)
# --------------------------------------------------------------------------
banking_cycle_events.45 = {
	type = country_event
	placement = root

	event_image = {
		texture = "gfx/event_pictures/stock_exchange.dds"
	}

	on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"
	icon = "gfx/interface/icons/event_icons/event_map.dds"

	title = banking_cycle_events.45.t
	desc = banking_cycle_events.45.d
	flavor = banking_cycle_events.45.f

	duration = 3
	is_popup = yes

	immediate = {
		random_country = {
			limit = {
				NOT = { this = root }
				has_diplomatic_relevance = root
			}
			save_scope_as = bailout_country
		}
	}

	option = {
		name = banking_cycle_events.45.a
		default_option = yes
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_3_DESC"
			change_variable = { name = bubble_pressure add = -3 }
		}
		add_modifier = {
			name = banking_event_bailout_cost
			multiplier = banking_event_expense_large
			days = normal_modifier_time
			is_decaying = yes
		}
		add_modifier = {
			name = banking_event_bailout_goodwill
			days = normal_modifier_time
			is_decaying = yes
		}
		if = {
			limit = { exists = scope:bailout_country }
			change_relations = {
				country = scope:bailout_country
				value = 30
			}
		}
		ai_chance = {
			base = 40
		}
	}

	option = {
		name = banking_cycle_events.45.b
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_3_DESC"
			change_variable = { name = finance_cycle_value add = -3 }
		}
		custom_tooltip = {
			text = "BUBBLE_PRESSURE_MINUS_2_DESC"
			change_variable = { name = bubble_pressure add = -2 }
		}
		add_modifier = {
			name = banking_event_bailout_cost
			multiplier = banking_event_expense_small
			days = short_modifier_time
			is_decaying = yes
		}
		if = {
			limit = { exists = scope:bailout_country }
			change_relations = {
				country = scope:bailout_country
				value = 10
			}
		}
		ai_chance = {
			base = 35
		}
	}

	option = {
		name = banking_cycle_events.45.c
		custom_tooltip = {
			text = "CYCLE_VALUE_MINUS_5_DESC"
			change_variable = { name = finance_cycle_value add = -5 }
		}
		custom_tooltip = {
			text = "MOMENTUM_MINUS_1_DESC"
			change_variable = { name = finance_cycle_momentum add = -1 }
		}
		if = {
			limit = { exists = scope:bailout_country }
			change_relations = {
				country = scope:bailout_country
				value = -20
			}
		}
		add_loyalists = {
			value = small_radicals
			strata = upper
		}
		ai_chance = {
			base = 25
		}
	}
}
"""

# ============================================================================
# NEW MODIFIERS
# ============================================================================

MODIFIERS = r"""
# --- New banking event modifiers (events 21-45) ---

banking_event_merchant_prosperity = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	goods_output_services_mult = 0.03
}

banking_event_provincial_exchange = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	state_trade_capacity_mult = 0.03
}

banking_event_scandal_fallout = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	goods_output_services_mult = -0.03
}

banking_event_trade_bills = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	state_trade_capacity_mult = 0.03
}

banking_event_pension_stability = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_loan_interest_rate_mult = -0.03
}

banking_event_telegraph_settlement = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	goods_output_services_mult = 0.03
}

banking_event_interbank_guarantee = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_expenses_add = 1
}

banking_event_cooperative_growth = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	building_group_bg_agriculture_throughput_add = 0.03
}

banking_event_bank_holiday = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	goods_output_services_mult = -0.05
}

banking_event_trust_collapse = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	goods_output_services_mult = -0.05
	country_loan_interest_rate_mult = 0.05
}

banking_event_commercial_paper = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	building_group_bg_manufacturing_throughput_add = 0.03
}

banking_event_deposit_insurance = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_loan_interest_rate_mult = -0.03
}

banking_event_joint_stock_boom = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	building_group_bg_manufacturing_throughput_add = 0.05
}

banking_event_fintech_growth = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	goods_output_services_mult = 0.03
	country_loan_interest_rate_mult = -0.03
}

banking_event_mbs_boom = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	building_group_bg_construction_throughput_add = 0.05
	goods_output_services_mult = 0.05
}

banking_event_microfinance = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	building_group_bg_agriculture_throughput_add = 0.03
	goods_output_services_mult = 0.02
}

banking_event_qe_stimulus = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_loan_interest_rate_mult = -0.05
}

banking_event_rating_crackdown = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	goods_output_services_mult = -0.05
	country_loan_interest_rate_mult = 0.05
}

banking_event_student_debt_relief = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_positive.dds
	country_prestige_mult = 0.03
}

banking_event_student_debt_relief_cost = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_expenses_add = 1
}

banking_event_green_bonds = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	building_group_bg_construction_throughput_add = 0.03
	country_prestige_mult = 0.03
}

banking_event_venture_boom = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_gear_positive.dds
	building_group_bg_manufacturing_throughput_add = 0.05
}

banking_event_predatory_crackdown = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_negative.dds
	goods_output_services_mult = -0.03
}

banking_event_bailout_cost = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_coins_negative.dds
	country_expenses_add = 1
}

banking_event_bailout_goodwill = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	country_prestige_mult = 0.05
}
"""

# ============================================================================
# SCRIPTED EFFECT ENTRIES (to be inserted into the random_list)
# ============================================================================

EFFECT_ENTRIES = r"""
			# ---- NEW EVENTS 21-45 ----

			# Event 21: Merchant Bank Prosperity (stable/expansion, no extra tech)
			0 = {
				modifier = {
					if = {
						limit = {
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
							}
						}
						add = 5
					}
				}
				trigger_event = { id = banking_cycle_events.21 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 22: New Provincial Exchange (expansion+, no extra tech)
			0 = {
				modifier = {
					if = {
						limit = {
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.22 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 23: Banking Scandal (any phase, no extra tech)
			0 = {
				modifier = {
					add = 4
				}
				trigger_event = { id = banking_cycle_events.23 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 24: Warehouse Receipts Fraud (expansion+, bubble >= 20)
			0 = {
				modifier = {
					if = {
						limit = {
							var:bubble_pressure >= 20
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.24 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 25: Trade Bill Innovation (stable+, not at war)
			0 = {
				modifier = {
					if = {
						limit = {
							is_at_war = no
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.25 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}

			# ---- MID ERA NEW EVENTS ----

			# Event 26: Pension Fund Growth (expansion+, mutual_funds)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = mutual_funds
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.26 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 27: Telegraph Banking Revolution (expansion+, central_banking)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = central_banking
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.27 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 28: Interbank Lending Freeze (stagnation/downturn, central_banking)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = central_banking
							OR = {
								banking_cycle_is_stagnation = yes
								banking_cycle_is_downturn = yes
							}
						}
						add = 5
					}
					if = { limit = { banking_cycle_is_downturn = yes } add = 3 }
				}
				trigger_event = { id = banking_cycle_events.28 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 29: Agricultural Cooperative Banking (stable+, central_banking)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = central_banking
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.29 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 30: Foreign Debt Arbitrage (expansion+, investment_banks)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = investment_banks
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
					if = { limit = { banking_cycle_is_frenzy = yes } add = 2 }
				}
				trigger_event = { id = banking_cycle_events.30 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 31: Bank Holiday Proposal (downturn/panic, central_banking)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = central_banking
							OR = {
								banking_cycle_is_downturn = yes
								banking_cycle_is_panic = yes
							}
						}
						add = 4
					}
					if = { limit = { banking_cycle_is_panic = yes } add = 3 }
				}
				trigger_event = { id = banking_cycle_events.31 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 32: Trust Company Failure (RARE, boom/frenzy, mutual_funds, bubble >= 30)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = mutual_funds
							OR = { banking_cycle_is_boom = yes banking_cycle_is_frenzy = yes }
							var:bubble_pressure >= 30
						}
						add = 2
					}
				}
				trigger_event = { id = banking_cycle_events.32 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 33: Commercial Paper Market (stable/expansion, investment_banks)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = investment_banks
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.33 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 34: Deposit Insurance Debate (stagnation+, central_banking)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = central_banking
							OR = {
								banking_cycle_is_stagnation = yes
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
							}
						}
						add = 3
					}
				}
				trigger_event = { id = banking_cycle_events.34 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 35: Joint-Stock Company Boom (expansion+, corporate_management)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = corporate_management
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.35 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}

			# ---- LATE ERA NEW EVENTS ----

			# Event 36: Fintech Disruption (expansion+, modern_financial_instruments)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = modern_financial_instruments
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.36 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 37: Mortgage-Backed Securities (boom/frenzy, consumer_credit)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = consumer_credit
							OR = { banking_cycle_is_boom = yes banking_cycle_is_frenzy = yes }
						}
						add = 3
					}
					if = { limit = { banking_cycle_is_frenzy = yes } add = 2 }
				}
				trigger_event = { id = banking_cycle_events.37 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 38: Microfinance Initiative (stable+, keynesian_economics)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = keynesian_economics
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.38 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 39: Quantitative Easing Debate (downturn/panic, keynesian_economics)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = keynesian_economics
							OR = {
								banking_cycle_is_downturn = yes
								banking_cycle_is_panic = yes
							}
						}
						add = 5
					}
					if = { limit = { banking_cycle_is_panic = yes } add = 3 }
				}
				trigger_event = { id = banking_cycle_events.39 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 40: Credit Rating Agency Failure (boom/frenzy, modern_financial_instruments)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = modern_financial_instruments
							OR = { banking_cycle_is_boom = yes banking_cycle_is_frenzy = yes }
						}
						add = 3
					}
				}
				trigger_event = { id = banking_cycle_events.40 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 41: Student Loan Burden (expansion+, consumer_credit)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = consumer_credit
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
								banking_cycle_is_frenzy = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.41 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 42: Green Bond Initiative (stable+, keynesian_economics)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = keynesian_economics
							OR = {
								banking_cycle_is_stable = yes
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 3
					}
				}
				trigger_event = { id = banking_cycle_events.42 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 43: Venture Capital Boom (expansion/boom, modern_financial_instruments)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = modern_financial_instruments
							OR = {
								banking_cycle_is_expansion = yes
								banking_cycle_is_boom = yes
							}
						}
						add = 4
					}
				}
				trigger_event = { id = banking_cycle_events.43 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 44: Predatory Lending Scandal (boom/frenzy, consumer_credit)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = consumer_credit
							OR = { banking_cycle_is_boom = yes banking_cycle_is_frenzy = yes }
						}
						add = 3
					}
				}
				trigger_event = { id = banking_cycle_events.44 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
			# Event 45: International Bailout Request (downturn/panic, keynesian_economics)
			0 = {
				modifier = {
					if = {
						limit = {
							has_technology_researched = keynesian_economics
							OR = {
								banking_cycle_is_downturn = yes
								banking_cycle_is_panic = yes
							}
						}
						add = 3
					}
				}
				trigger_event = { id = banking_cycle_events.45 }
				set_variable = { name = banking_event_cooldown value = 12 }
			}
"""

# ============================================================================
# LOCALIZATION
# ============================================================================

EVENT_LOC = r""" banking_cycle_events.21.a:0 "Splendid news!"
 banking_cycle_events.21.b:0 "Let us not get carried away"
 banking_cycle_events.21.d:0 "One of our most respected merchant banks has reported record profits for the quarter, far exceeding all expectations. The news has spread rapidly through the financial district, lifting confidence across the sector. Other banks are reporting healthy returns as well, and the mood among investors is buoyant."
 banking_cycle_events.21.f:0 "\"Did you see the Rothschild figures? Extraordinary.\"\n\n\"My own portfolio has never looked healthier. I believe we may be entering a golden age of finance.\"\n\n\"You said that last year.\"\n\n\"And I was right last year too.\""
 banking_cycle_events.21.t:0 "Merchant Bank Prosperity"
 banking_cycle_events.22.a:0 "The more exchanges, the better!"
 banking_cycle_events.22.b:0 "Require rigorous oversight first"
 banking_cycle_events.22.d:0 "A prosperous provincial city has petitioned to open its own stock exchange, arguing that the capital's bourse is too distant and too exclusive to serve regional investors. Local merchants and manufacturers are enthusiastic, seeing it as a way to raise capital without traveling to the metropolis. The proposal would broaden access to investment but could also fragment oversight."
 banking_cycle_events.22.f:0 "\"Why should all the money flow through one city? We have industry, we have capital, and we have ambition. What we lack is a trading floor.\"\n\n\"And regulation, apparently.\"\n\n\"Details.\""
 banking_cycle_events.22.t:0 "New Provincial Exchange"
 banking_cycle_events.23.a:0 "Prosecute to the fullest extent!"
 banking_cycle_events.23.b:0 "Let this serve as a warning"
 banking_cycle_events.23.d:0 "A scandal has erupted in the banking sector. A prominent banker has been caught diverting depositors' funds into personal speculative ventures. The scheme was discovered when a routine audit revealed massive discrepancies between the bank's reported reserves and its actual holdings. Public confidence in the banking system has been shaken."
 banking_cycle_events.23.f:0 "\"He lived like a prince on other people's savings. Three houses, a stable of racehorses, and a yacht - all purchased with money that was supposed to be sitting safely in the vault.\"\n\n\"And his depositors?\"\n\n\"Ruined, most of them.\""
 banking_cycle_events.23.t:0 "Banking Scandal"
 banking_cycle_events.24.a:0 "Root out the fraud!"
 banking_cycle_events.24.b:0 "Quietly contain the damage"
 banking_cycle_events.24.c:0 "Let the market sort it out"
 banking_cycle_events.24.d:0 "Investigators have discovered a network of fraudulent warehouse receipts circulating through the commodity lending market. Merchants have been borrowing against goods that don't exist - or pledging the same goods to multiple lenders. The extent of the fraud is unclear, but several banks have already frozen their commodity lending operations, and prices on the exchange are volatile."
 banking_cycle_events.24.f:0 "\"The warehouse was supposed to contain two thousand bales of cotton. When the inspectors opened the doors, they found three hundred bales and a great deal of empty space.\"\n\n\"And the receipts?\"\n\n\"Still circulating. Still being traded. Still being used as collateral.\""
 banking_cycle_events.24.t:0 "Warehouse Receipts Fraud"
 banking_cycle_events.25.a:0 "A welcome innovation"
 banking_cycle_events.25.b:0 "Seize on the opportunity"
 banking_cycle_events.25.d:0 "Merchant houses have developed a refined system of trade bills that allows goods to be bought and sold on credit with unprecedented ease. These new instruments enable commerce to flow more smoothly between distant cities, reducing the need for physical coin and expanding the volume of trade. Bankers are eager to discount these bills, seeing healthy profits in the growing market."
 banking_cycle_events.25.f:0 "\"A bill drawn in Liverpool, accepted in London, discounted in Amsterdam, and redeemed in New York. The world grows smaller with every signature.\""
 banking_cycle_events.25.t:0 "Trade Bill Innovation"
 banking_cycle_events.26.a:0 "A foundation of stability"
 banking_cycle_events.26.b:0 "Let them invest more aggressively"
 banking_cycle_events.26.d:0 "Pension funds established for workers in major industries have grown substantially, accumulating vast pools of long-term capital. Unlike speculative investors who chase quick returns, these funds seek steady, reliable income to meet future obligations. Their growing presence in the bond and property markets is providing a stabilizing counterweight to short-term speculation."
 banking_cycle_events.26.f:0 "\"The pension fund trustees are the dullest investors in the market. They buy bonds and hold them. They buy property and hold it. They are magnificently, beautifully boring.\"\n\n\"And magnificently, beautifully solvent.\""
 banking_cycle_events.26.t:0 "Pension Fund Growth"
 banking_cycle_events.27.a:0 "Connect every branch!"
 banking_cycle_events.27.b:0 "Proceed cautiously"
 banking_cycle_events.27.d:0 "The telegraph has revolutionized interbank communications. Settlement times that once took days or weeks now take hours. Banks can verify balances, confirm transactions, and coordinate lending across vast distances almost instantaneously. The speed has attracted new participants to the financial markets and increased trading volumes dramatically."
 banking_cycle_events.27.f:0 "\"Before the wire, it took a week to confirm a transfer from Edinburgh to London. Now it takes twenty minutes. The world has changed beyond recognition.\"\n\n\"And mistakes travel just as fast.\"\n\n\"Let us hope there are fewer of them.\""
 banking_cycle_events.27.t:0 "Modern Settlements"
 banking_cycle_events.28.a:0 "Let trust rebuild naturally"
 banking_cycle_events.28.b:0 "Guarantee interbank obligations"
 banking_cycle_events.28.c:0 "Force banks to resume lending"
 banking_cycle_events.28.d:0 "The interbank lending market has seized up. Banks that normally lend freely to one another overnight have stopped, each suspecting that its counterparties may be concealing losses. Without interbank lending, the entire financial system risks grinding to a halt - banks cannot meet daily obligations, businesses cannot access working capital, and the economy threatens to seize up like an engine without oil."
 banking_cycle_events.28.f:0 "\"The banks won't lend to each other because they don't trust each other. They don't trust each other because they know what's on their own balance sheets.\""
 banking_cycle_events.28.t:0 "Interbank Lending Freeze"
 banking_cycle_events.29.a:0 "Support the cooperatives"
 banking_cycle_events.29.b:0 "Let them attract private capital too"
 banking_cycle_events.29.d:0 "In the countryside, farmers and smallholders have begun pooling their savings into cooperative lending institutions. These modest banks, governed by their own depositors, provide credit for seed and equipment at rates far below what commercial banks charge. The model is spreading rapidly, bringing financial services to communities that have never had access to formal banking."
 banking_cycle_events.29.f:0 "\"We had nothing - no bank would touch us. Now we lend to ourselves, and not a penny has been lost.\"\n\n\"The commercial bankers scoff at the amounts involved.\"\n\n\"Let them scoff. We can feed our families.\""
 banking_cycle_events.29.t:0 "Cooperative Banking"
 banking_cycle_events.30.a:0 "Let profits flow!"
 banking_cycle_events.30.b:0 "Require hedging and disclosure"
 banking_cycle_events.30.c:0 "Restrict cross-border speculation"
 banking_cycle_events.30.d:0 "Sophisticated investors have discovered they can borrow cheaply in countries with low interest rates and invest the proceeds in countries offering higher returns. These so-called 'carry trades' are generating enormous profits for those who understand them, but they create hidden linkages between national financial systems. If exchange rates shift suddenly, the unraveling could be catastrophic."
 banking_cycle_events.30.f:0 "\"Borrow in Tokyo at one percent, invest in Buenos Aires at eight. The profit is almost effortless.\"\n\n\"And when the exchange rate moves?\"\n\n\"It won't.\"\n\n\"How can you be certain?\"\n\n\"Because if it does, we're all finished.\""
 banking_cycle_events.30.t:0 "Foreign Debt Arbitrage"
 banking_cycle_events.31.a:0 "Declare a bank holiday"
 banking_cycle_events.31.b:0 "Keep the banks open"
 banking_cycle_events.31.c:0 "Limited closure with emergency lending"
 banking_cycle_events.31.d:0 "With public confidence in the banking system collapsing, advisors are urging the government to declare a 'bank holiday' - a temporary, mandatory closure of all financial institutions. The idea is to stop the panic, allow time for inspection and reorganization, and reopen only those banks that are solvent. It's a drastic measure, but the alternative may be a complete meltdown."
 banking_cycle_events.31.f:0 "\"Close every bank in the country?\"\n\n\"For three days. Perhaps a week.\"\n\n\"The public will riot.\"\n\n\"The public is already rioting. At least this way, when we reopen, they'll have something left to withdraw.\""
 banking_cycle_events.31.t:0 "The Bank Holiday"
 banking_cycle_events.32.a:0 "Let the collapse run its course"
 banking_cycle_events.32.b:0 "Organize an emergency rescue"
 banking_cycle_events.32.c:0 "Minimize the news"
 banking_cycle_events.32.d:0 "One of the largest trust companies in the country has collapsed spectacularly, its assets frozen and its offices shuttered. The company had been investing depositors' funds in increasingly speculative ventures, and when several of those ventures failed simultaneously, the losses overwhelmed the company's reserves. Depositors' savings have evaporated, and other trust companies are now facing runs."
 banking_cycle_events.32.f:0 "\"The directors were seen leaving through the back entrance, carrying leather cases. The depositors were left at the front, carrying nothing.\""
 banking_cycle_events.32.t:0 "Trust Company Failure"
 banking_cycle_events.33.a:0 "Encourage the market"
 banking_cycle_events.33.b:0 "Maximize growth from this"
 banking_cycle_events.33.d:0 "A market for commercial paper - short-term promissory notes issued by businesses - has developed rapidly, allowing companies to borrow directly from investors without going through banks. The innovation reduces borrowing costs for creditworthy firms and provides investors with a safe, liquid asset. The market is growing quickly, adding a new pillar of stability to the financial system."
 banking_cycle_events.33.f:0 "\"Ninety-day notes, backed by the full credit of the issuing firm. Safe as houses, liquid as water, and yielding three percent.\"\n\n\"You make it sound too good to be true.\"\n\n\"That's because you've been listening to bankers, who are furious they're being cut out.\""
 banking_cycle_events.33.t:0 "Commercial Paper Market"
 banking_cycle_events.34.a:0 "Establish a full guarantee"
 banking_cycle_events.34.b:0 "The market disciplines itself"
 banking_cycle_events.34.c:0 "A limited guarantee only"
 banking_cycle_events.34.d:0 "After recent banking failures, a coalition of legislators is proposing a formal deposit insurance scheme - a government-backed guarantee that ordinary depositors will not lose their savings if their bank fails. Proponents argue it will prevent bank runs and stabilize the system. Critics warn it will encourage reckless lending by removing the consequences of failure."
 banking_cycle_events.34.f:0 "\"If the government guarantees deposits, why would any depositor ever bother to check whether their bank is sound?\"\n\n\"Because people don't check anyway. They trust the name on the door.\"\n\n\"Exactly. And now we propose to make that misplaced trust official policy.\""
 banking_cycle_events.34.t:0 "Deposit Insurance Debate"
 banking_cycle_events.35.a:0 "A splendid vehicle for enterprise!"
 banking_cycle_events.35.b:0 "Require proper governance standards"
 banking_cycle_events.35.d:0 "The joint-stock company model is experiencing a boom, with new companies being registered at an unprecedented rate. The ability to pool capital from many small investors to fund large enterprises has unleashed a wave of entrepreneurial energy. Railways, factories, shipping lines, and mining ventures are all benefiting from the flood of investment."
 banking_cycle_events.35.f:0 "\"Every week brings a new prospectus more magnificent than the last. Companies to drain marshes, companies to bridge oceans, companies to mine gold on the moon.\"\n\n\"And some of them might actually succeed.\"\n\n\"One or two, perhaps. The rest will succeed only in separating fools from their money.\""
 banking_cycle_events.35.t:0 "Joint-Stock Company Boom"
 banking_cycle_events.36.a:0 "Embrace the disruption!"
 banking_cycle_events.36.b:0 "Regulate the new entrants"
 banking_cycle_events.36.c:0 "Protect established banks"
 banking_cycle_events.36.d:0 "A wave of technology-driven financial firms is challenging established banks with faster, cheaper, and more accessible services. These new companies use advanced computing and telecommunications to process transactions, assess credit, and move money at a fraction of the cost of traditional banking. Established bankers are alarmed; consumers are delighted."
 banking_cycle_events.36.f:0 "\"The banks spent decades building grand marble halls. These newcomers operate from rented office space with a computer and a telephone line. And they're winning.\""
 banking_cycle_events.36.t:0 "Financial Technology Disruption"
 banking_cycle_events.37.a:0 "A brilliant innovation!"
 banking_cycle_events.37.b:0 "Require careful oversight"
 banking_cycle_events.37.c:0 "This instrument is too dangerous"
 banking_cycle_events.37.d:0 "Banks have begun bundling thousands of individual mortgages into tradeable securities, selling them to investors worldwide. The innovation allows banks to offload risk and free up capital for new lending, fueling a construction boom. But critics warn that banks no longer care whether borrowers can repay, since the risk is immediately passed on to investors who may not understand what they're buying."
 banking_cycle_events.37.f:0 "\"We originate the loan on Monday, package it on Tuesday, sell it on Wednesday, and by Thursday it's some pension fund's problem.\"\n\n\"And if the borrower defaults?\"\n\n\"That's Thursday's problem. We got paid on Wednesday.\""
 banking_cycle_events.37.t:0 "Mortgage-Backed Securities"
 banking_cycle_events.38.a:0 "Support the initiative"
 banking_cycle_events.38.b:0 "Let it develop privately"
 banking_cycle_events.38.d:0 "A new initiative is providing tiny loans to entrepreneurs and smallholders who have been shut out of the traditional banking system. The sums are modest - enough to buy a sewing machine, stock a market stall, or purchase seed for a season - but the impact on families and communities has been transformative. Repayment rates are surprisingly high, defying the skeptics who predicted the poor would default."
 banking_cycle_events.38.f:0 "\"She borrowed enough to buy three chickens and a rooster. Within two years she had a flock of fifty, two employees, and a cart. The bank that lent her the money made a tidy profit.\"\n\n\"Three chickens.\"\n\n\"Three chickens.\""
 banking_cycle_events.38.t:0 "Microfinance Initiative"
 banking_cycle_events.39.a:0 "Print money and buy bonds!"
 banking_cycle_events.39.b:0 "Limited, targeted purchases only"
 banking_cycle_events.39.c:0 "Sound money must not be debased"
 banking_cycle_events.39.d:0 "With interest rates already near zero and the economy still contracting, the central bank's economists have proposed an unconventional measure: creating new money to purchase government bonds in massive quantities. The goal is to drive down long-term borrowing costs and force investors into riskier assets, stimulating spending. The idea is controversial - critics call it 'printing money' and warn of inflation."
 banking_cycle_events.39.f:0 "\"So let me understand. The central bank creates money out of nothing, uses it to buy government debt, and this is supposed to fix the economy?\"\n\n\"In essence, yes.\"\n\n\"And this isn't just... cheating?\"\n\n\"We prefer the term 'unconventional monetary policy.'\""
 banking_cycle_events.39.t:0 "Quantitative Easing Debate"
 banking_cycle_events.40.a:0 "Overhaul the rating system!"
 banking_cycle_events.40.b:0 "Issue a formal reprimand"
 banking_cycle_events.40.c:0 "Ratings are just opinions"
 banking_cycle_events.40.d:0 "It has emerged that the credit rating agencies - the firms trusted to assess the safety of financial instruments - have been assigning their highest ratings to securities that are, in fact, nearly worthless. Investors relied on those ratings to make decisions worth billions. Now that the truth is out, trust in the entire system of financial assessment has been shattered."
 banking_cycle_events.40.f:0 "\"Triple-A. They rated it triple-A. It was a pile of bad loans wrapped in wishful thinking and sealed with a stamp that said 'safe as government bonds.'\"\n\n\"Perhaps they didn't understand what was inside.\"\n\n\"They were paid not to.\""
 banking_cycle_events.40.t:0 "Credit Rating Failure"
 banking_cycle_events.41.a:0 "Offer debt relief programs"
 banking_cycle_events.41.b:0 "Education is worth the investment"
 banking_cycle_events.41.c:0 "Cap tuition lending"
 banking_cycle_events.41.d:0 "A generation of university graduates is entering the workforce burdened by enormous education debts. The loans that seemed manageable when they were taken on are now consuming a crippling share of young workers' incomes, delaying home purchases, family formation, and savings. Consumer spending among the educated young has stagnated, and defaults on education loans are rising."
 banking_cycle_events.41.f:0 "\"I have two degrees, a mountain of debt, and a job that pays less than what my father earned with no degree at all. They told us education was the path to prosperity.\"\n\n\"It was. For the banks that lent you the money.\""
 banking_cycle_events.41.t:0 "Student Loan Burden"
 banking_cycle_events.42.a:0 "Champion green finance!"
 banking_cycle_events.42.b:0 "Let the market lead"
 banking_cycle_events.42.d:0 "A coalition of banks and government agencies has proposed issuing bonds specifically earmarked for environmental infrastructure: flood defenses, clean water systems, renewable energy installations, and pollution cleanup. The bonds would offer modest returns but carry government backing, and early interest from institutional investors has been strong. It represents a new way of financing public goods through financial markets."
 banking_cycle_events.42.f:0 "\"Invest in the future of the planet and earn three percent doing it. The prospectus practically writes itself.\"\n\n\"And if the projects fail?\"\n\n\"Then we'll have bigger problems than bond yields.\""
 banking_cycle_events.42.t:0 "Green Bond Initiative"
 banking_cycle_events.43.a:0 "Innovation needs capital!"
 banking_cycle_events.43.b:0 "Ensure prudent diversification"
 banking_cycle_events.43.d:0 "A new class of venture capital funds is channeling money into innovative but unproven enterprises: new manufacturing processes, experimental technologies, and bold commercial ventures. The returns for successful investments are spectacular, attracting a flood of capital from investors chasing the next big opportunity. Most ventures will fail, but the few that succeed are transforming entire industries."
 banking_cycle_events.43.f:0 "\"Nine out of ten will fail. But the tenth will change the world and repay the losses a hundredfold.\"\n\n\"That's what every speculator says.\"\n\n\"Yes, but some of us have spreadsheets.\""
 banking_cycle_events.43.t:0 "Venture Capital Boom"
 banking_cycle_events.44.a:0 "Crack down hard!"
 banking_cycle_events.44.b:0 "Issue new guidelines"
 banking_cycle_events.44.c:0 "The market is self-regulating"
 banking_cycle_events.44.d:0 "An investigation has revealed that certain lending institutions have been systematically targeting vulnerable borrowers - the uneducated, the desperate, and the elderly - with loans designed to be impossible to repay. Hidden fees, deceptive terms, and aggressive collection practices have trapped thousands of families in spiraling debt. The scale of the abuse is staggering."
 banking_cycle_events.44.f:0 "\"The contract was forty pages of small print. She signed because she needed the money for medicine. She didn't know the interest rate was forty percent. She didn't know the fees would double the principal. She didn't know she'd lose her house.\"\n\n\"And the lender?\"\n\n\"The lender knew everything.\""
 banking_cycle_events.44.t:0 "Predatory Lending Scandal"
 banking_cycle_events.45.a:0 "Extend a generous rescue package"
 banking_cycle_events.45.b:0 "Offer limited, conditional support"
 banking_cycle_events.45.c:0 "They must solve their own problems"
 banking_cycle_events.45.d:0 "A diplomatically important trading partner has quietly approached our government requesting emergency financial assistance. Their banking system is on the verge of collapse, and without external support, the crisis will spread to our own markets through trade disruptions and defaulted debts. The request puts us in a difficult position - refusal risks contagion, but aid comes at a steep cost to our own treasury."
 banking_cycle_events.45.f:0 "\"Their ambassador was remarkably calm, considering he was effectively saying 'lend us an enormous sum of money or we'll take your economy down with us.'\"\n\n\"That's diplomacy for you.\"\n\n\"I preferred it when diplomacy involved sending gunboats.\""
 banking_cycle_events.45.t:0 "International Bailout Request"
"""

# Modifier loc keys to add to aaaaa_extra_l_english.yml
MODIFIER_LOC = r""" banking_event_bailout_cost:0 "International Bailout"
 banking_event_bailout_cost_desc:0 "Emergency financial assistance to a trading partner."
 banking_event_bailout_goodwill:0 "International Financial Goodwill"
 banking_event_bailout_goodwill_desc:0 "Our generous financial assistance has earned us diplomatic goodwill."
 banking_event_bank_holiday:0 "Bank Holiday Disruption"
 banking_event_bank_holiday_desc:0 "The temporary closure of all banks is disrupting normal commerce."
 banking_event_commercial_paper:0 "Commercial Paper Market"
 banking_event_commercial_paper_desc:0 "Short-term business lending instruments are lubricating the wheels of commerce."
 banking_event_cooperative_growth:0 "Cooperative Banking Growth"
 banking_event_cooperative_growth_desc:0 "Agricultural cooperatives are providing affordable credit to rural communities."
 banking_event_deposit_insurance:0 "Deposit Insurance"
 banking_event_deposit_insurance_desc:0 "Government-backed deposit insurance is bolstering public confidence in the banking system."
 banking_event_fintech_growth:0 "Financial Technology Growth"
 banking_event_fintech_growth_desc:0 "Technology-driven financial firms are making services faster and cheaper."
 banking_event_green_bonds:0 "Green Bond Program"
 banking_event_green_bonds_desc:0 "Bonds financing environmental infrastructure projects."
 banking_event_interbank_guarantee:0 "Interbank Guarantee Costs"
 banking_event_interbank_guarantee_desc:0 "Government guarantees of interbank obligations."
 banking_event_joint_stock_boom:0 "Joint-Stock Company Boom"
 banking_event_joint_stock_boom_desc:0 "A proliferation of joint-stock companies is fueling industrial investment."
 banking_event_mbs_boom:0 "Mortgage Securities Boom"
 banking_event_mbs_boom_desc:0 "Mortgage-backed securities are fueling construction and financial services."
 banking_event_merchant_prosperity:0 "Banking Sector Prosperity"
 banking_event_merchant_prosperity_desc:0 "Strong banking sector profits are boosting confidence in financial services."
 banking_event_microfinance:0 "Microfinance Growth"
 banking_event_microfinance_desc:0 "Small loans to entrepreneurs are stimulating grassroots economic activity."
 banking_event_pension_stability:0 "Pension Fund Stability"
 banking_event_pension_stability_desc:0 "Growing pension funds provide a stable, long-term source of capital."
 banking_event_predatory_crackdown:0 "Lending Practice Reforms"
 banking_event_predatory_crackdown_desc:0 "Crackdown on predatory lending is temporarily constraining the financial sector."
 banking_event_provincial_exchange:0 "Provincial Exchange Growth"
 banking_event_provincial_exchange_desc:0 "New provincial stock exchanges are expanding access to capital markets."
 banking_event_qe_stimulus:0 "Monetary Stimulus"
 banking_event_qe_stimulus_desc:0 "Central bank bond-buying program is reducing borrowing costs."
 banking_event_rating_crackdown:0 "Credit Rating Reforms"
 banking_event_rating_crackdown_desc:0 "Overhaul of the credit rating system is temporarily disrupting financial markets."
 banking_event_scandal_fallout:0 "Banking Scandal Fallout"
 banking_event_scandal_fallout_desc:0 "A banking scandal has shaken confidence in financial institutions."
 banking_event_student_debt_relief:0 "Student Debt Relief"
 banking_event_student_debt_relief_desc:0 "Programs to relieve the burden of education debt."
 banking_event_student_debt_relief_cost:0 "Student Debt Relief Costs"
 banking_event_student_debt_relief_cost_desc:0 "Government spending on education debt relief."
 banking_event_telegraph_settlement:0 "Modern Financial Settlements"
 banking_event_telegraph_settlement_desc:0 "Rapid interbank settlements are boosting the efficiency of financial services."
 banking_event_trade_bills:0 "Trade Bill Market"
 banking_event_trade_bills_desc:0 "Refined trade bills are expanding the volume and reach of commerce."
 banking_event_trust_collapse:0 "Trust Company Collapse"
 banking_event_trust_collapse_desc:0 "The failure of a major trust company has damaged confidence in financial institutions."
 banking_event_venture_boom:0 "Venture Capital Boom"
 banking_event_venture_boom_desc:0 "Venture capital funds are driving innovation and industrial growth."
 civil_rights_triumph_modifier:0 "Civil Rights Triumph"
 civil_rights_triumph_modifier_desc:0 "Our nation's embrace of civil rights has earned us prestige and goodwill."
 je_civil_rights:0 "Civil Rights Movement"
 je_civil_rights_desc:0 "A political movement demanding equal rights for discriminated communities has taken root. How we respond will shape our nation's character."
 je_civil_rights_reason:0 "Discriminated communities are demanding equal treatment under the law."
 je_civil_rights_status_discriminatory:0 "Our current laws perpetuate #N discrimination#! against minority communities. The movement demands systemic reform."
 je_civil_rights_status_hostile:0 "Our laws enforce #R active hostility#! toward minority communities. The movement faces a long and difficult struggle."
 je_civil_rights_status_indifferent:0 "Our government takes no position on minority rights. The movement pushes for #G active protection#!."
 je_civil_rights_status_protective:0 "We have enacted protective measures, but the movement will not rest until #G full equality#! is achieved."
"""


def write_bom(path, content):
    """Write content with UTF-8 BOM encoding."""
    import codecs
    with open(path, 'w', encoding='utf-8-sig') as f:
        f.write(content)

def append_bom_safe(path, content):
    """Append content to existing BOM-encoded file."""
    # Read existing content
    with open(path, 'r', encoding='utf-8-sig') as f:
        existing = f.read()
    # Write back with new content appended
    write_bom(path, existing + content)


def main():
    # 1. Append events to banking_cycle_events.txt
    print("Appending 25 new events to banking_cycle_events.txt...")
    append_bom_safe(EVENTS_FILE, EVENTS)
    print(f"  Done. File: {EVENTS_FILE}")

    # 2. Append modifiers to extra_modifiers.txt
    print("Appending new modifiers to extra_modifiers.txt...")
    append_bom_safe(MODIFIERS_FILE, MODIFIERS)
    print(f"  Done. File: {MODIFIERS_FILE}")

    # 3. Insert new event entries into banking_cycle_effects.txt
    # We need to insert EFFECT_ENTRIES before the closing of the random_list
    print("Inserting new event entries into banking_cycle_effects.txt...")
    with open(EFFECTS_FILE, 'r', encoding='utf-8-sig') as f:
        effects_content = f.read()

    # Find the closing sequence after event 20: \t\t\t} closes the 0={} block,
    # \t\t} closes random_list, \t} closes outer if, } closes the effect.
    # We insert between the event block close and the random_list close.
    close_marker = "\t\t\t}\n\t\t}\n\t}\n}"
    idx = effects_content.rfind(close_marker)
    if idx == -1:
        print("  ERROR: Could not find insertion point in banking_cycle_effects.txt")
        print("  Please manually add the new event entries to the scripted effect.")
        return
    # Insert after the closing of event 20's 0={} block (after \t\t\t}\n)
    insert_pos = idx + len("\t\t\t}\n")
    effects_content = effects_content[:insert_pos] + EFFECT_ENTRIES + effects_content[insert_pos:]
    write_bom(EFFECTS_FILE, effects_content)
    print(f"  Done. File: {EFFECTS_FILE}")

    # 4. Append event loc to te_events_l_english.yml
    print("Appending event localization...")
    append_bom_safe(EVENTS_LOC, EVENT_LOC)
    print(f"  Done. File: {EVENTS_LOC}")

    # 5. Append modifier and JE loc to aaaaa_extra_l_english.yml
    print("Appending modifier/JE localization...")
    append_bom_safe(JE_LOC_FILE, MODIFIER_LOC)
    print(f"  Done. File: {JE_LOC_FILE}")

    # 6. Fix BOM on je_civil_rights.txt
    je_path = os.path.join(MOD, "common", "journal_entries", "je_civil_rights.txt")
    print(f"Ensuring BOM on {je_path}...")
    with open(je_path, 'r', encoding='utf-8') as f:
        je_content = f.read()
    write_bom(je_path, je_content)
    print("  Done.")

    print("\nAll files updated successfully!")
    print("Remember to run: python organize_loc.py")

if __name__ == "__main__":
    main()
