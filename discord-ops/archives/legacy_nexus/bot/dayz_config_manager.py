#!/usr/bin/env python3
"""
DayZ Server Configuration Manager
Handles globals.xml, cfgEffectArea.json, and init.c modifications
"""
import os
import json
import xml.etree.ElementTree as ET
from ftplib import FTP
from pathlib import Path
from typing import Dict, Any, List, Optional
from .patch_manager import PatchManager

class DayZConfigManager:
    def __init__(self, settings: Optional[Any] = None):
        # Load settings
        if settings:
            self.settings = settings
        else:
            from .config import get_settings
            self.settings = get_settings()

        # Paths from config
        self.workspace = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo")
        self.vanilla_path = Path(self.settings.vanilla_path or (self.workspace / "data/dayz_vanilla/official_repo/dayzOffline.chernarusplus"))
        
        # Provenance / Baseline (Vanilla 1.28)
        self.provenance_path = self.vanilla_path # Using vanilla directly as base 
        
        # Live / Output Config
        self.mission_path = Path(self.settings.mission_path or (self.workspace / "dayzxb_missions/dayzOffline.chernarusplus"))
        
        # Initialize Patch Manager
        self.patch_manager = PatchManager(
            base_path=self.provenance_path,
            output_path=self.mission_path
        )

        # File Paths (Pointing to LIVE config)
        self.globals_xml = self.mission_path / "db/globals.xml"
        self.gas_zones_json = self.mission_path / "cfgEffectArea.json"
        
        # FTP from config
        self.ftp_host = self.settings.ftp_host
        self.ftp_user = self.settings.ftp_user
        self.ftp_pass = self.settings.ftp_password

    def get_globals(self) -> Dict[str, Any]:
        """Read globals.xml from LIVE config and return key values"""
        if not self.globals_xml.exists():
            # If live doesn't exist, try to regenerate from base
            self.patch_manager.regenerate_xml_config("db/globals.xml")
            
        try:
            tree = ET.parse(self.globals_xml)
            root = tree.getroot()
            
            globals_dict = {}
            for var in root.findall('var'):
                name = var.get('name')
                value = var.get('value')
                var_type = var.get('type')
                
                # Convert to appropriate type
                if var_type == '0':  # Integer
                    globals_dict[name] = int(value)
                elif var_type == '1':  # Float
                    globals_dict[name] = float(value)
                else:
                    globals_dict[name] = value
            
            return globals_dict
        except Exception as e:
            print(f"Error reading globals.xml: {e}")
            return {}

    def update_globals(self, updates: Dict[str, Any]) -> bool:
        """
        Update globals.xml by creating a transient patch.
        NOTE: Ideally, specific features should be used, but this supports raw edits.
        """
        patches = []
        for name, value in updates.items():
            patches.append(self.patch_manager.create_global_patch(name, value))
            
        # We use a generic 'manual_override' patch ID for direct edits
        return self.patch_manager.apply_xml_patch("db/globals.xml", "manual_override", patches)

    def get_gas_zones(self) -> List[Dict[str, Any]]:
        """Read cfgEffectArea.json and return gas zones"""
        if not self.gas_zones_json.exists():
            self.patch_manager.regenerate_json_config("cfgEffectArea.json")

        try:
            with open(self.gas_zones_json, 'r') as f:
                data = json.load(f)
            
            # Add enabled flag (default to True for existing zones)
            zones = []
            for area in data.get('Areas', []):
                zone = {
                    'AreaName': area.get('AreaName'),
                    'Type': area.get('Type'),
                    'Data': area.get('Data'),
                    'PlayerData': area.get('PlayerData'),
                    'TriggerType': area.get('TriggerType'),
                    'enabled': True  # All zones in file are enabled
                }
                zones.append(zone)
            
            return zones
        except Exception as e:
            print(f"Error reading gas zones: {e}")
            return []

    def update_gas_zones(self, zones: List[Dict[str, Any]]) -> bool:
        """
        Update cfgEffectArea.json.
        Since gas zones removal involves filtering, we treat the 'filtered list' 
        as the target state and generate a JSON patch against the BASE.
        """
        # Filter out disabled zones to get the target state
        enabled_zones = []
        for zone in zones:
            if zone.get('enabled', True):
                zone_data = {k: v for k, v in zone.items() if k != 'enabled'}
                enabled_zones.append(zone_data)
        
        # For JSON patches, we can construct the specific 'replace' op for 'Areas'
        patch = [{
            "op": "replace",
            "path": "/Areas",
            "value": enabled_zones
        }]
        
        return self.patch_manager.apply_json_patch("cfgEffectArea.json", "gas_zones_config", patch)

    def get_gameplay(self) -> Dict[str, Any]:
        """Get gameplay settings from cfggameplay.json"""
        json_path = self.mission_path / "cfggameplay.json"
        
        if not json_path.exists():
            self.patch_manager.regenerate_json_config("cfggameplay.json")
            
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            return {
                "disableBaseDamage": data.get("BaseBuildingData", {}).get("HologramData", {}).get("DisableIsCollidingBBoxCheck", False), # Mapping logic TBD
                "staminaMax": data.get("PlayerData", {}).get("StaminaData", {}).get("StaminaMax", 100.0)
            }
        except Exception as e:
            print(f"Error reading gameplay config: {e}")
            return {}

    def update_gameplay(self, updates: Dict[str, Any]) -> bool:
        """Update gameplay settings using patches"""
        patches = []
        
        if "staminaMax" in updates:
            patches.append({
                "op": "replace",
                "path": "/PlayerData/StaminaData/staminaMax",
                "value": float(updates["staminaMax"])
            })

        if "disableBaseDamage" in updates:
            patches.append({
                "op": "replace",
                "path": "/GeneralData/disableBaseDamage",
                "value": bool(updates["disableBaseDamage"])
            })
            
        return self.patch_manager.apply_json_patch("cfggameplay.json", "gameplay_settings", patches)

    def clear_gameplay_patches(self) -> bool:
        """Revert gameplay settings to vanilla/provenance base"""
        # For now, we assume 'gameplay_settings' is the only patch ID we use for this file
        return self.patch_manager.remove_patch("cfggameplay.json", "gameplay_settings")

    def get_weather(self) -> Dict[str, Any]:
        """Get weather settings from cfgweather.xml"""
        xml_path = self.mission_path / "cfgweather.xml"
        
        if not xml_path.exists():
            self.patch_manager.regenerate_xml_config("cfgweather.xml")

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            return {"reset": root.get("reset", "1") == "1"}
        except Exception as e:
            print(f"Error reading weather config: {e}")
            return {}

    def update_weather(self, updates: Dict[str, Any]) -> bool:
        """Update weather settings using patches"""
        patches = []
        
        if "reset" in updates:
            patches.append({
                "op": "set_attr",
                "xpath": "/weather",
                "attr": "reset",
                "value": "1" if updates["reset"] else "0"
            })
            
        return self.patch_manager.apply_xml_patch("cfgweather.xml", "weather_settings", patches)

    def upload_to_server(self, local_file: str, remote_path: str) -> bool:
        """Upload config file to Nitrado server via FTP"""
        if not all([self.ftp_host, self.ftp_user, self.ftp_pass]):
            print("FTP credentials check failed in manager. (Env vars might be missing)")
            # Fallback to hardcoded for now if needed, or rely on .env loading
            # But debug_start.sh exports them now.
        
        try:
            with FTP(self.ftp_host or 'usla352.gamedata.io') as ftp:
                ftp.login(user=self.ftp_user or 'ni12435433_1', passwd=self.ftp_pass)
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f"STOR {remote_path}", f)
            print(f"Uploaded {local_file} to {remote_path}")
            return True
        except Exception as e:
            print(f"FTP Upload failed: {e}")
            return False


if __name__ == "__main__":
    manager = DayZConfigManager()
    
    # Test reading globals
    globals_data = manager.get_globals()
    print("Current Globals:")
    print(f"  ZombieMaxCount: {globals_data['ZombieMaxCount']}")
    print(f"  AnimalMaxCount: {globals_data['AnimalMaxCount']}")
    print(f"  LootDamageMin: {globals_data['LootDamageMin']}")
    print(f"  LootDamageMax: {globals_data['LootDamageMax']}")
    
    # Test reading gas zones
    zones = manager.get_gas_zones()
    print(f"\nGas Zones: {len(zones)} total")
    for zone in zones[:3]:
        print(f"  - {zone['AreaName']}")
