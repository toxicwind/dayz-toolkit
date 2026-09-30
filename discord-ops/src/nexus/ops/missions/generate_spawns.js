const fs = require('fs');
const path = require('path');

// Configuration
const PRESETS_FILE = '/home/toxic/dayz_workspace/Loot_Presets_Library.json';
const LOCATIONS_FILE = '/home/toxic/dayz_workspace/Target_Locations.json';
const OUTPUT_FILE = '/home/toxic/dayz_workspace/LockedContainers_Spawns.json';

// === DYNAMIC SETTINGS ===
const ROTATION_ENABLED = true;       // Enable location rotation
const ROTATION_PERCENTAGE = 0.6;      // Spawn 60% of locations per restart (18 of 30)
const TIER_WEIGHTS = {                // Higher tier = rarer
  1: 35,   // Coast/Common
  2: 30,   // Industrial
  3: 25,   // Military
  4: 10    // Tier4/Ultra-rare
};

// Helper: Rotate a point around [0,0,0] by a given Yaw angle (degrees)
function rotatePoint(x, z, angleDegrees) {
  const rad = angleDegrees * (Math.PI / 180);
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return {
    x: x * cos - z * sin,
    z: x * sin + z * cos
  };
}

// Helper: Shuffle array (Fisher-Yates)
function shuffleArray(arr) {
  const shuffled = [...arr];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

// Helper: Select preset based on location tier
function selectPresetForTier(presets, tier) {
  // Match preset to location tier if possible
  // Presets have naming like "Preset_1_Land_ContainerLocked_Yellow_DE"
  // Colors: Blue (Tier 1-2), Yellow (Tier 2-3), Orange (Tier 3), Red (Tier 4)
  const tierMap = {
    1: ['Blue', 'Yellow'],
    2: ['Blue', 'Yellow'],
    3: ['Yellow', 'Orange'],
    4: ['Orange', 'Red']
  };

  const preferredColors = tierMap[tier] || ['Blue'];
  const matchingPresets = presets.filter(p =>
    preferredColors.some(color => p.id.includes(color))
  );

  if (matchingPresets.length > 0) {
    return matchingPresets[Math.floor(Math.random() * matchingPresets.length)];
  }
  return presets[Math.floor(Math.random() * presets.length)];
}

// 1. Load Data
console.log('[INFO] Loading presets and locations...');
const presets = JSON.parse(fs.readFileSync(PRESETS_FILE, 'utf8'));
let locations = JSON.parse(fs.readFileSync(LOCATIONS_FILE, 'utf8'));

console.log(`[INFO] Found ${presets.length} Presets and ${locations.length} Target Locations.`);

// 2. Apply Rotation (if enabled)
if (ROTATION_ENABLED) {
  const activeCount = Math.ceil(locations.length * ROTATION_PERCENTAGE);
  locations = shuffleArray(locations).slice(0, activeCount);
  console.log(`[ROTATION] Spawning ${locations.length} of ${activeCount} locations (${Math.round(ROTATION_PERCENTAGE * 100)}%)`);
}

const finalObjects = [];

// 3. Main Logic: For each location, spawn tier-appropriate preset
locations.forEach((loc, i) => {
  const tier = loc.tier || 2;  // Default to tier 2
  const randomPreset = selectPresetForTier(presets, tier);

  console.log(`[SPAWN] Location ${i + 1} (${loc.name}) [Tier ${tier}] -> Spawning ${randomPreset.id}`);

  // Loop through all objects in the preset
  randomPreset.objects.forEach(obj => {
    const locYaw = loc.ypr ? loc.ypr[0] : 0;
    const rotatedOffset = rotatePoint(obj.relPos[0], obj.relPos[2], locYaw);

    const finalX = loc.pos[0] + rotatedOffset.x;
    const finalY = loc.pos[1] + obj.relPos[1];
    const finalZ = loc.pos[2] + rotatedOffset.z;
    const finalYaw = (obj.ypr[0] + locYaw) % 360;

    finalObjects.push({
      name: obj.name,
      pos: [finalX, finalY, finalZ],
      ypr: [finalYaw, obj.ypr[1], obj.ypr[2]],
      scale: obj.scale,
      enableCEPersistency: obj.enableCEPersistency,
      customString: obj.customString || ""
    });
  });
});

// 4. Export to DayZ Editor Format
const outputData = {
  "Objects": finalObjects,
  "meta": {
    "generatedAt": new Date().toISOString(),
    "locationsActive": locations.length,
    "rotationEnabled": ROTATION_ENABLED,
    "totalObjects": finalObjects.length
  }
};

fs.writeFileSync(OUTPUT_FILE, JSON.stringify(outputData, null, 4));
console.log(`[SUCCESS] Generated mission with ${finalObjects.length} objects.`);
console.log(`[OUTPUT] Saved to ${OUTPUT_FILE}`);
