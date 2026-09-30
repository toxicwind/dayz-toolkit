"use client";

import * as React from "react";
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Warning {
    item: string;
    level: "critical" | "warning" | "error";
    message: string;
}

export function EconomyDiagnostics() {
    const [warnings, setWarnings] = React.useState<Warning[]>([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchWarnings = async () => {
            try {
                const res = await fetch('/api/server/economy/intelligence/validate');
                const data = await res.json();
                setWarnings(data.warnings || []);
            } catch (error) {
                console.error("Failed to fetch diagnostics", error);
            } finally {
                setLoading(false);
            }
        };
        fetchWarnings();
    }, []);

    if (loading) return <div className="p-8 text-center text-muted-foreground animate-pulse">Running diagnostic scanner...</div>;

    if (warnings.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 space-y-4">
                <CheckCircle2 className="w-12 h-12 text-green-500/50" />
                <div className="text-center">
                    <h3 className="text-lg font-medium text-white">System Integrity Nominal</h3>
                    <p className="text-muted-foreground text-sm">No logical errors detected in types.xml.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <h3 className="text-sm font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2 mb-4">
                <AlertCircle className="w-4 h-4 text-primary" />
                Diagnostic Report
            </h3>
            <ScrollArea className="h-[500px] pr-4">
                <div className="grid gap-3">
                    {warnings.map((w, i) => (
                        <div key={i} className={cn(
                            "p-4 rounded-lg border flex items-start gap-4 transition-all duration-300 hover:shadow-lg hover:ring-1 hover:ring-white/10",
                            w.level === 'critical' ? "bg-red-500/10 border-red-500/20 shadow-red-500/5" : 
                            w.level === 'error' ? "bg-orange-500/10 border-orange-500/20 shadow-orange-500/5" :
                            "bg-amber-500/10 border-amber-500/20 shadow-amber-500/5"
                        )}>
                            <div className="flex-shrink-0 pt-0.5">
                                {w.level === 'critical' ? <AlertCircle className="w-5 h-5 text-red-500" /> :
                                 w.level === 'error' ? <AlertCircle className="w-5 h-5 text-orange-500" /> :
                                 <AlertTriangle className="w-5 h-5 text-amber-500" />}
                            </div>
                            <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs font-bold text-white/90">{w.item}</span>
                                    <span className={cn(
                                        "text-[10px] uppercase font-bold px-1.5 py-0.5 rounded",
                                        w.level === 'critical' ? "bg-red-500/20 text-red-500" :
                                        "bg-amber-500/20 text-amber-500"
                                    )}>
                                        {w.level}
                                    </span>
                                </div>
                                <p className="text-sm text-muted-foreground leading-relaxed">{w.message}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </ScrollArea>
        </div>
    );
}
export default EconomyDiagnostics;

export { EconomyDiagnostics };
