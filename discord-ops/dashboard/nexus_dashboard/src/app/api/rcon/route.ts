import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json({ error: 'RCON disabled for console build' }, { status: 404 });
}
