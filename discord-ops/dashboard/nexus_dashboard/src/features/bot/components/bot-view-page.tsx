"use client";

import * as React from "react";
import { PageContainer } from "@/components/layout/page-container";
import { GlassCard } from "@/components/ui/glass-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Bot, MessageSquare, ShieldCheck, Activity, Terminal, ExternalLink, Globe, Wifi } from "lucide-react";
import { cn } from "@/lib/utils";

export function BotPage() {
  const [status, setStatus] = React.useState<any>(null);
  const [logs, setLogs] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  const fetchData = async () => {
    try {
      const [sRes, lRes] = await Promise.all([
        fetch('/api/server/bot/status'),
        fetch('/api/server/bot/logs')
      ]);
      const sData = await sRes.json();
      const lData = await lRes.json();
      setStatus(sData);
      setLogs(lData.logs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <PageContainer>
        <div className="h-[80vh] flex flex-col items-center justify-center gap-4">
          <Bot className="w-12 h-12 text-primary animate-bounce" />
          <p className="font-mono text-xs tracking-widest text-primary animate-pulse uppercase">Syncing with Discord Gateway...</p>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-120px)]">
        {/* Identity & Status */}
        <div className="col-span-4 flex flex-col gap-6">
          <GlassCard className="p-8 flex flex-col items-center text-center relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4">
              <Badge variant={status?.status === "online" ? "default" : "destructive"} className="animate-pulse">
                {status?.status?.toUpperCase() || "OFFLINE"}
              </Badge>
            </div>
            <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-primary to-purple-600 p-1 mb-6 shadow-2xl group-hover:scale-105 transition-transform">
              <div className="w-full h-full rounded-full bg-black flex items-center justify-center overflow-hidden border-4 border-black">
                <Bot className="w-12 h-12 text-white" />
              </div>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mb-2">{status?.name || "DayZ Ops Command"}</h1>
            <p className="text-muted-foreground text-sm mb-6 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-primary" />
              Managed Operations Bot
            </p>

            <div className="grid grid-cols-2 gap-4 w-full pt-6 border-t border-white/5">
              <div className="flex flex-col gap-1 items-center">
                <span className="text-[10px] uppercase tracking-tighter text-muted-foreground font-bold italic">Ping</span>
                <span className="text-lg font-mono text-green-400">{status?.latency || "???"}</span>
              </div>
              <div className="flex flex-col gap-1 items-center">
                <span className="text-[10px] uppercase tracking-tighter text-muted-foreground font-bold italic">Cluster</span>
                <span className="text-lg font-mono text-primary">#01</span>
              </div>
            </div>
          </GlassCard>

          <GlassCard className="p-6">
            <h3 className="text-xs font-bold tracking-widest text-primary flex items-center gap-2 mb-6">
              <Globe className="w-4 h-4" />
              DEPLOYMENT CONTEXT
            </h3>
            <div className="space-y-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Authorized Guild</span>
                <span className="font-mono text-white text-xs">{status?.guild || "Official Guild"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Guild ID</span>
                <span className="font-mono text-white text-xs opacity-60 underline decoration-primary/30 cursor-help">{status?.guild_id || "784305829"}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-muted-foreground">Environment</span>
                <Badge variant="outline" className="text-[10px] h-5 border-primary/20 bg-primary/5">PRODUCTION</Badge>
              </div>
            </div>
          </GlassCard>

          <div className="mt-auto">
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground uppercase font-bold tracking-widest opacity-40 hover:opacity-100 transition-opacity cursor-default">
              <Wifi className="w-3 h-3" />
              Discord WebSocket Stable
            </div>
          </div>
        </div>

        {/* Activity Feed */}
        <div className="col-span-8 flex flex-col gap-6 overflow-hidden">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-primary/10">
            <header className="h-14 border-b border-white/5 flex items-center px-6 justify-between bg-black/40">
              <div className="flex items-center gap-3">
                <Terminal className="w-4 h-4 text-primary" />
                <h2 className="text-xs font-bold tracking-[0.3em] text-white uppercase italic">Bot Transaction Log</h2>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[10px] font-mono text-muted-foreground">LIVE FEED</span>
                </div>
              </div>
            </header>

            <ScrollArea className="flex-1 bg-black/20">
              <div className="p-6 space-y-4">
                {logs.map((log, i) => (
                  <div key={i} className="flex gap-4 group">
                    <div className="flex flex-col items-center">
                      <div className={cn(
                        "w-2 h-2 rounded-full mt-1.5 shadow-[0_0_8px]",
                        log.level === "error" ? "bg-red-500 shadow-red-500" :
                          log.level === "warning" ? "bg-amber-500 shadow-amber-500" :
                            "bg-primary shadow-primary"
                      )} />
                      <div className="w-px h-full bg-white/5 mt-1" />
                    </div>
                    <div className="flex flex-col gap-1 min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-white/80 uppercase tracking-tighter group-hover:text-primary transition-colors italic">
                          {log.action}
                        </span>
                        <span className="text-[9px] font-mono text-muted-foreground/50">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed font-mono selection:bg-primary/30">
                        {log.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>

            <footer className="h-10 border-t border-white/5 bg-black/40 px-6 flex items-center text-[9px] text-muted-foreground font-mono">
              <Activity className="w-3 h-3 mr-2 text-primary" />
              {logs.length} Operations logged in current session
            </footer>
          </GlassCard>
        </div>
      </div>
    </PageContainer>
  );
}
export default BotPage;
