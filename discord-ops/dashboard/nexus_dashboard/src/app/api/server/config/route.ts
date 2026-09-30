
import { NextResponse } from 'next/server';

export async function GET() {
    return NextResponse.json({
        server_name: 'DayZ Ops Local',
        status: 'online',
        map: 'Chernarus'
    });
}
