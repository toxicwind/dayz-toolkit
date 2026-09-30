import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BOT_API_URL || 'http://bot:43200';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';

    try {
        const res = await fetch(`${BOT_API_URL}/survival/neural-feed?limit=${limit}`, {
            cache: 'no-store',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        if (!res.ok) {
            return NextResponse.json(
                { error: `Bot API error: ${res.statusText}` },
                { status: res.status }
            );
        }

        const data = await res.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Failed to fetch neural feed:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
