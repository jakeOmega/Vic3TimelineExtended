"""
Heir Education Rework Implementation Script
=============================================
Generates all modified game files for the heir education system rework.

Changes:
1. New "terrible" tier below poor (5-tier system)
2. Hidden intelligence (1-5) affecting gain amount per tick
3. Slower base rate (3% per focus per month, down from 5%)
4. Adult heir pre-initialization based on age
5. 8% rebel child chance (ideology inversion at resolution)
6. Progress bar max raised to 20
7. Updated trait resolution thresholds for 5-tier system
"""

import os
import sys

# BOM-encoded write helper
def write_bom(path, content):
    """Write content with UTF-8 BOM encoding."""
    import codecs
    with open(path, 'w', encoding='utf-8-sig', newline='\r\n') as f:
        f.write(content)
    print(f"  Written: {os.path.basename(path)}")

MOD_ROOT = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
#  1. SCRIPTED EFFECTS
# ═══════════════════════════════════════════════════════════════

def generate_effects():
    """Generate the complete heir_education_effects.txt"""
    
    # Intelligence-modified gain effects for each focus
    trait_focuses = [
        ("admin", "heir_ed_admin", "heir_education_innovation_cost", "heir_education_admin_ig_reaction"),
        ("diplo", "heir_ed_diplo", "heir_education_innovation_cost", "heir_education_diplo_ig_reaction"),
        ("military", "heir_ed_military", "heir_education_innovation_cost", "heir_education_military_ig_reaction"),
    ]
    
    ideology_focuses = [
        ("progressive", "heir_ed_ideology", "1", "heir_education_progressive_ig_reaction"),
        ("conservative", "heir_ed_ideology", "-1", "heir_education_conservative_ig_reaction"),
    ]
    
    ig_focuses = [
        ("radical", "heir_ed_ig_radical", "heir_education_radical_ig_reaction"),
        ("moderate", "heir_ed_ig_moderate", "heir_education_moderate_ig_reaction"),
        ("regressive", "heir_ed_ig_regressive", "heir_education_regressive_ig_reaction"),
    ]
    
    gain_effects = []
    
    # Trait gain effects (admin, diplo, military)
    for focus_name, var_name, cost_mod, ig_reaction in trait_focuses:
        gain_effects.append(f"""heir_ed_gain_{focus_name} = {{
\t# Intelligence modifies gain amount:
\t#   High (4-5): 30% chance of double gain (+2)
\t#   Medium (3): standard gain (+1)
\t#   Low (1-2): 25% chance of wasted opportunity (+0)
\tif = {{
\t\tlimit = {{ var:heir_ed_intelligence >= 4 }}
\t\trandom_list = {{
\t\t\t30 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 2 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 2 }}
\t\t\t}}
\t\t\t70 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_intelligence <= 2 }}
\t\trandom_list = {{
\t\t\t25 = {{ }}
\t\t\t75 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse = {{
\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t}}
\tscope:journal_entry = {{
\t\tset_bar_progress = {{ name = heir_education_progress_bar value = root.var:heir_ed_total }}
\t}}
\tadd_modifier = {{ name = {cost_mod} days = 30 is_decaying = yes }}
\t{ig_reaction} = yes
}}""")
    
    # Ideology gain effects (progressive, conservative)
    for focus_name, var_name, add_val, ig_reaction in ideology_focuses:
        gain_effects.append(f"""heir_ed_gain_{focus_name} = {{
\tif = {{
\t\tlimit = {{ var:heir_ed_intelligence >= 4 }}
\t\trandom_list = {{
\t\t\t30 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = {add_val} }}
\t\t\t\tchange_variable = {{ name = {var_name} add = {add_val} }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 2 }}
\t\t\t}}
\t\t\t70 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = {add_val} }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_intelligence <= 2 }}
\t\trandom_list = {{
\t\t\t25 = {{ }}
\t\t\t75 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = {add_val} }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse = {{
\t\tchange_variable = {{ name = {var_name} add = {add_val} }}
\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t}}
\tscope:journal_entry = {{
\t\tset_bar_progress = {{ name = heir_education_progress_bar value = root.var:heir_ed_total }}
\t}}
\t{ig_reaction} = yes
}}""")
    
    # IG gain effects (radical, moderate, regressive)
    for focus_name, var_name, ig_reaction in ig_focuses:
        gain_effects.append(f"""heir_ed_gain_{focus_name} = {{
\tif = {{
\t\tlimit = {{ var:heir_ed_intelligence >= 4 }}
\t\trandom_list = {{
\t\t\t30 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 2 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 2 }}
\t\t\t}}
\t\t\t70 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_intelligence <= 2 }}
\t\trandom_list = {{
\t\t\t25 = {{ }}
\t\t\t75 = {{
\t\t\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\t\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t\t\t}}
\t\t}}
\t}}
\telse = {{
\t\tchange_variable = {{ name = {var_name} add = 1 }}
\t\tchange_variable = {{ name = heir_ed_total add = 1 }}
\t}}
\tscope:journal_entry = {{
\t\tset_bar_progress = {{ name = heir_education_progress_bar value = root.var:heir_ed_total }}
\t}}
\t{ig_reaction} = yes
}}""")
    
    gain_section = "\n\n".join(gain_effects)
    
    # Trait resolution helper - generates the if/else_if chain for one trait category
    def trait_resolution(trait_category, var_name):
        """Generate resolution block for admin/diplomat/commander"""
        # Thresholds: investment -> [terrible, poor, average, skilled, exceptional]
        tiers = {
            8: [0, 2, 10, 38, 50],
            5: [2, 5, 18, 45, 30],
            3: [5, 15, 30, 35, 15],
            1: [15, 25, 35, 20, 5],
            0: [35, 30, 25, 8, 2],
        }
        trait_names = [
            f"ruler_terrible_{trait_category}",
            f"ruler_poor_{trait_category}",
            f"ruler_average_{trait_category}",
            f"ruler_skilled_{trait_category}",
            f"ruler_exceptional_{trait_category}",
        ]
        
        blocks = []
        sorted_thresholds = sorted(tiers.keys(), reverse=True)
        for i, threshold in enumerate(sorted_thresholds):
            weights = tiers[threshold]
            keyword = "if" if i == 0 else "else_if"
            
            if threshold == 0:
                # Default case
                keyword = "else"
                condition = ""
            else:
                condition = f"\n\t\tlimit = {{ has_variable = {var_name} var:{var_name} >= {threshold} }}"
            
            trait_entries = "\n".join(
                f"\t\t\t{w} = {{ add_trait = {name} }}"
                for w, name in zip(weights, trait_names)
            )
            
            if keyword == "else":
                blocks.append(f"""\telse = {{
\t\their ?= {{
\t\t\trandom_list = {{
{trait_entries}
\t\t\t}}
\t\t}}
\t}}""")
            else:
                blocks.append(f"""\t{keyword} = {{{condition}
\t\their ?= {{
\t\t\trandom_list = {{
{trait_entries}
\t\t\t}}
\t\t}}
\t}}""")
        
        return "\n".join(blocks)
    
    admin_resolution = trait_resolution("administrator", "heir_ed_admin")
    diplo_resolution = trait_resolution("diplomat", "heir_ed_diplo")
    military_resolution = trait_resolution("commander", "heir_ed_military")
    
    # Read the existing ideology and IG resolution (lines ~100-355 of original)
    # I'll rewrite them with the rebel child addition
    
    content = f"""### Heir Education - Scripted Effects
### Reworked: 5-tier system (terrible/poor/average/skilled/exceptional)
### Hidden intelligence (1-5) modifies gain amount per pulse tick
### 8% rebel child chance inverts ideology at resolution
### Adult heirs pre-initialized based on age

# ──────────────────────── INTELLIGENCE-MODIFIED GAIN EFFECTS ────────────────────────
# Called by monthly pulse when a focus's 3% chance succeeds.
# Intelligence modifies the AMOUNT gained per tick:
#   Low intelligence (1-2): 25% chance of wasted opportunity (no gain)
#   Medium intelligence (3): standard +1 gain
#   High intelligence (4-5): 30% chance of double gain (+2)

{gain_section}

# ──────────────────────── ADULT HEIR INITIALIZATION ────────────────────────
# Pre-initializes investment variables for heirs who aren't newborns.
# Simulates passive development based on heir's age.
# Called from JE immediate block.

heir_education_init_adult = {{
\their ?= {{
\t\t# Age 15+: significant prior development
\t\tif = {{
\t\t\tlimit = {{ age >= 15 }}
\t\t\troot = {{
\t\t\t\t# Admin: 1-3 points
\t\t\t\trandom_list = {{
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_admin add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_admin add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_admin add = 3 }} change_variable = {{ name = heir_ed_total add = 3 }} }}
\t\t\t\t}}
\t\t\t\t# Diplo: 1-3 points
\t\t\t\trandom_list = {{
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_diplo add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_diplo add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_diplo add = 3 }} change_variable = {{ name = heir_ed_total add = 3 }} }}
\t\t\t\t}}
\t\t\t\t# Military: 1-3 points
\t\t\t\trandom_list = {{
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_military add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_military add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t\t25 = {{ change_variable = {{ name = heir_ed_military add = 3 }} change_variable = {{ name = heir_ed_total add = 3 }} }}
\t\t\t\t}}
\t\t\t\t# Random ideology lean
\t\t\t\trandom_list = {{
\t\t\t\t\t30 = {{ change_variable = {{ name = heir_ed_ideology add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t40 = {{ }}
\t\t\t\t\t30 = {{ change_variable = {{ name = heir_ed_ideology add = -1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t}}
\t\t\t\t# Random IG lean
\t\t\t\trandom_list = {{
\t\t\t\t\t33 = {{ change_variable = {{ name = heir_ed_ig_radical add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t34 = {{ change_variable = {{ name = heir_ed_ig_moderate add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t33 = {{ change_variable = {{ name = heir_ed_ig_regressive add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\t# Age 10-14: moderate prior development
\t\telse_if = {{
\t\t\tlimit = {{ age >= 10 }}
\t\t\troot = {{
\t\t\t\trandom_list = {{
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_admin add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_admin add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t}}
\t\t\t\trandom_list = {{
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_diplo add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_diplo add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t}}
\t\t\t\trandom_list = {{
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_military add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t\t50 = {{ change_variable = {{ name = heir_ed_military add = 2 }} change_variable = {{ name = heir_ed_total add = 2 }} }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\t# Age 5-9: minimal prior development
\t\telse_if = {{
\t\t\tlimit = {{ age >= 5 }}
\t\t\troot = {{
\t\t\t\trandom_list = {{
\t\t\t\t\t60 = {{ }}
\t\t\t\t\t40 = {{ change_variable = {{ name = heir_ed_admin add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t}}
\t\t\t\trandom_list = {{
\t\t\t\t\t60 = {{ }}
\t\t\t\t\t40 = {{ change_variable = {{ name = heir_ed_diplo add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t}}
\t\t\t\trandom_list = {{
\t\t\t\t\t60 = {{ }}
\t\t\t\t\t40 = {{ change_variable = {{ name = heir_ed_military add = 1 }} change_variable = {{ name = heir_ed_total add = 1 }} }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
}}

# ──────────────────────── MAIN RESOLUTION ────────────────────────
# Called when the heir reaches adulthood or on JE timeout.
# 5-tier system: terrible / poor / average / skilled / exceptional
# Investment thresholds scaled for 3% monthly pulse:
#   0   = no investment -> heavily weighted toward terrible/poor
#   1-2 = light investment
#   3-4 = moderate investment
#   5-7 = heavy investment
#   8+  = extreme investment (sustained high-intelligence focus over many years)

heir_education_resolve_effect = {{
\t# ─── Resolve Administrative Trait ───
{admin_resolution}

\t# ─── Resolve Diplomatic Trait ───
{diplo_resolution}

\t# ─── Resolve Military Trait ───
{military_resolution}

\t# ─── Rebel Child Check ───
\t# 8% chance the heir's ideology inverts from what the player aimed for
\trandom_list = {{
\t\t8 = {{
\t\t\tchange_variable = {{ name = heir_ed_ideology multiply = -1 }}
\t\t}}
\t\t92 = {{ }}
\t}}

\t# ─── Resolve Ideology ───
\t# Positive = progressive, Negative = conservative
\t# Thresholds at ±1 (leaning) and ±4 (strong)
\tif = {{
\t\tlimit = {{ var:heir_ed_ideology >= 4 }}
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t50 = {{ set_ideology = ideology:ideology_reformer }}
\t\t\t\t30 = {{ set_ideology = ideology:ideology_liberal }}
\t\t\t\t20 = {{ set_ideology = ideology:ideology_radical }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_ideology >= 1 }}
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t40 = {{ set_ideology = ideology:ideology_reformer }}
\t\t\t\t35 = {{ set_ideology = ideology:ideology_moderate }}
\t\t\t\t25 = {{ set_ideology = ideology:ideology_liberal }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_ideology <= -4 }}
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t50 = {{ set_ideology = ideology:ideology_traditionalist }}
\t\t\t\t30 = {{ set_ideology = ideology:ideology_patriarchal }}
\t\t\t\t20 = {{ set_ideology = ideology:ideology_orthodox }}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{ var:heir_ed_ideology <= -1 }}
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t40 = {{ set_ideology = ideology:ideology_traditionalist }}
\t\t\t\t35 = {{ set_ideology = ideology:ideology_moderate }}
\t\t\t\t25 = {{ set_ideology = ideology:ideology_patriarchal }}
\t\t\t}}
\t\t}}
\t}}
\telse = {{
\t\t# Neutral ideology
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t50 = {{ set_ideology = ideology:ideology_moderate }}
\t\t\t\t20 = {{ set_ideology = ideology:ideology_reformer }}
\t\t\t\t20 = {{ set_ideology = ideology:ideology_traditionalist }}
\t\t\t\t10 = {{ set_ideology = ideology:ideology_liberal }}
\t\t\t}}
\t\t}}
\t}}

\t# ─── Resolve IG Alignment ───
\t# Compares radical vs moderate vs regressive investment
\t# Winner's magnitude determines alignment strength
\tif = {{
\t\tlimit = {{
\t\t\tvar:heir_ed_ig_radical >= var:heir_ed_ig_moderate
\t\t\tvar:heir_ed_ig_radical >= var:heir_ed_ig_regressive
\t\t\tvar:heir_ed_ig_radical >= 1
\t\t}}
\t\t# Radical wins
\t\tif = {{
\t\t\tlimit = {{ var:heir_ed_ig_radical >= 4 }}
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t40 = {{ set_interest_group_type = ig_type:ig_trade_unions }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_intelligentsia }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_rural_folk }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\telse = {{
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_trade_unions }}
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_intelligentsia }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_rural_folk }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{
\t\t\tvar:heir_ed_ig_moderate >= var:heir_ed_ig_radical
\t\t\tvar:heir_ed_ig_moderate >= var:heir_ed_ig_regressive
\t\t\tvar:heir_ed_ig_moderate >= 1
\t\t}}
\t\t# Moderate wins
\t\tif = {{
\t\t\tlimit = {{ var:heir_ed_ig_moderate >= 4 }}
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t40 = {{ set_interest_group_type = ig_type:ig_industrialists }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_petty_bourgeoisie }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_armed_forces }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\telse = {{
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_industrialists }}
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_petty_bourgeoisie }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_armed_forces }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
\telse_if = {{
\t\tlimit = {{
\t\t\tvar:heir_ed_ig_regressive >= var:heir_ed_ig_radical
\t\t\tvar:heir_ed_ig_regressive >= var:heir_ed_ig_moderate
\t\t\tvar:heir_ed_ig_regressive >= 1
\t\t}}
\t\t# Regressive wins
\t\tif = {{
\t\t\tlimit = {{ var:heir_ed_ig_regressive >= 4 }}
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t40 = {{ set_interest_group_type = ig_type:ig_landowners }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_devout }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_rural_folk }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t\telse = {{
\t\t\their ?= {{
\t\t\t\trandom_list = {{
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_landowners }}
\t\t\t\t\t35 = {{ set_interest_group_type = ig_type:ig_devout }}
\t\t\t\t\t30 = {{ set_interest_group_type = ig_type:ig_rural_folk }}
\t\t\t\t}}
\t\t\t}}
\t\t}}
\t}}
\telse = {{
\t\t# No clear winner - random IG
\t\their ?= {{
\t\t\trandom_list = {{
\t\t\t\t15 = {{ set_interest_group_type = ig_type:ig_industrialists }}
\t\t\t\t15 = {{ set_interest_group_type = ig_type:ig_landowners }}
\t\t\t\t14 = {{ set_interest_group_type = ig_type:ig_intelligentsia }}
\t\t\t\t14 = {{ set_interest_group_type = ig_type:ig_devout }}
\t\t\t\t14 = {{ set_interest_group_type = ig_type:ig_trade_unions }}
\t\t\t\t14 = {{ set_interest_group_type = ig_type:ig_armed_forces }}
\t\t\t\t14 = {{ set_interest_group_type = ig_type:ig_rural_folk }}
\t\t\t}}
\t\t}}
\t}}

\t# ─── Mark heir as educated ───
\their ?= {{
\t\tset_variable = received_education
\t}}
}}

# ──────────────────────── IG REACTION EFFECTS ────────────────────────
# Called by gain effects when investments advance

heir_education_admin_ig_reaction = {{
\tig:ig_industrialists = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_armed_forces = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_diplo_ig_reaction = {{
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_military_ig_reaction = {{
\tig:ig_armed_forces = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_progressive_ig_reaction = {{
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_trade_unions = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_devout = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_landowners = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_conservative_ig_reaction = {{
\tig:ig_devout = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_landowners = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_trade_unions = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_radical_ig_reaction = {{
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_rural_folk = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_trade_unions = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_landowners = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_devout = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_moderate_ig_reaction = {{
\tig:ig_industrialists = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_petty_bourgeoisie = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_armed_forces = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

heir_education_regressive_ig_reaction = {{
\tig:ig_landowners = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_devout = {{
\t\tadd_modifier = {{ name = ig_approval_positive_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_intelligentsia = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
\tig:ig_trade_unions = {{
\t\tadd_modifier = {{ name = ig_approval_negative_modifier days = short_modifier_time is_decaying = yes }}
\t}}
}}

# ──────────────────────── CLEANUP ────────────────────────

heir_education_cleanup_effect = {{
\tremove_variable = heir_ed_admin
\tremove_variable = heir_ed_diplo
\tremove_variable = heir_ed_military
\tremove_variable = heir_ed_ideology
\tremove_variable = heir_ed_ig_radical
\tremove_variable = heir_ed_ig_moderate
\tremove_variable = heir_ed_ig_regressive
\tremove_variable = heir_ed_total
\tremove_variable = heir_ed_intelligence
\t# Focus variables
\tif = {{ limit = {{ has_variable = heir_ed_focus_admin }} remove_variable = heir_ed_focus_admin }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_diplo }} remove_variable = heir_ed_focus_diplo }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_military }} remove_variable = heir_ed_focus_military }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_progressive }} remove_variable = heir_ed_focus_progressive }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_conservative }} remove_variable = heir_ed_focus_conservative }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_radical }} remove_variable = heir_ed_focus_radical }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_moderate }} remove_variable = heir_ed_focus_moderate }}
\tif = {{ limit = {{ has_variable = heir_ed_focus_regressive }} remove_variable = heir_ed_focus_regressive }}
\t# Modifiers
\tif = {{ limit = {{ has_modifier = heir_education_innovation_cost }} remove_modifier = heir_education_innovation_cost }}
\tif = {{ limit = {{ has_modifier = heir_education_grace_period }} remove_modifier = heir_education_grace_period }}
\tif = {{ limit = {{ has_modifier = heir_education_event_cooldown }} remove_modifier = heir_education_event_cooldown }}
}}

# ──────────────────────── NON-HEIR TRAIT ASSIGNMENT ────────────────────────
# Assigns aptitude traits to adult characters who lack them.
# 5-tier distribution for characters without formal education.
# Generals/admirals biased toward better military traits.

assign_aptitude_traits_effect = {{
\t# Administrative trait
\tevery_scope_character = {{
\t\tlimit = {{
\t\t\tNOT = {{ age < define:NCharacters|ADULT_AGE }}
\t\t\tOR = {{
\t\t\t\tis_ruler = yes
\t\t\t\thas_role = politician
\t\t\t\thas_role = agitator
\t\t\t\thas_role = general
\t\t\t\thas_role = admiral
\t\t\t}}
\t\t\tNOR = {{
\t\t\t\thas_trait = ruler_terrible_administrator
\t\t\t\thas_trait = ruler_poor_administrator
\t\t\t\thas_trait = ruler_average_administrator
\t\t\t\thas_trait = ruler_skilled_administrator
\t\t\t\thas_trait = ruler_exceptional_administrator
\t\t\t}}
\t\t}}
\t\trandom_list = {{
\t\t\t20 = {{ add_trait = ruler_terrible_administrator }}
\t\t\t30 = {{ add_trait = ruler_poor_administrator }}
\t\t\t35 = {{ add_trait = ruler_average_administrator }}
\t\t\t12 = {{ add_trait = ruler_skilled_administrator }}
\t\t\t3 = {{ add_trait = ruler_exceptional_administrator }}
\t\t}}
\t}}

\t# Diplomatic trait
\tevery_scope_character = {{
\t\tlimit = {{
\t\t\tNOT = {{ age < define:NCharacters|ADULT_AGE }}
\t\t\tOR = {{
\t\t\t\tis_ruler = yes
\t\t\t\thas_role = politician
\t\t\t\thas_role = agitator
\t\t\t\thas_role = general
\t\t\t\thas_role = admiral
\t\t\t}}
\t\t\tNOR = {{
\t\t\t\thas_trait = ruler_terrible_diplomat
\t\t\t\thas_trait = ruler_poor_diplomat
\t\t\t\thas_trait = ruler_average_diplomat
\t\t\t\thas_trait = ruler_skilled_diplomat
\t\t\t\thas_trait = ruler_exceptional_diplomat
\t\t\t}}
\t\t}}
\t\trandom_list = {{
\t\t\t20 = {{ add_trait = ruler_terrible_diplomat }}
\t\t\t30 = {{ add_trait = ruler_poor_diplomat }}
\t\t\t35 = {{ add_trait = ruler_average_diplomat }}
\t\t\t12 = {{ add_trait = ruler_skilled_diplomat }}
\t\t\t3 = {{ add_trait = ruler_exceptional_diplomat }}
\t\t}}
\t}}

\t# Military trait - biased toward skilled/exceptional for generals/admirals
\tevery_scope_character = {{
\t\tlimit = {{
\t\t\tNOT = {{ age < define:NCharacters|ADULT_AGE }}
\t\t\tOR = {{
\t\t\t\tis_ruler = yes
\t\t\t\thas_role = politician
\t\t\t\thas_role = agitator
\t\t\t\thas_role = general
\t\t\t\thas_role = admiral
\t\t\t}}
\t\t\tNOR = {{
\t\t\t\thas_trait = ruler_terrible_commander
\t\t\t\thas_trait = ruler_poor_commander
\t\t\t\thas_trait = ruler_average_commander
\t\t\t\thas_trait = ruler_skilled_commander
\t\t\t\thas_trait = ruler_exceptional_commander
\t\t\t}}
\t\t}}
\t\tif = {{
\t\t\tlimit = {{
\t\t\t\tOR = {{
\t\t\t\t\thas_role = general
\t\t\t\t\thas_role = admiral
\t\t\t\t}}
\t\t\t}}
\t\t\trandom_list = {{
\t\t\t\t5 = {{ add_trait = ruler_terrible_commander }}
\t\t\t\t15 = {{ add_trait = ruler_poor_commander }}
\t\t\t\t30 = {{ add_trait = ruler_average_commander }}
\t\t\t\t35 = {{ add_trait = ruler_skilled_commander }}
\t\t\t\t15 = {{ add_trait = ruler_exceptional_commander }}
\t\t\t}}
\t\t}}
\t\telse = {{
\t\t\trandom_list = {{
\t\t\t\t20 = {{ add_trait = ruler_terrible_commander }}
\t\t\t\t30 = {{ add_trait = ruler_poor_commander }}
\t\t\t\t35 = {{ add_trait = ruler_average_commander }}
\t\t\t\t12 = {{ add_trait = ruler_skilled_commander }}
\t\t\t\t3 = {{ add_trait = ruler_exceptional_commander }}
\t\t\t}}
\t\t}}
\t}}
}}"""
    
    return content


# ═══════════════════════════════════════════════════════════════
#  2. JOURNAL ENTRY
# ═══════════════════════════════════════════════════════════════

def generate_je():
    """Generate the complete je_heir_education.txt"""
    
    # Build the monthly pulse focus blocks
    focuses = [
        ("admin", "heir_ed_gain_admin"),
        ("diplo", "heir_ed_gain_diplo"),
        ("military", "heir_ed_gain_military"),
        ("progressive", "heir_ed_gain_progressive"),
        ("conservative", "heir_ed_gain_conservative"),
        ("radical", "heir_ed_gain_radical"),
        ("moderate", "heir_ed_gain_moderate"),
        ("regressive", "heir_ed_gain_regressive"),
    ]
    
    focus_blocks = []
    for focus_name, gain_effect in focuses:
        focus_blocks.append(f"""\t\t\t# {focus_name.title()} focus
\t\t\tif = {{
\t\t\t\tlimit = {{ has_variable = heir_ed_focus_{focus_name} }}
\t\t\t\trandom_list = {{
\t\t\t\t\t3 = {{ {gain_effect} = yes }}
\t\t\t\t\t97 = {{ }}
\t\t\t\t}}
\t\t\t}}""")
    
    focus_section = "\n".join(focus_blocks)
    
    content = f"""### Heir Education Journal Entry
### Reworked: 3% base monthly pulse (down from 5%), intelligence-modified gains,
### adult heir pre-initialization, 5-tier trait resolution, rebel child mechanic.

je_heir_education = {{
\ticon = "gfx/interface/icons/event_icons/event_portrait.dds"
\tgroup = je_group_internal_affairs

\tis_shown_when_inactive = {{
\t\thas_law = law_type:law_monarchy
\t}}

\tpossible = {{
\t\thas_law = law_type:law_monarchy
\t\texists = heir
\t\their ?= {{
\t\t\tNOT = {{ has_variable = received_education }}
\t\t}}
\t}}

\tscripted_progress_bar = heir_education_progress_bar

\t# Toggle buttons - enable/disable pairs (only one of each pair visible at a time)
\tscripted_button = he_enable_admin_focus
\tscripted_button = he_disable_admin_focus
\tscripted_button = he_enable_diplo_focus
\tscripted_button = he_disable_diplo_focus
\tscripted_button = he_enable_military_focus
\tscripted_button = he_disable_military_focus
\tscripted_button = he_enable_progressive
\tscripted_button = he_disable_progressive
\tscripted_button = he_enable_conservative
\tscripted_button = he_disable_conservative
\tscripted_button = he_enable_radical
\tscripted_button = he_disable_radical
\tscripted_button = he_enable_moderate
\tscripted_button = he_disable_moderate
\tscripted_button = he_enable_regressive
\tscripted_button = he_disable_regressive

\timmediate = {{
\t\tset_variable = {{ name = heir_ed_admin value = 0 }}
\t\tset_variable = {{ name = heir_ed_diplo value = 0 }}
\t\tset_variable = {{ name = heir_ed_military value = 0 }}
\t\tset_variable = {{ name = heir_ed_ideology value = 0 }}
\t\tset_variable = {{ name = heir_ed_ig_radical value = 0 }}
\t\tset_variable = {{ name = heir_ed_ig_moderate value = 0 }}
\t\tset_variable = {{ name = heir_ed_ig_regressive value = 0 }}
\t\tset_variable = {{ name = heir_ed_total value = 0 }}
\t\t# Hidden intelligence score (1-5): affects gain amount per pulse tick
\t\t# Higher = faster learning, but player never sees exact value
\t\trandom_list = {{
\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 1 }} }}
\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 2 }} }}
\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 3 }} }}
\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 4 }} }}
\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 5 }} }}
\t\t}}
\t\their ?= {{
\t\t\tset_variable = being_educated
\t\t}}
\t\t# Pre-initialize adult heirs based on their age
\t\their_education_init_adult = yes
\t\t# Update progress bar with any pre-initialized total
\t\tscope:journal_entry = {{
\t\t\tset_bar_progress = {{ name = heir_education_progress_bar value = root.var:heir_ed_total }}
\t\t}}
\t\t# Grace period prevents instant completion for adult heirs
\t\tadd_modifier = {{ name = heir_education_grace_period days = 365 }}
\t}}

\tcomplete = {{
\t\texists = heir
\t\their ?= {{
\t\t\thas_variable = being_educated
\t\t\tNOT = {{ age < define:NCharacters|ADULT_AGE }}
\t\t}}
\t\tNOT = {{ has_modifier = heir_education_grace_period }}
\t}}

\ton_complete = {{
\t\their_education_resolve_effect = yes
\t\their_education_cleanup_effect = yes
\t}}

\t# If the heir changes (dies, replaced), detect and reset
\ton_monthly_pulse = {{
\t\teffect = {{
\t\t\t# ─── Heir change detection ───
\t\t\tif = {{
\t\t\t\tlimit = {{
\t\t\t\t\tOR = {{
\t\t\t\t\t\tNOT = {{ exists = heir }}
\t\t\t\t\t\their ?= {{ NOT = {{ has_variable = being_educated }} }}
\t\t\t\t\t}}
\t\t\t\t\thas_variable = heir_ed_total
\t\t\t\t}}
\t\t\t\tset_variable = {{ name = heir_ed_admin value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_diplo value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_military value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_ideology value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_ig_radical value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_ig_moderate value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_ig_regressive value = 0 }}
\t\t\t\tset_variable = {{ name = heir_ed_total value = 0 }}
\t\t\t\t# Re-roll intelligence for new heir
\t\t\t\trandom_list = {{
\t\t\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 1 }} }}
\t\t\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 2 }} }}
\t\t\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 3 }} }}
\t\t\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 4 }} }}
\t\t\t\t\t20 = {{ set_variable = {{ name = heir_ed_intelligence value = 5 }} }}
\t\t\t\t}}
\t\t\t\t# Clear focus variables
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_admin }} remove_variable = heir_ed_focus_admin }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_diplo }} remove_variable = heir_ed_focus_diplo }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_military }} remove_variable = heir_ed_focus_military }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_progressive }} remove_variable = heir_ed_focus_progressive }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_conservative }} remove_variable = heir_ed_focus_conservative }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_radical }} remove_variable = heir_ed_focus_radical }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_moderate }} remove_variable = heir_ed_focus_moderate }}
\t\t\t\tif = {{ limit = {{ has_variable = heir_ed_focus_regressive }} remove_variable = heir_ed_focus_regressive }}
\t\t\t\tscope:journal_entry = {{
\t\t\t\t\tset_bar_progress = {{ name = heir_education_progress_bar value = 0 }}
\t\t\t\t}}
\t\t\t\tif = {{
\t\t\t\t\tlimit = {{ exists = heir }}
\t\t\t\t\their ?= {{
\t\t\t\t\t\tset_variable = being_educated
\t\t\t\t\t}}
\t\t\t\t\t# Pre-initialize for new adult heir
\t\t\t\t\their_education_init_adult = yes
\t\t\t\t\tscope:journal_entry = {{
\t\t\t\t\t\tset_bar_progress = {{ name = heir_education_progress_bar value = root.var:heir_ed_total }}
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}}

\t\t\t# ─── Monthly investment processing ───
\t\t\t# Each active focus has a 3% chance per month to trigger a gain.
\t\t\t# Gain amount is modified by hidden intelligence score.
{focus_section}

\t\t\t# ─── Random education events ───
\t\t\trandom_list = {{
\t\t\t\t2 = {{
\t\t\t\t\ttrigger = {{
\t\t\t\t\t\tNOT = {{ has_modifier = heir_education_event_cooldown }}
\t\t\t\t\t\thas_variable = heir_ed_total
\t\t\t\t\t\tvar:heir_ed_total >= 2
\t\t\t\t\t}}
\t\t\t\t\ttrigger_event = {{ id = heir_education_events.1 }}
\t\t\t\t\tadd_modifier = {{ name = heir_education_event_cooldown days = 365 }}
\t\t\t\t}}
\t\t\t\t2 = {{
\t\t\t\t\ttrigger = {{
\t\t\t\t\t\tNOT = {{ has_modifier = heir_education_event_cooldown }}
\t\t\t\t\t\thas_variable = heir_ed_total
\t\t\t\t\t\tvar:heir_ed_total >= 1
\t\t\t\t\t}}
\t\t\t\t\ttrigger_event = {{ id = heir_education_events.2 }}
\t\t\t\t\tadd_modifier = {{ name = heir_education_event_cooldown days = 365 }}
\t\t\t\t}}
\t\t\t\t2 = {{
\t\t\t\t\ttrigger = {{
\t\t\t\t\t\tNOT = {{ has_modifier = heir_education_event_cooldown }}
\t\t\t\t\t\thas_variable = heir_ed_total
\t\t\t\t\t\tvar:heir_ed_total >= 3
\t\t\t\t\t\tany_country = {{
\t\t\t\t\t\t\thas_treaty_alliance_with = {{ TARGET = ROOT }}
\t\t\t\t\t\t}}
\t\t\t\t\t}}
\t\t\t\t\ttrigger_event = {{ id = heir_education_events.3 }}
\t\t\t\t\tadd_modifier = {{ name = heir_education_event_cooldown days = 365 }}
\t\t\t\t}}
\t\t\t\t94 = {{ }}
\t\t\t}}
\t\t}}
\t}}

\tinvalid = {{
\t\tNOT = {{ has_law = law_type:law_monarchy }}
\t}}

\tprogressbar = no
\tshould_be_pinned_by_default = yes

\tstatus_desc = {{
\t\tfirst_valid = {{
\t\t\ttriggered_desc = {{
\t\t\t\tdesc = je_heir_education_status_no_focus
\t\t\t\ttrigger = {{
\t\t\t\t\tNOR = {{
\t\t\t\t\t\thas_variable = heir_ed_focus_admin
\t\t\t\t\t\thas_variable = heir_ed_focus_diplo
\t\t\t\t\t\thas_variable = heir_ed_focus_military
\t\t\t\t\t\thas_variable = heir_ed_focus_progressive
\t\t\t\t\t\thas_variable = heir_ed_focus_conservative
\t\t\t\t\t\thas_variable = heir_ed_focus_radical
\t\t\t\t\t\thas_variable = heir_ed_focus_moderate
\t\t\t\t\t\thas_variable = heir_ed_focus_regressive
\t\t\t\t\t}}
\t\t\t\t}}
\t\t\t}}
\t\t\ttriggered_desc = {{
\t\t\t\tdesc = je_heir_education_status_bright
\t\t\t\ttrigger = {{
\t\t\t\t\tvar:heir_ed_intelligence >= 4
\t\t\t\t}}
\t\t\t}}
\t\t\ttriggered_desc = {{
\t\t\t\tdesc = je_heir_education_status_slow
\t\t\t\ttrigger = {{
\t\t\t\t\tvar:heir_ed_intelligence <= 2
\t\t\t\t}}
\t\t\t}}
\t\t\ttriggered_desc = {{
\t\t\t\tdesc = je_heir_education_status_active
\t\t\t\ttrigger = {{ always = yes }}
\t\t\t}}
\t\t}}
\t}}

\tweight = 100

\ttimeout = 5475 # 15 years - safety fallback
\ton_timeout = {{
\t\their_education_resolve_effect = yes
\t\their_education_cleanup_effect = yes
\t}}

\tcurrent_value = {{
\t\tvalue = var:heir_ed_total
\t}}

\tgoal_add_value = {{
\t\tvalue = 20
\t}}
}}"""
    
    return content


# ═══════════════════════════════════════════════════════════════
#  3. PROGRESS BAR
# ═══════════════════════════════════════════════════════════════

def generate_progress_bar():
    return """heir_education_progress_bar = {
\tstart_value = 0
\tmin_value = 0
\tmax_value = 20
\tdefault_green = yes
}"""


# ═══════════════════════════════════════════════════════════════
#  4. TERRIBLE TRAITS - inserted into ruler_aptitude_traits.txt
# ═══════════════════════════════════════════════════════════════

TERRIBLE_ADMIN = """ruler_terrible_administrator = {
\ttype = condition
\ttexture = "gfx/interface/icons/character_trait_icons/imposing.dds"

\tcharacter_modifier = {
\t\tcharacter_popularity_add = -20
\t}

\tcommand_modifier = {
\t}

\tcountry_modifier = {
\t\tcountry_bureaucracy_mult = -0.20
\t\tstate_tax_capacity_mult = -0.20
\t\tcountry_legitimacy_base_add = -10
\t}

\tagitator_modifier = {
\t}

\tinterest_group_modifier = {
\t\tinterest_group_pol_str_mult = -0.10
\t}

\texecutive_modifier = {
\t\tbuilding_throughput_add = -0.05
\t}

\tpossible = {
\t\tNOT = { age < define:NCharacters|ADULT_AGE }
\t\tOR = {
\t\t\thas_role = politician
\t\t\thas_role = agitator
\t\t\tis_ruler = yes
\t\t\tis_heir = yes
\t\t}
\t}

\tweight = {
\t\tvalue = 0
\t}

\treplace = {
\t\truler_poor_administrator
\t\truler_average_administrator
\t\truler_skilled_administrator
\t\truler_exceptional_administrator
\t}
}
"""

TERRIBLE_DIPLOMAT = """ruler_terrible_diplomat = {
\ttype = condition
\ttexture = "gfx/interface/icons/character_trait_icons/cruel.dds"

\tcharacter_modifier = {
\t\tcharacter_popularity_add = -15
\t}

\tcommand_modifier = {
\t}

\tcountry_modifier = {
\t\tcountry_prestige_mult = -0.20
\t\tcountry_diplomatic_reputation_add = -10
\t\tcountry_infamy_generation_mult = 0.20
\t\tinterest_group_amenability_add = -10
\t}

\tagitator_modifier = {
\t}

\tinterest_group_modifier = {
\t\tinterest_group_pop_attraction_mult = -0.10
\t}

\texecutive_modifier = {
\t}

\tpossible = {
\t\tNOT = { age < define:NCharacters|ADULT_AGE }
\t\tOR = {
\t\t\thas_role = politician
\t\t\thas_role = agitator
\t\t\tis_ruler = yes
\t\t\tis_heir = yes
\t\t}
\t}

\tweight = {
\t\tvalue = 0
\t}

\treplace = {
\t\truler_poor_diplomat
\t\truler_average_diplomat
\t\truler_skilled_diplomat
\t\truler_exceptional_diplomat
\t}
}
"""

TERRIBLE_COMMANDER = """ruler_terrible_commander = {
\ttype = condition
\ttexture = "gfx/interface/icons/character_trait_icons/wrathful.dds"

\tcharacter_modifier = {
\t\tcharacter_popularity_add = -15
\t}

\tcommand_modifier = {
\t\tunit_offense_mult = -0.15
\t\tunit_defense_mult = -0.15
\t}

\tcountry_modifier = {
\t\tcountry_war_exhaustion_casualties_mult = 0.20
\t\tunit_morale_loss_mult = 0.4
\t\tunit_experience_gain_mult = -0.4
\t\tinterest_group_ig_armed_forces_approval_add = -5
\t\tinterest_group_ig_armed_forces_pop_attraction_mult = -0.10
\t}

\tagitator_modifier = {
\t}

\tinterest_group_modifier = {
\t}

\texecutive_modifier = {
\t}

\tpossible = {
\t\tNOT = { age < define:NCharacters|ADULT_AGE }
\t\tOR = {
\t\t\thas_role = politician
\t\t\thas_role = agitator
\t\t\thas_role = general
\t\t\thas_role = admiral
\t\t\tis_ruler = yes
\t\t\tis_heir = yes
\t\t}
\t}

\tweight = {
\t\tvalue = 0
\t}

\treplace = {
\t\truler_poor_commander
\t\truler_average_commander
\t\truler_skilled_commander
\t\truler_exceptional_commander
\t}
}
"""


# ═══════════════════════════════════════════════════════════════
#  5. LOCALIZATION KEYS
# ═══════════════════════════════════════════════════════════════

LOC_KEYS = """
 ruler_terrible_administrator:0 "Terrible Administrator"
 ruler_terrible_administrator_desc:0 "An utterly incompetent ruler with no grasp of governance whatsoever. The bureaucracy is in shambles, records are lost, and even basic administration grinds to a halt."
 ruler_terrible_diplomat:0 "Terrible Diplomat"
 ruler_terrible_diplomat_desc:0 "A ruler spectacularly unsuited for diplomacy. Foreign envoys leave insulted, alliances crumble, and the nation's reputation suffers at every turn."
 ruler_terrible_commander:0 "Terrible Commander"
 ruler_terrible_commander_desc:0 "A military leader of breathtaking incompetence. Troops are mismanaged, battles are lost through sheer blundering, and soldiers lose faith in the chain of command."
 je_heir_education_status_bright:0 "#bold The heir is a quick study.#! Education is progressing well."
 je_heir_education_status_slow:0 "#bold The heir struggles to grasp concepts.#! Education makes slow progress."
 HEIR_ED_REBEL_CHILD:0 "#R The heir has developed their own radical views, defying their education!#!"
"""


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("Heir Education Rework - Implementation")
    print("=" * 50)
    
    # 1. Write effects file
    effects_path = os.path.join(MOD_ROOT, "common", "scripted_effects", "heir_education_effects.txt")
    write_bom(effects_path, generate_effects())
    
    # 2. Write JE file
    je_path = os.path.join(MOD_ROOT, "common", "journal_entries", "je_heir_education.txt")
    write_bom(je_path, generate_je())
    
    # 3. Write progress bar file
    pb_path = os.path.join(MOD_ROOT, "common", "scripted_progress_bars", "heir_education_progress_bars.txt")
    write_bom(pb_path, generate_progress_bar())
    
    # 4. Insert terrible traits into ruler_aptitude_traits.txt
    traits_path = os.path.join(MOD_ROOT, "common", "character_traits", "ruler_aptitude_traits.txt")
    with open(traits_path, 'r', encoding='utf-8-sig') as f:
        traits_content = f.read()
    
    # Insert terrible traits before each section's "poor" trait
    # Admin section
    traits_content = traits_content.replace(
        "ruler_poor_administrator = {",
        TERRIBLE_ADMIN + "ruler_poor_administrator = {"
    )
    # Diplomat section
    traits_content = traits_content.replace(
        "ruler_poor_diplomat = {",
        TERRIBLE_DIPLOMAT + "ruler_poor_diplomat = {"
    )
    # Commander section
    traits_content = traits_content.replace(
        "ruler_poor_commander = {",
        TERRIBLE_COMMANDER + "ruler_poor_commander = {"
    )
    
    # Update replace lists in all 12 existing traits to include terrible variants
    # Admin traits
    for trait in ["ruler_poor_administrator", "ruler_average_administrator", 
                  "ruler_skilled_administrator", "ruler_exceptional_administrator"]:
        old_replace = f"replace = {{\n"
        # Find the replace block for this trait and add terrible
        # Look for the replace block that's inside this specific trait
        # We need to add ruler_terrible_administrator to the replace list
        pass
    
    # Simpler approach: just do targeted replacements
    admin_replace_additions = [
        ("ruler_poor_administrator", "ruler_terrible_administrator"),
        ("ruler_average_administrator", "ruler_terrible_administrator"),
        ("ruler_skilled_administrator", "ruler_terrible_administrator"),
        ("ruler_exceptional_administrator", "ruler_terrible_administrator"),
    ]
    diplo_replace_additions = [
        ("ruler_poor_diplomat", "ruler_terrible_diplomat"),
        ("ruler_average_diplomat", "ruler_terrible_diplomat"),
        ("ruler_skilled_diplomat", "ruler_terrible_diplomat"),
        ("ruler_exceptional_diplomat", "ruler_terrible_diplomat"),
    ]
    commander_replace_additions = [
        ("ruler_poor_commander", "ruler_terrible_commander"),
        ("ruler_average_commander", "ruler_terrible_commander"),
        ("ruler_skilled_commander", "ruler_terrible_commander"),
        ("ruler_exceptional_commander", "ruler_terrible_commander"),
    ]
    
    all_additions = admin_replace_additions + diplo_replace_additions + commander_replace_additions
    
    for trait_name, terrible_name in all_additions:
        # Find the replace block inside this trait's definition
        # Look for the trait definition, then find its replace = { block
        # Add the terrible trait name to the replace list
        
        # Strategy: find "replace = {" that comes after the trait definition
        # and add the terrible variant
        import re
        
        # Find the trait's replace block: it's the first "replace = {" block 
        # after the trait definition starts
        # We need to find the replace block that belongs to THIS trait specifically
        
        # Find all occurrences of the trait name in replace blocks and add terrible
        # Actually, the replace block structure is:
        # \treplace = {
        # \t\tother_trait_1
        # \t\tother_trait_2
        # \t\tother_trait_3
        # \t}
        # We need to add terrible variant to each trait's own replace block
        
        # Find the trait definition and its replace block
        # Pattern: after "trait_name = {" ... "replace = {" ... "}"
        pass
    
    # Better approach: parse and reconstruct replace blocks
    # For each existing trait, find its replace block and add the terrible variant
    
    import re
    
    def add_to_replace_block(content, trait_name, add_trait):
        """Add a trait to the replace block of a specific trait definition."""
        # Find the trait definition
        trait_start = content.find(f"{trait_name} = {{")
        if trait_start == -1:
            print(f"  WARNING: Could not find {trait_name}")
            return content
        
        # Find the replace block within this trait (search from trait_start)
        replace_pos = content.find("replace = {", trait_start)
        if replace_pos == -1:
            print(f"  WARNING: Could not find replace block for {trait_name}")
            return content
        
        # Make sure this replace block is within this trait definition
        # (not in the next trait's definition)
        next_trait = content.find("\n}", trait_start + len(trait_name) + 4)
        if replace_pos > next_trait:
            print(f"  WARNING: replace block found outside {trait_name} definition")
            return content
        
        # Find the closing brace of the replace block
        replace_close = content.find("}", replace_pos + len("replace = {"))
        
        # Insert the new trait before the closing brace
        insert_pos = replace_close
        # Add proper indentation
        insertion = f"\t\t{add_trait}\n\t"
        content = content[:insert_pos] + insertion + content[insert_pos:]
        
        return content
    
    for trait_name, terrible_name in all_additions:
        traits_content = add_to_replace_block(traits_content, trait_name, terrible_name)
    
    # Also need to update the NOR blocks in weight sections that check for traits
    # The weight sections often check "NOR = { has_trait = X has_trait = Y }"
    # These need to include terrible variants too
    # For poor_administrator's weight: check NOR for skilled/exceptional - add terrible check
    # Actually, the weight blocks determine natural acquisition probability.
    # terrible traits have weight 0 (only from education), so the weight NOR blocks
    # in other traits don't need to exclude terrible - a character with terrible 
    # would have it replaced by the replace block anyway.
    # So we don't need to modify weight blocks.
    
    write_bom(traits_path, traits_content)
    
    # 5. Append localization keys
    loc_path = os.path.join(MOD_ROOT, "localization", "english", "aaaaa_extra_l_english.yml")
    with open(loc_path, 'r', encoding='utf-8-sig') as f:
        loc_content = f.read()
    
    # Check if keys already exist
    if "ruler_terrible_administrator" not in loc_content:
        loc_content += LOC_KEYS
        write_bom(loc_path, loc_content)
        print("  Appended localization keys")
    else:
        print("  Localization keys already present")
    
    print("\n" + "=" * 50)
    print("Implementation complete!")
    print("\nFiles modified:")
    print("  - common/scripted_effects/heir_education_effects.txt (complete rewrite)")
    print("  - common/journal_entries/je_heir_education.txt (complete rewrite)")
    print("  - common/scripted_progress_bars/heir_education_progress_bars.txt (max 15→20)")
    print("  - common/character_traits/ruler_aptitude_traits.txt (added terrible tier)")
    print("  - localization/english/aaaaa_extra_l_english.yml (new keys)")
    print("\nReminder: Run organize_loc.py and verify BOM encoding")


if __name__ == "__main__":
    main()
