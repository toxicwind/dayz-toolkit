import { NextResponse } from 'next/server';

export async function GET(req: Request) {
    try {
        const { searchParams } = new URL(req.url);
        const scan = searchParams.get('scan') === 'true';

        const res = await fetch(`http://bot:43200/intelligence/players?scan=${scan}`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            cache: 'no-store'
        });

        if (!res.ok) {
            throw new Error('Bot API error');
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Intelligence Proxy Error:', error);
        return NextResponse.json({ error: 'Failed to fetch player intelligence' }, { status: 500 });
    }
}
