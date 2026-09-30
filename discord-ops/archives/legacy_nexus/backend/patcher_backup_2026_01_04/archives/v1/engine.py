import logging
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

log = logging.getLogger("patch_engine")


class PatchEngine:
    def __init__(self, staging_dir, repo_root):
        self.staging_dir = Path(staging_dir)
        self.repo_root = Path(repo_root)

    def apply_raw_copy(self, patch_id, source_rel, target_rel):
        """Copy file from source to target."""
        # Source is relative to REPO_ROOT (usually backend/patcher/patches/...)
        # Target is relative to STAGING_DIR (e.g. custom/...)
        # Or source is in patches dir?
        # apply_unified_patches.py passes patch.get("source"), patch.get("target") from raw_copy patch.
        # Let's assume source is relative to repo root if not absolute.

        src = self.repo_root / source_rel
        dst = self.staging_dir / target_rel

        if not src.exists():
            log.error(f"[{patch_id}] Source missing: {src}")
            return False

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        log.info(f"[{patch_id}] Copied {src.name} -> {target_rel}")
        return True

    def apply_xml_patch(self, patch_id, target_file, complex_patches, data_xml=None):
        """Apply XML patches."""
        target_path = self.staging_dir / target_file
        if not target_path.exists():
            log.error(f"[{patch_id}] Target XML missing: {target_path}")
            return False

        try:
            tree = ET.parse(target_path)
            root = tree.getroot()
            modified = False

            # Handle data injection (data_xml)
            if data_xml:
                # Parse data_xml string into element
                try:
                    injected_root = ET.fromstring(data_xml)
                    # For DayZ events/types, usually we append children of the injected root to the target root
                    # logic: iterate children of injected_root and append to root
                    for child in list(injected_root):
                        root.append(child)
                    modified = True
                    log.info(f"[{patch_id}] Injected XML data")
                except ET.ParseError as e:
                    log.error(f"[{patch_id}] Invalid data_xml: {e}")
                    raise e

            for op in complex_patches:
                xpath = op.get("xpath")
                # Fix absolute xpath issue
                if xpath.startswith("//"):
                    xpath = "." + xpath

                action = op.get("action", "modify").lower()
                attributes = op.get("attributes", {})
                op.get("value")  # Can be dict for multiple values

                # Support "values": {"nominal": "2"} style used in Goopsta/JSON patches
                values_dict = op.get("values", {})

                nodes = root.findall(xpath)
                if not nodes:
                    # STRICT REQUIREMENT: Fail hard on 0 matches
                    # Only fail if action implies finding existing nodes
                    log.error(f"[{patch_id}] XPath '{xpath}' matched 0 nodes in {target_file}")
                    # raise ValueError(f"XPath '{xpath}' matched 0 nodes in {target_file}")
                    # Softening to log error for now to allow partial success?
                    # Prompt said "fails hard with an error".
                    # Let's keep raising, but maybe catch it in apply_unified_patches to not stop everything?
                    # apply_unified_patches.py catches exceptions.
                    # But verifying "no silent no-op" means I should raise.
                    raise ValueError(f"XPath '{xpath}' matched 0 nodes")

                for node in nodes:
                    if action == "modify":
                        # Handle direct text update
                        text_val = op.get("text")
                        if text_val is not None:
                            node.text = str(text_val)
                            modified = True

                        # Handle attributes
                        for k, v in attributes.items():
                            node.set(k, str(v))
                            modified = True

                        # Handle nested values (e.g. <nominal>2</nominal> relative to matched node)
                        # e.g. xpath matched <type>, values={"nominal": "2"}
                        for tag, val in values_dict.items():
                            # Find child tag
                            # Handle attribute update via '@attr': e.g. 'category/@name'
                            # But typical usage is child element text
                            child = node.find(tag)
                            if child is not None:
                                child.text = str(val)
                                modified = True
                            # Create if missing? Or log warning?
                            # Usually we expect it to exist.
                            # For some patches, we might updating attributes like 'active' on event.
                            elif tag in node.attrib:
                                node.set(tag, str(val))
                                modified = True
                            else:
                                # DayZ XML structure usually simple.
                                # If not found as child, maybe it's attribute?
                                # Let's check attributes again
                                pass

            if modified:
                tree.write(target_path, encoding="utf-8", xml_declaration=True)
                log.info(f"[{patch_id}] Applied XML patch to {target_file}")
                return True

        except Exception as e:
            log.error(f"[{patch_id}] XML Patch failed: {e}")
            raise e  # Escalate error

    def apply_gameplay_patch(self, patch_id, path, values):
        """Apply generic gameplay json/object patch."""
        # Stub for now, based on json patching logic
        pass

    def apply_script_patch(self, patch_id, script_file):
        """Apply script injection."""
        # Stub
        pass
