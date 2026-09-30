import { NextResponse } from 'next/server';

export async function POST(req: Request) {
    try {
        const { action } = await req.json();

        if (!['restart', 'stop'].includes(action)) {
            return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
        }

        // Proxy to the bot's internal API
        const botResponse = await fetch(`http://bot:43200/server/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
        console.error('Server Action Error:', error);
        return NextResponse.json(
            { error: 'Internal Server Error', details: error instanceof Error ? error.message : String(error) },
            { status: 500 }
        );
    }
}
