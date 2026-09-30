import json
import logging
import os

log = logging.getLogger("dayz-discord-ops.spawn_manager")


class SpawnManager:
    def __init__(self, missions_path: str = "/home/toxic/dayz_workspace/Missions.json"):
        self.missions_path = missions_path

    def queue_spawn(self, gamertag: str, item_name: str, pos: tuple[float, float, float]):
        """
        Appends a new object to Missions.json for the next restart.
        """
        if not os.path.exists(self.missions_path):
            log.error(f"Missions file not found at {self.missions_path}")
            return False

        try:
            with open(self.missions_path) as f:
                data = json.load(f)

            if "Objects" not in data:
                data["Objects"] = []

            # Create new object entry
            # Coordinate format in Missions.json is [x, y, z]
            # ypr is [yaw, pitch, roll] - random yaw is usually fine, or 0
            new_obj = {
                "name": item_name,
                "pos": [pos[0], pos[1], pos[2]],
                "ypr": [0.0, 0.0, 0.0],
                "scale": 1.0,
                "enableCEPersistency": 0,
                "customString": f"Trader Buy: {gamertag}",
            }

            data["Objects"].append(new_obj)

            with open(self.missions_path, "w") as f:
                json.dump(data, f, indent=4)

            log.info(f"Queued spawn for {item_name} at {pos} for {gamertag}")
            return True

        except Exception as e:
            log.error(f"Failed to queue spawn: {e}")
            return False
