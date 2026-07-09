#!/usr/bin/env python3
from pathlib import Path
import re

posts = sorted(Path('_posts').glob('*.md'))
if not posts:
    print('No posts found in _posts/')
    exit(0)

for p in posts:
    text = p.read_text(encoding='utf-8')
    # find front-matter
    m = re.match(r'^(---\n[\s\S]*?\n---\n)', text)
    if not m:
        continue
    fm = m.group(1)
    body = text[len(fm):]
    # extract location from front matter
    loc_m = re.search(r'^location:\s*(?:"([^"]+)"|([^\n]+))', fm, flags=re.M)
    if loc_m:
        loc = (loc_m.group(1) or loc_m.group(2)).strip()
    else:
        loc = ''
    city = ''
    country = ''
    if loc:
        parts = [s.strip() for s in loc.split(',') if s.strip()]
        if len(parts) >= 2:
            city = parts[0]
            country = parts[-1]
        elif len(parts) == 1:
            city = parts[0]
    # find gallery_images block
    g_m = re.search(r'(gallery_images:\n(?:[ \t\-:\n\w"\'/._,\(\)\-]*))', fm, flags=re.M)
    if not g_m:
        continue
    g_block = g_m.group(1)
    new_block = g_block
    # iterate over image entries
    # pattern matches each '- image: ...' plus following indented lines
    entry_re = re.compile(r'(^\s*-\s*image:\s*(?:"[^"]+"|[^\n]+)(?:\n(?:\s{4,}[^\n]+\n)*)?)', flags=re.M)
    changed = False
    def ensure_meta(entry_text):
        # if city and country already present, leave
        if re.search(r'\n\s*city:\s*', entry_text) and re.search(r'\n\s*country:\s*', entry_text):
            return entry_text, False
        # find caption if present
        cap_m = re.search(r'\n(\s*)caption:\s*(?:"([^"]*)"|([^\n]+))', entry_text)
        # build metadata lines
        lines = ''
        if city:
            lines += f"    city: \"{city}\"\n"
        if country:
            lines += f"    country: \"{country}\"\n"
        if not lines:
            return entry_text, False
        if cap_m:
            parts = entry_text.rsplit('\n', 1)
            if len(parts) == 2:
                return parts[0] + '\n' + lines + parts[1], True
            else:
                return entry_text + '\n' + lines, True
        else:
            parts = entry_text.split('\n',1)
            if len(parts) == 2:
                return parts[0] + '\n' + lines + parts[1], True
            else:
                return entry_text + '\n' + lines, True

    def repl(m):
        entry = m.group(1)
        new_entry, did = ensure_meta(entry)
        nonlocal_changed = did
        return new_entry

    # perform substitution manually to track changes
    new_entries = []
    last_end = 0
    new_block_parts = []
    for em in entry_re.finditer(g_block):
        start, end = em.span(1)
        entry = em.group(1)
        new_entry, did = ensure_meta(entry)
        if did:
            changed = True
        new_block_parts.append(g_block[last_end:start])
        new_block_parts.append(new_entry)
        last_end = end
    new_block_parts.append(g_block[last_end:])
    new_block = ''.join(new_block_parts)
    if changed:
        new_fm = fm.replace(g_block, new_block)
        new_text = new_fm + body
        backup = p.with_suffix(p.suffix + '.bak.meta')
        backup.write_text(text, encoding='utf-8')
        p.write_text(new_text, encoding='utf-8')
        print('Updated', p.name)

print('Done')
