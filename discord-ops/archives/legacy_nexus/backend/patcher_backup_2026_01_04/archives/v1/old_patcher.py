import json
import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("Patcher")


class DayZConfigPatcher:
    """
    Unified engine to apply XML, JSON, and C-script patches.
    Now defaults to using the /fixed/ directory for clean data.
    """

    def __init__(self, mission_dir, patch_data_dir, manifest_path, enable_init_patching=False):
        self.mission_dir = Path(mission_dir)
        self.patch_data_dir = Path(patch_data_dir)
        self.manifest_path = Path(manifest_path)
        self.manifest = self._load_json(self.manifest_path)
        self.enable_init_patching = enable_init_patching

    def _load_json(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON from {path}: {e}")
            return {}

    def _backup_file(self, file_path):
        backup = file_path.with_suffix(file_path.suffix + ".bak")
        if not backup.exists():
            shutil.copy2(file_path, backup)
            logger.info(f"Created backup: {backup.name}")

    def patch_xml(self, target_rel_path, data_rel_path):
        target_path = self.mission_dir / target_rel_path
        data_path = self.patch_data_dir / data_rel_path
        if not target_path.exists() or not data_path.exists():
            logger.warning(f"XML Patch skipped: {target_rel_path} or {data_rel_path} not found.")
            return
        self._backup_file(target_path)
        try:
            target_tree = ET.parse(target_path)
            target_root = target_tree.getroot()
            patch_tree = ET.parse(data_path)
            patch_root = patch_tree.getroot()
            for child in patch_root:
                target_root.append(child)
            try:
                ET.indent(target_tree, space="    ", level=0)
            except AttributeError:
                pass
            target_tree.write(target_path, encoding="utf-8", xml_declaration=True)
            logger.info(f"Applied XML patch to {target_rel_path}")
        except Exception as e:
            logger.error(f"Error patching XML {target_rel_path}: {e}")

    def patch_json(self, target_rel_path, data_rel_path, mode="merge"):
        target_path = self.mission_dir / target_rel_path
        data_path = self.patch_data_dir / data_rel_path
        if not target_path.exists() or not data_path.exists():
            logger.warning(f"JSON Patch skipped: {target_rel_path} not found.")
            return
        self._backup_file(target_path)
        target_data = self._load_json(target_path)
        patch_data = self._load_json(data_path)
        if mode == "merge":

            def deep_merge(dict1, dict2):
                for key, value in dict2.items():
                    if isinstance(value, dict) and key in dict1 and isinstance(dict1[key], dict):
                        deep_merge(dict1[key], value)
                    else:
                        dict1[key] = value
                return dict1

            target_data = deep_merge(target_data, patch_data)
        else:
            target_data = patch_data
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(target_data, f, indent=4)
        logger.info(f"Applied JSON patch to {target_rel_path}")

    def patch_init_c(self, target_rel_path, data_rel_path):
        if not self.enable_init_patching:
            logger.info(f"Skipping init.c patch (DISABLED): {data_rel_path}")
            return
        target_path = self.mission_dir / target_rel_path
        data_path = self.patch_data_dir / data_rel_path
        if not target_path.exists() or not data_path.exists():
            return
        self._backup_file(target_path)
        with open(data_path) as f:
            patch_code = f.read()
        with open(target_path) as f:
            content = f.read()
        if patch_code.strip() in content:
            logger.info(f"Patch already present in {target_rel_path}, skipping.")
            return
        with open(target_path, "a") as f:
            f.write("\n// --- BEG PATCH ---\n")
            f.write(patch_code)
            f.write("\n// --- END PATCH ---\n")
        logger.info(f"Injected code into {target_rel_path}")

    def run(self):
        logger.info("Starting consolidated patching process...")
        # Check manifest for global safety disable
        if self.manifest.get("disable_init_c", False):
            self.enable_init_patching = False
            logger.info("Init.c patching explicitly disabled in manifest.")

        for patch in self.manifest.get("patches", []):
            _name, target, data = patch.get("name"), patch.get("target"), patch.get("data")
            file_type = patch.get("type", "xml")
            if file_type == "xml":
                self.patch_xml(target, data)
            elif file_type == "json":
                self.patch_json(target, data, mode=patch.get("mode", "merge"))
            elif file_type == "init":
                self.patch_init_c(target, data)
        logger.info("Patching complete.")


if __name__ == "__main__":
    MISSION_DIR = "/home/toxic/dayz_workspace/server_files/mpmissions/dayz_Offline.chernarusplus"
    FIXED_DIR = "/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend/patcher/fixed"
    MANIFEST_FILE = "/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend/patcher/manifest.json"

    # Initialize with clean data directory
    patcher = DayZConfigPatcher(MISSION_DIR, FIXED_DIR, MANIFEST_FILE, enable_init_patching=False)
    patcher.run()
