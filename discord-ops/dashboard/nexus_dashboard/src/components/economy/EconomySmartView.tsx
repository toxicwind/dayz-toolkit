"use client";

import * as React from "react";
import { Package, ChevronDown, ChevronRight, Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface Item {
    name: string;
    nominal: number;
    min: number;
    lifetime: number;
}

export function EconomySmartView() {
    const [clusters, setClusters] = React.useState<Record<string, Item[]>>({});
    const [loading, setLoading] = React.useState(true);
    const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});

    React.useEffect(() => {
        const fetchClusters = async () => {
            try {
                const res = await fetch('/api/server/economy/intelligence/clusters');
                const data = await res.json();
                setClusters(data);
            } catch (error) {
                console.error("Failed to fetch clusters", error);
            } finally {
                setLoading(false);
            }
        };
        fetchClusters();
    }, []);

    const toggle = (base: string) => {
        setExpanded(prev => ({ ...prev, [base]: !prev[base] }));
    };

    if (loading) return <div className="p-8 text-center text-muted-foreground">Mapping semantic clusters...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2">
                    <Layers className="w-4 h-4 text-primary" />
                    Semantic Clusters
                </h3>
                <span className="text-[10px] text-muted-foreground italic">Groups variants into families</span>
            </div>
            <ScrollArea className="h-[600px] pr-4">
                <div className="grid gap-4">
                    {Object.entries(clusters).sort((a,b) => b[1].length - a[1].length).map(([base, items]) => (
                        <div key={base} className="bg-white/5 rounded-lg border border-white/10 overflow-hidden transition-all duration-300 hover:border-white/20">
                            <button 
                                onClick={() => toggle(base)}
                                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors group"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-primary/10 rounded group-hover:bg-primary/20 transition-colors">
                                        <Package className="w-4 h-4 text-primary" />
                                    </div>
                                    <div className="text-left">
                                        <div className="font-bold text-sm text-white">{base}</div>
                                        <div className="text-[10px] text-muted-foreground">{items.length} Variants discovered</div>
                                    </div>
                                </div>
                                {expanded[base] ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
                            </button>
                            
                            {expanded[base] && (
                                <div className="p-4 pt-0 space-y-2 border-t border-white/5 bg-black/20">
                                    <div className="grid grid-cols-4 gap-2 text-[10px] font-bold text-muted-foreground py-2 uppercase tracking-tight">
                                        <div className="col-span-1">Variant</div>
                                        <div>Nominal</div>
                                        <div>Min</div>
                                        <div>Lifetime</div>
                                    </div>
                                    {items.map((item, idx) => (
                                        <div key={idx} className="grid grid-cols-4 gap-2 items-center text-xs py-1.5 border-b border-white/5 last:border-0 hover:bg-white/5 px-1 rounded transition-colors pr-2">
                                            <div className="font-mono text-white/70 truncate pr-2">{item.name}</div>
                                            <div className="font-bold text-primary">{item.nominal}</div>
                                            <div className="text-muted-foreground">{item.min}</div>
                                            <div className="text-muted-foreground/50">{item.lifetime}s</div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </ScrollArea>
        </div>
    );
}
export default EconomySmartView;

export { EconomySmartView };
