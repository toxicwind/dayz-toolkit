import os
import shutil
import json
import xml.etree.ElementTree as ET
from pathlib import Path

def load_config(config_path):
    if not os.path.exists(config_path):
        print(f"Warning: {config_path} not found. (Using Defaults)")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data.get('economy', {})
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def update_globals(mission_path, economy_settings):
    globals_xml = mission_path / "db" / "globals.xml"
    globals_bak = mission_path / "db" / "globals.xml.bak"

    if not globals_xml.exists():
        print(f"Error: {globals_xml} not found.")
        return

    # Backup if not exists
    if not globals_bak.exists():
        print(f"Creating backup: {globals_bak}")
        shutil.copy2(globals_xml, globals_bak)
    
    # Always read from BACKUP to ensure clean state
    source_file = globals_bak

    try:
        tree = ET.parse(source_file)
        root = tree.getroot()
        
        # Map JSON keys to XML var names
        var_map = {
            'zombie_max': 'ZombieMaxCount',
            'animal_max': 'AnimalMaxCount',
        }

        for json_key, xml_key in var_map.items():
            if json_key in economy_settings:
                for var in root.findall('var'):
                    if var.get('name') == xml_key:
                        var.set('value', str(economy_settings[json_key]))
        
        tree.write(globals_xml, encoding='utf-8', xml_declaration=True)
        print(f"Updated {globals_xml}")

    except Exception as e:
        print(f"Failed to update globals.xml: {e}")

def update_types(mission_path, economy_settings):
    types_xml = mission_path / "db" / "types.xml"
    types_bak = mission_path / "db" / "types.xml.bak"
    
    if not types_xml.exists():
        print(f"Error: {types_xml} not found.")
        return

    # Backup if not exists
    if not types_bak.exists():
        print(f"Creating backup: {types_bak}")
        shutil.copy2(types_xml, types_bak)

    # Always read from BACKUP to ensure clean state
    source_file = types_bak

    loot_multiplier = float(economy_settings.get('loot_multiplier', 1.0))
    lifetime_multiplier = float(economy_settings.get('lifetime_multiplier', 1.0))

    try:
        tree = ET.parse(source_file)
        root = tree.getroot()
        
        for type_elem in root.findall('type'):
            # Update nominal (count)
            if loot_multiplier != 1.0:
                nominal = type_elem.find('nominal')
                if nominal is not None:
                    try:
                        val = int(nominal.text)
                        new_val = int(val * loot_multiplier)
                        nominal.text = str(new_val)
                    except (ValueError, TypeError):
                        pass
                
                min_elem = type_elem.find('min')
                if min_elem is not None:
                    try:
                        val = int(min_elem.text)
                        new_val = int(val * loot_multiplier)
                        min_elem.text = str(new_val)
                    except (ValueError, TypeError):
                        pass

            # Update lifetime
            if lifetime_multiplier != 1.0:
                lifetime = type_elem.find('lifetime')
                if lifetime is not None:
                    try:
                        val = int(lifetime.text)
                        new_val = int(val * lifetime_multiplier)
                        lifetime.text = str(new_val)
                    except (ValueError, TypeError):
                        pass

        tree.write(types_xml, encoding='utf-8', xml_declaration=True)
        print(f"Updated {types_xml} (Loot: {loot_multiplier}x, Lifetime: {lifetime_multiplier}x)")

    except Exception as e:
        print(f"Failed to update types.xml: {e}")

def main():
    # In Docker, we expect:
    # Config/Scripts in: /app/backend_data (mapped from host ./backend_data)
    # Missions in: /app/missions (mapped from host ../dayzxb_missions)
    
    if os.path.exists("/app/backend_data"):
        base_config_path = Path("/app/backend_data")
        missions_root = Path("/app/missions")
    else:
        # Fallback for local testing
        base_path = Path(__file__).parent
        base_config_path = base_path
        # Assuming we are in backend_data and missions is parallel (host structure)
        missions_root = base_path.parent.parent / "dayzxb_missions" 

    mission_name = "dayzOffline.chernarusplus"
    mission_path = missions_root / mission_name
    
    # Path to JSON config in backend_data
    config_path = base_config_path / "EZStreet_ServerConfig.json"
    
    # Load .env file (try parent of backend_data, or /app)
    env_path = base_config_path.parent / ".env"
    if env_path.exists():
        print(f"Loading .env from {env_path}")
        from dotenv import load_dotenv
        load_dotenv(env_path)
    
    print(f"Loading config from {config_path}...")
    economy_settings = load_config(config_path)

    # Override with Env Vars
    if os.getenv('ECONOMY_LOOT_MULTIPLIER'):
        economy_settings['loot_multiplier'] = float(os.environ['ECONOMY_LOOT_MULTIPLIER'])
        print(f"Override: loot_multiplier = {economy_settings['loot_multiplier']}")
        
    if os.getenv('ECONOMY_LIFETIME_MULTIPLIER'):
        economy_settings['lifetime_multiplier'] = float(os.environ['ECONOMY_LIFETIME_MULTIPLIER'])
        print(f"Override: lifetime_multiplier = {economy_settings['lifetime_multiplier']}")

    if os.getenv('ECONOMY_ZOMBIE_MAX'):
        economy_settings['zombie_max'] = int(os.environ['ECONOMY_ZOMBIE_MAX'])
        print(f"Override: zombie_max = {economy_settings['zombie_max']}")

    if os.getenv('ECONOMY_ANIMAL_MAX'):
        economy_settings['animal_max'] = int(os.environ['ECONOMY_ANIMAL_MAX'])
        print(f"Override: animal_max = {economy_settings['animal_max']}")
    
    if not mission_path.exists():
        print(f"Mission {mission_name} not found in {missions_root}")
        return

    print(f"Applying config to mission: {mission_name}")
    update_globals(mission_path, economy_settings)
    update_types(mission_path, economy_settings)
    print("Done.")

if __name__ == "__main__":
    main()
