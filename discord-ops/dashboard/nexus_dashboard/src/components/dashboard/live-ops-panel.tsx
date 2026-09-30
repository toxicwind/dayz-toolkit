"use client";

import React, { useEffect, useState, useRef } from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Activity,
    Terminal,
    Wifi,
    WifiOff,
    Skull,
    Crosshair,
    Zap,
    Play
} from 'lucide-react';
import { cn } from '@/lib/utils'; // Assuming this exists, based on glass-card import

// Types based on API analysis
interface KillEvent {
    id: number;
    timestamp: string;
    killer: string;
    victim: string;
    weapon: string | null;
    distance_m: number | null;
    location: string | null;
}

interface ServerStatus {
    status: 'online' | 'offline' | 'connecting';
    players: number;
    message: string;
}

const POLL_INTERVAL_MS = 3000;
const STATUS_INTERVAL_MS = 5000;

export function LiveOpsPanel() {
    const [status, setStatus] = useState<ServerStatus | null>(null);
    const [killfeed, setKillfeed] = useState<KillEvent[]>([]);
    const [isSimulating, setIsSimulating] = useState(false);
    const [logs, setLogs] = useState<string[]>([]);
    const scrollRef = useRef<HTMLDivElement>(null);

    // --- Data Fetching ---

    const fetchStatus = async () => {
        try {
            // Use config URL or relative path if proxying
            const res = await fetch('/api/a2s/status');
            // Note: we might need to use the full URL if on different port, 
            // but usually Next.js rewrites /api to the backend. 
            // If not, we'll try the direct port mentioned in previous context (18789 or 18787).
            // Given the 'page.tsx' used localhost:18787, we should probably stick to that or assume a proxy is set up.
            // Let's try relative first, assuming Next.js config handles it, or fall back if distinct.
            // Actually, looking at page.tsx, it was using http://localhost:18787 explicitly.
            // For client-side, we should use the same domain or a configuring proxy.
            // I'll assume standard /api proxy or CORS allow.
            const data = await res.json();
            setStatus(data);
        } catch (e) {
            console.warn("Status fetch failed", e);
        }
    };

    const fetchKillfeed = async () => {
        try {
            const res = await fetch('/api/killfeed?limit=50');
            const data = await res.json();
            if (data.kills) {
                setKillfeed(data.kills);
            }
        } catch (e) {
            console.warn("Killfeed fetch failed", e);
        }
    };

    useEffect(() => {
        fetchStatus();
        fetchKillfeed();

        const statusTimer = setInterval(fetchStatus, STATUS_INTERVAL_MS);
        const feedTimer = setInterval(fetchKillfeed, POLL_INTERVAL_MS);

        return () => {
            clearInterval(statusTimer);
            clearInterval(feedTimer);
        };
    }, []);

    // --- Handlers ---

    const handleTriggerSimulation = async () => {
        setIsSimulating(true);
        addLog("Initiating OMEGA Self-Play Protocol...");

        try {
            const res = await fetch('/api/simulation/trigger', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: 'full_demo', count: 5 })
            });
            const data = await res.json();

            if (data.status === 'success') {
                addLog(`Simulation Active: ${data.message}`);
                // Force immediate refresh
                setTimeout(fetchKillfeed, 1000);
            } else {
                addLog(`Error: ${data.message}`);
            }
        } catch (e) {
            addLog("Critical Failure: Command Link Severed");
        } finally {
            setTimeout(() => setIsSimulating(false), 2000);
        }
    };

    const addLog = (msg: string) => {
        setLogs(prev => [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev].slice(0, 10));
    };

    // --- Formatting ---

    const formatDistance = (m: number | null) => m ? `${m.toFixed(1)}m` : 'Point Blank';

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
            {/* Left Column: Status & Controls */}
            <div className="space-y-6 lg:col-span-1 flex flex-col">
                {/* Status Card */}
                <GlassCard className="p-6 relative overflow-hidden group">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-widest">System Status</h3>
                            <div className="mt-1 flex items-baseline gap-2">
                                <span className={cn(
                                    "text-3xl font-black tracking-tighter transition-colors",
                                    status?.status === 'online' ? "text-emerald-400" : "text-rose-500"
                                )}>
                                    {status?.status?.toUpperCase() || "OFFLINE"}
                                </span>
                            </div>
                        </div>
                        <div className={cn(
                            "p-2 rounded-full ring-1 ring-white/10 shadow-inner",
                            status?.status === 'online' ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
                        )}>
                            {status?.status === 'online' ? <Wifi size={20} /> : <WifiOff size={20} />}
                        </div>
                    </div>

                    <div className="space-y-4">
                        <div className="flex justify-between items-center text-sm border-t border-white/5 pt-4">
                            <span className="text-muted-foreground">Active Players</span>
                            <span className="font-mono text-white text-lg">{status?.players || 0} / 60</span>
                        </div>
                    </div>

                    {/* Decor */}
                    <div className="absolute -bottom-12 -right-12 w-24 h-24 bg-primary/20 blur-3xl rounded-full pointer-events-none group-hover:bg-primary/30 transition-all" />
                </GlassCard>

                {/* Control Panel */}
                <GlassCard className="p-6 flex-1 flex flex-col justify-between border-primary/20 bg-primary/5">
                    <div>
                        <div className="flex items-center gap-2 mb-2 text-primary">
                            <Terminal size={18} />
                            <h3 className="text-sm font-bold uppercase tracking-widest">Command Override</h3>
                        </div>
                        <p className="text-xs text-muted-foreground mb-6">
                            Authorized Personnel Only. Triggers synthetic combat heuristic analysis (Self-Play).
                        </p>
                    </div>

                    <div className="space-y-4">
                        <Button
                            onClick={handleTriggerSimulation}
                            disabled={isSimulating}
                            className={cn(
                                "w-full h-14 font-bold tracking-widest uppercase transition-all duration-300",
                                isSimulating ? "bg-amber-500/80 animate-pulse" : "bg-primary hover:bg-primary/80"
                            )}
                        >
                            {isSimulating ? (
                                <span className="flex items-center gap-2"><Activity className="animate-spin" /> INITIATING...</span>
                            ) : (
                                <span className="flex items-center gap-2"><Play fill="currentColor" /> EXECUTE DRILL</span>
                            )}
                        </Button>

                        {/* Console Output */}
                        <div className="bg-black/40 rounded-lg p-3 font-mono text-[10px] text-green-400/80 h-32 overflow-hidden border border-white/5">
                            {logs.length === 0 && <span className="opacity-50">System Ready. Waiting for input...</span>}
                            {logs.map((log, i) => (
                                <div key={i} className="truncate">{log}</div>
                            ))}
                        </div>
                    </div>
                </GlassCard>
            </div>

            {/* Right Column: Live Killfeed */}
            <div className="lg:col-span-2 h-full">
                <GlassCard className="h-full flex flex-col p-0 overflow-hidden">
                    <div className="p-4 border-b border-white/10 bg-white/5 backdrop-blur-xl flex justify-between items-center z-10">
                        <div className="flex items-center gap-3">
                            <div className="p-1.5 bg-rose-500/20 rounded-md text-rose-400">
                                <Skull size={18} />
                            </div>
                            <div>
                                <h3 className="font-bold text-white tracking-tight">LIVE INTELLIGENCE FEED</h3>
                                <div className="flex items-center gap-2">
                                    <span className="relative flex h-2 w-2">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                    </span>
                                    <span className="text-[10px] text-emerald-400 font-mono tracking-widest uppercase">RECEIVING TELEMETRY</span>
                                </div>
                            </div>
                        </div>
                        <Badge variant="outline" className="font-mono text-[10px] border-white/10 bg-black/20">
                            LATEST 50 EVENTS
                        </Badge>
                    </div>

                    <ScrollArea className="flex-1 p-0">
                        <div className="flex flex-col">
                            {killfeed.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-64 text-muted-foreground gap-4">
                                    <Crosshair size={48} className="opacity-20" />
                                    <p>No recent combat signatures detected.</p>
                                </div>
                            ) : (
                                killfeed.map((event, i) => (
                                    <div
                                        key={`${event.id}-${i}`}
                                        className="group flex items-center justify-between p-4 border-b border-white/5 hover:bg-white/5 transition-colors relative"
                                    >
                                        <div className="flex items-center gap-4 z-10">
                                            {/* Icon based on killer existence */}
                                            <div className={cn(
                                                "w-10 h-10 rounded-full flex items-center justify-center border shadow-lg",
                                                event.killer
                                                    ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                                                    : "bg-neutral-500/10 border-neutral-500/20 text-neutral-400"
                                            )}>
                                                {event.killer ? <Crosshair size={18} /> : <Skull size={18} />}
                                            </div>

                                            <div className="space-y-0.5">
                                                <div className="text-sm text-balance">
                                                    {event.killer ? (
                                                        <>
                                                            <span className="font-bold text-rose-300">{event.killer}</span>
                                                            <span className="text-muted-foreground mx-1">eliminated</span>
                                                            <span className="font-bold text-neutral-100">{event.victim}</span>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <span className="font-bold text-neutral-100">{event.victim}</span>
                                                            <span className="text-muted-foreground mx-1">died</span>
                                                        </>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono">
                                                    {event.weapon && (
                                                        <span className="flex items-center gap-1 text-amber-500/80">
                                                            <Zap size={10} /> {event.weapon}
                                                        </span>
                                                    )}
                                                    {event.distance_m !== null && (
                                                        <span>{formatDistance(event.distance_m)}</span>
                                                    )}
                                                    {event.location && (
                                                        <span className="text-blue-400/80">{event.location}</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="text-[10px] font-mono text-muted-foreground/50 whitespace-nowrap z-10">
                                            {new Date(event.timestamp).toLocaleTimeString()}
                                        </div>

                                        {/* Hover Effect */}
                                        <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                                    </div>
                                ))
                            )}
                        </div>
                    </ScrollArea>
                </GlassCard>
            </div>
        </div>
    );
}
