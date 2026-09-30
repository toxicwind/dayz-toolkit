#!/usr/bin/env python3
"""Normalize ingested donor files into structured entries.

Scans `outputs/donors/*.md` for code fences and keyword matches, deduplicates entries,
and appends a normalized section to `outputs/consolidated_prompts.md`. Also updates
`outputs/summary.json` with counts and donor stats.
"""
import re
import json
from pathlib import Path
from collections import OrderedDict, defaultdict

KEYWORDS = [
    'Query', 'Intent', 'MOE_CYCLE', 'caprover', 'caprover', 'cloudflare', 'nginx', 'tunnel',
    'Run MOE_CYCLE', 'docker-compose', 'PORTAINER', 'caprover', 'captain', 'proof-gate'
]


def extract_code_blocks(text):
    pattern = re.compile(r'```(?:[\w+-]*)\n(.*?)```', re.DOTALL)
    return [m.group(1).strip() for m in pattern.finditer(text)]


def extract_keyword_snippets(text, keywords, radius=200):
    found = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), text, re.IGNORECASE):
            start = max(0, m.start() - radius)
            end = min(len(text), m.end() + radius)
            snippet = text[start:end].strip()
            found.append((kw, snippet))
    return found


def normalize(donors_dir='outputs/donors', consolidated='outputs/consolidated_prompts.md', summary_path='outputs/summary.json'):
    donors_dir = Path(donors_dir)
    consolidated = Path(consolidated)
    summary_path = Path(summary_path)

    entries = OrderedDict()
    donor_counts = defaultdict(int)

    for p in sorted(donors_dir.glob('*')):
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        code_blocks = extract_code_blocks(text)
        for cb in code_blocks:
            key = cb.strip()
            if not key:
                continue
            if key not in entries:
                entries[key] = {'source': str(p), 'type': 'code', 'excerpt': cb[:2000]}
                donor_counts[str(p)] += 1

        kw_snips = extract_keyword_snippets(text, KEYWORDS)
        for kw, snip in kw_snips:
            key = snip.strip()
            if key not in entries:
                entries[key] = {'source': str(p), 'type': 'keyword', 'keyword': kw, 'excerpt': snip}
                donor_counts[str(p)] += 1

    # Append normalized entries to consolidated markdown
    consolidated.parent.mkdir(parents=True, exist_ok=True)
    with consolidated.open('a', encoding='utf-8') as out:
        out.write('\n\n# Normalized donor entries\n')
        out.write(f'Total normalized entries: {len(entries)}\n\n')
        for i, (k, v) in enumerate(entries.items(), 1):
            out.write(f'## Entry {i} - {v.get("type")}\n')
            out.write(f'- source: {v.get("source")}\n')
            if v.get('type') == 'keyword':
                out.write(f'- keyword: {v.get("keyword")}\n')
            out.write('\n```\n')
            out.write(v.get('excerpt') or '')
            out.write('\n```\n\n')

    # Update summary.json
    summary = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
        except Exception:
            summary = {}
    summary['normalized_entries_count'] = len(entries)
    summary['donor_stats'] = {k: v for k, v in donor_counts.items()}
    summary_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(f'Normalized {len(entries)} entries from {len(donor_counts)} donors')


if __name__ == '__main__':
    normalize()
