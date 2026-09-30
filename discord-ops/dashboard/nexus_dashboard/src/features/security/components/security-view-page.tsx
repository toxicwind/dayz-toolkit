"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertTriangle, Activity, RefreshCw, Lock, Zap } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function SecurityView({ initialData = {} }: { initialData?: any }) {
    const router = useRouter();
    const [scanning, setScanning] = useState(false);
    const [data, setData] = useState(initialData);

    const runSweep = async () => {
        setScanning(true);
        try {
            // Trigger the scan
            const res = await fetch("http://localhost:18789/security/scan", {
                method: "GET", // Using GET as per api.py definition
            });
            const newData = await res.json();
            setData(newData);
            router.refresh();
        } catch (e) {
            console.error("Sweep failed", e);
        } finally {
            setScanning(false);
        }
    };

    const isOptimal = data.scan_result?.status === "ready";
    const statusColor = isOptimal ? "text-emerald-500" : "text-red-500";
    const borderClass = isOptimal ? "border-emerald-900/30" : "border-red-900/50";

    return (
        <div className="flex-1 space-y-4 p-8 pt-6 bg-zinc-950 min-h-screen">
            <div className="flex items-center justify-between space-y-2">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                        <Lock className="h-8 w-8 text-yellow-500" />
                        SECURITY PROTOCOL
                    </h2>
                    <p className="text-zinc-400">Heist Anti-Cheat & Integrity Monitor</p>
                </div>
                <div className="flex items-center space-x-2">
                    <Button
                        onClick={runSweep}
                        disabled={scanning}
                        className="bg-red-700 hover:bg-red-600 text-white border border-red-500/50 shadow-[0_0_15px_rgba(220,38,38,0.5)] transition-all"
                    >
                        {scanning ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Zap className="mr-2 h-4 w-4" />}
                        {scanning ? "SWEEPING SECTORS..." : "TRIGGER SWEEP"}
                    </Button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {/* Card 1: Heuristics */}
                <Card className={`bg-black/60 backdrop-blur border ${borderClass}`}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-200">Duping Heuristics</CardTitle>
                        <ShieldCheck className={`h-4 w-4 ${statusColor}`} />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white flex items-center gap-2">
                            {isOptimal ? "ACTIVE" : "OFFLINE"}
                            {isOptimal && <span className="relative flex h-3 w-3">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                            </span>}
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">
                            Proximity: <span className="text-yellow-500/80">{data.scan_result?.config?.proximity_threshold || "15.0"}m</span>
                        </p>
                    </CardContent>
                </Card>

                {/* Card 2: Last Scan */}
                <Card className="bg-black/60 backdrop-blur border border-zinc-800">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-200">Last Pulse</CardTitle>
                        <Activity className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white font-mono">
                            {data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : "N/A"}
                        </div>
                        <p className="text-xs text-zinc-500 mt-1 truncate">
                            {data.message || "No telemetry signals"}
                        </p>
                    </CardContent>
                </Card>

                {/* Card 3: Threat Level */}
                <Card className="bg-black/60 backdrop-blur border border-zinc-800">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-200">Threat Level</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-white">LOW</div>
                        <div className="w-full bg-zinc-800 h-1 mt-2 rounded-full overflow-hidden">
                            <div className="bg-emerald-500 h-full w-2" />
                        </div>
                        <p className="text-xs text-zinc-500 mt-1">
                            0 anomalies detected
                        </p>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 grid-cols-1">
                <Card className="col-span-1 bg-black/40 border-zinc-800/60">
                    <CardHeader>
                        <CardTitle className="text-white">Raw Telemetry Stream</CardTitle>
                        <CardDescription className="text-zinc-400">Live feed from `run_security_check.py`</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="bg-black p-4 rounded-md border border-zinc-800 font-mono text-xs text-green-500/80 overflow-x-auto shadow-inner">
                            <pre>{JSON.stringify(data, null, 2)}</pre>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
