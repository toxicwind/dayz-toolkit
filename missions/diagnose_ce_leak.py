#!/usr/bin/env python3
"""
Diagnostic script to identify Central Economy groups with no spawn points
that are causing the memory leak in DayZ server.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

def analyze_event_spawns(xml_path):
    """Analyze cfgeventspawns.xml for groups with no positions"""
    print(f"Analyzing: {xml_path}")
    print("=" * 80)
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    groups_with_issues = []
    total_groups = 0
    total_positions = 0
    
    for event in root.findall('.//event'):
        event_name = event.get('name', 'UNKNOWN')
        
        for group in event.findall('.//group'):
            total_groups += 1
            group_name = group.get('name', 'UNKNOWN')
            
            # Count positions in this group
            positions = group.findall('.//pos')
            pos_count = len(positions)
            total_positions += pos_count
            
            if pos_count == 0:
                groups_with_issues.append({
                    'event': event_name,
                    'group': group_name,
                    'positions': pos_count
                })
                print(f"⚠️  EMPTY GROUP FOUND:")
                print(f"   Event: {event_name}")
                print(f"   Group: {group_name}")
                print(f"   Positions: {pos_count}")
                print()
    
    print("=" * 80)
    print(f"Total Groups: {total_groups}")
    print(f"Total Positions: {total_positions}")
    print(f"Groups with NO positions: {len(groups_with_issues)}")
    print()
    
    if groups_with_issues:
        print("🚨 PROBLEMATIC GROUPS (likely causing memory leak):")
        print("-" * 80)
        for issue in groups_with_issues:
            print(f"  - {issue['group']} (in event: {issue['event']})")
    
    return groups_with_issues

def analyze_types_xml(xml_path):
    """Check types.xml for excessive nominal values or duplicates"""
    print(f"\nAnalyzing: {xml_path}")
    print("=" * 80)
    
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    type_names = []
    high_nominal = []
    
    for type_elem in root.findall('.//type'):
        name = type_elem.get('name', 'UNKNOWN')
        type_names.append(name)
        
        nominal_elem = type_elem.find('nominal')
        if nominal_elem is not None:
            try:
                nominal = int(nominal_elem.text)
                if nominal > 1000:
                    high_nominal.append({'name': name, 'nominal': nominal})
            except (ValueError, TypeError):
                pass
    
    # Check for duplicates
    duplicates = [name for name in set(type_names) if type_names.count(name) > 1]
    
    print(f"Total Types: {len(type_names)}")
    print(f"Duplicate Types: {len(duplicates)}")
    print(f"Types with nominal > 1000: {len(high_nominal)}")
    
    if duplicates:
        print("\n⚠️  DUPLICATE TYPE NAMES:")
        for dup in duplicates[:10]:  # Show first 10
            print(f"  - {dup}")
    
    if high_nominal:
        print("\n⚠️  TYPES WITH VERY HIGH NOMINAL VALUES:")
        for item in sorted(high_nominal, key=lambda x: x['nominal'], reverse=True)[:10]:
            print(f"  - {item['name']}: {item['nominal']}")
    
    return duplicates, high_nominal

if __name__ == "__main__":
    from vector.config import get_settings
    settings = get_settings()
    mission_path = settings.staging_dir / "dayzxb_missions/dayzOffline.chernarusplus"
    
    print("🔍 DayZ Central Economy Diagnostic Tool")
    print("=" * 80)
    print()
    
    # Analyze event spawns
    eventspawns_path = mission_path / "cfgeventspawns.xml"
    if eventspawns_path.exists():
        empty_groups = analyze_event_spawns(eventspawns_path)
    else:
        print(f"❌ File not found: {eventspawns_path}")
    
    # Analyze types.xml
    types_path = mission_path / "db" / "types.xml"
    if types_path.exists():
        duplicates, high_nominal = analyze_types_xml(types_path)
    else:
        print(f"❌ File not found: {types_path}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
