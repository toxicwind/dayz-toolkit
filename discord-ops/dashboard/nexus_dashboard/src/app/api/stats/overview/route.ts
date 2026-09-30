import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET() {
    try {
        const res = await fetch(`${BOT_API_URL}/stats/overview`, {
            cache: 'no-store',
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
        console.error('Failed to fetch stats overview:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
