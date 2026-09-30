import logging
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("dayz-discord-ops.poi_manager")


@dataclass
class CustomPOI:
    name: str
    category: str
    x: float
    z: float
    y: float = 0.0  # Optional, usually less critical for 2D map distance


class POIManager:
    """
    Manages custom Points of Interest (POIs) parsed from server configuration files.
    Allows resolving a coordinate to the nearest named custom location.
    """

    def __init__(self, xml_path: str | None = None):
        self.pois: list[CustomPOI] = []
        self._initialized = False
        if xml_path:
            self.load_from_xml(xml_path)

    def load_from_xml(self, xml_path: str) -> None:
        """Parses cfgeventspawns.xml to extract custom locations."""
        path = Path(xml_path)
        if not path.exists():
            log.warning(f"POI XML file not found at {xml_path}")
            return

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            count = 0
            # Iterate through all <event> tags
            for event in root.findall("event"):
                event_name = event.get("name", "Unknown")

                # Friendly name mapping
                friendly_name = self._get_friendly_name(event_name)

                for pos in event.findall("pos"):
                    try:
                        x = float(pos.get("x", 0))
                        z = float(pos.get("z", 0))
                        y = float(pos.get("y", 0))  # Y might be missing or 0

                        self.pois.append(CustomPOI(name=friendly_name, category=event_name, x=x, z=z, y=y))
                        count += 1
                    except (ValueError, TypeError):
                        continue

            self._initialized = True
            log.info(f"Loaded {count} custom POIs from {xml_path}")

        except ET.ParseError as e:
            log.error(f"Failed to parse POI XML: {e}")
        except Exception as e:
            log.exception(f"Unexpected error loading POIs: {e}")

    def get_nearest_poi(self, x: float, z: float, max_distance: float = 250.0) -> tuple[CustomPOI, float] | None:
        """
        Finds the nearest POI within max_distance.
        Returns (POI, distance) or None if nothing found.
        """
        if not self.pois:
            return None

        nearest_poi = None
        min_dist_sq = max_distance * max_distance
        found = False

        # Brute force is fine for < 10-20k points.
        # For significantly larger datasets, we would implement a QuadTree or similar.
        for poi in self.pois:
            dx = x - poi.x
            dz = z - poi.z
            dist_sq = dx * dx + dz * dz

            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_poi = poi
                found = True

        if found and nearest_poi:
            return nearest_poi, math.sqrt(min_dist_sq)

        return None

    def _get_friendly_name(self, event_name: str) -> str:
        """Maps raw event names to readable location names."""
        # Custom mapping based on the user's XML file content
        mapping = {
            "StaticContainerLocked": "Secret Military Crate",
            "VehicleCivilianSedan": "Abandoned Sedan",
            "VehicleSedan02": "Abandoned Sedan 02",
            "VehicleHatchback02": "Abandoned Hatchback",
            "StaticHeliCrash": "Helicopter Crash Site",
            "StaticSantaCrash": "Santa's Sleigh Crash",
            "StaticChristmasTree": "Christmas Tree",
            "StaticBonfire": "Bonfire Site",
            "StaticContaminatedArea": "Toxic Zone",
            "VehicleOffroadHatchback": "Abandoned Offroad",
            "VehicleOffroad02": "Abandoned Humvee",
            "StaticPoliceCar": "Police Incident",
        }
        return mapping.get(event_name, event_name)


# Global instance
_poi_manager_instance: POIManager | None = None


def get_poi_manager() -> POIManager:
    global _poi_manager_instance
    if _poi_manager_instance is None:
        # Default path, can be re-initialized properly by the bot startup
        _poi_manager_instance = POIManager()
    return _poi_manager_instance
