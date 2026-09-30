import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BOT_API_URL || 'http://bot:43200';

export async function GET() {
  try {
    const res = await fetch(`${BOT_API_URL}/config/globals`, { 
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!res.ok) {
        return NextResponse.json({ status: 'error', message: `Backend error: ${res.status}` }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching global config:', error);
    return NextResponse.json({ status: 'error', message: 'Failed to fetch global config' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${BOT_API_URL}/config/globals`, {
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
    console.error('Error updating global config:', error);
    return NextResponse.json({ status: 'error', message: 'Failed to update global config' }, { status: 500 });
  }
}
