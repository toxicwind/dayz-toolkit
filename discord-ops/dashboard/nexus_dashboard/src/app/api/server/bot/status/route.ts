import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/bot/status`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!response.ok) {
      return NextResponse.json({ 
        status: 'offline',
        name: 'DayZ Ops Command',
        latency: 'N/A',
        guild: 'Unknown',
        guild_id: 'N/A'
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Bot Status Error:', error);
    return NextResponse.json({ 
      status: 'offline',
      name: 'DayZ Ops Command',
      latency: 'N/A',
      guild: 'Unknown',
      guild_id: 'N/A'
    });
  }
}
