import { NextResponse } from 'next/server';

const BOT_API_URL = process.env.BOT_API_URL || 'http://bot:43200';

export async function GET() {
  try {
    const res = await fetch(`${BOT_API_URL}/mission/files`, {
      cache: 'no-store',
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch mission files' }, { status: 500 });
  }
}
