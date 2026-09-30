import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/survival/profiles`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!response.ok) {
      return NextResponse.json({ profiles: [], total: 0 }, { status: response.status });
    }

    return NextResponse.json(await response.json());
  } catch (error) {
    console.error('Profiles Error:', error);
    return NextResponse.json({ profiles: [], total: 0, error: 'Failed' }, { status: 500 });
  }
}
