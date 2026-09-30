"""
Mission file management and validation utilities for DayZ Central Economy.
Provides tools for validating, diagnosing, patching, and scaling CE XML files.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
import xml.etree.ElementTree as ET
import shutil
import json

# === Error Classes ===
class MissionToolError(Exception):
    """Base exception for mission tool errors"""
    pass

class LayoutError(MissionToolError):
    """Mission folder layout/structure error"""
    pass

class XmlError(MissionToolError):
    """XML parsing/validation error"""
    pass

# === XML Utilities ===
@dataclass(frozen=True)
class XmlDoc:
    path: Path
    tree: ET.ElementTree

    @property
    def root(self) -> ET.Element:
        return self.tree.getroot()

def parse_xml(path: Path) -> XmlDoc:
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        raise XmlError(f"Invalid XML: {path}: {e}") from e
    return XmlDoc(path=path, tree=tree)

def write_xml(doc: XmlDoc, path: Path | None = None) -> None:
    out = path or doc.path
    try:
        ET.indent(doc.tree, space="  ", level=0)
    except Exception:
        pass
    out.write_bytes(ET.tostring(doc.root, encoding="utf-8", xml_declaration=True))

def text_int(elem: ET.Element | None, default: int | None = None) -> int | None:
    if elem is None or elem.text is None:
        return default
    try:
        return int(str(elem.text).strip())
    except ValueError:
        return default

def set_text(elem: ET.Element, value: int | str) -> None:
    elem.text = str(value)

def as_bool01(v: bool) -> str:
    return "1" if v else "0"

# === Mission Layout Detection ===
@dataclass(frozen=True)
class MissionLayout:
    root: Path
    cfgeconomycore: Path
    economy: Path
    types: Path | None
    events: Path | None
    cfgeventspawns: Path | None

    def rel(self, p: Path) -> str:
        try:
            return str(p.relative_to(self.root)).replace('\\','/')
        except Exception:
            return str(p)

@dataclass(frozen=True)
class CeFileRef:
    folder: str
    name: str
    type: str

    def relpath(self) -> str:
        return f"{self.folder}/{self.name}" if self.folder else self.name

def detect_mission(root: Path) -> MissionLayout:
    root = root.resolve()
    if not root.exists() or not root.is_dir():
        raise LayoutError(f"Input mission folder not found: {root}")

    core = root / "cfgeconomycore.xml"
    econ = root / "economy.xml"
    if not core.exists():
        raise LayoutError(f"Missing cfgeconomycore.xml in {root}")
    if not econ.exists():
        raise LayoutError(f"Missing economy.xml in {root}")

    types = events = evsp = None
    for cand in [root/"types.xml", root/"db"/"types.xml"]:
        if cand.exists():
            types = cand
            break
    for cand in [root/"events.xml", root/"db"/"events.xml"]:
        if cand.exists():
            events = cand
            break
    for cand in [root/"cfgeventspawns.xml", root/"db"/"cfgeventspawns.xml"]:
        if cand.exists():
            evsp = cand
            break

    return MissionLayout(root=root, cfgeconomycore=core, economy=econ, types=types, events=events, cfgeventspawns=evsp)

def read_ce_refs(cfgeconomycore_path: Path) -> list[CeFileRef]:
    doc = parse_xml(cfgeconomycore_path)
    root = doc.root
    out: list[CeFileRef] = []
    for ce in root.findall("ce"):
        folder = ce.get("folder","").strip()
        for f in ce.findall("file"):
            name = (f.get("name") or "").strip()
            ftype = (f.get("type") or "").strip()
            if not name or not ftype:
                continue
            out.append(CeFileRef(folder=folder, name=name, type=ftype))
    return out

def ce_ref_exists(mission_root: Path, ref: CeFileRef) -> bool:
    p = mission_root / ref.folder / ref.name if ref.folder else (mission_root / ref.name)
    return p.exists()

# === Validation ===
@dataclass(frozen=True)
class Finding:
    level: str
    where: str
    message: str

    def as_line(self) -> str:
        return f"[{self.level}] {self.where}: {self.message}"

def validate_mission(root: Path) -> list[Finding]:
    """Validate mission structure and common CE issues"""
    layout = detect_mission(root)
    findings: list[Finding] = []

    # Parse core files
    try:
        parse_xml(layout.cfgeconomycore)
        parse_xml(layout.economy)
    except XmlError as e:
        findings.append(Finding("ERROR", "mission", str(e)))
        return findings

    # cfgeconomycore refs must exist
    for ref in read_ce_refs(layout.cfgeconomycore):
        if not ce_ref_exists(layout.root, ref):
            findings.append(Finding("ERROR", "cfgeconomycore.xml",
                 f"Referenced file missing: {ref.relpath()}"))

    # economy switches
    econ = parse_xml(layout.economy).root
    custom = econ.find("custom")
    if custom is not None and (custom.get("init") in ("0","false","False")):
        findings.append(Finding("ERROR", layout.rel(layout.economy),
             "custom init=0. Custom CE overlays will not initialize."))

    return findings

# === Diagnostics ===
@dataclass(frozen=True)
class DoctorNote:
    title: str
    detail: str

def diagnose_mission(root: Path) -> list[DoctorNote]:
    """Run opinionated diagnostics on mission"""
    layout = detect_mission(root)
    notes: list[DoctorNote] = []

    findings = validate_mission(root)
    errors = [f for f in findings if f.level == "ERROR"]

    if errors:
        notes.append(DoctorNote(
            "Hard errors detected",
            "\n".join([f.as_line() for f in errors])
        ))

    # Check if custom CE is disabled
    econ = parse_xml(layout.economy).root
    custom = econ.find("custom")
    if custom is not None and custom.get("init") in ("0","false","False"):
        notes.append(DoctorNote(
            "Custom CE is disabled in economy.xml",
            'Set <custom init="1" ...> or your overlays will not initialize.'
        ))

    if not notes:
        notes.append(DoctorNote(
            "Looks structurally OK",
            "No obvious blockers found.",
        ))

    return notes

# === Scaling ===
@dataclass(frozen=True)
class ScaleResult:
    touched: int
    changed: int

def scale_types_xml(path: Path, nominal_mult: float, min_mult: Optional[float] = None, 
                    round_mode: str = "ceil", keep_zero: bool = False) -> ScaleResult:
    """Scale nominal/min counts in types.xml"""
    doc = parse_xml(path)
    root = doc.root
    touched = 0
    changed = 0
    
    if min_mult is None:
        min_mult = nominal_mult

    import math
    round_fn = {"ceil": math.ceil, "floor": math.floor, "round": round}.get(round_mode, math.ceil)

    for typ in root.findall("type"):
        for tag, mult in [("nominal", nominal_mult), ("min", min_mult)]:
            el = typ.find(tag)
            if el is None or el.text is None:
                continue
            touched += 1
            try:
                old_val = int(el.text.strip())
                if old_val == 0 and not keep_zero:
                    continue
                new_val = round_fn(old_val * mult)
                if new_val != old_val:
                    set_text(el, new_val)
                    changed += 1
            except ValueError:
                continue

    if changed > 0:
        write_xml(doc)

    return ScaleResult(touched=touched, changed=changed)
