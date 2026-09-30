import fs from 'fs/promises';
import path from 'path';
import { PatchManager } from './patch-manager';

// Resolve patch path relative to the project root
// Assuming process.cwd() is the dashboard directory or repo root
const REPO_ROOT = path.resolve(process.cwd(), '..');
const WORKSPACE_ROOT = process.env.DAYZ_WORKSPACE || path.join(REPO_ROOT, 'server/ezstreet');
const PATCH_FILES = [
  'EZADMIN Base (Hobo).json',
  'EZStreet bm Trader.json',
  'LockedContainers_Spawns.json'
];

// Helper for robust file reading with retries
async function robustReadFile(filePath: string, retries = 3, delay = 500): Promise<string> {
  for (let i = 0; i < retries; i++) {
    try {
      await fs.access(filePath);
      return await fs.readFile(filePath, 'utf-8');
    } catch (e: any) {
      if (i === retries - 1) throw e; // Fail on last attempt
      // If file doesn't exist or is locked, wait and retry
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  throw new Error(`Failed to read ${filePath} after retries`);
}

export async function loadServerPatches() {
  const manager = PatchManager.getInstance();
  const logs: string[] = [];

  logs.push(`[PatchLoader] Starting patch load from: ${WORKSPACE_ROOT}`);

  for (const filename of PATCH_FILES) {
    try {
      const filePath = path.resolve(WORKSPACE_ROOT, filename);
      logs.push(`[PatchLoader] Attempting to load: ${filePath}`);

      // Use robust read
      let fileContent: string;
      try {
        fileContent = await robustReadFile(filePath);
        logs.push(`[PatchLoader] ✓ Read file: ${filePath}`);
      } catch (readErr: any) {
        logs.push(`[PatchLoader] ✗ File not accessible or readable: ${filePath} (${readErr.message})`);
        throw readErr;
      }

      let jsonContent;
      try {
        jsonContent = JSON.parse(fileContent);
      } catch (parseErr: any) {
        logs.push(`[PatchLoader] ✗ JSON Parse Error for ${filename}: ${parseErr.message}`);
        throw new Error(`Invalid JSON in ${filename}`);
      }

      const keys = Object.keys(jsonContent);
      logs.push(`[PatchLoader] Keys found: ${keys.join(', ')}`);

      // The JSON structure usually has top-level keys like "Objects"
      const data = jsonContent.Objects || [];

      if (data.length === 0) {
        logs.push(`[PatchLoader] WARNING: ${filename} has 0 objects`);
      }

      manager.registerPatch(filename, data);
      logs.push(`[PatchLoader] ✓ Registered ${filename} with ${data.length} items`);
    } catch (error: any) {
      logs.push(`[PatchLoader] ✗ FAILED to load ${filename}: ${error.message}`);
      console.error(`[PatchLoader] Error details for ${filename}:`, error);
    }
  }

  const containerCount = manager.getAllContainers().length;
  logs.push(`[PatchLoader] === TOTAL CONTAINERS FOUND: ${containerCount} ===`);

  return { manager, logs };
}

