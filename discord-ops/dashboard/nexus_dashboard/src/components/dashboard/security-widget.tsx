import { GlassCard } from "@/components/ui/glass-card";
import { ShieldCheck, Lock } from "lucide-react";
import Link from "next/link";

interface SecurityWidgetProps {
    status: string;
    threatLevel: string;
}

export function SecurityWidget({ status, threatLevel }: SecurityWidgetProps) {
    const isSecure = status === "ACTIVE";

    return (
        <Link href="/dashboard/security" className="block group">
            <GlassCard className="p-4 relative overflow-hidden transition-all duration-300 group-hover:border-red-500/50" opacity={15}>
                <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-40 transition-opacity">
                    <Lock className="h-12 w-12 text-red-500" />
                </div>

                <div className="flex items-center gap-2 mb-2">
                    <ShieldCheck className={`h-4 w-4 ${isSecure ? "text-emerald-500" : "text-red-500"}`} />
                    <div className="text-sm font-medium text-slate-300">Security Protocol</div>
                </div>

                <div className="text-2xl font-bold text-white tracking-tight">
                    {isSecure ? "SYSTEM SECURE" : "THREAT DETECTED"}
                </div>

                <div className="mt-2 flex items-center gap-2">
                    <div className={`h-1.5 w-1.5 rounded-full ${isSecure ? "bg-emerald-500 animate-pulse" : "bg-red-500 animate-ping"}`} />
                    <p className="text-xs text-neutral-400">
                        Heuristics: <span className="text-slate-200">{status}</span>
                    </p>
                </div>
            </GlassCard>
        </Link>
    );
}
