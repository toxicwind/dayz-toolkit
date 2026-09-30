# DayZ JSON Patcher (mission config)

This bundle patches a DayZ mission folder (`dayzOffline.chernarusplus`) using JSON-only patch definitions.

## Commands

List patches:

```bash
python3 patcher.py list --manifest patches/manifest.json
```

Apply enabled patches to a copied output mission:

```bash
python3 patcher.py apply --base base/dayzOffline.chernarusplus --manifest patches/manifest.json --out output_mission
```

Base can also be a zip:

```bash
python3 patcher.py apply --base base/dayzOffline.chernarusplus.zip --manifest patches/manifest.json --out output_mission
```

## Patch types

- `json_merge`: deep-merge fragment into a JSON file. Default strictness is `warn` (prints unknown paths but continues).
- `xml_ops`: apply JSON-defined ops to XML.

All toggles live in `patches/manifest.json`.
