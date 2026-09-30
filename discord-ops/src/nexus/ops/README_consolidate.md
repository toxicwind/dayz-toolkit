# Prompt Consolidation Pipeline

**Date:** 2026-01-09  
**Purpose:** Consolidate ChatReplay/JSON prompt files, recursively include referenced files, discover and integrate donor patterns from December 2025 / January 2026.

---

## Quick Start

### 1. Consolidate a ChatReplay JSON file

```bash
python3 tools/consolidate_prompts.py \
  --input /home/toxic/copilot_all_prompts_2026-01-09T20-05-44.chatreplay.json \
  --output outputs \
  --max-depth 3
```

**Outputs:**
- `outputs/consolidated_prompts.md` — deduplicated prompts + referenced files
- `outputs/summary.json` — metadata (counts, paths)

---

### 2. Ingest donor files (with provenance)

```bash
python3 tools/ingest_donors.py \
  -i copilot_consolidated_prompts.txt \
     patcher/patches/manifest.json \
     WEB_QUERY_LOG.md \
     multi-agent-multitask.md \
     config-captain.json \
     dashboard/config/sources.json \
  --output outputs
```

**Outputs:**
- `outputs/donors/*.md` — per-donor markdown with metadata
- Appends provenance previews to `outputs/consolidated_prompts.md`
- Updates `outputs/summary.json` with `donor_files` list

---

### 3. Normalize and extract patterns

```bash
python3 tools/normalize_donors.py
```

**What it does:**
- Scans `outputs/donors/*.md`
- Extracts code blocks and keyword matches (e.g., "MOE_CYCLE", "caprover", "nginx")
- Deduplicates entries
- Appends structured entries to `outputs/consolidated_prompts.md`
- Updates `outputs/summary.json` with `normalized_entries_count` and `donor_stats`

---

## Full Pipeline (one command)

```bash
python3 tools/consolidate_prompts.py \
  --input /home/toxic/copilot_all_prompts_2026-01-09T20-05-44.chatreplay.json \
  --output outputs --max-depth 3 && \
python3 tools/ingest_donors.py \
  -i copilot_consolidated_prompts.txt \
     patcher/patches/manifest.json \
     WEB_QUERY_LOG.md \
     multi-agent-multitask.md \
     config-captain.json \
     dashboard/config/sources.json \
  --output outputs && \
python3 tools/normalize_donors.py
```

---

## Outputs Summary

| File | Description |
|------|-------------|
| `outputs/consolidated_prompts.md` | Human-readable consolidated prompts + donors + normalized entries |
| `outputs/summary.json` | Structured metadata (counts, referenced files, donor stats) |
| `outputs/donors/*.md` | Per-donor files with provenance and excerpts |

---

## Stats (2026-01-09 run)

- **Input:** `/home/toxic/copilot_all_prompts_2026-01-09T20-05-44.chatreplay.json`
- **Total text pieces:** 33,123
- **Deduplicated prompts:** 1,021
- **Referenced files:** 59
- **Donor files:** 6
- **Normalized entries:** 2,299

Top donor contributions:
- `copilot_consolidated_prompts.txt`: 2,219 entries
- `config-captain.json`: 65 entries
- `WEB_QUERY_LOG.md`: 12 entries

---

## Keywords Searched

`Query`, `Intent`, `MOE_CYCLE`, `caprover`, `cloudflare`, `nginx`, `tunnel`, `docker-compose`, `PORTAINER`, `captain`, `proof-gate`

---

## Notes

- Referenced files are recursively loaded up to `--max-depth` (default: 3)
- Donor ingestion respects file permissions and avoids credentials
- Normalization deduplicates by content hash to avoid repetition
- All outputs are UTF-8 encoded

---

## Re-run anytime

To refresh outputs:

```bash
rm -rf outputs/donors outputs/consolidated_prompts.md outputs/summary.json
# Then run the full pipeline above
```
