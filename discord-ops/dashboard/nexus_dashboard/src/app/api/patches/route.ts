import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import util from 'util';

// Configuring the runtime to nodejs
export const runtime = 'nodejs';

const execPromise = util.promisify(exec);
const PATCHES_DIR = process.env.PATCHES_DIR || '/app/patcher/patches';
const MANIFEST_PATH = path.join(PATCHES_DIR, 'manifest.json');

export async function GET() {
    try {
        if (!fs.existsSync(MANIFEST_PATH)) {
            return NextResponse.json([], { status: 200 });
        }

        const content = fs.readFileSync(MANIFEST_PATH, 'utf-8');
        const manifestData = JSON.parse(content);
        const patchesList = manifestData.patches || [];

        // Also scan for available patch files to ensure manifest integrity
        const files = fs.readdirSync(PATCHES_DIR).filter(f => f.endsWith('.json') && f !== 'manifest.json');

        const patches = patchesList.map((patch: any) => {
            // Find if file exists
            const fileExists = files.includes(path.basename(patch.file));
            return { ...patch, id: patch.file.replace('.json', ''), fileExists };
        });

        return NextResponse.json({
            patches,
            categories: manifestData.categories || {},
            meta: manifestData.meta || {}
        });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to load patches' }, { status: 500 });
    }
}

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { id, file, enabled } = body;

        if ((!id && !file) || typeof enabled !== 'boolean') {
            return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
        }

        const targetFile = file || `${id}.json`;

        if (!fs.existsSync(MANIFEST_PATH)) {
            return NextResponse.json({ error: 'Manifest not found' }, { status: 404 });
        }

        const content = fs.readFileSync(MANIFEST_PATH, 'utf-8');
        const manifestData = JSON.parse(content);

        manifestData.patches = manifestData.patches.map((patch: any) => {
            if (patch.file === targetFile) {
                return { ...patch, enabled };
            }
            return patch;
        });

        fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifestData, null, 4), 'utf-8');

        return NextResponse.json({ success: true, manifest: manifestData });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to update patch' }, { status: 500 });
    }
}
