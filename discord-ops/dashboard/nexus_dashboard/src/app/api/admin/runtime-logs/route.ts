import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execPromise = promisify(exec);

export async function GET() {
    try {
        // Attempt to get the last 50 lines of logs from the dashboard's stdout/stderr
        // Note: In Next.js dev mode, this is tricky as it's the parent process.
        // We will try to read the bot logs as a fallback since they are shared.
        const { stdout } = await execPromise('tail -n 50 /app/logs/bot.log || echo "No logs available"');

        return NextResponse.json({
            timestamp: new Date().toISOString(),
            logs: stdout.split('\n'),
            status: 'operational'
        });
    } catch (error) {
        return NextResponse.json({
            error: 'Failed to retrieve runtime logs',
            details: error instanceof Error ? error.message : String(error)
        }, { status: 500 });
    }
}
