import { NextResponse } from 'next/server';

export async function GET() {
    const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';
    try {
        const res = await fetch(`${BACKEND_URL}/killfeed`, { cache: 'no-store' });
        if (!res.ok) return NextResponse.json({ kills: [] });
        const data = await res.json();
        return NextResponse.json(data);
    } catch (e) {
        return NextResponse.json({ kills: [] });
    }
}
