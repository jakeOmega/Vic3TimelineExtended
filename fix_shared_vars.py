"""
Fix shared variable conflicts in the space race system.

Issues fixed:
1. sr_failure_cooldown multi-decrement: Remove decrement from all 8 JE monthly pulses
2. sr_last_failed_milestone race condition: Replace with per-JE sr_failed_<m> flags  
3. sr_milestone_progress in events: Replace with per-JE variables for milestone-specific events,
   remove from generic events, expand for multi-milestone events
"""

import re
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# Milestone short names and their per-JE progress variables
MILESTONES = {
    'suborbital': 'sr_progress_suborbital',
    'orbital': 'sr_progress_orbital',
    'moon_landing': 'sr_progress_moon_landing',
    'probe': 'sr_progress_probe',
    'moon_base': 'sr_progress_moon_base',
    'mars_landing': 'sr_progress_mars_landing',
    'interstellar_probe': 'sr_progress_interstellar_probe',
    'solar_colonization': 'sr_progress_solar_colonization',
}

# Milestone number → short name (for sr_last_failed_milestone replacement)
MILESTONE_NUMS = {
    1: 'suborbital',
    2: 'orbital',
    3: 'moon_landing',
    4: 'probe',
    5: 'moon_base',
    6: 'mars_landing',
    7: 'interstellar_probe',
    8: 'solar_colonization',
}

# Event → milestone mapping for single-milestone events
SINGLE_MILESTONE_EVENTS = {
    30: 'suborbital',
    31: 'orbital',
    32: 'moon_landing',
    33: 'mars_landing',
    34: 'interstellar_probe',
    35: 'solar_colonization',
    36: 'moon_base',
    37: 'probe',
    42: 'mars_landing',
    45: 'probe',
    53: 'solar_colonization',
}

# Multi-milestone events → list of milestones they can fire for
MULTI_MILESTONE_EVENTS = {
    40: ['orbital', 'moon_landing', 'moon_base'],
    41: ['moon_base', 'mars_landing'],
    43: ['moon_base', 'mars_landing'],
    44: ['moon_landing', 'moon_base', 'mars_landing', 'solar_colonization'],
    46: ['moon_base', 'mars_landing'],
    47: ['orbital', 'probe', 'moon_base'],
    48: ['mars_landing', 'solar_colonization'],
    54: ['suborbital', 'orbital'],
    55: ['moon_base', 'mars_landing', 'solar_colonization'],
}

# "Any active milestone" events  
ANY_MILESTONE_EVENTS = [20, 49, 50, 52]

# Generic failure/setback events (remove sr_milestone_progress modifications)
GENERIC_EVENTS = list(range(10, 27))  # 10-26


def read_file(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8-sig') as f:
        return f.read()


def write_file(path, content):
    full = os.path.join(BASE, path)
    with open(full, 'w', encoding='utf-8-sig') as f:
        f.write(content)


def find_event_block(content, event_num):
    """Find start and end positions of a space_race_events.N = { ... } block."""
    pattern = rf'space_race_events\.{event_num}\s*=\s*\{{'
    match = re.search(pattern, content)
    if not match:
        return None, None
    # Count braces from the opening brace
    start = match.start()
    brace_count = 0
    for i in range(match.end() - 1, len(content)):
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                return start, i + 1
    return start, None


# ===================================================
# FIX 1: JE monthly pulse cooldown + milestone flags
# ===================================================
def fix_je_file():
    path = 'common/journal_entries/je_space_race.txt'
    content = read_file(path)
    
    # 1a. Remove cooldown decrement blocks from all 8 JEs
    # Pattern: 4-line block with comment + if/limit/change_variable
    cooldown_pattern = r'\n\t\t\t# Tick down failure cooldown\n\t\t\tif = \{\n\t\t\t\tlimit = \{ sr_has_failure_cooldown = yes \}\n\t\t\t\tchange_variable = \{ name = sr_failure_cooldown subtract = 1 \}\n\t\t\t\}'
    count = len(re.findall(cooldown_pattern, content))
    content = re.sub(cooldown_pattern, '', content)
    print(f"  Removed {count} cooldown decrement blocks")
    
    # 1b. Replace sr_last_failed_milestone with per-JE sr_failed_<m> flags
    for num, milestone in MILESTONE_NUMS.items():
        old = f'set_variable = {{ name = sr_last_failed_milestone value = {num} }}'
        new = f'set_variable = {{ name = sr_failed_{milestone} value = yes }}'
        count = content.count(old)
        content = content.replace(old, new)
        if count:
            print(f"  Replaced sr_last_failed_milestone={num} -> sr_failed_{milestone} ({count}x)")
    
    write_file(path, content)
    print(f"  Written: {path}")


# ===================================================
# FIX 2: Events file - sr_milestone_progress
# ===================================================
def fix_events_file():
    path = 'events/space_race_events.txt'
    content = read_file(path)
    
    # --- Pass 1: Single-milestone events (simple replacement) ---
    for event_id, milestone in SINGLE_MILESTONE_EVENTS.items():
        start, end = find_event_block(content, event_id)
        if start is None:
            print(f"  WARNING: Event {event_id} not found!")
            continue
        block = content[start:end]
        new_block = block.replace('sr_milestone_progress', MILESTONES[milestone])
        if block != new_block:
            count = block.count('sr_milestone_progress')
            content = content[:start] + new_block + content[end:]
            print(f"  Event {event_id}: replaced {count}x sr_milestone_progress -> {MILESTONES[milestone]}")
    
    # --- Pass 2: Generic events (remove sr_milestone_progress modifications) ---
    for event_id in GENERIC_EVENTS:
        start, end = find_event_block(content, event_id)
        if start is None:
            continue
        block = content[start:end]
        
        # Remove multi-line change_variable blocks for sr_milestone_progress
        # Pattern: change_variable = { name = sr_milestone_progress add/multiply/subtract = N }
        # Can be single-line or multi-line
        
        # Multi-line (3 lines):
        pattern_multiline = r'\n[ \t]*change_variable\s*=\s*\{[ \t]*\n[ \t]*name\s*=\s*sr_milestone_progress[ \t]*\n[ \t]*(?:add|multiply|subtract)\s*=\s*[\d.]+[ \t]*\n[ \t]*\}'
        matches = list(re.finditer(pattern_multiline, block))
        if matches:
            new_block = re.sub(pattern_multiline, '', block)
            content = content[:start] + new_block + content[end:]
            # Update end position for subsequent events
            end = start + len(new_block)
            print(f"  Event {event_id}: removed {len(matches)} sr_milestone_progress change_variable blocks")
            block = new_block
        
        # Also handle the if-wrapped version in event 20:
        # if = { limit = { has_variable = sr_active_milestone } change_variable { ... sr_milestone_progress ... } }
        if event_id == 20:
            start, end = find_event_block(content, event_id)
            if start:
                block = content[start:end]
                # Replace the if-wrapped progress boost with boost helper
                old_text = """if = {
			limit = { has_variable = sr_active_milestone }
			change_variable = {
				name = sr_milestone_progress
				add = 3
			}
		}"""
                new_text = """if = {
			limit = { has_variable = sr_active_milestone }
			set_variable = { name = sr_progress_boost value = 3 }
			sr_boost_active_milestones = yes
		}"""
                if old_text in block:
                    new_block = block.replace(old_text, new_text)
                    content = content[:start] + new_block + content[end:]
                    print(f"  Event 20: converted progress boost to sr_boost_active_milestones")
    
    # --- Pass 3: Multi-milestone events ---
    for event_id, milestones in MULTI_MILESTONE_EVENTS.items():
        start, end = find_event_block(content, event_id)
        if start is None:
            print(f"  WARNING: Multi-milestone event {event_id} not found!")
            continue
        block = content[start:end]
        
        if 'sr_milestone_progress' not in block:
            continue
        
        # Replace trigger: var:sr_milestone_progress >= N
        # Find the threshold value
        trigger_match = re.search(r'var:sr_milestone_progress\s*>=\s*(\d+)', block)
        if trigger_match:
            threshold = trigger_match.group(1)
            old_trigger = trigger_match.group(0)
            
            # Build OR block for per-JE progress checks
            or_lines = []
            for m in milestones:
                or_lines.append(f'\t\t\tAND = {{\n\t\t\t\thas_variable = sr_active_{m}\n\t\t\t\tvar:{MILESTONES[m]} >= {threshold}\n\t\t\t}}')
            new_trigger = 'OR = {\n' + '\n'.join(or_lines) + '\n\t\t}'
            
            # Replace the single-line trigger with the OR block
            block = block.replace(old_trigger, new_trigger, 1)
        
        # Replace effects: change_variable { name = sr_milestone_progress add/subtract = N }
        # Find all such blocks and replace with per-JE if-blocks
        effect_pattern = r'(\t+)change_variable\s*=\s*\{\s*\n(\t+)name\s*=\s*sr_milestone_progress\s*\n\t+(\w+)\s*=\s*([\d.]+)\s*\n\t+\}'
        
        def replace_effect(match):
            indent = match.group(1)
            op = match.group(3)  # add, subtract, multiply
            value = match.group(4)
            
            lines = []
            for m in milestones:
                lines.append(f'{indent}if = {{')
                lines.append(f'{indent}\tlimit = {{ has_variable = sr_active_{m} }}')
                lines.append(f'{indent}\tchange_variable = {{ name = {MILESTONES[m]} {op} = {value} }}')
                lines.append(f'{indent}}}')
            return '\n'.join(lines)
        
        new_block = re.sub(effect_pattern, replace_effect, block)
        
        if block != new_block:
            content = content[:start] + new_block + content[end:]
            # Recalculate end since block size changed
            end = start + len(new_block)
            print(f"  Event {event_id}: expanded to per-JE for {milestones}")
    
    # --- Pass 4: "Any milestone" events (49, 50, 52) ---
    for event_id in ANY_MILESTONE_EVENTS:
        if event_id == 20:
            continue  # Already handled above
        start, end = find_event_block(content, event_id)
        if start is None:
            print(f"  WARNING: Any-milestone event {event_id} not found!")
            continue
        block = content[start:end]
        
        if 'sr_milestone_progress' not in block:
            continue
        
        # Replace trigger threshold with a broad check (any active milestone has enough progress)
        trigger_match = re.search(r'var:sr_milestone_progress\s*>=\s*(\d+)', block)
        if trigger_match:
            threshold = trigger_match.group(1)
            old_trigger = trigger_match.group(0)
            
            # Build OR block checking all 8 milestones
            or_lines = []
            for m_name, m_var in MILESTONES.items():
                or_lines.append(f'\t\t\tAND = {{\n\t\t\t\thas_variable = sr_active_{m_name}\n\t\t\t\tvar:{m_var} >= {threshold}\n\t\t\t}}')
            new_trigger = 'OR = {\n' + '\n'.join(or_lines) + '\n\t\t}'
            block = block.replace(old_trigger, new_trigger, 1)
        
        # Replace effects: change_variable sr_milestone_progress add = N
        # with: set_variable + sr_boost_active_milestones
        effect_pattern = r'(\t+)change_variable\s*=\s*\{\s*\n(\t+)name\s*=\s*sr_milestone_progress\s*\n\t+(add)\s*=\s*([\d.]+)\s*\n\t+\}'
        
        def replace_any_effect(match):
            indent = match.group(1)
            value = match.group(4)
            lines = [
                f'{indent}set_variable = {{ name = sr_progress_boost value = {value} }}',
                f'{indent}sr_boost_active_milestones = yes',
            ]
            return '\n'.join(lines)
        
        new_block = re.sub(effect_pattern, replace_any_effect, block)
        
        # Handle subtract too
        sub_pattern = r'(\t+)change_variable\s*=\s*\{\s*\n(\t+)name\s*=\s*sr_milestone_progress\s*\n\t+(subtract)\s*=\s*([\d.]+)\s*\n\t+\}'
        
        def replace_any_sub(match):
            indent = match.group(1)
            value = match.group(4)
            lines = [
                f'{indent}set_variable = {{ name = sr_progress_boost value = -{value} }}',
                f'{indent}sr_boost_active_milestones = yes',
            ]
            return '\n'.join(lines)
        
        new_block = re.sub(sub_pattern, replace_any_sub, new_block)
        
        if block != new_block:
            content = content[:start] + new_block + content[end:]
            print(f"  Event {event_id}: converted to sr_boost_active_milestones")
    
    # --- Final check: any remaining sr_milestone_progress references ---
    remaining = [(m.start(), content[max(0,m.start()-50):m.end()+50]) 
                 for m in re.finditer(r'sr_milestone_progress', content)]
    if remaining:
        print(f"\n  WARNING: {len(remaining)} remaining sr_milestone_progress references:")
        for pos, ctx in remaining:
            # Find line number
            line_num = content[:pos].count('\n') + 1
            print(f"    Line {line_num}: ...{ctx.strip()[:80]}...")
    else:
        print(f"\n  All sr_milestone_progress references resolved!")
    
    write_file(path, content)
    print(f"  Written: {path}")


# ===================================================
# FIX 3: Scripted effects
# ===================================================
def fix_effects_file():
    path = 'common/scripted_effects/space_race_effects.txt'
    content = read_file(path)
    
    # 3a. Rewrite sr_switch_to_safe_effect to use per-JE flags
    old_switch = """sr_switch_to_safe_effect = {
	if = {
		limit = { has_variable = sr_last_failed_milestone }
		# Suborbital (1)
		if = {
			limit = { var:sr_last_failed_milestone = 1 }
			if = { limit = { has_variable = sr_ambitious_suborbital } remove_variable = sr_ambitious_suborbital }
			set_variable = { name = sr_safe_suborbital value = yes }
		}
		# Orbital (2)
		if = {
			limit = { var:sr_last_failed_milestone = 2 }
			if = { limit = { has_variable = sr_ambitious_orbital } remove_variable = sr_ambitious_orbital }
			set_variable = { name = sr_safe_orbital value = yes }
		}
		# Moon Landing (3)
		if = {
			limit = { var:sr_last_failed_milestone = 3 }
			if = { limit = { has_variable = sr_ambitious_moon_landing } remove_variable = sr_ambitious_moon_landing }
			set_variable = { name = sr_safe_moon_landing value = yes }
		}
		# Probe (4)
		if = {
			limit = { var:sr_last_failed_milestone = 4 }
			if = { limit = { has_variable = sr_ambitious_probe } remove_variable = sr_ambitious_probe }
			set_variable = { name = sr_safe_probe value = yes }
		}
		# Moon Base (5)
		if = {
			limit = { var:sr_last_failed_milestone = 5 }
			if = { limit = { has_variable = sr_ambitious_moon_base } remove_variable = sr_ambitious_moon_base }
			set_variable = { name = sr_safe_moon_base value = yes }
		}
		# Mars Landing (6)
		if = {
			limit = { var:sr_last_failed_milestone = 6 }
			if = { limit = { has_variable = sr_ambitious_mars_landing } remove_variable = sr_ambitious_mars_landing }
			set_variable = { name = sr_safe_mars_landing value = yes }
		}
		# Interstellar Probe (7)
		if = {
			limit = { var:sr_last_failed_milestone = 7 }
			if = { limit = { has_variable = sr_ambitious_interstellar_probe } remove_variable = sr_ambitious_interstellar_probe }
			set_variable = { name = sr_safe_interstellar_probe value = yes }
		}
		# Solar Colonization (8)
		if = {
			limit = { var:sr_last_failed_milestone = 8 }
			if = { limit = { has_variable = sr_ambitious_solar_colonization } remove_variable = sr_ambitious_solar_colonization }
			set_variable = { name = sr_safe_solar_colonization value = yes }
		}
		sr_recalculate_cost = yes
	}
}"""

    new_switch = """# Switch failed milestone(s) to safe approach using per-JE flags
# Each flag sr_failed_<m> is set in the monthly pulse before firing failure events
# Uses if (not else_if) so multiple simultaneous failures are all processed
sr_switch_to_safe_effect = {
	if = {
		limit = { has_variable = sr_failed_suborbital }
		if = { limit = { has_variable = sr_ambitious_suborbital } remove_variable = sr_ambitious_suborbital }
		set_variable = { name = sr_safe_suborbital value = yes }
		remove_variable = sr_failed_suborbital
	}
	if = {
		limit = { has_variable = sr_failed_orbital }
		if = { limit = { has_variable = sr_ambitious_orbital } remove_variable = sr_ambitious_orbital }
		set_variable = { name = sr_safe_orbital value = yes }
		remove_variable = sr_failed_orbital
	}
	if = {
		limit = { has_variable = sr_failed_moon_landing }
		if = { limit = { has_variable = sr_ambitious_moon_landing } remove_variable = sr_ambitious_moon_landing }
		set_variable = { name = sr_safe_moon_landing value = yes }
		remove_variable = sr_failed_moon_landing
	}
	if = {
		limit = { has_variable = sr_failed_probe }
		if = { limit = { has_variable = sr_ambitious_probe } remove_variable = sr_ambitious_probe }
		set_variable = { name = sr_safe_probe value = yes }
		remove_variable = sr_failed_probe
	}
	if = {
		limit = { has_variable = sr_failed_moon_base }
		if = { limit = { has_variable = sr_ambitious_moon_base } remove_variable = sr_ambitious_moon_base }
		set_variable = { name = sr_safe_moon_base value = yes }
		remove_variable = sr_failed_moon_base
	}
	if = {
		limit = { has_variable = sr_failed_mars_landing }
		if = { limit = { has_variable = sr_ambitious_mars_landing } remove_variable = sr_ambitious_mars_landing }
		set_variable = { name = sr_safe_mars_landing value = yes }
		remove_variable = sr_failed_mars_landing
	}
	if = {
		limit = { has_variable = sr_failed_interstellar_probe }
		if = { limit = { has_variable = sr_ambitious_interstellar_probe } remove_variable = sr_ambitious_interstellar_probe }
		set_variable = { name = sr_safe_interstellar_probe value = yes }
		remove_variable = sr_failed_interstellar_probe
	}
	if = {
		limit = { has_variable = sr_failed_solar_colonization }
		if = { limit = { has_variable = sr_ambitious_solar_colonization } remove_variable = sr_ambitious_solar_colonization }
		set_variable = { name = sr_safe_solar_colonization value = yes }
		remove_variable = sr_failed_solar_colonization
	}
	sr_recalculate_cost = yes
}"""

    if old_switch in content:
        content = content.replace(old_switch, new_switch)
        print("  Rewrote sr_switch_to_safe_effect for per-JE flags")
    else:
        print("  WARNING: Could not find sr_switch_to_safe_effect to replace!")
        print("  Trying to find it...")
        if 'sr_switch_to_safe_effect' in content:
            print("  Found sr_switch_to_safe_effect but text didn't match exactly")
    
    # 3b. Add sr_boost_active_milestones helper effect (before sr_complete_milestone_effect)
    boost_effect = """
# Boost progress for all active milestones
# Set sr_progress_boost before calling (can be negative for penalties)
sr_boost_active_milestones = {
	if = {
		limit = { has_variable = sr_active_suborbital }
		change_variable = { name = sr_progress_suborbital add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_orbital }
		change_variable = { name = sr_progress_orbital add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_moon_landing }
		change_variable = { name = sr_progress_moon_landing add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_probe }
		change_variable = { name = sr_progress_probe add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_moon_base }
		change_variable = { name = sr_progress_moon_base add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_mars_landing }
		change_variable = { name = sr_progress_mars_landing add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_interstellar_probe }
		change_variable = { name = sr_progress_interstellar_probe add = var:sr_progress_boost }
	}
	if = {
		limit = { has_variable = sr_active_solar_colonization }
		change_variable = { name = sr_progress_solar_colonization add = var:sr_progress_boost }
	}
	remove_variable = sr_progress_boost
}

"""
    
    # Insert before sr_complete_milestone_effect
    insert_marker = '# Called when a milestone is completed'
    if insert_marker in content:
        content = content.replace(insert_marker, boost_effect + insert_marker)
        print("  Added sr_boost_active_milestones helper effect")
    else:
        print("  WARNING: Could not find insertion point for sr_boost_active_milestones")
    
    write_file(path, content)
    print(f"  Written: {path}")


def main():
    print("=" * 60)
    print("Fixing space race shared variable conflicts")
    print("=" * 60)
    
    print("\n--- Fix 1: JE monthly pulse (cooldown + milestone flags) ---")
    fix_je_file()
    
    print("\n--- Fix 2: Events (sr_milestone_progress) ---")
    fix_events_file()
    
    print("\n--- Fix 3: Scripted effects ---")
    fix_effects_file()
    
    print("\n" + "=" * 60)
    print("Done!")


if __name__ == '__main__':
    main()
