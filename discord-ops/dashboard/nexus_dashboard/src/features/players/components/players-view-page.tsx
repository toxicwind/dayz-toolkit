"use client";

import * as React from "react";
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Users, UserX, Shield, Search, RefreshCw } from "lucide-react";
import { PageContainer } from '@/components/layout/page-container';
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type Player = {
    gamertag: string;
    status: string;
    last_seen: string | null;
};

export function PlayersPage() {
    const [players, setPlayers] = React.useState<Player[]>([]);
    const [loading, setLoading] = React.useState(false);
    const [searchTerm, setSearchTerm] = React.useState("");
    const [actionLoading, setActionLoading] = React.useState<string | null>(null);

    const fetchPlayers = React.useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/server/players');
            const data = await res.json();
            if (data.players) {
                setPlayers(data.players);
            }
        } catch (error) {
            toast.error("Failed to fetch players");
        } finally {
            setLoading(false);
        }
    }, []);

    const handleAction = async (gamertag: string, action: 'kick' | 'ban') => {
        if (!confirm(`Are you sure you want to ${action} ${gamertag}?`)) return;

        setActionLoading(gamertag);
        try {
            const res = await fetch('/api/server/players', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action, gamertag })
            });
            const data = await res.json();
            if (data.status === 'success') {
                toast.success(`${action === 'kick' ? 'Kicked' : 'Banned'} ${gamertag}`);
                fetchPlayers();
            } else {
                toast.error(data.message || `Failed to ${action} player`);
            }
        } catch (error) {
            toast.error(`Error: ${error}`);
        } finally {
            setActionLoading(null);
        }
    };

    React.useEffect(() => {
        fetchPlayers();
        const interval = setInterval(fetchPlayers, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, [fetchPlayers]);

    const filteredPlayers = players.filter(p =>
        p.gamertag.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <PageContainer>
            <div className="flex flex-col gap-6">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-2xl font-bold tracking-tight text-foreground uppercase italic pl-2 border-l-4 border-primary">
                            Survivor Registry
                        </h2>
                        <p className="text-muted-foreground pl-2 text-sm">Active player monitoring and moderation control.</p>
                    </div>
                    <Button onClick={fetchPlayers} variant="outline" size="sm" disabled={loading}>
                        <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
                        Refresh
                    </Button>
                </div>

                <GlassCard className="p-6" opacity={10}>
                    <div className="flex items-center gap-4 mb-6">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                            <Input
                                placeholder="Search by gamertag..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10 bg-background/50 border-border"
                            />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Users className="w-4 h-4" />
                            <span className="font-mono">{filteredPlayers.length} Active</span>
                        </div>
                    </div>

                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-border">
                                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-foreground uppercase tracking-wider">Gamertag</th>
                                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-foreground uppercase tracking-wider">Status</th>
                                    <th className="text-left py-3 px-4 text-xs font-bold text-muted-foreground uppercase tracking-wider">Last Seen</th>
                                    <th className="text-right py-3 px-4 text-xs font-bold text-muted-foreground uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredPlayers.map((player, idx) => (
                                    <tr key={idx} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                                        <td className="py-3 px-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                                                <span className="font-mono text-sm text-foreground">{player.gamertag}</span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-4">
                                            <span className={cn(
                                                "px-2 py-1 rounded text-xs font-bold uppercase",
                                                player.status === 'online' ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"
                                            )}>
                                                {player.status}
                                            </span>
                                        </td>
                                        <td className="py-3 px-4 text-sm text-muted-foreground font-mono">
                                            {player.last_seen ? new Date(player.last_seen).toLocaleString() : 'Unknown'}
                                        </td>
                                        <td className="py-3 px-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => handleAction(player.gamertag, 'kick')}
                                                    disabled={actionLoading === player.gamertag}
                                                    className="text-xs"
                                                >
                                                    <UserX className="w-3 h-3 mr-1" />
                                                    Kick
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    onClick={() => handleAction(player.gamertag, 'ban')}
                                                    disabled={actionLoading === player.gamertag}
                                                    className="text-xs"
                                                >
                                                    <Shield className="w-3 h-3 mr-1" />
                                                    Ban
                                                </Button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {filteredPlayers.length === 0 && (
                                    <tr>
                                        <td colSpan={4} className="py-12 text-center text-muted-foreground">
                                            {searchTerm ? 'No players match your search.' : 'No active players detected.'}
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
export default PlayersPage;
