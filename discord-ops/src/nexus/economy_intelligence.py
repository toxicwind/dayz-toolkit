import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from fastapi import APIRouter

log = logging.getLogger("dayz-discord-ops.economy_intel")

router = APIRouter(prefix="/api/economy", tags=["economy"])


class EconomyIntelligence:
    def __init__(self, types_xml_path: Path):
        self.path = types_xml_path
        self.tree = None

        # Try multiple possible locations
        from .config import get_settings
        settings = get_settings()
        
        possible_paths = [
            types_xml_path,
            settings.chronos_root / "dayzxb_missions/dayzOffline.chernarusplus/db/types.xml",
            Path("missions/dayzOffline.chernarusplus/db/types.xml"),
            Path("missions/db/types.xml"),
            settings.chronos_root / "dayzxb_missions/dayzOffline.chernarusplus/db/types.xml",
        ]

        for p in possible_paths:
            if p.exists():
                try:
                    self.tree = ET.parse(p)
                    self.path = p
                    log.info(f"Loaded types.xml from {p}")
                    break
                except Exception as e:
                    log.error(f"Failed to parse {p}: {e}")

        if not self.tree:
            log.error(f"Could not find or parse types.xml. Tried: {[str(p) for p in possible_paths]}")

    def get_smart_clusters(self) -> dict[str, list[dict[str, Any]]]:
        """Groups items by base name variants (e.g. AK74, M4A1)"""
        if not self.tree:
            return {}

        clusters = {}
        root = self.tree.getroot()

        for t in root.findall("type"):
            name = t.get("name")
            # Pattern: BaseName_Color or BaseName_Camo or BaseName
            # Simple heuristic: Split by underscores and take the first part OR match common prefixes
            match = re.match(r"^([A-Za-z0-9]+)(?:_.*)?$", name)
            base_name = match.group(1) if match else "Other"

            # Refinement for common weapon/item bases
            if "_" in name:
                parts = name.split("_")
                # e.g. Mag_STANAG_30Rnd -> Mag_STANAG
                if parts[0] in ["Mag", "Ammo", "Weapon", "Item", "ZmbM"]:
                    base_name = "_".join(parts[:2])
                else:
                    base_name = parts[0]

            if base_name not in clusters:
                clusters[base_name] = []

            item_data = {
                "name": name,
                "nominal": int(t.findtext("nominal", "0")),
                "min": int(t.findtext("min", "0")),
                "lifetime": int(t.findtext("lifetime", "0")),
            }
            clusters[base_name].append(item_data)

        # Filter out clusters with only 1 item to reduce noise, unless it's a known important base
        return {k: v for k, v in clusters.items() if len(v) > 1 or k.startswith("ZmbM")}

    def validate_logic(self) -> list[dict[str, str]]:
        """Checks for logical errors in types.xml"""
        if not self.tree:
            return [{"level": "error", "message": "XML file not found or unparseable"}]

        warnings = []
        root = self.tree.getroot()

        for t in root.findall("type"):
            name = t.get("name")
            try:
                nominal = int(t.findtext("nominal", "0"))
                min_val = int(t.findtext("min", "0"))

                if min_val > nominal:
                    warnings.append(
                        {
                            "item": name,
                            "level": "critical",
                            "message": f"Min ({min_val}) is greater than Nominal ({nominal}). This causes spawn loop pressure.",
                        }
                    )

                if nominal > 0 and min_val == 0:
                    warnings.append(
                        {
                            "item": name,
                            "level": "warning",
                            "message": "Min is set to 0. Loot will only restock once the entire pool is exhausted.",
                        }
                    )

                # Check for 0 lifetime
                lifetime = int(t.findtext("lifetime", "0"))
                if nominal > 0 and lifetime < 300:
                    warnings.append(
                        {
                            "item": name,
                            "level": "warning",
                            "message": f"Lifetime is very short ({lifetime}s). Item might despawn before players find it.",
                        }
                    )

            except ValueError:
                warnings.append({"item": name, "level": "error", "message": "Invalid numeric values detected."})

        return warnings
