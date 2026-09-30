"use client";

import * as React from "react";
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Users, Search, RefreshCw, Eye, Fingerprint, ShieldAlert, Cpu } from "lucide-react";
import { PageContainer } from '@/components/layout/page-container';
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type TrackedPlayer = {
    steam_id: string;
    real_name: string;
    fake_name: string | null;
    first_seen: string | null;
    last_seen: string | null;
    notes: string | null;
};

export function IntelligencePage() {
    const [players, setPlayers] = React.useState<TrackedPlayer[]>([]);
    const [loading, setLoading] = React.useState(false);
    const [searchTerm, setSearchTerm] = React.useState("");

    const fetchPlayers = React.useCallback(async (scan = false) => {
        setLoading(true);
        try {
            const res = await fetch(`/api/intelligence/players?scan=${scan}`);
            const data = await res.json();
            if (data.players) {
                setPlayers(data.players);
                if (scan) toast.success("Scan complete");
            }
        } catch (error) {
            toast.error("Failed to update intelligence");
        } finally {
            setLoading(false);
        }
    }, []);

    const handleSetAlias = async (steam_id: string, current_alias: string | null) => {
        const newAlias = window.prompt("Assign Codename / Alias:", current_alias || "");
        if (newAlias === null) return; // Cancelled

        try {
            const res = await fetch('/api/intelligence/alias', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ steam_id, fake_name: newAlias })
            });
            const data = await res.json();
            if (data.status === 'success') {
                toast.success(`Alias set for ${steam_id}`);
                fetchPlayers(false); // Refresh list
            } else {
                toast.error(data.message || "Failed to set alias");
            }
        } catch (error) {
            toast.error("Failed to connect to Intelligence API");
        }
    };

    React.useEffect(() => {
        // Initial scan on mount
        fetchPlayers(true);

        // Poll every 60 seconds
        const interval = setInterval(() => {
            fetchPlayers(true);
        }, 60000);

        return () => clearInterval(interval);
    }, [fetchPlayers]);

    const filteredPlayers = players.filter(p =>
        (p.real_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.fake_name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.steam_id.includes(searchTerm)
    );

    return (
        <PageContainer>
            <div className="flex flex-col gap-8 relative z-10">
                {/* Header Section */}
                <div className="flex items-end justify-between border-b border-violet-500/20 pb-6">
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-violet-500/10 rounded-lg border border-violet-500/20">
                                <Cpu className="w-6 h-6 text-violet-400" />
                            </div>
                            <h2 className="text-3xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-fuchsia-400 uppercase italic">
                                Intelligence Network
                            </h2>
                        </div>
                        <p className="text-violet-400/60 pl-1 text-sm font-mono tracking-wide max-w-md">
                            // AUTOMATED PLAYER PROFILING AND IDENTITY CORRELATION SYSTEM
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/5 border border-violet-500/10 text-violet-400/50 text-xs font-mono mr-4">
                            {loading ? (
                                <>
                                    <RefreshCw className="w-3 h-3 animate-spin" />
                                    SCANNING...
                                </>
                            ) : (
                                <>
                                    <span className="relative flex h-2 w-2">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                    </span>
                                    LIVE FEED ACTIVE
                                </>
                            )}
                        </div>
                        <Button
                            onClick={() => fetchPlayers(true)}
                            size="sm"
                            disabled={loading}
                            className="bg-violet-600 hover:bg-violet-500 text-white border border-violet-500/50 shadow-[0_0_15px_rgba(139,92,246,0.3)] hover:shadow-[0_0_25px_rgba(139,92,246,0.5)] transition-all duration-300"
                        >
                            <Eye className={cn("w-4 h-4 mr-2", loading && "animate-pulse")} />
                            FORCE_SCAN
                        </Button>
                    </div>
                </div>

                <GlassCard className="p-0 overflow-hidden border-violet-500/20 bg-black/40 backdrop-blur-xl" opacity={5}>
                    {/* Toolbar */}
                    <div className="p-4 border-b border-white/5 flex items-center justify-between bg-white/5">
                        <div className="relative w-96 max-w-full group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-600 to-fuchsia-600 rounded-lg blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-violet-400" />
                                <Input
                                    placeholder="SEARCH_TARGETS [ID / ALIAS]..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10 bg-black/80 border-white/10 text-white font-mono placeholder:text-neutral-600 focus:border-violet-500/50 transition-colors h-10"
                                />
                            </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs font-mono">
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-300">
                                <Users className="w-3 h-3" />
                                <span>TARGETS: {filteredPlayers.length}</span>
                            </div>
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span>SYSTEM: ONLINE</span>
                            </div>
                        </div>
                    </div>

                    {/* Table */}
                    <div className="overflow-x-auto min-h-[400px]">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-white/5 border-b border-white/5">
                                    <th className="py-4 px-6 text-[10px] font-bold text-violet-400 uppercase tracking-[0.2em]">Codename / Identity</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-neutral-500 uppercase tracking-[0.2em]">Real Identity</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-neutral-500 uppercase tracking-[0.2em] hidden md:table-cell">Unique ID (Steam)</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-neutral-500 uppercase tracking-[0.2em]">Last Contact</th>
                                    <th className="py-4 px-6 text-[10px] font-bold text-neutral-500 uppercase tracking-[0.2em] text-right">Operations</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredPlayers.map((player) => (
                                    <tr
                                        key={player.steam_id}
                                        className="border-b border-white/5 hover:bg-white/[0.02] transition-colors group"
                                    >
                                        <td className="py-4 px-6">
                                            <div className="flex items-center gap-3">
                                                <div className={cn(
                                                    "w-10 h-10 rounded-lg flex items-center justify-center border transition-all duration-300",
                                                    player.fake_name
                                                        ? "bg-violet-500/10 border-violet-500/30 text-violet-400 shadow-[0_0_10px_rgba(139,92,246,0.1)]"
                                                        : "bg-neutral-800/50 border-white/5 text-neutral-600"
                                                )}>
                                                    {player.fake_name ? <Fingerprint className="w-5 h-5" /> : <Users className="w-5 h-5" />}
                                                </div>
                                                <div className="flex flex-col">
                                                    <span className={cn(
                                                        "font-mono text-sm tracking-wide",
                                                        player.fake_name
                                                            ? "text-transparent bg-clip-text bg-gradient-to-r from-violet-300 to-fuchsia-300 font-bold"
                                                            : "text-neutral-500 italic"
                                                    )}>
                                                        {player.fake_name || "UNASSIGNED"}
                                                    </span>
                                                    {player.fake_name && <span className="text-[10px] text-violet-500/50 uppercase tracking-widest">Tracking Active</span>}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="py-4 px-6">
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium text-neutral-300">{player.real_name}</span>
                                            </div>
                                        </td>
                                        <td className="py-4 px-6 hidden md:table-cell">
                                            <code className="px-2 py-1 rounded bg-black/40 border border-white/5 text-xs font-mono text-neutral-500">
                                                {player.steam_id}
                                            </code>
                                        </td>
                                        <td className="py-4 px-6">
                                            <span className="text-xs font-mono text-neutral-500">
                                                {player.last_seen ? new Date(player.last_seen).toLocaleString() : 'NEVER'}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6">
                                            <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity translate-x-4 group-hover:translate-x-0 duration-200">
                                                <Button
                                                    size="sm"
                                                    variant="secondary"
                                                    onClick={() => handleSetAlias(player.steam_id, player.fake_name)}
                                                    className="h-8 bg-white/5 hover:bg-violet-500/20 text-neutral-400 hover:text-violet-300 border border-white/10 hover:border-violet-500/50"
                                                >
                                                    RENAME
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {filteredPlayers.length === 0 && (
                                    <tr>
                                        <td colSpan={5} className="py-20 text-center">
                                            <div className="flex flex-col items-center justify-center gap-4 text-neutral-600">
                                                <ShieldAlert className="w-12 h-12 opacity-20" />
                                                <p className="text-sm font-mono uppercase tracking-widest">No Intelligence Data Available</p>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                </GlassCard>
            </div>
        </PageContainer>
    );
}
export default IntelligencePage;
