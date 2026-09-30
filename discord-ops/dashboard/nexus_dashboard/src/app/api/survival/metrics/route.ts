import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/survival/metrics`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!response.ok) {
      return NextResponse.json({ 
        total_survivors: 0,
        active_now: 0,
        avg_survival_time: 0,
        total_deaths_24h: 0,
        hotspot_zones: [],
        threat_level: 'calm'
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Survival Metrics Error:', error);
    return NextResponse.json({ 
      total_survivors: 0,
      active_now: 0,
      avg_survival_time: 0,
      total_deaths_24h: 0,
      hotspot_zones: [],
      threat_level: 'calm',
      error: 'Failed to fetch metrics'
    }, { status: 500 });
  }
}
