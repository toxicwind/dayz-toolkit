"use client";

import React, { useEffect, useState } from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    ZAxis,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';
import { Scan, Crosshair, Map as MapIcon, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface KillEvent {
    id: number;
    timestamp: string;
    killer: string;
    victim: string;
    weapon: string | null;
    distance_m: number | null;
    location: string | null;
    location_x: number | null; // From API (implied select *)
    location_y: number | null;
    location_z: number | null;
    pos_x?: number | null; // From new DB schema (if API uses raw cols)
    pos_z?: number | null;
}

// Map Configuration
const MAP_SIZE = 15360; // DayZ Chernarus Size
const REFRESH_MS = 5000;

export function TacticalMap() {
    const [kills, setKills] = useState<KillEvent[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchKills = async () => {
        try {
            const res = await fetch('/api/killfeed?limit=200'); // Get more points for heatmap feel
            const data = await res.json();
            if (data.kills) {
                // Normalize data: Use pos_x/pos_z if available (new schema), else location_x/z
                const processed = data.kills
                    .map((k: any) => ({
                        ...k,
                        x: k.pos_x ?? k.location_x ?? null,
                        z: k.pos_z ?? k.location_z ?? null,
                        // Recency score for z-index/size (seconds ago)
                        recency: Math.max(0, (Date.now() - new Date(k.timestamp).getTime()) / 1000)
                    }))
                    .filter((k: any) => k.x !== null && k.z !== null && k.x !== 0 && k.z !== 0); // valid points only

                setKills(processed);
            }
        } catch (e) {
            console.error("Map fetch error", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchKills();
        const timer = setInterval(fetchKills, REFRESH_MS);
        return () => clearInterval(timer);
    }, []);

    // Custom Tooltip
    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-black/90 border border-emerald-500/30 p-2 rounded text-xs font-mono shadow-xl backdrop-blur-md">
                    <div className="font-bold text-emerald-400 mb-1">{new Date(data.timestamp).toLocaleTimeString()}</div>
                    <div className="text-white">
                        {data.killer ? <span className="text-rose-400">{data.killer}</span> : <span className="text-neutral-400">Environment</span>}
                        {' '}➔{' '}
                        <span className="text-white">{data.victim}</span>
                    </div>
                    <div className="text-muted-foreground mt-1">
                        {data.weapon && `[API: ${data.weapon}]`} {data.distance_m ? `(${data.distance_m.toFixed(0)}m)` : ''}
                    </div>
                    <div className="text-[10px] text-emerald-600 mt-1">LOC: {data.x.toFixed(0)}, {data.z.toFixed(0)}</div>
                </div>
            );
        }
        return null;
    };

    return (
        <GlassCard className="h-[400px] flex flex-col relative overflow-hidden group border-emerald-500/20 bg-black/40">
            {/* Background Grid - CSS Pattern */}
            <div
                className="absolute inset-0 opacity-20 pointer-events-none"
                style={{
                    backgroundImage: `linear-gradient(rgba(16, 185, 129, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(16, 185, 129, 0.1) 1px, transparent 1px)`,
                    backgroundSize: '40px 40px'
                }}
            />

            {/* Radar Sweep Effect */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
                <div className="w-full h-[2px] bg-emerald-500/30 shadow-[0_0_15px_rgba(16,185,129,0.5)] animate-[scan_4s_linear_infinite]" />
            </div>

            {/* Header */}
            <div className="absolute top-4 left-4 z-10 flex flex-col gap-1 pointer-events-none">
                <div className="flex items-center gap-2">
                    <Scan className="text-emerald-500 animate-pulse" size={18} />
                    <h3 className="text-sm font-bold text-emerald-100 tracking-widest uppercase glow-text">Tactical Radar</h3>
                </div>
                <div className="text-[10px] items-center flex gap-2 font-mono text-emerald-500/70">
                    <span className="bg-emerald-500/10 px-1 rounded">LIVE FEED</span>
                    <span>{kills.length} SIGNATURES</span>
                </div>
            </div>

            {/* Map Chart */}
            <div className="flex-1 w-full h-full p-4 relative z-0">
                <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        {/* Domain 0-15360. 
                    DayZ Map: 
                    X: 0 (West) -> 15360 (East). 
                    Z: 0 (South) -> 15360 (North). 
                    Recharts Y Axis: 0 is at bottom (standard Cartesian). 
                    So X=X, Y=Z maps perfectly. 
                */}
                        <XAxis type="number" dataKey="x" domain={[0, MAP_SIZE]} hide />
                        <YAxis type="number" dataKey="z" domain={[0, MAP_SIZE]} hide />
                        <ZAxis type="number" range={[50, 400]} /> {/* Optional sizing logic could go here */}

                        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#10b981' }} />

                        <Scatter name="Kills" data={kills} fill="#10b981">
                            {kills.map((entry, index) => {
                                // Color Coding
                                let color = '#ef4444'; // Red (Killer)
                                if (!entry.killer) color = '#3b82f6'; // Blue (PVE)
                                if (entry.recency < 300) color = '#ffffff'; // White hot (Recent < 5 mins)

                                // Opacity based on age
                                const opacity = Math.max(0.3, 1 - (entry.recency / 3600)); // Fade over hour

                                return <Cell key={`cell-${index}`} fill={color} fillOpacity={opacity} strokeWidth={entry.recency < 60 ? 2 : 0} stroke="#fff" />;
                            })}
                        </Scatter>
                    </ScatterChart>
                </ResponsiveContainer>

                {/* Map Decorations */}
                <div className="absolute bottom-4 right-4 text-[10px] font-mono text-emerald-600/50 pointer-events-none">
                    GRID: 15x15km<br />
                    SCALE: 1:1<br />
                    SECURE
                </div>
            </div>
        </GlassCard>
    );
}
