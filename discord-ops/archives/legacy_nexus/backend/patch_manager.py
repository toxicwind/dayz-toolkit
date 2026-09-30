import json
import logging
from pathlib import Path
from typing import Any

import jsonpatch
from lxml import etree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PatchManager:
    def __init__(self, base_path: str | Path, output_path: str | Path):
        """
        Initialize the Patch Manager.

        Args:
            base_path: Directory containing vanilla/provenance files (Immutable).
            output_path: Directory where the 'Live' server config is generated.
        """
        self.base_path = Path(base_path)
        self.output_path = Path(output_path)
        self.patches_dir = self.output_path / "patches"
        self.patches_dir.mkdir(parents=True, exist_ok=True)

        # Ensure output directory structure exists
        self.output_path.mkdir(parents=True, exist_ok=True)

    def validate_patch_structure(self, patch_body: list[dict], patch_type: str = "json") -> bool:
        """
        Validate patch structure against schema.

        Args:
            patch_body: List of patch operations.
            patch_type: 'json' (RFC 6902) or 'xml' (Custom XPath).
        """
        if not isinstance(patch_body, list):
            logger.error(f"Patch body must be a list, got {type(patch_body)}")
            return False

        valid_ops_json = {"add", "remove", "replace", "move", "copy", "test"}
        valid_ops_xml = {"replace", "remove", "set_attr", "add"}  # Extended for XML

        for i, op in enumerate(patch_body):
            if not isinstance(op, dict):
                logger.error(f"Patch op #{i} is not a dict")
                return False

            # Key check
            keys = set(op.keys())
            if patch_type == "json":
                if "op" not in keys or "path" not in keys:
                    logger.error(f"JSON Op #{i} missing 'op' or 'path': {op}")
                    return False
                if op["op"] not in valid_ops_json:
                    logger.error(f"JSON Op #{i} invalid op '{op.get('op')}'")
                    return False
            else:  # XML
                if "op" not in keys or "xpath" not in keys:
                    logger.error(f"XML Op #{i} missing 'op' or 'xpath': {op}")
                    return False
                if op["op"] not in valid_ops_xml:
                    logger.error(f"XML Op #{i} invalid op '{op.get('op')}'")
                    return False

        return True

    def validate_patch_structure(self, patch_body: list[dict], patch_type: str = "json") -> bool:
        """
        Validate patch structure against schema.

        Args:
            patch_body: List of patch operations.
            patch_type: 'json' (RFC 6902) or 'xml' (Custom XPath).
        """
        if not isinstance(patch_body, list):
            logger.error(f"Patch body must be a list, got {type(patch_body)}")
            return False

        valid_ops_json = {"add", "remove", "replace", "move", "copy", "test"}
        valid_ops_xml = {"replace", "remove", "set_attr", "add"}  # Extended for XML

        for i, op in enumerate(patch_body):
            if not isinstance(op, dict):
                logger.error(f"Patch op #{i} is not a dict")
                return False

            # Key check
            keys = set(op.keys())
            if patch_type == "json":
                if "op" not in keys or "path" not in keys:
                    logger.error(f"JSON Op #{i} missing 'op' or 'path': {op}")
                    return False
                if op["op"] not in valid_ops_json:
                    logger.error(f"JSON Op #{i} invalid op '{op.get('op')}'")
                    return False
            else:  # XML
                if "op" not in keys or "xpath" not in keys:
                    logger.error(f"XML Op #{i} missing 'op' or 'xpath': {op}")
                    return False
                if op["op"] not in valid_ops_xml:
                    logger.error(f"XML Op #{i} invalid op '{op.get('op')}'")
                    return False

        return True

    def _get_active_patches(self, config_file: str) -> list[dict]:
        """
        Retrieve list of active patches for a specific configuration file.
        In a real implementation, this might read from a manifest.json or database.
        For now, we'll scan the patches dir for files starting with the config name.
        """
        # TODO: Implement robust ordering/manifest system
        patch_files = sorted(self.patches_dir.glob(f"{config_file}.patch_*.json"))
        patches = []
        for pf in patch_files:
            try:
                with open(pf) as f:
                    patches.append(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load patch {pf}: {e}")
        return patches

    def apply_json_patch(self, config_file: str, patch_id: str, patch_body: list[dict]) -> bool:
        """
        Save a JSON patch and regenerate the live config.

        Args:
            config_file: Name of the file (e.g., 'cfggameplay.json')
            patch_id: Unique name for the feature (e.g., 'infinite_stamina')
            patch_body: RFC 6902 JSON patch list
        """
        patch_filename = f"{config_file}.patch_{patch_id}.json"
        patch_path = self.patches_dir / patch_filename

        try:
            # Ensure subdirectory exists (e.g. patches/db/ for db/globals.xml)
            patch_path.parent.mkdir(parents=True, exist_ok=True)

            with open(patch_path, "w") as f:
                json.dump(patch_body, f, indent=4)
            logger.info(f"Saved patch: {patch_filename}")

            return self.regenerate_json_config(config_file)
        except Exception as e:
            logger.error(f"Failed to apply JSON patch {patch_id}: {e}")
            return False

    def remove_patch(self, config_file: str, patch_id: str) -> bool:
        """Remove a specific patch file and regenerate config."""
        patch_filename = f"{config_file}.patch_{patch_id}.json"
        patch_path = self.patches_dir / patch_filename

        if patch_path.exists():
            patch_path.unlink()
            logger.info(f"Removed patch: {patch_filename}")
            if config_file.endswith(".json"):
                return self.regenerate_json_config(config_file)
            elif config_file.endswith(".xml"):
                return self.regenerate_xml_config(config_file)  # Placeholder
            return True
        return False

    def regenerate_json_config(self, config_file: str) -> bool:
        """
        Re-builds a JSON config file from Base + All Active Patches.
        """
        base_file = self.base_path / config_file
        if not base_file.exists():
            logger.error(f"Base file not found: {base_file}")
            return False

        try:
            # 1. Load Base
            with open(base_file) as f:
                doc = json.load(f)

            # 2. Load and Apply All Patches
            patches = self._get_active_patches(config_file)
            for patch_data in patches:
                patch = jsonpatch.JsonPatch(patch_data)
                doc = patch.apply(doc)

            # 3. Write to Output (Live)
            target_file = self.output_path / config_file
            with open(target_file, "w") as f:
                json.dump(doc, f, indent=4)

            logger.info(f"Regenerated {config_file} with {len(patches)} patches.")
            return True

        except Exception as e:
            logger.error(f"Failed to regenerate {config_file}: {e}")
            return False

    # XML Patching is significantly more complex due to lack of standard "XML Patch" format
    # We will implement a simplified XPath-based patcher for now using lxml
    def apply_xml_patch(self, config_file: str, patch_id: str, patch_body: list[dict]) -> bool:
        """
        Save an XML "patch" (custom generic structure) and regenerate.

        Patch Body Schema (Simplified):
        [
            {"op": "replace", "xpath": "/variables/var[@name='ZombieMaxCount']/@value", "value": "2000"},
            {"op": "remove", "xpath": "/variables/var[@name='UselessVar']"}
        ]
        """
        patch_filename = f"{config_file}.patch_{patch_id}.json"
        patch_path = self.patches_dir / patch_filename

        try:
            # Ensure subdirectory exists for patches (e.g. patches/db/)
            patch_path.parent.mkdir(parents=True, exist_ok=True)

            with open(patch_path, "w") as f:
                json.dump(patch_body, f, indent=4)

            return self.regenerate_xml_config(config_file)
        except Exception as e:
            logger.error(f"Failed to apply XML patch {patch_id}: {e}")
            return False

    def regenerate_xml_config(self, config_file: str) -> bool:
        """
        Re-builds an XML config file from Base + All Active Patches.
        """
        base_file = self.base_path / config_file
        if not base_file.exists():
            logger.error(f"Base file not found: {base_file}")
            return False

        try:
            # 1. Load Base
            parser = ET.XMLParser(remove_blank_text=False)
            tree = ET.parse(str(base_file), parser)

            # 2. Load and Apply Patches
            patches = self._get_active_patches(config_file)
            for patch_list in patches:
                for op in patch_list:
                    self._apply_single_xml_op(tree, op)

            # 3. Write to Output
            target_file = self.output_path / config_file
            tree.write(str(target_file), encoding="utf-8", xml_declaration=True, pretty_print=True)

            logger.info(f"Regenerated {config_file} with {len(patches)} patches.")
            return True

        except Exception as e:
            logger.error(f"Failed to regenerate {config_file}: {e}")
            return False

    def _apply_single_xml_op(self, tree, op: dict):
        """Helper to apply a single patch operation to an lxml tree"""
        xpath = op.get("xpath")
        action = op.get("op")
        value = op.get("value")

        nodes = tree.xpath(xpath)
        if not nodes:
            logger.warning(f"XPath not found: {xpath}")
            return

        for node in nodes:
            if action == "replace":
                if isinstance(node, ET._Element):
                    node.text = str(value)
                elif isinstance(node, str) or isinstance(node, ET._ElementUnicodeResult):
                    # Attribute or text node result. lxml xpath returns smart objects
                    # Handling attributes is tricky with pure xpath result, usually parent element is needed
                    # For our specific needs, let's assume xpath points to elements or we handle special attribute syntax
                    pass
            elif action == "set_attr":
                # Custom op: xpath to element, then set attribute
                attr_name = op.get("attr")
                if isinstance(node, ET._Element):
                    node.set(attr_name, str(value))

    # NOTE: lxml xpath result handling for attributes is complex.
    # Refined Approach for Globals.xml specifically:
    # Most DayZ XMLs are lists of <var name="X" value="Y" /> or similar flat structures.
    def create_global_patch(self, var_name: str, new_value: Any) -> dict:
        """Helper to create a patch for globals.xml format"""
        return {"op": "set_attr", "xpath": f"//var[@name='{var_name}']", "attr": "value", "value": new_value}
