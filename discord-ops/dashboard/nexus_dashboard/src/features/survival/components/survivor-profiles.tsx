'use client';

import * as React from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { User, Shield, Zap, Skull, Activity, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Profile {
    steam_id: string;
    player_name: string;
    total_playtime: number;
    survival_score: number;
    kills: number;
    deaths: number;
    kd_ratio: number;
    favorite_weapon: string;
    activity_pattern: string;
    threat_level: string;
    status: string;
}

export function SurvivorProfiles() {
    const [profiles, setProfiles] = React.useState<Profile[]>([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchProfiles = async () => {
            try {
                const res = await fetch('/api/survival/profiles');
                const data = await res.json();
                if (data.profiles) {
                    setProfiles(data.profiles);
                }
            } catch (error) {
                console.error('Failed to fetch profiles:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchProfiles();
    }, []);

    const getPatternIcon = (pattern: string) => {
        switch (pattern.toLowerCase()) {
            case 'aggressive': return <Zap className="w-4 h-4 text-orange-400" />;
            case 'explorer': return <Activity className="w-4 h-4 text-emerald-400" />;
            case 'builder': return <Shield className="w-4 h-4 text-blue-400" />;
            default: return <User className="w-4 h-4 text-muted-foreground" />;
        }
    };

    const getThreatColor = (level: string) => {
        switch (level.toLowerCase()) {
            case 'extreme': return 'bg-red-500/20 text-red-400 border-red-500/50';
            case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
            case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
            default: return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
        }
    };

    return (
        <GlassCard className="p-6 h-full flex flex-col" opacity={10}>
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <Target className="w-5 h-5 text-red-500" />
                    <h3 className="text-xl font-black uppercase tracking-tighter">Survivor Intelligence</h3>
                </div>
                <Badge variant="outline" className="border-red-500/30 text-red-500 animate-pulse">
                    LIVE INTEL
                </Badge>
            </div>

            <ScrollArea className="flex-1 pr-4">
                <div className="space-y-4">
                    {loading ? (
                        <div className="py-12 text-center text-muted-foreground animate-pulse">Syncing telemetry profiles...</div>
                    ) : profiles.map((p) => (
                        <div key={p.steam_id} className="p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-all group overflow-hidden relative">
                            {/* Threat Indicator Bar */}
                            <div className={cn(
                                "absolute left-0 top-0 bottom-0 w-1",
                                p.threat_level === 'extreme' ? "bg-red-500" :
                                    p.threat_level === 'high' ? "bg-orange-500" : "bg-emerald-500"
                            )} />

                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-white/5 rounded-lg group-hover:scale-110 transition-transform">
                                        {getPatternIcon(p.activity_pattern)}
                                    </div>
                                    <div>
                                        <div className="font-bold text-foreground flex items-center gap-2">
                                            {p.player_name}
                                            {p.status === 'online' && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]" />}
                                        </div>
                                        <div className="text-[10px] font-mono text-muted-foreground uppercase">{p.steam_id}</div>
                                    </div>
                                </div>
                                <Badge className={cn("text-[10px] uppercase font-bold", getThreatColor(p.threat_level))}>
                                    {p.threat_level} Threat
                                </Badge>
                            </div>

                            <div className="grid grid-cols-3 gap-4 mt-4">
                                <div className="bg-black/20 p-2 rounded-lg border border-white/5">
                                    <div className="text-[10px] text-muted-foreground uppercase mb-1">Survival Score</div>
                                    <div className="text-lg font-black text-orange-400">{p.survival_score}</div>
                                </div>
                                <div className="bg-black/20 p-2 rounded-lg border border-white/5">
                                    <div className="text-[10px] text-muted-foreground uppercase mb-1">K/D Ratio</div>
                                    <div className="text-lg font-black text-foreground">{p.kd_ratio}</div>
                                </div>
                                <div className="bg-black/20 p-2 rounded-lg border border-white/5">
                                    <div className="text-[10px] text-muted-foreground uppercase mb-1">Playtime</div>
                                    <div className="text-lg font-black text-blue-400">{Math.round(p.total_playtime)}h</div>
                                </div>
                            </div>

                            <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                                <div className="flex items-center gap-1">
                                    <Zap className="w-3 h-3" />
                                    FAV: {p.favorite_weapon}
                                </div>
                                <div className="uppercase">{p.activity_pattern} PATTERN</div>
                            </div>
                        </div>
                    ))}
                    {!loading && profiles.length === 0 && (
                        <div className="py-20 text-center text-muted-foreground italic border-2 border-dashed border-white/5 rounded-2xl">
                            No biometric signatures detected in database.
                        </div>
                    )}
                </div>
            </ScrollArea>
        </GlassCard>
    );
}
export default SurvivorProfiles;

export { SurvivorProfiles };
