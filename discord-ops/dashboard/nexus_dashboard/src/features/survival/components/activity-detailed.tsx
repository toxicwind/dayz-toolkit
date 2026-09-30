'use client';

import * as React from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Activity, Shield, Zap, Skull, LogIn, LogOut, Info, MapPin } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';

interface SystemActivity {
    id: string;
    timestamp: string;
    player_name: string;
    activity_type: string;
    intensity: number;
    details: string;
    location: { x: number, y: number, z: number };
    threat_detected: boolean;
    anomaly_score: number;
}

export function ActivityDetailed() {
    const [activities, setActivities] = React.useState<SystemActivity[]>([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchFeed = async () => {
            try {
                const res = await fetch('/api/survival/activity-feed');
                const data = await res.json();
                if (data.activities) {
                    setActivities(data.activities);
                }
            } catch (error) {
                console.error('Failed to fetch activity feed:', error);
            } finally {
                setLoading(false);
            }
        };
        fetchFeed();
        const interval = setInterval(fetchFeed, 30000);
        return () => clearInterval(interval);
    }, []);

    const getTypeIcon = (type: string) => {
        switch (type.toLowerCase()) {
            case 'combat': return <Skull className="w-4 h-4 text-red-500" />;
            case 'interaction': return <LogIn className="w-4 h-4 text-emerald-400" />;
            case 'building': return <Shield className="w-4 h-4 text-blue-400" />;
            case 'looting': return <Zap className="w-4 h-4 text-yellow-400" />;
            default: return <Activity className="w-4 h-4 text-purple-400" />;
        }
    };

    return (
        <GlassCard className="p-6 h-full flex flex-col" opacity={15}>
            <div className="flex items-center gap-3 mb-6">
                <div className="relative">
                    <Activity className="w-6 h-6 text-purple-500" />
                    <div className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 rounded-full animate-ping" />
                </div>
                <div>
                    <h3 className="text-xl font-black uppercase tracking-tighter">System Activity Feed</h3>
                    <p className="text-[10px] text-muted-foreground font-mono">LIVE SERVER FEED | SECTOR 01</p>
                </div>
            </div>

            <ScrollArea className="flex-1 pr-4">
                <div className="space-y-6">
                    {loading ? (
                        <div className="py-20 text-center animate-pulse text-purple-400/50 uppercase font-black tracking-widest">Receiving Signals...</div>
                    ) : activities.map((act) => (
                        <div key={act.id} className="relative pl-6 border-l border-white/10 group">
                            {/* Point Indicator */}
                            <div className={cn(
                                "absolute -left-[5px] top-1 w-2.5 h-2.5 rounded-full border-2 border-background shadow-[0_0_10px_rgba(0,0,0,0.5)] transition-all group-hover:scale-125",
                                act.threat_detected ? "bg-red-500 box-shadow-[0_0_15px_rgba(239,68,68,0.8)]" : "bg-purple-500"
                            )} />

                            <div className="flex justify-between items-start mb-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-black text-foreground uppercase tracking-tight">{act.player_name}</span>
                                    <div className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[9px] font-mono text-muted-foreground flex items-center gap-1">
                                        {getTypeIcon(act.activity_type)}
                                        {act.activity_type.toUpperCase()}
                                    </div>
                                </div>
                                <span className="text-[10px] text-muted-foreground font-mono">
                                    {formatDistanceToNow(new Date(act.timestamp), { addSuffix: true })}
                                </span>
                            </div>

                            <div className="text-xs text-muted-foreground leading-relaxed mb-2 italic">
                                "{act.details}"
                            </div>

                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-1 text-[9px] text-muted-foreground font-mono">
                                    <MapPin className="w-3 h-3" />
                                    COORD: {Math.round(act.location.x)}, {Math.round(act.location.y)}
                                </div>
                                {act.anomaly_score > 0.5 && (
                                    <div className="text-[9px] font-black text-red-500 uppercase tracking-tighter">
                                        Anomaly Index: {(act.anomaly_score * 100).toFixed(0)}%
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {!loading && activities.length === 0 && (
                        <div className="text-center py-20 text-muted-foreground italic border-2 border-dashed border-white/5 rounded-2xl">
                            Static silence. No activity signatures detected.
                        </div>
                    )}
                </div>
            </ScrollArea>
        </GlassCard>
    );
}
export default ActivityDetailed;

export { ActivityDetailed };
