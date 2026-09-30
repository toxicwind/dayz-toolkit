import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const window = searchParams.get('window') || '24';
    
    try {
        const res = await fetch(`${BOT_API_URL}/stats/trends?window_hours=${window}`, {
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
        console.error('Failed to fetch stats trends:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}
