'use client';

import { GlassCard } from '@/components/ui/glass-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { User, LogIn, LogOut, AlertTriangle, Info } from 'lucide-react';

interface Log {
    id: number;
    timestamp: string;
    type: string;
    message: string;
    severity: string;
}

export function ActivityFeed({ logs }: { logs: Log[] }) {
    const getIcon = (type: string) => {
        switch (type) {
            case 'JOIN': return <LogIn className="w-4 h-4 text-emerald-400" />;
            case 'LEAVE': return <LogOut className="w-4 h-4 text-rose-400" />;
            case 'A2S_FAIL': return <AlertTriangle className="w-4 h-4 text-amber-400" />;
            default: return <Info className="w-4 h-4 text-blue-400" />;
        }
    };

    const getLabel = (type: string) => {
        switch (type) {
            case 'JOIN': return 'INFILTRATION';
            case 'LEAVE': return 'EXTRACTION';
            case 'A2S_FAIL': return 'COMMS_LOSS';
            default: return type;
        }
    };

    return (
        <GlassCard className="p-6 h-[500px] flex flex-col" opacity={5}>
            <h3 className="text-xl font-bold text-foreground tracking-widest uppercase mb-6">CRIME.NET FEED</h3>
            <ScrollArea className="flex-1 pr-4">
                <div className="space-y-4">
                    {logs.map((log) => (
                        <div key={log.id} className="flex gap-4 items-start pb-4 border-b border-border last:border-0">
                            <div className={cn(
                                "p-2 rounded-lg bg-card/10",
                                log.severity === 'warning' ? "bg-amber-500/10" : ""
                            )}>
                                {getIcon(log.type)}
                            </div>
                            <div className="flex-1 space-y-1">
                                <div className="text-sm font-medium text-foreground">{log.message}</div>
                                <div className="text-xs text-muted-foreground flex justify-between">
                                    <span className="uppercase tracking-tighter">{getLabel(log.type)}</span>
                                    <span>{formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                    {logs.length === 0 && (
                        <div className="text-center py-12 text-muted-foreground italic">
                            No active contracts or signals in target sector.
                        </div>
                    )}
                </div>
            </ScrollArea>
        </GlassCard>
    );
}
export default ActivityFeed;
