import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const botResponse = await fetch(`http://bot:43200/players`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!botResponse.ok) {
      return NextResponse.json({ error: `Bot API Error: ${botResponse.statusText}` }, { status: botResponse.status });
    }

    const data = await botResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Players Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const { action, gamertag } = await req.json();

    if (!action || !gamertag) {
      return NextResponse.json({ error: 'Action and gamertag required' }, { status: 400 });
    }

    const endpoint = action === 'kick' ? '/players/kick' : '/server/ban';
    const botResponse = await fetch(`http://bot:43200${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gamertag }),
    });

    if (!botResponse.ok) {
      return NextResponse.json({ error: `Bot API Error: ${botResponse.statusText}` }, { status: botResponse.status });
    }

    const data = await botResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Player Action Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
