import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Configuring the runtime to nodejs
export const runtime = 'nodejs';

const WORKSPACE_PATH = '/home/toxic/dayz_workspace/dayzxb_missions/dayzOffline.chernarusplus';

// Allowlist of editable JSON files to prevent arbitrary file access
const ALLOWED_FILES = [
    'cfggameplay.json',
    'custom/EZStreet_bm_Trader.json',
    'custom/EZStreet_Loadout_Fresh.json',
    'custom/safe_zones.json',
    'custom/LockedContainers_Spawns.json'
];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const file = searchParams.get('file');

  if (file) {
    if (!ALLOWED_FILES.includes(file)) {
        return NextResponse.json({ error: 'File not allowed' }, { status: 403 });
    }

    try {
      const filePath = path.join(WORKSPACE_PATH, file);
      
      if (!fs.existsSync(filePath)) {
          return NextResponse.json({ error: 'File not found' }, { status: 404 });
      }

      const content = fs.readFileSync(filePath, 'utf-8');
      return NextResponse.json({ content: JSON.parse(content) });
    } catch (error) {
      return NextResponse.json({ error: 'Failed to read file' }, { status: 500 });
    }
  }

  return NextResponse.json(ALLOWED_FILES);
}

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { file, content } = body;

        if (!file || !content) {
            return NextResponse.json({ error: 'Missing file or content' }, { status: 400 });
        }

        if (!ALLOWED_FILES.includes(file)) {
            return NextResponse.json({ error: 'File not allowed' }, { status: 403 });
        }

        const filePath = path.join(WORKSPACE_PATH, file);
        // Pretty print JSON with 4 spaces for readability
        const jsonContent = JSON.stringify(content, null, 4);
        
        fs.writeFileSync(filePath, jsonContent, 'utf-8');
        return NextResponse.json({ success: true });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to save file' }, { status: 500 });
    }
}
