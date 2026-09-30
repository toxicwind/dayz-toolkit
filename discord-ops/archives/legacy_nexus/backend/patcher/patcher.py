#!/usr/bin/env python3
"""DayZ mission patcher (pure-JSON patch definitions).

Design constraints
- Treat the mission base as immutable; generate an output mission directory.
- Patch definitions are JSON files only.
  - JSON targets: deep-merge patches (atomic fragments).
  - XML targets: JSON-defined operations (xpath + set/append/upsert/remove).
- Keep patches small and composable; put 'what it does' in the manifest.

Supported actions (manifest.patches[].type)
- json_merge: deep merge into a JSON file (default strict: warn on unknown keys)
- xml_ops: apply a list of XML operations to an XML file
- json_ops: apply small JSON operations (currently append_unique for arrays)
- raw_copy: copy a patch file into the output mission (create new files)

Run
  python3 patcher.py list --manifest patches/manifest.json
  python3 patcher.py apply --base base/dayzOffline.chernarusplus --manifest patches/manifest.json --out output_mission

Base can be either a directory or a .zip containing a directory named dayzOffline.chernarusplus/.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import xml.etree.ElementTree as ET


def eprint(*a: Any) -> None:
    print(*a, file=sys.stderr)


def read_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def indent_xml(elem: ET.Element, level: int = 0) -> None:
    """Pretty-print in-place for stable diffs."""
    i = "\n" + level * "  "
    if len(elem):
        if not (elem.text and elem.text.strip()):
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not (elem.tail and elem.tail.strip()):
            elem.tail = i
    else:
        if level and not (elem.tail and elem.tail.strip()):
            elem.tail = i


# ----------------------------
# JSON merge
# ----------------------------


def deep_merge(dst: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)  # type: ignore[index]
        else:
            dst[k] = v
    return dst


def iter_leaf_paths(patch: Any, prefix: Tuple[str, ...] = ()) -> Iterable[Tuple[Tuple[str, ...], Any]]:
    if isinstance(patch, dict):
        for k, v in patch.items():
            yield from iter_leaf_paths(v, prefix + (str(k),))
    else:
        yield prefix, patch


def json_path_exists(obj: Any, path: Tuple[str, ...]) -> bool:
    cur = obj
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return False
    return True


# ----------------------------
# XML ops
# ----------------------------


def _find_with_xpath(root: ET.Element, xpath: str) -> List[ET.Element]:
    try:
        return list(root.findall(xpath))
    except SyntaxError as ex:
        raise ValueError(f"Invalid xpath for ElementTree: {xpath}: {ex}")


def _iter_parents(root: ET.Element):
    for parent in root.iter():
        for child in list(parent):
            yield parent, child


def json_xml_element(defn: Dict[str, Any]) -> ET.Element:
    tag = defn["tag"]
    attrib = {str(k): str(v) for k, v in (defn.get("attributes") or {}).items()}
    elem = ET.Element(tag, attrib)
    if "text" in defn and defn["text"] is not None:
        elem.text = str(defn["text"])
    for ch in defn.get("children") or []:
        elem.append(json_xml_element(ch))
    return elem


def apply_xml_ops(xml_path: Path, ops: List[Dict[str, Any]]) -> List[str]:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    notes: List[str] = []
    for idx, op in enumerate(ops):
        kind = op.get("op")
        if not kind:
            raise ValueError(f"xml_ops[{idx}] missing 'op'")

        if kind == "set_attr":
            xpath = op["xpath"]
            set_map = op.get("set") or {}
            nodes = _find_with_xpath(root, xpath)
            for n in nodes:
                for k, v in set_map.items():
                    n.set(str(k), str(v))
            notes.append(f"set_attr xpath={xpath} matched={len(nodes)}")

        elif kind == "set_text":
            xpath = op["xpath"]
            text = op.get("text")
            nodes = _find_with_xpath(root, xpath)
            for n in nodes:
                n.text = "" if text is None else str(text)
            notes.append(f"set_text xpath={xpath} matched={len(nodes)}")

        elif kind == "remove":
            xpath = op["xpath"]
            targets = set(_find_with_xpath(root, xpath))
            removed = 0
            if targets:
                for parent, child in _iter_parents(root):
                    if child in targets:
                        parent.remove(child)
                        removed += 1
            notes.append(f"remove xpath={xpath} matched={len(targets)} removed={removed}")

        elif kind == "append":
            xpath = op["xpath"]
            children = op.get("children") or []
            nodes = _find_with_xpath(root, xpath)
            for n in nodes:
                for ch_def in children:
                    n.append(json_xml_element(ch_def))
            notes.append(f"append xpath={xpath} matched={len(nodes)} appended_each={len(children)}")

        elif kind == "upsert":
            parent_xpath = op.get("parent_xpath", ".")
            tag = op["tag"]
            key_attrs = op.get("key_attrs") or {}
            replace_children = bool(op.get("replace_children", False))
            children = op.get("children") or []

            parents = _find_with_xpath(root, parent_xpath)
            if not parents:
                notes.append(f"upsert parent_xpath={parent_xpath} matched=0 (SKIP)")
                continue

            made = 0
            updated = 0
            for p in parents:
                match = None
                for ch in p.findall(tag):
                    ok = True
                    for ak, av in key_attrs.items():
                        if ch.get(str(ak)) != str(av):
                            ok = False
                            break
                    if ok:
                        match = ch
                        break

                if match is None:
                    new_elem = ET.Element(tag, {str(k): str(v) for k, v in key_attrs.items()})
                    for ch_def in children:
                        new_elem.append(json_xml_element(ch_def))
                    p.append(new_elem)
                    made += 1
                else:
                    for ak, av in key_attrs.items():
                        match.set(str(ak), str(av))
                    if replace_children:
                        for existing in list(match):
                            match.remove(existing)
                        for ch_def in children:
                            match.append(json_xml_element(ch_def))
                    updated += 1

            notes.append(f"upsert parent_xpath={parent_xpath} tag={tag} made={made} updated={updated}")

        else:
            raise ValueError(f"Unknown xml op: {kind}")

    indent_xml(root)
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    return notes


# ----------------------------
# Base resolution
# ----------------------------


def resolve_base(base: Path, scratch_dir: Path) -> Path:
    if base.is_dir():
        return base
    if base.is_file() and base.suffix.lower() == ".zip":
        scratch_dir.mkdir(parents=True, exist_ok=True)
        extract_to = scratch_dir / f"base_extracted_{base.stem}"
        if extract_to.exists():
            return extract_to / "dayzOffline.chernarusplus"
        with zipfile.ZipFile(base, "r") as z:
            z.extractall(extract_to)
        return extract_to / "dayzOffline.chernarusplus"
    raise FileNotFoundError(f"Base not found or unsupported: {base}")


def copy_base_to_output(base_dir: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(base_dir, out_dir)


# ----------------------------
# Manifest
# ----------------------------


@dataclass
class PatchEntry:
    name: str
    description: str
    type: str
    target: str
    file: str
    enabled: bool
    order: int
    strict: str
    conflicts: List[str]


def load_manifest(manifest_path: Path):
    m = read_json(manifest_path)
    meta = m.get("meta") or {}
    patches = []
    for i, p in enumerate(m.get("patches") or []):
        patches.append(
            PatchEntry(
                name=str(p["name"]),
                description=str(p.get("description", "")),
                type=str(p["type"]),
                target=str(p["target"]),
                file=str(p["file"]),
                enabled=bool(p.get("enabled", False)),
                order=int(p.get("order", i * 10)),
                strict=str(p.get("strict", "warn")),
                conflicts=[str(x) for x in (p.get("conflicts") or [])],
            )
        )
    patches.sort(key=lambda pe: pe.order)
    return meta, patches


# ----------------------------
# Apply patches
# ----------------------------



def _json_pointer_tokens(ptr: str) -> List[str]:
    if not ptr.startswith("/"):
        raise ValueError(f"json pointer must start with '/': {ptr}")
    # RFC6901-ish unescape (~1 -> /, ~0 -> ~)
    out: List[str] = []
    for raw in ptr.split("/")[1:]:
        out.append(raw.replace("~1", "/").replace("~0", "~"))
    return out


def _json_get_parent_and_key(root: Any, ptr: str, create: bool = False) -> Tuple[Any, str]:
    tokens = _json_pointer_tokens(ptr)
    if not tokens:
        raise ValueError("json pointer cannot be root for this operation")
    cur: Any = root
    for t in tokens[:-1]:
        if isinstance(cur, dict):
            if t not in cur or cur[t] is None:
                if not create:
                    raise KeyError(f"missing json path segment: {t} in {ptr}")
                cur[t] = {}
            cur = cur[t]
        else:
            raise TypeError(f"json path traverses non-object at segment '{t}' in {ptr}")
    return cur, tokens[-1]


def apply_json_ops(base_obj: Any, ops_obj: Any) -> None:
    if not isinstance(base_obj, (dict, list)):
        raise ValueError("json_ops target must be a JSON object or array")
    if not isinstance(ops_obj, dict) or not isinstance(ops_obj.get("ops"), list):
        raise ValueError('json_ops patch file must be {"ops": [...]}')

    for op in ops_obj["ops"]:
        if not isinstance(op, dict) or "op" not in op:
            raise ValueError(f"invalid json_ops op: {op}")
        kind = op["op"]

        if kind == "append_unique":
            ptr = str(op["path"])
            val = op.get("value")
            parent, key = _json_get_parent_and_key(base_obj, ptr, create=True)
            if not isinstance(parent, dict):
                raise TypeError(f"append_unique parent must be object: {ptr}")
            if key not in parent or parent[key] is None:
                parent[key] = []
            arr = parent[key]
            if not isinstance(arr, list):
                raise TypeError(f"append_unique target must be array: {ptr}")
            if val not in arr:
                arr.append(val)
        else:
            raise ValueError(f"unsupported json_ops kind: {kind}")


def apply_patch(manifest_dir: Path, out_dir: Path, entry: PatchEntry) -> None:
    target_path = out_dir / entry.target
    patch_path = manifest_dir / entry.file

    # Create new files in the output (Xbox-friendly; avoids init.c / mods)
    if entry.type == "raw_copy":
        if not patch_path.exists():
            eprint(f"[WARN] raw_copy source missing: {entry.file}")
            return
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(patch_path, target_path)
        print(f"[COPY] {entry.name} -> {entry.target}")
        return

    # Small JSON operations (append_unique etc) without clobbering whole arrays
    if entry.type == "json_ops":
        if not target_path.exists():
            eprint(f"[WARN] json target missing: {entry.target}")
            return
        base_obj = read_json(target_path)
        ops_obj = read_json(patch_path)
        apply_json_ops(base_obj, ops_obj)
        write_json(target_path, base_obj)
        print(f"[JOPS] {entry.name} -> {entry.target}")
        return

    if entry.type == "json_merge":
        if not target_path.exists():
            eprint(f"[WARN] json target missing: {entry.target}")
            return
        base_obj = read_json(target_path)
        patch_obj = read_json(patch_path)
        deep_merge(base_obj, patch_obj)
        write_json(target_path, base_obj)
        print(f"[JSON] {entry.name} -> {entry.target}")
        return

    if entry.type == "xml_ops":
        if not target_path.exists():
            eprint(f"[WARN] xml target missing: {entry.target}")
            return
        ops_obj = read_json(patch_path)
        ops = ops_obj.get("ops")
        if not isinstance(ops, list):
            raise ValueError(f'xml_ops patch file must be {{"ops": [...]}}: {entry.file}')
        apply_xml_ops(target_path, ops)
        print(f"[XML] {entry.name} -> {entry.target}")
        return

    if entry.type == "text_replace":
        if not target_path.exists():
            eprint(f"[WARN] text target missing: {entry.target}")
            return
        rules_obj = read_json(patch_path)
        rules = rules_obj.get("replacements")
        if not isinstance(rules, list):
            raise ValueError(f'text_replace patch file must be {{"replacements": [...]}}: {entry.file}')
        apply_text_replace(target_path, rules)
        print(f"[TXT] {entry.name} -> {entry.target}")
        return

    raise ValueError(f"Unknown patch type: {entry.type}")

def warn_conflicts(patches: List[PatchEntry]) -> None:
    enabled = {p.name for p in patches if p.enabled}
    for p in patches:
        if not p.enabled:
            continue
        hit = [c for c in p.conflicts if c in enabled]
        if hit:
            eprint(f"[CONFLICT] {p.name} conflicts with enabled patches: {hit}")


# ----------------------------
# CLI
# ----------------------------


def cmd_list(args: argparse.Namespace) -> int:
    meta, patches = load_manifest(Path(args.manifest))
    print(json.dumps(meta, indent=2))
    print()
    for p in patches:
        flag = "ON " if p.enabled else "off"
        print(f"[{flag}] {p.name} (type={p.type} target={p.target} file={p.file} order={p.order})")
        if p.description:
            print(f"      {p.description}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest)
    base = Path(args.base)
    out = Path(args.out)
    scratch = Path(args.scratch)

    _meta, patches = load_manifest(manifest)
    base_dir = resolve_base(base, scratch)
    if not base_dir.exists():
        raise FileNotFoundError(f"Resolved base dir missing: {base_dir}")

    copy_base_to_output(base_dir, out)
    warn_conflicts(patches)

    print(f"[INIT] base={base_dir}")
    print(f"[INIT] out ={out}")

    manifest_dir = manifest.parent
    for p in patches:
        if not p.enabled:
            continue
        print(f"[APPLY] {p.name}: {p.description}")
        apply_patch(manifest_dir, out, p)

    print("[DONE] output mission ready")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="patcher.py")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_list = sub.add_parser("list", help="List patches in the manifest")
    ap_list.add_argument("--manifest", default="patches/manifest.json")
    ap_list.set_defaults(func=cmd_list)

    ap_apply = sub.add_parser("apply", help="Apply enabled patches to a copied base mission")
    ap_apply.add_argument("--base", default="base/dayzOffline.chernarusplus")
    ap_apply.add_argument("--manifest", default="patches/manifest.json")
    ap_apply.add_argument("--out", default="output_mission")
    ap_apply.add_argument("--scratch", default=".patcher_scratch")
    ap_apply.set_defaults(func=cmd_apply)

    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
