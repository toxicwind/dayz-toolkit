import asyncio
import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from modules.chronos.service import ChronosService

async def verify_chronos():
    print("🧪 Starting Chronos Manual Verification...")
    
    # Test Exhumation
    print("\n--- Testing Exhumation ---")
    exhumed = await ChronosService.exhume_keys()
    print(f"Exhumed {len(exhumed)} potential keys.")
    if exhumed:
        print(f"Sample keys: {list(exhumed)[:5]}")
    
    # Test Settings Loading
    print("\n--- Testing Settings Loading ---")
    settings = await ChronosService.load_settings()
    print(f"Loaded settings. Count: {len(settings)}")
    
    # Test Merging
    print("\n--- Testing Predatory Merging ---")
    mock_exhumed = {"chronos.predatory.mode", "chronos.entropy.limit", "test.unknown"}
    merged = ChronosService.merge_predatory_defaults(settings.copy(), mock_exhumed)
    print(f"Merged count: {len(merged)}")
    for key in mock_exhumed:
        if key in merged:
            print(f"  {key}: {merged[key]}")
    
    # Test Local Audit (Query)
    print("\n--- Testing Predator Query (Multi-Vector) ---")
    query = "git"
    predator_res = await ChronosService.predator_query(query)
    print(f"Query: '{query}'")
    print(f"Decision: {predator_res['decision']}")
    print(f"Local Results (first 2 lines):\n{chr(10).join(predator_res['local'].splitlines()[:2])}")
    if predator_res['emergent']:
        print(f"Emergent Context: Found hit (len: {len(predator_res['emergent'])})")

    # Test Ghost Mapping
    print("\n--- Testing Ghost Mapping ---")
    keys = {"chronos.predatory.mode", "unknown.ghost.key"}
    usage = await ChronosService.cross_reference_usage(keys)
    for k, v in usage.items():
        print(f"  {k}: {v['status']} (Occurrences: {v['occurrences']})")

    # Test Entropy Scan
    print("\n--- Testing Entropy Scan ---")
    emap = await ChronosService.entropy_scan()
    print(f"Top Hotspot: {emap['insights']['top_hotspot']}")
    print(f"Total Config Density: {emap['insights']['total_config_density']}")
    sample_entropy = list(emap['map'].items())[0] if emap['map'] else ("None", {"entropy": 0})
    print(f"Sample: {sample_entropy[0]} -> {sample_entropy[1]['entropy']}e")

    # Test Predictive Patching
    print("\n--- Testing Predictive Patching ---")
    patch = await ChronosService.predictive_patch("API")
    print(f"Target: {patch['target_component']}")
    print(f"Action: {patch['suggested_action']}")

    # Test Recovery (Blob Scavenge)
    print("\n--- Testing Historical Recovery (Blob Scavenge) ---")
    recovery = await ChronosService.blob_scavenge(["settings"])
    print(f"Found {len(recovery)} hits in dangling blobs.")

    print("\n✅ Emergent Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_chronos())
