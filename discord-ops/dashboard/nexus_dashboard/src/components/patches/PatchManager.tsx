'use client';

import * as React from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
    Zap,
    Shield,
    Activity,
    Box,
    Cloud,
    Database,
    AlertCircle,
    Info,
    RefreshCw,
    Search
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';

interface Patch {
    id: string;
    file: string;
    enabled: boolean;
    category: string;
    fileExists: boolean;
}

export function PatchManager() {
    const [patches, setPatches] = React.useState<Patch[]>([]);
    const [categories, setCategories] = React.useState<Record<string, string>>({});
    const [loading, setLoading] = React.useState(true);
    const [searchQuery, setSearchQuery] = React.useState('');
    const [toggling, setToggling] = React.useState<string | null>(null);

    const fetchPatches = React.useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/patches');
            const data = await res.json();
            if (data.patches) {
                setPatches(data.patches);
                setCategories(data.categories);
            }
        } catch (error) {
            toast.error('Failed to load patches');
        } finally {
            setLoading(false);
        }
    }, []);

    React.useEffect(() => {
        fetchPatches();
    }, [fetchPatches]);

    const handleToggle = async (patch: Patch) => {
        setToggling(patch.id);
        try {
            const res = await fetch('/api/patches', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file: patch.file,
                    enabled: !patch.enabled
                }),
            });
            const data = await res.json();
            if (data.success) {
                toast.success(`${patch.enabled ? 'Disabled' : 'Enabled'} ${patch.id}`);
                // Optimistic UI or re-fetch
                setPatches(prev => prev.map(p =>
                    p.id === patch.id ? { ...p, enabled: !patch.enabled } : p
                ));
            } else {
                toast.error(data.error || 'Failed to update patch');
            }
        } catch (error) {
            toast.error('Network error updating patch');
        } finally {
            setToggling(null);
        }
    };

    const getCategoryIcon = (category: string) => {
        switch (category) {
            case 'gameplay': return <Activity className="w-4 h-4" />;
            case 'base': return <Shield className="w-4 h-4" />;
            case 'spawn': return <Zap className="w-4 h-4" />;
            case 'economy': return <Database className="w-4 h-4" />;
            case 'world': return <Cloud className="w-4 h-4" />;
            default: return <Box className="w-4 h-4" />;
        }
    };

    const filteredPatches = patches.filter(p =>
        p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.category.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                        placeholder="Search patches (stamina, vehicles, base...)"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 bg-black/40 border-white/10"
                    />
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchPatches}
                    disabled={loading}
                    className="bg-primary/10 border-primary/20 hover:bg-primary/20 text-primary"
                >
                    <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
                    Refresh Manifest
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <GlassCard key={i} className="h-40 animate-pulse" />
                    ))
                ) : filteredPatches.length > 0 ? (
                    filteredPatches.map((patch) => (
                        <GlassCard
                            key={patch.id}
                            className={cn(
                                "p-6 transition-all duration-300 group",
                                patch.enabled
                                    ? "border-primary/30 shadow-[0_0_20px_-10px_rgba(var(--primary-rgb),0.3)]"
                                    : "opacity-80 hover:opacity-100"
                            )}
                            opacity={patch.enabled ? 20 : 10}
                        >
                            <div className="flex flex-col h-full gap-4">
                                <div className="flex items-start justify-between">
                                    <div className="p-2 rounded-lg bg-black/40 border border-white/5 text-primary">
                                        {getCategoryIcon(patch.category)}
                                    </div>
                                    <Switch
                                        checked={patch.enabled}
                                        onCheckedChange={() => handleToggle(patch)}
                                        disabled={toggling === patch.id || !patch.fileExists}
                                    />
                                </div>

                                <div className="space-y-1">
                                    <h3 className="font-black uppercase tracking-tighter text-lg leading-tight group-hover:text-primary transition-colors">
                                        {patch.id.replace(/^\d+_/, '').replace(/_/g, ' ')}
                                    </h3>
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-[10px] uppercase tracking-widest bg-white/5 border-white/10">
                                            {patch.category}
                                        </Badge>
                                        {!patch.fileExists && (
                                            <Badge variant="destructive" className="text-[10px] uppercase">
                                                File Missing
                                            </Badge>
                                        )}
                                    </div>
                                </div>

                                <div className="mt-auto pt-2 border-t border-white/5 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                                    <span className="truncate max-w-[120px]">{patch.file}</span>
                                    {patch.enabled ? (
                                        <span className="text-emerald-400 flex items-center gap-1">
                                            <div className="w-1 h-1 rounded-full bg-emerald-400 animate-pulse" />
                                            ACTIVE
                                        </span>
                                    ) : (
                                        <span>INACTIVE</span>
                                    )}
                                </div>
                            </div>
                        </GlassCard>
                    ))
                ) : (
                    <div className="col-span-full py-20 flex flex-col items-center justify-center text-center space-y-4">
                        <div className="p-4 rounded-full bg-white/5 border border-white/10">
                            <Box className="w-12 h-12 text-muted-foreground/50" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold">No patches found</h3>
                            <p className="text-muted-foreground">Try adjusting your search or refresh the manifest.</p>
                        </div>
                    </div>
                )}
            </div>

            <GlassCard className="p-6 border-amber-500/20 bg-amber-500/5" opacity={10}>
                <div className="flex items-start gap-4">
                    <div className="p-2 rounded-full bg-amber-500/10 text-amber-500">
                        <Info className="w-5 h-5" />
                    </div>
                    <div className="space-y-1">
                        <h4 className="font-bold text-amber-500 uppercase tracking-tight">Manual Application Required</h4>
                        <p className="text-sm text-muted-foreground leading-relaxed">
                            Toggling patches updates the <code className="bg-black/40 px-1 rounded text-amber-200">manifest.json</code>.
                            To apply changes to the live server, you must trigger the <span className="font-bold text-foreground italic">Re-build Mission</span> action
                            from the Advanced Server Management panel.
                        </p>
                    </div>
                </div>
            </GlassCard>
        </div>
    );
}
