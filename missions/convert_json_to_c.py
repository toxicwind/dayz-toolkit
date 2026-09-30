import json
import os

def vector_to_string(vec):
    return f"Vector({vec[0]}, {vec[1]}, {vec[2]})"

def process_file(filepath, output_lines):
    print(f"Processing {filepath}...")
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        objects = data.get("Objects", [])
        for obj in objects:
            name = obj.get("name")
            pos = obj.get("pos")
            ypr = obj.get("ypr")
            scale = obj.get("scale", 1.0)
            
            if not name or not pos or not ypr:
                continue
                
            # Create object
            output_lines.append(f'\tobj = GetGame().CreateObject("{name}", {vector_to_string(pos)});')
            output_lines.append(f'\tif (obj) {{')
            output_lines.append(f'\t\tobj.SetOrientation({vector_to_string(ypr)});')
            if scale != 1.0:
                 output_lines.append(f'\t\tobj.SetScale({scale});')
            
            # Handle specific flags if needed, mostly static objects just need position/orientation
            output_lines.append(f'\t\tobj.SetFlags(EntityFlags.STATIC, false);')
            output_lines.append(f'\t\tobj.Update();')
            output_lines.append(f'\t}}')
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    from vector.config import get_settings
    settings = get_settings()
    base_dir = settings.staging_dir / "dayzxb_missions/dayzOffline.chernarusplus/custom"
    files = [
        "LockedContainers_Spawns.json",
        "EZStreet_bm_Trader.json",
        "EZStreet_Containers.json",
        "EZADMIN_Base_Hobo.json"
    ]
    
    output_lines = []
    output_lines.append("void SpawnCustomObjects()")
    output_lines.append("{")
    output_lines.append("\tObject obj;")
    
    for filename in files:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            process_file(filepath, output_lines)
        else:
            print(f"File not found: {filepath}")
            
    output_lines.append("}")
    
    output_path = os.path.join(base_dir, "custom_spawns.c")
    with open(output_path, 'w') as f:
        f.write("\n".join(output_lines))
    print(f"Written to {output_path}")

if __name__ == "__main__":
    main()
