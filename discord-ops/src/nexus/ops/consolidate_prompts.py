#!/usr/bin/env python3
"""Consolidate prompts from a ChatReplay/JSON file and recursively include referenced files.

Usage:
  python3 tools/consolidate_prompts.py --input /path/to/file.json --output outputs --max-depth 3

Produces:
  outputs/consolidated_prompts.md
  outputs/summary.json
"""
import argparse
import json
import os
import re
from pathlib import Path
from collections import OrderedDict


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def gather_strings(obj, out):
    if obj is None:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            gather_strings(v, out)
    elif isinstance(obj, list):
        for i in obj:
            gather_strings(i, out)


PATH_RE = re.compile(r"(?:file://)?(/[^)\s]+|\./[^)\s]+|\.\./[^)\s]+|[\w\-./]+\.(?:json|md|txt|py))")


def find_paths_in_text(text):
    if not isinstance(text, str):
        return []
    matches = PATH_RE.findall(text)
    # normalize
    cleaned = []
    for m in matches:
        p = m.strip('"')
        cleaned.append(p)
    return cleaned


def read_file_if_exists(base_dir, p):
    # Try absolute path first, then relative to base_dir
    if p.startswith('/'): 
        cand = Path(p)
    else:
        cand = Path(base_dir) / p
    try:
        if cand.exists() and cand.is_file():
            return cand.read_text(encoding='utf-8')
    except Exception:
        return None
    return None


def consolidate(input_path, output_dir, max_depth=3):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = None
    try:
        data = load_json(input_path)
    except Exception as e:
        print(f"Failed to load JSON {input_path}: {e}")
        return 1

    # Extract all textual pieces
    texts = []
    if isinstance(data, dict):
        # common structures: {"messages": [...]}, or other
        if 'messages' in data and isinstance(data['messages'], list):
            gather_strings(data['messages'], texts)
        else:
            gather_strings(data, texts)
    elif isinstance(data, list):
        gather_strings(data, texts)

    # Deduplicate while preserving order
    dedup = list(OrderedDict.fromkeys([t.strip() for t in texts if t and t.strip()]))

    # Prepare outputs
    md_lines = []
    md_lines.append(f"# Consolidated prompts from {input_path}\n")
    md_lines.append(f"Total textual pieces found: {len(texts)}\n")
    md_lines.append(f"Deduplicated pieces: {len(dedup)}\n")

    # List deduped prompts
    md_lines.append("## Prompts / Messages (deduplicated)\n")
    for i, s in enumerate(dedup, 1):
        md_lines.append(f"### Prompt {i}\n")
        md_lines.append('''```
''')
        md_lines.append(s)
        md_lines.append('''```
''')

    # Recursively follow file references
    visited = set()
    file_contents = {}

    def recurse_texts(list_of_texts, base_dir, depth):
        if depth <= 0:
            return
        for t in list_of_texts:
            for p in find_paths_in_text(t):
                if p in visited:
                    continue
                visited.add(p)
                content = read_file_if_exists(base_dir, p)
                if content is None:
                    continue
                file_contents[p] = content
                # also gather paths from this content and recurse
                nested = []
                gather_strings(content, nested)
                # but content is string; find paths directly
                nested_paths = find_paths_in_text(content)
                # create a pseudo-list of texts to recurse; include content itself
                recurse_texts([content], Path(base_dir) if not str(p).startswith('/') else Path('/'), depth-1)

    base_dir = Path(input_path).parent
    recurse_texts(dedup, base_dir, max_depth)

    if file_contents:
        md_lines.append('\n## Included referenced files\n')
        for p, c in file_contents.items():
            md_lines.append(f'### Source: {p}\n')
            md_lines.append('''```
''')
            md_lines.append(c)
            md_lines.append('''```
''')

    # Write markdown
    md_path = output_dir / 'consolidated_prompts.md'
    md_path.write_text('\n'.join(md_lines), encoding='utf-8')

    # Summary JSON
    summary = {
        'input': str(input_path),
        'total_text_pieces': len(texts),
        'deduped_count': len(dedup),
        'referenced_files': list(file_contents.keys())
    }
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(f"Wrote {md_path} and {output_dir / 'summary.json'}")
    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', '-i', required=True)
    p.add_argument('--output', '-o', default='outputs')
    p.add_argument('--max-depth', type=int, default=3)
    args = p.parse_args()
    return consolidate(args.input, args.output, args.max_depth)


if __name__ == '__main__':
    raise SystemExit(main())
