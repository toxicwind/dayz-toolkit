import { PageContainer } from '@/components/layout/page-container';
import { StatsAreaChart } from '@/components/stats-area-chart';
import { GlassCard } from '@/components/ui/glass-card';

async function getStats() {
    // Use the internal API or DB directly if SSR
    // For now, let's assume we fetch from our new API route
    // In production, we'd use lib/db directly to save a hop
    const res = await fetch(`${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/api/stats`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
}

export default async function OverviewPage() {
    const stats = await getStats();

    return (
        <PageContainer scrollable={true}>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-3xl font-bold tracking-tight text-white">Ops Dashboard</h2>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    <GlassCard className="p-4" opacity={15}>
                        <div className="text-sm font-medium text-blue-300">Live Status</div>
                        <div className="text-2xl font-bold text-white">ONLINE</div>
                        <p className="text-xs text-neutral-400">A2S Query Responsive</p>
                    </GlassCard>
                </div>

                <div className="grid gap-4 grid-cols-1">
                    <StatsAreaChart data={stats} />
                </div>
            </div>
        </PageContainer>
    );
}
