import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BOT_API_URL || 'http://bot:43200';

export async function GET() {
  try {
    const res = await fetch(`${BOT_API_URL}/config/gas-zones`, { 
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' }
    });

    if (!res.ok) {
        return NextResponse.json({ status: 'error', message: `Backend error: ${res.status}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching gas zones:', error);
    return NextResponse.json({ status: 'error', message: 'Failed to fetch gas zones' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${BOT_API_URL}/config/gas-zones`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
        return NextResponse.json({ status: 'error', message: `Backend error: ${res.status}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating gas zones:', error);
    return NextResponse.json({ status: 'error', message: 'Failed to update gas zones' }, { status: 500 });
  }
}
