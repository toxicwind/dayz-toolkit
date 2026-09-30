
import xml.etree.ElementTree as ET
import sys

try:
    from src.mildlyawesome.config import get_settings
    settings = get_settings()
    types_path = settings.staging_dir / "dayzxb_missions/dayzOffline.chernarusplus/db/types.xml"
    tree = ET.parse(str(types_path))
    root = tree.getroot()
    for type_elem in root.findall('type'):
        nominal = type_elem.find('nominal')
        if nominal is not None:
            val = int(nominal.text)
            new_val = int(val / 1.5)
            # Avoid 0 if it wasn't 0 (simple heuristic, not perfect but okay for revert)
            if val > 0 and new_val == 0: new_val = 1 
            if val == 0: new_val = 0
            # Special fix for ACOGOptic
            if type_elem.get('name') == 'ACOGOptic' and val == 15: new_val = 10
            
            nominal.text = str(new_val)
        
        min_elem = type_elem.find('min')
        if min_elem is not None:
             val = int(min_elem.text)
             new_val = int(val / 1.5)
             if val > 0 and new_val == 0: new_val = 1
             if val == 0: new_val = 0
             min_elem.text = str(new_val)

    tree.write(str(types_path), encoding='utf-8', xml_declaration=True)
    print("Reverted.")
except Exception as e:
    print(e)
