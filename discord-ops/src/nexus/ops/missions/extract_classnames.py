#!/usr/bin/env python3
"""
Extract DayZ Class Names from types.xml for trader mapping
"""
import xml.etree.ElementTree as ET
import json

def extract_classnames(types_xml_path):
    """Extract all item classnames from types.xml"""
    tree = ET.parse(types_xml_path)
    root = tree.getroot()
    
    classnames = {}
    for type_elem in root.findall('.//type'):
        name = type_elem.get('name')
        if name:
            # Get category if it exists
            category = None
            category_elem = type_elem.find('category')
            if category_elem is not None:
                category = category_elem.get('name')
            
            classnames[name] = {
                'classname': name,
                'category': category or 'Unknown'
            }
    
    return classnames

if __name__ == "__main__":
    from src.mildlyawesome.config import get_settings
    settings = get_settings()
    types_path = settings.staging_dir / "dayzxb_missions/dayzOffline.chernarusplus/db/types.xml"
    
    print(f"Extracting classnames from {types_path}...")
    classnames = extract_classnames(types_path)
    
    # Save to JSON
    output_path = settings.chronos_root / "dayz_classnames.json"
    with open(output_path, 'w') as f:
        json.dump(classnames, f, indent=2, sort_keys=True)
    
    print(f"Extracted {len(classnames)} classnames to {output_path}")
    
    # Search for some common items from the trader list
    search_terms = ['M65', 'Bushlat', 'Rider', 'Hiking', 'Leather', 'Gorka', 'Quilted', 'Jeans', 'Boot', 'Hunter']
    
    print("\n=== Sample Matches ===")
    for term in search_terms:
        matches = [k for k in classnames.keys() if term.lower() in k.lower()]
        if matches:
            print(f"\n{term}:")
            for m in matches[:5]:  # Show first 5
                print(f"  - {m}")
