import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const body = await req.json();

        const res = await fetch('http://bot:43200/intelligence/alias', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            throw new Error('Bot API error');
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Alias Proxy Error:', error);
        return NextResponse.json({ error: 'Failed to set alias' }, { status: 500 });
    }
}
