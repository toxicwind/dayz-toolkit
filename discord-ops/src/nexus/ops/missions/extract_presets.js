const fs = require('fs');
const path = require('path');

const WORKSPACE = process.env.DAYZ_WORKSPACE || '/home/toxic/dayz_workspace/dayz_discord_ops_repo';

// 1. Resolve the source file (no hardcoded absolute paths)
const sourceCandidates = [
  process.env.EZSTREET_CONTAINERS,                                       // explicit override
  path.join(WORKSPACE, 'server/ezstreet/EZStreet_Containers.json'),      // repo-local copy
  path.join(WORKSPACE, 'EZStreet_Containers.json'),                      // legacy root location
];

const sourcePath = sourceCandidates.find(p => p && fs.existsSync(p));
if (!sourcePath) {
  console.error('[ERROR] EZStreet_Containers.json not found. Set EZSTREET_CONTAINERS or place it in server/ezstreet/.');
  process.exit(1);
}

const rawData = fs.readFileSync(sourcePath, 'utf8');
const data = JSON.parse(rawData);

console.log(`[INFO] Loaded ${data.Objects.length} objects from ${sourcePath}`);

// 2. Identify Clusters (Anchor-Based Approach)
const clusters = [];

// Step A: Find Anchors (Containers)
const anchors = data.Objects.filter(obj => obj.name.includes('ContainerLocked'));

console.log(`[INFO] Found ${anchors.length} Anchor Containers.`);

anchors.forEach((anchor, index) => {
  clusters.push({
    anchor: anchor,
    items: [anchor] // Start with the anchor itself
  });
});

// Step B: Assign every other item to the nearest anchor
data.Objects.forEach(obj => {
  // Skip if it's one of the anchors (already added)
  if (obj.name.includes('ContainerLocked')) return;

  let nearestDist = Infinity;
  let nearestClusterIndex = -1;

  anchors.forEach((anchor, index) => {
    const dx = obj.pos[0] - anchor.pos[0];
    const dy = obj.pos[1] - anchor.pos[1];
    const dz = obj.pos[2] - anchor.pos[2];
    const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

    if (dist < nearestDist) {
      nearestDist = dist;
      nearestClusterIndex = index;
    }
  });

  // Threshold: Only assign if within 50m of an anchor
  if (nearestDist <= 50) {
    clusters[nearestClusterIndex].items.push(obj);
  } else {
    console.log(`[WARN] Orphan object found: ${obj.name} at ${obj.pos.map(n => Math.round(n))} (Nearest anchor: ${nearestDist.toFixed(1)}m)`);
  }
});

console.log(`[INFO] Grouped objects into ${clusters.length} clusters.`);

// 3. Normalize Coordinates & Build Library
const presetLibrary = [];

clusters.forEach((clusterData, index) => {
  const anchorObj = clusterData.anchor;
  const items = clusterData.items;
  const anchorPos = anchorObj.pos;

  // Create Normalized Objects (Relative Position)
  const normalizedObjects = items.map(obj => {
    return {
      name: obj.name,
      // Relative Offset: [x - anchorX, y - anchorY, z - anchorZ]
      relPos: [
        obj.pos[0] - anchorPos[0],
        obj.pos[1] - anchorPos[1],
        obj.pos[2] - anchorPos[2]
      ],
      ypr: obj.ypr,
      scale: obj.scale,
      enableCEPersistency: obj.enableCEPersistency,
      customString: obj.customString || ""
    };
  });

  const presetName = `Preset_${index + 1}_${anchorObj.name}`;

  presetLibrary.push({
    id: presetName,
    containerType: anchorObj.name,
    itemCount: items.length,
    originalPos: anchorPos,
    objects: normalizedObjects
  });

  console.log(`   > Cluster ${index + 1}: Anchored on ${anchorObj.name}. Contains ${items.length} items.`);
});

// 4. Save the Library
const outputPath = path.join(WORKSPACE, 'server/ezstreet/Loot_Presets_Library.json');
fs.writeFileSync(outputPath, JSON.stringify(presetLibrary, null, 4));
console.log(`[SUCCESS] Saved ${presetLibrary.length} presets to ${outputPath}`);
