/**
 * DayZ Configuration Source Scanner
 * Recursively scans directories and builds a reference map
 * 
 * Usage: node scan_sources.js
 */

const fs = require('fs');
const path = require('path');

// Configuration
const MANIFEST_PATH = '/home/toxic/dayz_workspace/VERSION_MANIFEST.json';
const OUTPUT_PATH = '/home/toxic/dayz_workspace/SOURCE_INDEX.json';

// Scan patterns
const CONFIG_EXTENSIONS = ['.xml', '.json', '.c'];
const IGNORE_PATTERNS = ['node_modules', '.git', 'backups'];

/**
 * Recursively scan a directory for config files
 */
function scanDirectory(dirPath, basePath = dirPath) {
  const results = [];

  try {
    const items = fs.readdirSync(dirPath);

    for (const item of items) {
      const fullPath = path.join(dirPath, item);
      const relativePath = path.relative(basePath, fullPath);

      // Skip ignored patterns
      if (IGNORE_PATTERNS.some(pattern => item.includes(pattern))) {
        continue;
      }

      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        // Recurse into subdirectory
        results.push(...scanDirectory(fullPath, basePath));
      } else if (stat.isFile()) {
        const ext = path.extname(item).toLowerCase();
        if (CONFIG_EXTENSIONS.includes(ext)) {
          results.push({
            name: item,
            path: fullPath,
            relativePath: relativePath,
            extension: ext,
            size: stat.size,
            modified: stat.mtime.toISOString()
          });
        }
      }
    }
  } catch (err) {
    console.error(`[WARN] Cannot scan ${dirPath}: ${err.message}`);
  }

  return results;
}

/**
 * Generate file hash for change detection
 */
function getFileSignature(filePath) {
  try {
    const content = fs.readFileSync(filePath);
    // Simple hash: first 100 chars + size
    const preview = content.toString('utf8', 0, 100).replace(/\s+/g, ' ');
    return {
      size: content.length,
      preview: preview.substring(0, 50) + '...'
    };
  } catch (err) {
    return { error: err.message };
  }
}

/**
 * Build complete source index
 */
function buildSourceIndex() {
  console.log('[INFO] Building source index...');

  const manifest = JSON.parse(fs.readFileSync(MANIFEST_PATH, 'utf8'));
  const index = {
    generatedAt: new Date().toISOString(),
    sources: {}
  };

  // Scan each source
  for (const [key, source] of Object.entries(manifest.sources)) {
    if (!source.path || !fs.existsSync(source.path)) {
      console.log(`[SKIP] ${key}: path not found`);
      continue;
    }

    console.log(`[SCAN] ${key}: ${source.path}`);
    const files = scanDirectory(source.path);

    index.sources[key] = {
      description: source.description,
      branch: source.branch || 'unknown',
      origin: source.origin || 'unknown',
      fileCount: files.length,
      files: files.map(f => ({
        name: f.name,
        relativePath: f.relativePath,
        size: f.size,
        modified: f.modified
      }))
    };
  }

  // Write index
  fs.writeFileSync(OUTPUT_PATH, JSON.stringify(index, null, 2));
  console.log(`[SUCCESS] Index saved to ${OUTPUT_PATH}`);
  console.log(`[STATS] Total sources: ${Object.keys(index.sources).length}`);

  return index;
}

// Run if called directly
if (require.main === module) {
  buildSourceIndex();
}

module.exports = { scanDirectory, buildSourceIndex };
