/**
 * DayZ Multi-Format Patch Applicator (JSON & XML)
 * Consolidated version handling cfggameplay.json and various XML database files.
 */
const fs = require('fs');
const path = require('path');
const { DOMParser, XMLSerializer } = require('xmldom');
const xpath = require('xpath');

// --- Configuration ---
// Cleaned up MISSION_DIR to point directly to your vanilla path
const WORKSPACE = process.env.DAYZ_WORKSPACE || '/home/toxic/dayz_workspace/dayz_discord_ops_repo';
let PATCHES_DIR = path.join(WORKSPACE, 'patcher/patches');
if (!fs.existsSync(PATCHES_DIR)) {
  PATCHES_DIR = path.join(WORKSPACE, 'patches'); // legacy fallback
}
const MANIFEST_FILE = path.join(PATCHES_DIR, 'manifest.json');
const MISSION_DIR = '/home/toxic/dayz_workspace/dayz_discord_ops_repo/data/dayz_vanilla/official_repo/dayzOffline.chernarusplus';
const DRY_RUN = process.argv.includes('--dry-run');

// --- Utilities ---

function deepMerge(target, source) {
  for (const key of Object.keys(source)) {
    if (source[key] instanceof Object && key in target) {
      deepMerge(target[key], source[key]);
    } else {
      target[key] = source[key];
    }
  }
  return target;
}

/**
 * Logic for JSON (cfggameplay.json)
 */
function applyGameplayPatch(patch, filename) {
  if (!patch.path) {
    console.error(`[ERROR] JSON patch ${filename} is missing "path".`);
    return false;
  }

  const targetFile = path.join(MISSION_DIR, 'cfggameplay.json');
  if (!fs.existsSync(targetFile)) return false;

  const config = JSON.parse(fs.readFileSync(targetFile, 'utf8'));
  const pathParts = patch.path.split('.');
  let target = config;

  for (let i = 0; i < pathParts.length - 1; i++) {
    if (!target[pathParts[i]]) target[pathParts[i]] = {};
    target = target[pathParts[i]];
  }

  const lastKey = pathParts[pathParts.length - 1];
  if (!target[lastKey]) target[lastKey] = {};
  
  deepMerge(target[lastKey], patch.values);

  if (!DRY_RUN) {
    fs.writeFileSync(targetFile, JSON.stringify(config, null, 2));
  }
  return true;
}

/**
 * Logic for XML (types, events, globals, spawnabletypes, weather)
 */
function applyXmlPatch(patch, patchFilePath) {
  const targetFile = path.join(MISSION_DIR, patch.target);
  
  if (!fs.existsSync(targetFile)) {
    console.log(`[DEBUG] Cannot find target file: ${targetFile}`);
    return false;
  }

  const xmlRaw = fs.readFileSync(targetFile, 'utf8');
  const doc = new DOMParser().parseFromString(xmlRaw, 'text/xml');
  let modified = false;

  // Unified task list for both simple and complex XML patches
  const tasks = patch.complex_patches || (patch.xpath ? [{ xpath: patch.xpath, values: patch.values }] : []);

  // Handle XPath Attribute Updates
  tasks.forEach(task => {
    const nodes = xpath.select(task.xpath, doc);
    nodes.forEach(node => {
      for (let [attr, val] of Object.entries(task.values)) {
        if (attr.includes('_multiplier')) {
          const baseAttr = attr.replace('_multiplier', '');
          const current = parseFloat(node.getAttribute(baseAttr));
          node.setAttribute(baseAttr, (current * val).toString());
        } else {
          node.setAttribute(attr, val.toString());
        }
        modified = true;
      }
    });
  });

  // Handle Item Lists with Multipliers (Vehicle counts in types.xml)
  if (patch.items && patch.values) {
    patch.items.forEach(itemName => {
      const node = xpath.select(`//type[@name='${itemName}']`, doc)[0];
      if (node) {
        for (let [key, multiplier] of Object.entries(patch.values)) {
          const tagName = key.replace('_multiplier', '');
          const element = node.getElementsByTagName(tagName)[0];
          if (element && element.firstChild) {
            const newVal = Math.round(parseFloat(element.firstChild.nodeValue) * multiplier);
            element.firstChild.nodeValue = newVal.toString();
            modified = true;
          }
        }
      }
    });
  }

  // Handle Raw XML block injection (Vehicles equipped)
  const dataFile = patchFilePath.replace('.json', '_data.xml');
  if (fs.existsSync(dataFile)) {
    const dataDoc = new DOMParser().parseFromString(fs.readFileSync(dataFile, 'utf8'), 'text/xml');
    const newTypes = dataDoc.getElementsByTagName('type');
    for (let i = 0; i < newTypes.length; i++) {
      const typeName = newTypes[i].getAttribute('name');
      const existing = xpath.select(`//type[@name='${typeName}']`, doc)[0];
      if (existing) {
        doc.documentElement.replaceChild(newTypes[i], existing);
      } else {
        doc.documentElement.appendChild(newTypes[i]);
      }
      modified = true;
    }
  }

  if (modified && !DRY_RUN) {
    const serializer = new XMLSerializer();
    fs.writeFileSync(targetFile, serializer.serializeToString(doc));
  }
  return modified;
}

// --- Main Execution ---

console.log('=== DayZ Unified Patch Applicator ===');
console.log(`Mission: ${MISSION_DIR}`);
console.log(`Mode:    ${DRY_RUN ? 'DRY RUN' : 'APPLY'}`);
console.log('---');

const manifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf8'));
let applied = 0;
let skipped = 0;

for (const entry of manifest.patches) {
  if (!entry.enabled) {
    console.log(`[DISABLED] ${entry.file}`);
    skipped++;
    continue;
  }

  const patchFilePath = path.join(PATCHES_DIR, entry.file);
  if (!fs.existsSync(patchFilePath)) {
    console.log(`[MISSING]  ${entry.file}`);
    skipped++;
    continue;
  }

  const patch = JSON.parse(fs.readFileSync(patchFilePath, 'utf8'));

  try {
    let success = false;
    if (patch.type === 'xml_patch' || patch.target.endsWith('.xml')) {
      success = applyXmlPatch(patch, patchFilePath);
    } else {
      success = applyGameplayPatch(patch, entry.file);
    }

    if (success) {
      console.log(`[OK]       ${entry.file}`);
      applied++;
    } else {
      console.log(`[SKIP]     ${entry.file}`);
      skipped++;
    }
  } catch (err) {
    console.error(`[FAIL]     ${entry.file}: ${err.message}`);
    skipped++;
  }
}

console.log('---');
console.log(`Results: ${applied} applied, ${skipped} skipped.`);
