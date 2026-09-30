"use client";

import { useEffect, useState, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Pause, Play, Trash2 } from "lucide-react";

type LogLevel = "info" | "warn" | "error" | "combat" | "admin" | "system";

interface LogEvent {
    timestamp: string;
    source: string;
    level: LogLevel;
    message: string;
    player?: string;
}

export function LogViewer() {
    const [logs, setLogs] = useState<LogEvent[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Connect to WebSocket
        // Assuming API is on localhost:18789 for now, or use env var
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:18789/ws/logs";

        const connect = () => {
            try {
                const ws = new WebSocket(wsUrl);
                wsRef.current = ws;

                ws.onopen = () => {
                    setIsConnected(true);
                    console.log("Connected to Log Stream");
                };

                ws.onmessage = (event) => {
                    if (isPaused) return;
                    try {
                        const data = JSON.parse(event.data);
                        setLogs((prev) => [data, ...prev].slice(0, 1000)); // Keep last 1000
                    } catch (e) {
                        console.error("Failed to parse log", e);
                    }
                };

                ws.onclose = () => {
                    setIsConnected(false);
                    setTimeout(connect, 3000); // Reconnect
                };

                ws.onerror = (err) => {
                    console.error("WS Error", err);
                    ws.close();
                }
            } catch (e) {
                console.error("WS Connection Failed", e);
            }
        };

        connect();

        return () => {
            wsRef.current?.close();
        };
    }, [isPaused]);

    const getLevelColor = (level: LogLevel) => {
        switch (level) {
            case "error": return "text-red-500";
            case "warn": return "text-yellow-500";
            case "combat": return "text-orange-500 font-bold"; // Killfeed
            case "admin": return "text-purple-400";
            case "system": return "text-gray-400";
            default: return "text-blue-400";
        }
    };

    return (
        <Card className="h-[600px] flex flex-col bg-zinc-950 border-zinc-800">
            <CardHeader className="flex flex-row items-center justify-between py-3 border-b border-zinc-800">
                <div className="flex items-center gap-2">
                    <CardTitle className="text-lg font-mono">Live Console</CardTitle>
                    <Badge variant={isConnected ? "default" : "destructive"} className="text-xs">
                        {isConnected ? "LIVE" : "OFFLINE"}
                    </Badge>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => setIsPaused(!isPaused)}>
                        {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setLogs([])}>
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden relative">
                <ScrollArea className="h-full w-full p-4 font-mono text-xs">
                    {logs.map((log, i) => (
                        <div key={i} className="mb-1 flex gap-2 border-b border-zinc-900/50 pb-1 last:border-0 hover:bg-zinc-900/30 px-1 rounded">
                            <span className="text-zinc-500 shrink-0 opacity-50 w-[140px]">
                                {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                            <span className={`uppercase font-bold shrink-0 w-[60px] ${getLevelColor(log.level)}`}>
                                {log.level}
                            </span>
                            <span className="text-zinc-300 break-all whitespace-pre-wrap">
                                {log.message}
                            </span>
                        </div>
                    ))}
                    {logs.length === 0 && (
                        <div className="text-zinc-600 text-center mt-20 italic">
                            Waiting for logs...
                        </div>
                    )}
                </ScrollArea>
            </CardContent>
        </Card>
    );
}
export default LogViewer;
