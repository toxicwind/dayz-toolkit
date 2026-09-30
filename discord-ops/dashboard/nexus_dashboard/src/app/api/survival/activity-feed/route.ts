import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';
    
    const response = await fetch(`${BACKEND_URL}/survival/activity-feed?limit=${limit}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!response.ok) {
      return NextResponse.json({ activities: [], total: 0 }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Neural Feed Error:', error);
    return NextResponse.json({ activities: [], total: 0, error: 'Failed to fetch neural feed' }, { status: 500 });
  }
}
