"""Generate event image inventory document for docs/."""
import json
import urllib.request
import re
import os
from collections import defaultdict

def main():
    # Get all events from server
    events_data = json.loads(urllib.request.urlopen('http://localhost:8950/events').read())
    events = events_data['events']

    # Read all localization from all yml files
    loc = {}
    for root, dirs, files in os.walk('localization/english'):
        for fn in files:
            if not fn.endswith('.yml'):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, 'r', encoding='utf-8-sig') as f:
                    for line in f:
                        m = re.match(r'^\s+(\S+?):\d+\s+"(.*)"', line)
                        if m:
                            loc[m.group(1)] = m.group(2)
            except Exception:
                pass

    # Parse event files to find which file each event is in (preserving order)
    event_files = defaultdict(list)
    events_dir = 'events'
    for fn in sorted(os.listdir(events_dir)):
        if not fn.endswith('.txt'):
            continue
        fp = os.path.join(events_dir, fn)
        with open(fp, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        for m in re.finditer(r'^(\S+\.\d+)\s*=\s*\{', content, re.MULTILINE):
            eid = m.group(1)
            event_files[fn].append(eid)

    # Index server events by ID for fast lookup
    events_by_id = {ev['id']: ev for ev in events}

    # Build output
    output = []
    output.append('# Event Image Generation Inventory')
    output.append('')
    output.append('This document inventories all mod events for the purpose of generating custom event images.')
    output.append('Each event is listed with its title, description, and flavor text (where available).')
    output.append('')
    total = sum(len(v) for v in event_files.values())
    output.append(f'**Total events:** {total}')
    output.append(f'**Event files:** {len(event_files)}')
    output.append('')

    for fn in sorted(event_files.keys()):
        eids = event_files[fn]
        output.append(f'## {fn}')
        output.append('')
        for eid in eids:
            title = loc.get(eid + '.t', '(no localization)')
            desc = loc.get(eid + '.d', '(no localization)')
            flavor = loc.get(eid + '.f', '(none)')

            ev = events_by_id.get(eid, {})
            img = ev.get('image', '(unknown)')

            output.append(f'### {eid}')
            output.append(f'- **Title:** {title}')
            output.append(f'- **Description:** {desc}')
            output.append(f'- **Flavor:** {flavor}')
            output.append(f'- **Current image:** {img}')
            output.append('')

    with open('docs/event_image_inventory.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f'Written {len(output)} lines for {total} events across {len(event_files)} files')

if __name__ == '__main__':
    main()
