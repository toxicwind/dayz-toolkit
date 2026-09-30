"use client";

import * as React from "react";
import { PageContainer } from "@/components/layout/page-container";
import { GlassCard } from "@/components/ui/glass-card";
import { Button } from "@/components/ui/button";
import {
  Search, FileText, Download, Terminal, Cloud,
  Power, RefreshCw, AlertTriangle, Box, Activity,
  ChevronRight, Database
} from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function LogisticsPage() {
  const [logs, setLogs] = React.useState<any[]>([]);
  const [selectedLog, setSelectedLog] = React.useState<string | null>(null);
  const [content, setContent] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [status, setStatus] = React.useState<string>("retrieving...");
  const [warnings, setWarnings] = React.useState<any[]>([]);
  const [clusters, setClusters] = React.useState<any>({});

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/server/status');
      const data = await res.json();
      if (data.status) setStatus(data.status);
    } catch (e) {
      setStatus("unavailable");
    }
  };

  const fetchIntel = async () => {
    try {
      const [wRes, cRes] = await Promise.all([
        fetch('/api/server/economy/intelligence/validate'),
        fetch('/api/server/economy/intelligence/clusters')
      ]);
      const wData = await wRes.json();
      const cData = await cRes.json();
      setWarnings(wData.warnings || []);
      setClusters(cData || {});
    } catch (e) {
      toast.error("Economy intelligence unavailable");
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/server/nitrado/logs');
      const data = await res.json();
      if (data.files) setLogs(data.files);
    } catch (error) {
      toast.error("Failed to fetch Nitrado logs");
    }
  };

  const fetchContent = async (path: string) => {
    setLoading(true);
    setSelectedLog(path);
    try {
      const res = await fetch('/api/server/nitrado/logs/content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      const data = await res.json();
      if (data.content) setContent(data.content);
    } finally {
      setLoading(false);
    }
  };

  const handlePower = async (action: 'restart' | 'stop') => {
    toast.promise(fetch(`/api/server/server/${action}`, { method: 'POST' }), {
      loading: `${action === 'restart' ? 'RESTARTING' : 'STOPPING'} ENGINE...`,
      success: "Command transmitted to Nitrado API",
      error: "Signal lost. Verify Nitrado credentials."
    });
    setTimeout(fetchStatus, 5000);
  };

  React.useEffect(() => {
    fetchStatus();
    fetchIntel();
    fetchLogs();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <PageContainer>
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-120px)]">
        {/* Left Column: Stats & Logs */}
        <div className="col-span-3 flex flex-col gap-6">
          {/* Power Controls */}
          <GlassCard className="p-4 bg-red-950/10 border-red-500/20">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold tracking-widest text-primary flex items-center gap-2">
                <Activity className="w-3 h-3" />
                ENGINE STATUS
              </h3>
              <Badge variant={status === "started" ? "default" : "destructive"} className="animate-pulse px-1 text-[10px] h-4">
                {status.toUpperCase()}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button size="sm" variant="outline" className="border-green-500/50 hover:bg-green-500/20 text-xs gap-2" onClick={() => handlePower('restart')}>
                <RefreshCw className="w-3 h-3" />
                RESTART
              </Button>
              <Button size="sm" variant="outline" className="border-red-500/50 hover:bg-red-500/20 text-xs gap-2" onClick={() => handlePower('stop')}>
                <Power className="w-3 h-3" />
                STOP
              </Button>
            </div>
          </GlassCard>

          {/* Log Navigation */}
          <GlassCard className="flex-1 overflow-hidden flex flex-col p-0">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <h3 className="text-xs font-bold tracking-widest text-primary flex items-center gap-2">
                <Cloud className="w-3 h-3" />
                CLOUD LOGS
              </h3>
            </div>
            <ScrollArea className="flex-1 bg-black/20">
              <div className="p-2 space-y-1">
                {logs.map((log) => (
                  <Button
                    key={log.path}
                    variant="ghost"
                    className={cn(
                      "w-full justify-between h-8 px-2 text-[10px] font-mono transition-all group",
                      selectedLog === log.path ? "bg-primary/20 text-white" : "text-muted-foreground hover:bg-white/5"
                    )}
                    onClick={() => fetchContent(log.path)}
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <FileText className="w-3 h-3 shrink-0" />
                      <span className="truncate">{log.name}</span>
                    </div>
                    <ChevronRight className={cn("w-3 h-3 transition-transform", selectedLog === log.path ? "rotate-90" : "opacity-0 group-hover:opacity-100")} />
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </GlassCard>
        </div>

        {/* Center Column: Intelligence & Editor */}
        <div className="col-span-6 flex flex-col gap-6">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden">
            <header className="h-12 border-b border-white/5 flex items-center px-4 justify-between bg-black/40">
              <div className="flex items-center gap-4">
                <h2 className="text-xs font-bold tracking-[0.2em] text-primary flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  OPERATIONAL INTELLIGENCE
                </h2>
                {warnings.length > 0 && (
                  <Badge variant="outline" className="text-orange-500 border-orange-500/30 bg-orange-500/10 gap-1 text-[10px]">
                    <AlertTriangle className="w-3 h-3" />
                    {warnings.length} CONFLICTS
                  </Badge>
                )}
              </div>
            </header>

            <div className="flex-1 p-6 overflow-hidden flex flex-col gap-6">
              {/* Warnings Scroller */}
              {warnings.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-[10px] uppercase tracking-widest text-muted-foreground font-bold">Priority Warnings</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {warnings.slice(0, 4).map((w, i) => (
                      <div key={i} className="p-2 rounded bg-orange-500/5 border border-orange-500/10 flex gap-2 items-start">
                        <AlertTriangle className="w-3 h-3 text-orange-500 shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <div className="text-[10px] font-bold text-orange-400 truncate">{w.item}</div>
                          <div className="text-[9px] text-orange-200/60 leading-tight">{w.message}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Smart Clusters */}
              <div className="flex-1 flex flex-col min-h-0">
                <h4 className="text-[10px] uppercase tracking-widest text-muted-foreground font-bold mb-3">Loot Distribution Clusters</h4>
                <ScrollArea className="flex-1 pr-4">
                  <div className="grid grid-cols-2 gap-3">
                    {Object.entries(clusters).map(([name, items]: [string, any]) => (
                      <div key={name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:border-primary/30 transition-colors">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold text-primary font-mono">{name}</span>
                          <Badge className="text-[9px] py-0 h-4 bg-white/5">{items.length} units</Badge>
                        </div>
                        <div className="space-y-1">
                          {items.slice(0, 3).map((item: any) => (
                            <div key={item.name} className="flex justify-between text-[9px] font-mono opacity-60">
                              <span className="truncate max-w-[120px]">{item.name}</span>
                              <span>{item.nominal}/{item.min}</span>
                            </div>
                          ))}
                          {items.length > 3 && (
                            <div className="text-[8px] text-center pt-1 opacity-30 italic">+{items.length - 3} more sub-variants</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* Right Column: Active Content Viewer */}
        <div className="col-span-3 flex flex-col gap-6">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden">
            <div className="p-4 border-b border-white/5 flex items-center justify-between bg-black/40">
              <h3 className="text-xs font-bold tracking-widest text-primary flex items-center gap-2">
                <Terminal className="w-3 h-3" />
                TERMINAL OUTPUT
              </h3>
              {selectedLog && (
                <Button variant="ghost" size="icon" className="h-6 w-6">
                  <Download className="w-3 h-3" />
                </Button>
              )}
            </div>
            <div className="flex-1 p-4 overflow-hidden relative">
              {loading ? (
                <div className="h-full flex flex-col items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                  <span className="text-[9px] text-primary animate-pulse font-mono tracking-tighter">BITSTREAM SYNC...</span>
                </div>
              ) : content ? (
                <ScrollArea className="h-full rounded bg-black/40 p-3 border border-white/5 font-mono text-[9px] leading-tight text-blue-100/60">
                  <pre className="whitespace-pre-wrap">{content}</pre>
                </ScrollArea>
              ) : (
                <div className="h-full flex flex-col items-center justify-center space-y-3 opacity-20">
                  <Box className="w-10 h-10" />
                  <p className="text-[10px] uppercase font-bold tracking-widest">Awaiting Input</p>
                </div>
              )}
            </div>
          </GlassCard>
        </div>
      </div>
    </PageContainer>
  );
}
export default LogisticsPage;
