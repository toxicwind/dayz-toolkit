import { NextResponse } from 'next/server';
import { dbRequest } from '@/lib/db';

export async function GET() {
    try {
        const logs = await dbRequest(
            'SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 50'
        );
        return NextResponse.json(logs);
    } catch (error) {
        console.error('Database Error:', error);
        return NextResponse.json({ error: 'Failed to fetch activity logs' }, { status: 500 });
    }
}
