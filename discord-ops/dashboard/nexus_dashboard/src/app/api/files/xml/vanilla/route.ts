import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const runtime = 'nodejs';

const VANILLA_BASE = process.env.VANILLA_BASE || '/app/data/dayz_vanilla/official_repo';
const VANILLA_MISSION = 'dayzOffline.chernarusplus';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const file = searchParams.get('file');

    if (!file) {
        return NextResponse.json({ error: 'File parameter required' }, { status: 400 });
    }

    try {
        // Remove 'custom/' prefix if present
        const cleanFile = file.replace('custom/', '');
        const vanillaPath = path.join(VANILLA_BASE, VANILLA_MISSION, cleanFile);

        if (!fs.existsSync(vanillaPath)) {
            return NextResponse.json({ error: 'Vanilla file not found', available: false }, { status: 404 });
        }

        const content = fs.readFileSync(vanillaPath, 'utf-8');
        return NextResponse.json({ content, available: true });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to read vanilla file', available: false }, { status: 500 });
    }
}
