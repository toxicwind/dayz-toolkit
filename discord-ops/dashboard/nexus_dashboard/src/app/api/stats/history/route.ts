import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const botResponse = await fetch(`http://bot:43200/stats/history`, {
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
    console.error('Stats History Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
