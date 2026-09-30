import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const { gamertag } = await req.json();

        if (!gamertag) {
            return NextResponse.json({ error: 'Gamertag required' }, { status: 400 });
        }

        // Proxy to the bot's internal API
        const botResponse = await fetch(`http://bot:43200/server/ban`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ gamertag }),
        });

        if (!botResponse.ok) {
            const errorText = await botResponse.text();
            return NextResponse.json(
                { error: `Bot API Error: ${botResponse.statusText}`, details: errorText },
                { status: botResponse.status }
            );
        }

        const data = await botResponse.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Ban Action Error:', error);
        return NextResponse.json(
            { error: 'Internal Server Error', details: error instanceof Error ? error.message : String(error) },
            { status: 500 }
        );
    }
}
