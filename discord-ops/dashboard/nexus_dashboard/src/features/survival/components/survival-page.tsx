'use client';

import { PageContainer } from '@/components/layout/page-container';
import { SurvivorProfiles } from './survivor-profiles';
import { ActivityDetailed } from './activity-detailed';
import { GlassCard } from '@/components/ui/glass-card';
import { Activity, Users, Zap, Shield, Skull } from 'lucide-react';
import { cn } from '@/lib/utils';
import * as React from 'react';

export function SurvivalView() {
    const [metrics, setMetrics] = React.useState<any>(null);

    React.useEffect(() => {
        const fetchMetrics = async () => {
            try {
                const res = await fetch('/api/survival/metrics');
                const data = await res.json();
                setMetrics(data);
            } catch (error) {
                console.error('Failed to fetch metrics:', error);
            }
        };
        fetchMetrics();
    }, []);

    return (
        <PageContainer scrollable={true}>
            <div className="space-y-8 pb-12">
                <div className="flex flex-col gap-2">
                    <h2 className="text-4xl font-black tracking-tighter text-foreground uppercase italic flex items-center gap-4">
                        Survival Intelligence <span className="text-red-600">Hub</span>
                    </h2>
                    <p className="text-muted-foreground text-sm font-mono uppercase tracking-widest bg-white/5 px-2 py-1 rounded inline-block w-fit">
                        Biometric Analysis & In-depth Surveillance Center
                    </p>
                </div>

                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    <GlassCard className="p-6" opacity={20}>
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-red-500/10 rounded-lg">
                                <Users className="w-5 h-5 text-red-400" />
                            </div>
                            <div>
                                <div className="text-[10px] uppercase font-bold text-muted-foreground">Known Survivors</div>
                                <div className="text-3xl font-black">{metrics?.total_survivors || '--'}</div>
                            </div>
                        </div>
                    </GlassCard>

                    <GlassCard className="p-6" opacity={15}>
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-emerald-500/10 rounded-lg">
                                <Zap className="w-5 h-5 text-emerald-400" />
                            </div>
                            <div>
                                <div className="text-[10px] uppercase font-bold text-muted-foreground">Active Missions</div>
                                <div className="text-3xl font-black">{metrics?.active_now || '--'}</div>
                            </div>
                        </div>
                    </GlassCard>

                    <GlassCard className="p-6" opacity={15}>
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-blue-500/10 rounded-lg">
                                <Shield className="w-5 h-5 text-blue-400" />
                            </div>
                            <div>
                                <div className="text-[10px] uppercase font-bold text-muted-foreground">Avg. Survival</div>
                                <div className="text-3xl font-black">{metrics?.avg_survival_time || '--'}<span className="text-xs font-normal ml-1">h</span></div>
                            </div>
                        </div>
                    </GlassCard>

                    <GlassCard className="p-6" opacity={15}>
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-purple-500/10 rounded-lg">
                                <Skull className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <div className="text-[10px] uppercase font-bold text-muted-foreground">Fatalities (24h)</div>
                                <div className="text-3xl font-black text-red-500">{metrics?.total_deaths_24h || '--'}</div>
                            </div>
                        </div>
                    </GlassCard>
                </div>

                <div className="grid gap-8 lg:grid-cols-5 min-h-[600px]">
                    <div className="lg:col-span-2">
                        <SurvivorProfiles />
                    </div>
                    <div className="lg:col-span-3">
                        <ActivityDetailed />
                    </div>
                </div>

                <div className="grid gap-8 lg:grid-cols-2">
                    <GlassCard className="p-6" opacity={10}>
                        <h3 className="text-xl font-black uppercase tracking-tighter mb-6">Hotspot Analysis</h3>
                        <div className="space-y-4">
                            {metrics?.hotspot_zones?.map((z: any) => (
                                <div key={z.zone} className="flex items-center gap-4">
                                    <div className="text-xs font-mono w-20">{z.zone}</div>
                                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]"
                                            style={{ width: `${Math.min(z.activity, 100)}%` }}
                                        />
                                    </div>
                                    <div className="text-xs font-bold text-red-400">{z.activity}%</div>
                                </div>
                            ))}
                        </div>
                    </GlassCard>
                    <GlassCard className="p-6 flex flex-col items-center justify-center text-center" opacity={10}>
                        <div className="mb-4 p-4 bg-white/5 rounded-full border border-white/10">
                            <Activity className={cn(
                                "w-12 h-12",
                                metrics?.threat_level === 'critical' ? "text-red-500 animate-pulse" : "text-emerald-500"
                            )} />
                        </div>
                        <h3 className="text-2xl font-black uppercase tracking-tighter">System Pulse</h3>
                        <div className={cn(
                            "text-4xl font-black uppercase mt-2",
                            metrics?.threat_level === 'critical' ? "text-red-600" : "text-emerald-400"
                        )}>
                            {metrics?.threat_level?.toUpperCase() || 'CALIBRATING'}
                        </div>
                        <p className="text-xs text-muted-foreground mt-2 max-w-sm">
                            Overall server volatility and threat assessment based on real-time activity signatures.
                        </p>
                    </GlassCard>
                </div>
            </div>
        </PageContainer>
    );
}
export default SurvivalView;

export { SurvivalView };
