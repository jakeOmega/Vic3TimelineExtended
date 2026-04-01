"""
Fix ai_chance blocks in Victoria 3 event files.

Converts if/limit/add syntax to modifier/trigger/add syntax.
Handles nested if blocks by flattening: outer limit conditions are
AND-combined with inner limit conditions.

Usage: python fix_ai_chance.py [--dry-run] <file1.txt> [file2.txt ...]
"""

import re
import sys
import os


def tokenize(text):
    """Simple tokenizer for Paradox script. Returns list of tokens."""
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        # Skip whitespace
        if c in ' \t\r\n':
            i += 1
            continue
        # Comments
        if c == '#':
            end = text.find('\n', i)
            if end == -1:
                end = len(text)
            tokens.append(('COMMENT', text[i:end]))
            i = end
            continue
        # Braces
        if c == '{':
            tokens.append(('LBRACE', '{'))
            i += 1
            continue
        if c == '}':
            tokens.append(('RBRACE', '}'))
            i += 1
            continue
        # = sign
        if c == '=':
            tokens.append(('EQ', '='))
            i += 1
            continue
        # >= <=
        if c == '>' and i + 1 < len(text) and text[i+1] == '=':
            tokens.append(('GEQ', '>='))
            i += 2
            continue
        if c == '<' and i + 1 < len(text) and text[i+1] == '=':
            tokens.append(('LEQ', '<='))
            i += 2
            continue
        if c == '>':
            tokens.append(('GT', '>'))
            i += 1
            continue
        if c == '<':
            tokens.append(('LT', '<'))
            i += 1
            continue
        # Quoted string
        if c == '"':
            end = text.find('"', i + 1)
            if end == -1:
                end = len(text)
            tokens.append(('STRING', text[i:end+1]))
            i = end + 1
            continue
        # Word/number (including identifiers with : . ? ! - @)
        if c.isalnum() or c in '_-@':
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] in '_-.:?!@'):
                j += 1
            tokens.append(('WORD', text[i:j]))
            i = j
            continue
        # Skip unknown chars
        i += 1
    return tokens


def find_matching_brace(tokens, start):
    """Find the index of the closing brace matching the opening brace at start."""
    depth = 0
    for i in range(start, len(tokens)):
        if tokens[i][0] == 'LBRACE':
            depth += 1
        elif tokens[i][0] == 'RBRACE':
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_block_content(tokens, start, end):
    """Reconstruct text from tokens[start:end]."""
    parts = []
    for t in tokens[start:end]:
        parts.append(t[1])
    return ' '.join(parts)


def collect_if_blocks(tokens, start, end):
    """
    Parse a block of tokens and collect if-blocks and standalone add/factor.
    Returns list of items, each being:
      ('if', limit_tokens, body_items)  -- an if block
      ('add', value)                     -- an add statement
      ('factor', value)                  -- a factor statement
      ('comment', text)                  -- a comment
    """
    items = []
    i = start
    while i < end:
        tok = tokens[i]
        # Comment
        if tok[0] == 'COMMENT':
            items.append(('comment', tok[1]))
            i += 1
            continue
        # if = { ... } or else_if = { ... }
        if tok[0] == 'WORD' and tok[1] in ('if', 'else_if'):
            # expect = {
            if i + 2 < end and tokens[i+1][0] == 'EQ' and tokens[i+2][0] == 'LBRACE':
                brace_end = find_matching_brace(tokens, i + 2)
                # Parse body between braces
                body_start = i + 3
                body_end = brace_end
                # Find limit block
                limit_tokens_list = []
                body_items = []
                j = body_start
                while j < body_end:
                    if tokens[j][0] == 'COMMENT':
                        body_items.append(('comment', tokens[j][1]))
                        j += 1
                        continue
                    if tokens[j][0] == 'WORD' and tokens[j][1] == 'limit':
                        if j + 2 < body_end and tokens[j+1][0] == 'EQ' and tokens[j+2][0] == 'LBRACE':
                            lb_end = find_matching_brace(tokens, j + 2)
                            limit_tokens_list = tokens[j+3:lb_end]
                            j = lb_end + 1
                            continue
                    if tokens[j][0] == 'WORD' and tokens[j][1] in ('add', 'factor'):
                        if j + 2 < body_end and tokens[j+1][0] == 'EQ':
                            body_items.append((tokens[j][1], tokens[j+2][1]))
                            j += 3
                            continue
                    if tokens[j][0] == 'WORD' and tokens[j][1] in ('if', 'else_if'):
                        if j + 2 < body_end and tokens[j+1][0] == 'EQ' and tokens[j+2][0] == 'LBRACE':
                            sub_brace_end = find_matching_brace(tokens, j + 2)
                            sub_items = collect_if_blocks(tokens, j, sub_brace_end + 1)
                            body_items.extend(sub_items)
                            j = sub_brace_end + 1
                            continue
                    j += 1
                items.append(('if', limit_tokens_list, body_items))
                i = brace_end + 1
                continue
        # Standalone add or factor
        if tok[0] == 'WORD' and tok[1] in ('add', 'factor'):
            if i + 2 < end and tokens[i+1][0] == 'EQ':
                items.append((tok[1], tokens[i+2][1]))
                i += 3
                continue
        i += 1
    return items


def flatten_if_to_modifiers(items, parent_triggers=None):
    """
    Recursively flatten if/limit/add items into modifier blocks.
    Returns list of (trigger_lines, add_or_factor, value, comments).
    """
    if parent_triggers is None:
        parent_triggers = []
    modifiers = []
    for item in items:
        if item[0] == 'comment':
            modifiers.append(item)
            continue
        if item[0] in ('add', 'factor'):
            if parent_triggers:
                modifiers.append(('modifier', parent_triggers[:], item[0], item[1]))
            else:
                modifiers.append(('bare', item[0], item[1]))
            continue
        if item[0] == 'if':
            limit_toks = item[1]
            body_items = item[2]
            # Build trigger string from limit tokens
            trigger_str = ' '.join(t[1] for t in limit_toks).strip()
            combined = parent_triggers + [trigger_str] if trigger_str else parent_triggers[:]
            # Check if body has any add/factor directly or nested ifs
            sub = flatten_if_to_modifiers(body_items, combined)
            modifiers.extend(sub)
    return modifiers


def format_trigger_content(trigger_str, base_indent):
    """Format trigger content with proper indentation using tokenization."""
    toks = tokenize(trigger_str)
    lines = []
    depth = 0
    i = 0
    while i < len(toks):
        t = toks[i]
        if t[0] == 'COMMENT':
            lines.append(base_indent + '\t' * depth + t[1])
            i += 1
            continue
        if t[0] == 'RBRACE':
            depth -= 1
            lines.append(base_indent + '\t' * depth + '}')
            i += 1
            continue
        # Collect a full statement: key op value or key op { ... }
        # Look ahead to see the pattern
        stmt_parts = [t[1]]
        j = i + 1
        # Collect until we hit a key that starts a new statement, or a brace
        if j < len(toks) and toks[j][0] in ('EQ', 'GEQ', 'LEQ', 'GT', 'LT'):
            stmt_parts.append(toks[j][1])
            j += 1
            if j < len(toks):
                if toks[j][0] == 'LBRACE':
                    # key = { ... }: put opening brace on same line
                    stmt_parts.append('{')
                    lines.append(base_indent + '\t' * depth + ' '.join(stmt_parts))
                    depth += 1
                    i = j + 1
                    continue
                else:
                    stmt_parts.append(toks[j][1])
                    j += 1
        lines.append(base_indent + '\t' * depth + ' '.join(stmt_parts))
        i = j
    return '\n'.join(lines)


def modifiers_to_text(modifiers, indent='\t\t\t'):
    """Convert flattened modifier list to formatted text."""
    lines = []
    for mod in modifiers:
        if mod[0] == 'comment':
            lines.append(indent + mod[1])
        elif mod[0] == 'bare':
            # bare add or factor (no trigger, just base-level)
            lines.append(f'{indent}{mod[1]} = {mod[2]}')
        elif mod[0] == 'modifier':
            trigger_parts = mod[1]
            op = mod[2]  # 'add' or 'factor'
            value = mod[3]
            # Single trigger or multiple?
            if len(trigger_parts) == 1 and '{' not in trigger_parts[0]:
                # Simple single-line trigger
                lines.append(f'{indent}modifier = {{')
                lines.append(f'{indent}\ttrigger = {{ {trigger_parts[0]} }}')
                lines.append(f'{indent}\t{op} = {value}')
                lines.append(f'{indent}}}')
            else:
                lines.append(f'{indent}modifier = {{')
                lines.append(f'{indent}\ttrigger = {{')
                for tp in trigger_parts:
                    # Format each trigger part
                    formatted = format_trigger_content(tp, indent + '\t\t')
                    lines.append(formatted)
                lines.append(f'{indent}\t}}')
                lines.append(f'{indent}\t{op} = {value}')
                lines.append(f'{indent}}}')
    return '\n'.join(lines)


def process_ai_chance_block(block_text, indent='\t\t'):
    """Convert an ai_chance block from if/limit/add to modifier/trigger/add."""
    tokens = tokenize(block_text)

    # Find base value
    base_val = None
    base_idx = None
    for i, t in enumerate(tokens):
        if t[0] == 'WORD' and t[1] == 'base' and i + 2 < len(tokens) and tokens[i+1][0] == 'EQ':
            base_val = tokens[i+2][1]
            base_idx = i + 3
            break

    if base_val is None:
        return None  # Can't process

    # Collect items after base
    items = collect_if_blocks(tokens, base_idx, len(tokens) - 1)  # -1 to skip final }

    # Check if any items use if pattern
    has_if = any(item[0] == 'if' for item in items)
    if not has_if:
        return None  # Nothing to fix

    # Flatten
    flat = flatten_if_to_modifiers(items)

    # Build output
    mod_indent = indent + '\t'
    result_lines = [f'{indent}ai_chance = {{']
    result_lines.append(f'{mod_indent}base = {base_val}')
    mod_text = modifiers_to_text(flat, mod_indent)
    if mod_text:
        result_lines.append(mod_text)
    result_lines.append(f'{indent}}}')

    return '\n'.join(result_lines)


def find_ai_chance_blocks(text):
    """Find all ai_chance = { ... } blocks in the text. Returns (start, end) char positions."""
    blocks = []
    i = 0
    while True:
        match = re.search(r'ai_chance\s*=\s*\{', text[i:])
        if not match:
            break
        block_start = i + match.start()
        # Find matching brace
        brace_start = i + match.end() - 1
        depth = 1
        j = brace_start + 1
        while j < len(text) and depth > 0:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            elif text[j] == '#':
                # Skip comment to end of line
                nl = text.find('\n', j)
                if nl == -1:
                    break
                j = nl
            j += 1
        block_end = j
        blocks.append((block_start, block_end))
        i = block_end

    return blocks


def has_if_in_ai_chance(block_text):
    """Check if an ai_chance block uses if = { pattern."""
    # Simple check: look for if = { inside the block
    return bool(re.search(r'\bif\s*=\s*\{', block_text))


def get_indent(text, pos):
    """Get the indentation at the given position (text between line start and pos)."""
    line_start = text.rfind('\n', 0, pos) + 1
    return text[line_start:pos]


def process_file(filepath, dry_run=False):
    """Process a single file, fixing all ai_chance blocks."""
    with open(filepath, 'rb') as f:
        raw = f.read()

    has_bom = raw[:3] == b'\xef\xbb\xbf'
    text = raw.decode('utf-8-sig')

    blocks = find_ai_chance_blocks(text)
    if not blocks:
        return 0

    changes = 0
    # Process in reverse order to preserve positions
    for start, end in reversed(blocks):
        block_text = text[start:end]
        if not has_if_in_ai_chance(block_text):
            continue

        indent = get_indent(text, start)
        # Extract just the block content (between outer braces)
        inner_start = block_text.index('{')
        inner = block_text[inner_start:]

        replacement = process_ai_chance_block(inner, indent)
        if replacement is None:
            continue

        # Replace from line start (not block start) since replacement includes indent
        line_start = text.rfind('\n', 0, start) + 1
        text = text[:line_start] + replacement + text[end:]
        changes += 1
        print(f"  Fixed ai_chance block at char {start}")

    if changes > 0 and not dry_run:
        encoding = 'utf-8-sig' if has_bom else 'utf-8'
        with open(filepath, 'w', encoding=encoding, newline='\n') as f:
            f.write(text)
        print(f"  Wrote {filepath} ({changes} blocks fixed)")
    elif changes > 0:
        print(f"  [DRY RUN] Would fix {changes} blocks in {filepath}")

    return changes


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    files = [a for a in sys.argv[1:] if not a.startswith('--')]

    if not files:
        print("Usage: python fix_ai_chance.py [--dry-run] <file1.txt> [file2.txt ...]")
        sys.exit(1)

    total = 0
    for f in files:
        if not os.path.exists(f):
            print(f"File not found: {f}")
            continue
        print(f"Processing {os.path.basename(f)}...")
        n = process_file(f, dry_run)
        total += n

    print(f"\nTotal: {total} ai_chance blocks fixed")
