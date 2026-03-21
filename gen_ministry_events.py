"""Generate ministry_law_events.txt with proper tab indentation and UTF-8 BOM.

Code generator that produces events/ministry_law_events.txt. Generates ministry
law enactment events with options, modifiers, and radical/loyalist effects.

Usage:
    python gen_ministry_events.py    # Generate events file
"""
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "events", "ministry_law_events.txt")

# Helper: indent with tabs
def T(n):
    return "\t" * n

# Build the NOT block for "not dissolving" triggers (events 1-3)
NO_DISSOLUTION_LAWS = [
    "law_no_ministry_of_war",
    "law_no_ministry_of_foreign_affairs",
    "law_no_ministry_of_commerce",
    "law_no_ministry_of_culture",
    "law_no_ministry_of_labor",
    "law_no_ministry_of_the_environment",
    "law_no_ministry_of_intelligence_and_security",
    "law_no_ministry_of_refugee_affairs",
    "law_no_ministry_of_propaganda",
    "law_no_ministry_of_science",
    "law_no_ministry_of_thought_control",
    "law_no_ministry_of_consumer_protection",
    "law_no_ministry_of_urban_planning",
    "law_no_ministry_of_religion",
    "law_no_ministry_of_international_aid",
]

def not_dissolving_block(indent):
    """NOT block that excludes all 'no_ministry' laws."""
    lines = [f"{T(indent)}NOT = {{"]
    for law in NO_DISSOLUTION_LAWS:
        lines.append(f"{T(indent+1)}is_enacting_law = law_type:{law}")
    lines.append(f"{T(indent)}}}")
    return "\n".join(lines)

def or_dissolving_block(indent):
    """OR block that includes all 'no_ministry' laws (for event 4)."""
    lines = [f"{T(indent)}OR = {{"]
    for law in NO_DISSOLUTION_LAWS:
        lines.append(f"{T(indent+1)}is_enacting_law = law_type:{law}")
    lines.append(f"{T(indent)}}}")
    return "\n".join(lines)

def standard_header(num, title_video, icon, extra_lines=""):
    """Common event header block."""
    return f"""{T(1)}type = country_event
{T(1)}placement = root

{T(1)}title = ministry_law_events.{num}.t
{T(1)}desc = ministry_law_events.{num}.d
{T(1)}flavor = ministry_law_events.{num}.f

{T(1)}category = enactment

{T(1)}event_image = {{
{T(2)}video = "{title_video}"
{T(1)}}}

{T(1)}on_created_soundeffect = "event:/SFX/UI/Alerts/event_appear"

{T(1)}icon = "{icon}"

{T(1)}duration = 3

{T(1)}cooldown = {{ days = normal_modifier_time }}"""

def save_and_cancel(indent=1):
    return f"""
{T(indent)}immediate = {{
{T(indent+1)}currently_enacting_law = {{
{T(indent+2)}save_scope_as = current_law_scope
{T(indent+1)}}}
{T(indent)}}}

{T(indent)}cancellation_trigger = {{
{T(indent+1)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(indent)}}}"""

def option_advance_radicals(num, letter, modifier_advance, strata, default=True):
    d = f"\n{T(2)}default_option = yes" if default else ""
    s = f"\n{T(3)}strata = {strata}" if strata else ""
    return f"""
{T(1)}option = {{ # {_option_comments[(num, letter)]}
{T(2)}name = ministry_law_events.{num}.{letter}{d}
{T(2)}add_enactment_modifier = {{
{T(3)}name = {modifier_advance}
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals{s}
{T(2)}}}
{T(1)}}}"""

def option_cautious_loyalists(num, letter, modifier_cautious, strata):
    s = f"\n{T(3)}strata = {strata}" if strata else ""
    return f"""
{T(1)}option = {{ # {_option_comments[(num, letter)]}
{T(2)}name = ministry_law_events.{num}.{letter}
{T(2)}add_enactment_modifier = {{
{T(3)}name = {modifier_cautious}
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals{s}
{T(2)}}}
{T(1)}}}"""

# Option comment lookup
_option_comments = {
    (1, 'a'): "Recruit aggressively - fill every desk",
    (1, 'b'): "Staff it gradually to ensure quality",
    (2, 'a'): "Allocate the full budget - half measures fail",
    (2, 'b'): "Promise a lean operation to win over the skeptics",
    (3, 'a'): "Assert the new ministry's jurisdiction firmly",
    (3, 'b'): "Allow a transitional period to ease the change",
    (4, 'a'): "Swift dissolution is best - rip off the bandage",
    (4, 'b'): "Offer generous severance and retraining",
    (5, 'a'): "Civilian oversight is non-negotiable",
    (5, 'b'): "Grant operational autonomy to ease the transition",
    (6, 'a'): "This debacle proves we need a proper ministry",
    (6, 'b'): "Use the incident to build a careful consensus",
    (7, 'a'): "Commerce demands coordination - push it through",
    (7, 'b'): "Design the ministry to address merchant concerns",
    (8, 'a'): "A great nation deserves a Ministry of Culture",
    (8, 'b'): "Let the artists help design it to win their support",
    (9, 'a'): "The ministry will serve the national interest",
    (9, 'b'): "Proceed carefully to minimize opposition",
    (9, 'c'): "Invite the key stakeholders to shape the ministry",
    (10, 'a'): "The environment cannot wait - push through",
    (10, 'b'): "Offer industry a seat at the table",
    (11, 'a'): "Security demands these tools - push forward",
    (11, 'b'): "Build in strict oversight to reassure the public",
    (12, 'a'): "A civilized nation does not turn away the desperate",
    (12, 'b'): "Frame it as an orderly process to ease domestic fears",
    (13, 'a'): "The truth must be guided for the good of the people",
    (13, 'b'): "Rebrand it as public information to calm the press",
    (14, 'a'): "Science needs state coordination - push forward",
    (14, 'b'): "Let the universities lead the design process",
    (15, 'a'): "Dissent must be monitored for the nation's safety",
    (15, 'b'): "Start with modest powers to avoid a backlash",
    (16, 'a'): "Consumers deserve protection - act now",
    (16, 'b'): "Let industry self-regulate within the new framework",
    (17, 'a'): "Cities need plans, not chaos - establish the ministry",
    (17, 'b'): "Consult with developers to smooth the transition",
    (18, 'a'): "Faith and governance shall strengthen each other",
    (18, 'b'): "Promise clerical autonomy within the ministry",
    (19, 'a'): "A great nation has obligations to the world",
    (19, 'b'): "Frame it as strategic investment to win domestic support",
}

# ── Build each event ──────────────────────────────────────────────────

events = []

# ======================================================================
#  EVENT 1 – Staffing the New Ministry
# ======================================================================
e1 = f"""# ======================================================================
#  1 – Staffing the New Ministry  (Generic – any ministry being created)
# ======================================================================
ministry_law_events.1 = {{
{standard_header(1, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_default.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law_type_group = law_group_ministries
{not_dissolving_block(2)}
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_staffing_advance
{T(3)}has_modifier = ministry_staffing_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}
{option_advance_radicals(1, 'a', 'ministry_staffing_advance', 'middle')}
{option_cautious_loyalists(1, 'b', 'ministry_staffing_cautious', 'middle')}
}}"""
events.append(e1)

# ======================================================================
#  EVENT 2 – The Budget Debate
# ======================================================================
e2 = f"""# ======================================================================
#  2 – The Budget Debate  (Generic – any ministry being created)
# ======================================================================
ministry_law_events.2 = {{
{standard_header(2, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_trade.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law_type_group = law_group_ministries
{not_dissolving_block(2)}
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_budget_advance
{T(3)}has_modifier = ministry_budget_cautious
{T(2)}}}
{T(2)}any_interest_group = {{
{T(3)}ig_counts_as_marginal = no
{T(3)}law_stance = {{
{T(4)}law = owner.currently_enacting_law.type
{T(4)}value < neutral
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}random_interest_group = {{
{T(3)}limit = {{
{T(4)}ig_counts_as_marginal = no
{T(4)}law_stance = {{
{T(5)}law = owner.currently_enacting_law.type
{T(5)}value < neutral
{T(4)}}}
{T(3)}}}
{T(3)}save_scope_as = opposing_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(2, 'a')]}
{T(2)}name = ministry_law_events.2.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_budget_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = upper
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(2, 'b')]}
{T(2)}name = ministry_law_events.2.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_budget_cautious
{T(2)}}}
{T(2)}scope:opposing_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e2)

# ======================================================================
#  EVENT 3 – Bureaucratic Turf Wars
# ======================================================================
e3 = f"""# ======================================================================
#  3 – Bureaucratic Turf Wars  (Generic – any ministry being created)
# ======================================================================
ministry_law_events.3 = {{
{standard_header(3, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_default.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law_type_group = law_group_ministries
{not_dissolving_block(2)}
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_turf_advance
{T(3)}has_modifier = ministry_turf_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}
{option_advance_radicals(3, 'a', 'ministry_turf_advance', 'middle')}
{option_cautious_loyalists(3, 'b', 'ministry_turf_cautious', 'middle')}
}}"""
events.append(e3)

# ======================================================================
#  EVENT 4 – The Redundant Clerks (dissolving)
# ======================================================================
e4 = f"""# ======================================================================
#  4 – The Redundant Clerks  (Generic – dissolving a ministry)
# ======================================================================
ministry_law_events.4 = {{
{standard_header(4, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_default.dds")}

{T(1)}trigger = {{
{or_dissolving_block(2)}
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_dissolution_advance
{T(3)}has_modifier = ministry_dissolution_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}

{T(1)}option = {{ # {_option_comments[(4, 'a')]}
{T(2)}name = ministry_law_events.4.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_dissolution_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = medium_radicals
{T(3)}strata = middle
{T(2)}}}
{T(1)}}}
{option_cautious_loyalists(4, 'b', 'ministry_dissolution_cautious', 'middle')}
}}"""
events.append(e4)

# ======================================================================
#  EVENT 5 – The Generals' War Room (Ministry of War)
# ======================================================================
e5 = f"""# ======================================================================
#  5 – The Generals' War Room  (Ministry of War)
# ======================================================================
ministry_law_events.5 = {{
{standard_header(5, "europenorthamerica_before_the_battle", "gfx/interface/icons/event_icons/event_military.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_war
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_war_generals_advance
{T(3)}has_modifier = ministry_war_generals_cautious
{T(2)}}}
{T(2)}ig:ig_armed_forces ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_armed_forces ?= {{
{T(3)}save_scope_as = armed_forces_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(5, 'a')]}
{T(2)}name = ministry_law_events.5.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_war_generals_advance
{T(2)}}}
{T(2)}scope:armed_forces_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_negative_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(5, 'b')]}
{T(2)}name = ministry_law_events.5.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_war_generals_cautious
{T(2)}}}
{T(2)}scope:armed_forces_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e5)

# ======================================================================
#  EVENT 6 – The Ambassador's Dilemma (Ministry of Foreign Affairs)
# ======================================================================
e6 = f"""# ======================================================================
#  6 – The Ambassador's Dilemma  (Ministry of Foreign Affairs)
# ======================================================================
ministry_law_events.6 = {{
{standard_header(6, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_newspaper.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_foreign_affairs
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_fa_diplomacy_advance
{T(3)}has_modifier = ministry_fa_diplomacy_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}

{T(1)}option = {{ # {_option_comments[(6, 'a')]}
{T(2)}name = ministry_law_events.6.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_fa_diplomacy_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = upper
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(6, 'b')]}
{T(2)}name = ministry_law_events.6.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_fa_diplomacy_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e6)

# ======================================================================
#  EVENT 7 – The Merchant's Petition (Ministry of Commerce)
# ======================================================================
e7 = f"""# ======================================================================
#  7 – The Merchant's Petition  (Ministry of Commerce)
# ======================================================================
ministry_law_events.7 = {{
{standard_header(7, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_trade.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_commerce
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_commerce_trade_advance
{T(3)}has_modifier = ministry_commerce_trade_cautious
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}save_scope_as = industrialists_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(7, 'a')]}
{T(2)}name = ministry_law_events.7.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_commerce_trade_advance
{T(2)}}}
{T(2)}scope:industrialists_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(7, 'b')]}
{T(2)}name = ministry_law_events.7.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_commerce_trade_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(3)}strata = upper
{T(2)}}}
{T(1)}}}
}}"""
events.append(e7)

# ======================================================================
#  EVENT 8 – The Artist's Subsidy (Ministry of Culture)
# ======================================================================
e8 = f"""# ======================================================================
#  8 – The Artist's Subsidy  (Ministry of Culture)
# ======================================================================
ministry_law_events.8 = {{
{standard_header(8, "southamerica_election", "gfx/interface/icons/event_icons/event_newspaper.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_culture
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_culture_patronage_advance
{T(3)}has_modifier = ministry_culture_patronage_cautious
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}save_scope_as = intelligentsia_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(8, 'a')]}
{T(2)}name = ministry_law_events.8.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_culture_patronage_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = middle
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(8, 'b')]}
{T(2)}name = ministry_law_events.8.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_culture_patronage_cautious
{T(2)}}}
{T(2)}scope:intelligentsia_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e8)

# ======================================================================
#  EVENT 9 – Capital vs. Labor (Ministry of Labor)
# ======================================================================
e9 = f"""# ======================================================================
#  9 – Capital vs. Labor  (Ministry of Labor – both variants)
# ======================================================================
ministry_law_events.9 = {{
{standard_header(9, "europenorthamerica_rich_and_poor", "gfx/interface/icons/event_icons/event_industry.dds")}

{T(1)}trigger = {{
{T(2)}OR = {{
{T(3)}is_enacting_law = law_type:law_pro_labor_ministry_of_labor
{T(3)}is_enacting_law = law_type:law_pro_capital_ministry_of_labor
{T(2)}}}
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_labor_struggle_advance
{T(3)}has_modifier = ministry_labor_struggle_cautious
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_trade_unions ?= {{
{T(3)}save_scope_as = trade_unions_ig
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}save_scope_as = industrialists_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(9, 'a')]}
{T(2)}name = ministry_law_events.9.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_labor_struggle_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(9, 'b')]}
{T(2)}name = ministry_law_events.9.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_labor_struggle_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(9, 'c')]}
{T(2)}name = ministry_law_events.9.c
{T(2)}trigger = {{
{T(3)}OR = {{
{T(4)}AND = {{
{T(5)}is_enacting_law = law_type:law_pro_labor_ministry_of_labor
{T(5)}ig:ig_trade_unions ?= {{
{T(6)}ig_counts_as_marginal = no
{T(5)}}}
{T(4)}}}
{T(4)}AND = {{
{T(5)}is_enacting_law = law_type:law_pro_capital_ministry_of_labor
{T(5)}ig:ig_industrialists ?= {{
{T(6)}ig_counts_as_marginal = no
{T(5)}}}
{T(4)}}}
{T(3)}}}
{T(2)}}}
{T(2)}highlighted_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_labor_struggle_advance
{T(2)}}}
{T(2)}if = {{
{T(3)}limit = {{ is_enacting_law = law_type:law_pro_labor_ministry_of_labor }}
{T(3)}scope:trade_unions_ig = {{
{T(4)}add_modifier = {{
{T(5)}name = ig_approval_positive_modifier
{T(5)}days = normal_modifier_time
{T(5)}is_decaying = yes
{T(4)}}}
{T(3)}}}
{T(3)}scope:industrialists_ig = {{
{T(4)}add_modifier = {{
{T(5)}name = ig_approval_negative_modifier
{T(5)}days = normal_modifier_time
{T(5)}is_decaying = yes
{T(4)}}}
{T(3)}}}
{T(2)}}}
{T(2)}if = {{
{T(3)}limit = {{ is_enacting_law = law_type:law_pro_capital_ministry_of_labor }}
{T(3)}scope:industrialists_ig = {{
{T(4)}add_modifier = {{
{T(5)}name = ig_approval_positive_modifier
{T(5)}days = normal_modifier_time
{T(5)}is_decaying = yes
{T(4)}}}
{T(3)}}}
{T(3)}scope:trade_unions_ig = {{
{T(4)}add_modifier = {{
{T(5)}name = ig_approval_negative_modifier
{T(5)}days = normal_modifier_time
{T(5)}is_decaying = yes
{T(4)}}}
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e9)

# ======================================================================
# EVENT 10 – The Smokestack Question (Ministry of the Environment)
# ======================================================================
e10 = f"""# ======================================================================
# 10 – The Smokestack Question  (Ministry of the Environment)
# ======================================================================
ministry_law_events.10 = {{
{standard_header(10, "europenorthamerica_rich_and_poor", "gfx/interface/icons/event_icons/event_industry.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_the_environment
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_env_smokestacks_advance
{T(3)}has_modifier = ministry_env_smokestacks_cautious
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}save_scope_as = industrialists_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(10, 'a')]}
{T(2)}name = ministry_law_events.10.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_env_smokestacks_advance
{T(2)}}}
{T(2)}scope:industrialists_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_negative_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(10, 'b')]}
{T(2)}name = ministry_law_events.10.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_env_smokestacks_cautious
{T(2)}}}
{T(2)}scope:industrialists_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e10)

# ======================================================================
# EVENT 11 – The Shadow Files (Ministry of Intelligence)
# ======================================================================
e11 = f"""# ======================================================================
# 11 – The Shadow Files  (Ministry of Intelligence and Security)
# ======================================================================
ministry_law_events.11 = {{
{standard_header(11, "middleeast_police_breaking_door", "gfx/interface/icons/event_icons/event_newspaper.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_intelligence_and_security
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_intel_shadow_advance
{T(3)}has_modifier = ministry_intel_shadow_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}
{option_advance_radicals(11, 'a', 'ministry_intel_shadow_advance', 'middle')}
{option_cautious_loyalists(11, 'b', 'ministry_intel_shadow_cautious', 'middle')}
}}"""
events.append(e11)

# ======================================================================
# EVENT 12 – The Refugee Ship (Ministry of Refugee Affairs)
# ======================================================================
e12 = f"""# ======================================================================
# 12 – The Refugee Ship  (Ministry of Refugee Affairs)
# ======================================================================
ministry_law_events.12 = {{
{standard_header(12, "africa_public_protest", "gfx/interface/icons/event_icons/event_protest.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_refugee_affairs
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_refugee_crisis_advance
{T(3)}has_modifier = ministry_refugee_crisis_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}

{T(1)}option = {{ # {_option_comments[(12, 'a')]}
{T(2)}name = ministry_law_events.12.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_refugee_crisis_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = lower
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(12, 'b')]}
{T(2)}name = ministry_law_events.12.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_refugee_crisis_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e12)

# ======================================================================
# EVENT 13 – The Loudspeaker State (Ministry of Propaganda)
# ======================================================================
e13 = f"""# ======================================================================
# 13 – The Loudspeaker State  (Ministry of Propaganda)
# ======================================================================
ministry_law_events.13 = {{
{standard_header(13, "middleeast_police_breaking_door", "gfx/interface/icons/event_icons/event_newspaper.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_propaganda
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_prop_loudspeaker_advance
{T(3)}has_modifier = ministry_prop_loudspeaker_cautious
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}save_scope_as = intelligentsia_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(13, 'a')]}
{T(2)}name = ministry_law_events.13.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_prop_loudspeaker_advance
{T(2)}}}
{T(2)}scope:intelligentsia_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_negative_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(13, 'b')]}
{T(2)}name = ministry_law_events.13.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_prop_loudspeaker_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e13)

# ======================================================================
# EVENT 14 – The Laboratory of the State (Ministry of Science)
# ======================================================================
e14 = f"""# ======================================================================
# 14 – The Laboratory of the State  (Ministry of Science)
# ======================================================================
ministry_law_events.14 = {{
{standard_header(14, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_default.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_science
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_sci_laboratory_advance
{T(3)}has_modifier = ministry_sci_laboratory_cautious
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}save_scope_as = intelligentsia_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(14, 'a')]}
{T(2)}name = ministry_law_events.14.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_sci_laboratory_advance
{T(2)}}}
{T(2)}scope:intelligentsia_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(14, 'b')]}
{T(2)}name = ministry_law_events.14.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_sci_laboratory_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(3)}strata = middle
{T(2)}}}
{T(1)}}}
}}"""
events.append(e14)

# ======================================================================
# EVENT 15 – The Watchers (Ministry of Thought Control)
# ======================================================================
e15 = f"""# ======================================================================
# 15 – The Watchers  (Ministry of Thought Control)
# ======================================================================
ministry_law_events.15 = {{
{standard_header(15, "middleeast_police_breaking_door", "gfx/interface/icons/event_icons/event_newspaper.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_thought_control
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_thought_watchers_advance
{T(3)}has_modifier = ministry_thought_watchers_cautious
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_intelligentsia ?= {{
{T(3)}save_scope_as = intelligentsia_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(15, 'a')]}
{T(2)}name = ministry_law_events.15.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_thought_watchers_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = medium_radicals
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(15, 'b')]}
{T(2)}name = ministry_law_events.15.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_thought_watchers_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(3)}strata = middle
{T(2)}}}
{T(1)}}}
}}"""
events.append(e15)

# ======================================================================
# EVENT 16 – The Tainted Product (Ministry of Consumer Protection)
# ======================================================================
e16 = f"""# ======================================================================
# 16 – The Tainted Product  (Ministry of Consumer Protection)
# ======================================================================
ministry_law_events.16 = {{
{standard_header(16, "europenorthamerica_rich_and_poor", "gfx/interface/icons/event_icons/event_trade.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_consumer_protection
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_consumer_tainted_advance
{T(3)}has_modifier = ministry_consumer_tainted_cautious
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_industrialists ?= {{
{T(3)}save_scope_as = industrialists_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(16, 'a')]}
{T(2)}name = ministry_law_events.16.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_consumer_tainted_advance
{T(2)}}}
{T(2)}scope:industrialists_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_negative_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(16, 'b')]}
{T(2)}name = ministry_law_events.16.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_consumer_tainted_cautious
{T(2)}}}
{T(2)}scope:industrialists_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}
}}"""
events.append(e16)

# ======================================================================
# EVENT 17 – The City Rises (Ministry of Urban Planning)
# ======================================================================
e17 = f"""# ======================================================================
# 17 – The City Rises  (Ministry of Urban Planning)
# ======================================================================
ministry_law_events.17 = {{
{standard_header(17, "europenorthamerica_london_center", "gfx/interface/icons/event_icons/event_industry.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_urban_planning
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_urban_sprawl_advance
{T(3)}has_modifier = ministry_urban_sprawl_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}

{T(1)}option = {{ # {_option_comments[(17, 'a')]}
{T(2)}name = ministry_law_events.17.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_urban_sprawl_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = upper
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(17, 'b')]}
{T(2)}name = ministry_law_events.17.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_urban_sprawl_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e17)

# ======================================================================
# EVENT 18 – The Pulpit and the State (Ministry of Religion)
# ======================================================================
e18 = f"""# ======================================================================
# 18 – The Pulpit and the State  (Ministry of Religion)
# ======================================================================
ministry_law_events.18 = {{
{standard_header(18, "southamerica_election", "gfx/interface/icons/event_icons/event_default.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_religion
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_religion_pulpit_advance
{T(3)}has_modifier = ministry_religion_pulpit_cautious
{T(2)}}}
{T(2)}ig:ig_devout ?= {{
{T(3)}ig_counts_as_marginal = no
{T(2)}}}
{T(1)}}}

{T(1)}immediate = {{
{T(2)}currently_enacting_law = {{
{T(3)}save_scope_as = current_law_scope
{T(2)}}}
{T(2)}ig:ig_devout ?= {{
{T(3)}save_scope_as = devout_ig
{T(2)}}}
{T(1)}}}

{T(1)}cancellation_trigger = {{
{T(2)}NOT = {{ currently_enacting_law = scope:current_law_scope }}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(18, 'a')]}
{T(2)}name = ministry_law_events.18.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_religion_pulpit_advance
{T(2)}}}
{T(2)}scope:devout_ig = {{
{T(3)}add_modifier = {{
{T(4)}name = ig_approval_positive_modifier
{T(4)}days = normal_modifier_time
{T(4)}is_decaying = yes
{T(3)}}}
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(18, 'b')]}
{T(2)}name = ministry_law_events.18.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_religion_pulpit_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e18)

# ======================================================================
# EVENT 19 – The Distant Crisis (Ministry of International Aid)
# ======================================================================
e19 = f"""# ======================================================================
# 19 – The Distant Crisis  (Ministry of International Aid)
# ======================================================================
ministry_law_events.19 = {{
{standard_header(19, "africa_public_protest", "gfx/interface/icons/event_icons/event_protest.dds")}

{T(1)}trigger = {{
{T(2)}is_enacting_law = law_type:law_ministry_of_international_aid
{T(2)}NOR = {{
{T(3)}has_modifier = ministry_aid_distant_advance
{T(3)}has_modifier = ministry_aid_distant_cautious
{T(2)}}}
{T(1)}}}
{save_and_cancel()}

{T(1)}option = {{ # {_option_comments[(19, 'a')]}
{T(2)}name = ministry_law_events.19.a
{T(2)}default_option = yes
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_aid_distant_advance
{T(2)}}}
{T(2)}add_radicals = {{
{T(3)}value = small_radicals
{T(3)}strata = upper
{T(2)}}}
{T(1)}}}

{T(1)}option = {{ # {_option_comments[(19, 'b')]}
{T(2)}name = ministry_law_events.19.b
{T(2)}add_enactment_modifier = {{
{T(3)}name = ministry_aid_distant_cautious
{T(2)}}}
{T(2)}add_loyalists = {{
{T(3)}value = small_radicals
{T(2)}}}
{T(1)}}}
}}"""
events.append(e19)

# ── Assemble and write ────────────────────────────────────────────────
full_text = "namespace = ministry_law_events\n\n" + "\n\n".join(events) + "\n"

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8-sig") as f:
    f.write(full_text)

# ── Verification ──────────────────────────────────────────────────────
print(f"Written to: {OUTPUT_PATH}")
line_count = full_text.count("\n")
print(f"Total lines: {line_count}")

# Check no _stall references remain
if "_stall" in full_text:
    print("WARNING: '_stall' found in output!")
else:
    print("OK: No '_stall' references found.")

# Check for add_enactment_setback
if "add_enactment_setback" in full_text:
    print("WARNING: 'add_enactment_setback' found in output!")
else:
    print("OK: No 'add_enactment_setback' references found.")

# Check tabs are present
tab_count = full_text.count("\t")
print(f"Tab characters: {tab_count}")

# Verify BOM
with open(OUTPUT_PATH, "rb") as f:
    bom = f.read(3)
expected_bom = b'\xef\xbb\xbf'
print(f"BOM bytes: {bom!r}  (expected {expected_bom!r})")
print(f"BOM correct: {bom == expected_bom}")

# Count events
import re
event_count = len(re.findall(r"^ministry_law_events\.\d+", full_text, re.MULTILINE))
print(f"Events written: {event_count}")

# Verify _cautious modifiers exist
cautious_count = full_text.count("_cautious")
advance_count = full_text.count("_advance")
print(f"'_cautious' occurrences: {cautious_count}")
print(f"'_advance' occurrences: {advance_count}")
