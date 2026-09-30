import { NextResponse } from 'next/server';
import { dbRequest } from '@/lib/db';

export async function GET() {
    try {
        const stats = await dbRequest(
            'SELECT * FROM player_stats ORDER BY timestamp DESC LIMIT 288' // Approx 24 hours at 5m intervals
        );
        return NextResponse.json(stats);
    } catch (error) {
        console.error('Database Error:', error);
        return NextResponse.json({ error: 'Failed to fetch stats' }, { status: 500 });
    }
}
