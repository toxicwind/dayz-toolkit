import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// Configuring the runtime to nodejs
export const runtime = 'nodejs';

const DB_PATH = '/home/toxic/dayz_workspace/dayzxb_missions/dayzOffline.chernarusplus/db';
const CUSTOM_PATH = '/home/toxic/dayz_workspace/dayzxb_missions/dayzOffline.chernarusplus/custom';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const file = searchParams.get('file');

  if (file) {
    // Read content of a specific file
    try {
      // Determine base path based on folder prefix or defaults
      let filePath = '';
      if (file.startsWith('custom/')) {
         filePath = path.join(CUSTOM_PATH, path.basename(file));
      } else {
         filePath = path.join(DB_PATH, path.basename(file));
      }
      
      if (!fs.existsSync(filePath)) {
          return NextResponse.json({ error: 'File not found' }, { status: 404 });
      }

      const content = fs.readFileSync(filePath, 'utf-8');
      return NextResponse.json({ content });
    } catch (error) {
      return NextResponse.json({ error: 'Failed to read file' }, { status: 500 });
    }
  }

  // List XML files
  try {
    const dbFiles = fs.readdirSync(DB_PATH).filter(f => f.endsWith('.xml'));
    const customFiles = fs.readdirSync(CUSTOM_PATH).filter(f => f.endsWith('.xml'));
    
    // Add prefix to custom files for identification
    const allFiles = [
        ...dbFiles,
        ...customFiles.map(f => `custom/${f}`)
    ];

    return NextResponse.json(allFiles);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to list files' }, { status: 500 });
  }
}

export async function POST(request: Request) {
    try {
        const body = await request.json();
        const { file, content } = body;

        if (!file || !content) {
            return NextResponse.json({ error: 'Missing file or content' }, { status: 400 });
        }

        let filePath = '';
        if (file.startsWith('custom/')) {
            filePath = path.join(CUSTOM_PATH, path.basename(file));
        } else {
            filePath = path.join(DB_PATH, path.basename(file));
        }

        fs.writeFileSync(filePath, content, 'utf-8');
        return NextResponse.json({ success: true });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to save file' }, { status: 500 });
    }
}
