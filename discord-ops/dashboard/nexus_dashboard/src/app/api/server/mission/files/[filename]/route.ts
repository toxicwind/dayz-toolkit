import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BOT_API_URL || 'http://bot:43200';

export async function GET(
    request: Request,
    { params }: { params: Promise<{ filename: string }> }
) {
    const { filename } = await params;
    try {
        const res = await fetch(`${BOT_API_URL}/mission/files/${filename}`, {
            cache: 'no-store',
        });
        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ error: `Failed to fetch mission file ${filename}` }, { status: 500 });
    }
}

export async function POST(
    request: Request,
    { params }: { params: Promise<{ filename: string }> }
) {
    const { filename } = await params;
    try {
        const body = await request.json();
        const res = await fetch(`${BOT_API_URL}/mission/files/${filename}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        return NextResponse.json({ error: `Failed to update mission file ${filename}` }, { status: 500 });
    }
}
