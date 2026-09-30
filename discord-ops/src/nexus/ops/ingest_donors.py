#!/usr/bin/env python3
"""Ingest donor files and append provenance to outputs.

Usage:
  python3 tools/ingest_donors.py --inputs path1 path2 ...

Writes per-donor markdown to outputs/donors/ and appends provenance to outputs/consolidated_prompts.md
"""
import argparse
from pathlib import Path
import json
import datetime


def sanitize_name(p: Path):
    name = p.name.replace('/', '_')
    return name


def ingest(paths, output_dir='outputs'):
    out = Path(output_dir)
    donors_dir = out / 'donors'
    donors_dir.mkdir(parents=True, exist_ok=True)

    consolidated = out / 'consolidated_prompts.md'
    if not consolidated.exists():
        consolidated.write_text('# Consolidated prompts (donors appended)\n')

    for p in paths:
        src = Path(p)
        if not src.exists():
            print(f"Missing: {p}")
            continue
        try:
            text = src.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Failed to read {p}: {e}")
            continue

        meta = {
            'source': str(src),
            'size': src.stat().st_size,
            'mtime': datetime.datetime.utcfromtimestamp(src.stat().st_mtime).isoformat() + 'Z'
        }

        donor_md = donors_dir / (sanitize_name(src) + '.md')
        content = "# Donor: {}\n\n```text\n{}\n```\n\n---\n\n".format(src, text)
        content += json.dumps(meta, indent=2)
        donor_md.write_text(content, encoding='utf-8')

        # Append provenance to consolidated_prompts.md
        with consolidated.open('a', encoding='utf-8') as f:
            f.write(f"\n## Donor: {src}\n")
            f.write(f"- size: {meta['size']}\n")
            f.write(f"- mtime: {meta['mtime']}\n")
            f.write('\n```\n')
            # write head of file for quick preview (first 2000 chars)
            preview = text[:2000]
            f.write(preview)
            if len(text) > 2000:
                f.write('\n... (truncated)')
            f.write('\n```\n')

        print(f"Ingested {p} -> {donor_md}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', '-i', nargs='+', required=True)
    p.add_argument('--output', '-o', default='outputs')
    args = p.parse_args()
    ingest(args.inputs, args.output)


if __name__ == '__main__':
    main()
