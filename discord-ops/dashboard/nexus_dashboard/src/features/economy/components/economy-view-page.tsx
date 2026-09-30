"use client";

import * as React from "react";
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from "@/components/ui/button";
import {
    Download,
    Settings2,
    FileText,
    Database,
    LayoutDashboard,
    ChevronRight,
    Search,
    RefreshCw,
    Shield
} from "lucide-react";
import { PageContainer } from '@/components/layout/page-container';
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { EconomyConfigForm } from "@/components/economy/EconomyConfigForm";
import { EconomyFileEditor } from "@/components/economy/EconomyFileEditor";
import { EconomyDiagnostics } from "@/components/economy/EconomyDiagnostics";
import { EconomySmartView } from "@/components/economy/EconomySmartView";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { BrainCircuit, Activity, AlertCircle, Layers } from "lucide-react";
import { useServerConfig } from "@/hooks/use-server-config";

export function EconomyPage() {
    const { config } = useServerConfig();
    const [files, setFiles] = React.useState<string[]>([]);
    const [selectedView, setSelectedView] = React.useState<"global" | "files" | "intel" | "clusters" | "diagnostics">("global");
    const [selectedFile, setSelectedFile] = React.useState<string | null>(null);
    const [loadingFiles, setLoadingFiles] = React.useState(false);
    const [searchQuery, setSearchQuery] = React.useState("");

    const fetchFiles = React.useCallback(async () => {
        setLoadingFiles(true);
        try {
            const res = await fetch('/api/server/mission/files');
            const data = await res.json();
            if (data.files) {
                setFiles(data.files);
            }
        } catch (error) {
            toast.error("Failed to list mission files");
        } finally {
            setLoadingFiles(false);
        }
    }, []);

    React.useEffect(() => {
        fetchFiles();
    }, [fetchFiles]);

    const filteredFiles = React.useMemo(() => {
        return files.filter(f => f.toLowerCase().includes(searchQuery.toLowerCase()));
    }, [files, searchQuery]);

    const handleSelectFile = (file: string) => {
        setSelectedFile(file);
        setSelectedView("files");
    };

    const handleSelectView = (view: typeof selectedView) => {
        setSelectedView(view);
        setSelectedFile(null);
    };

    return (
        <PageContainer>
            <div className="flex bg-black/40 backdrop-blur-2xl h-[calc(100vh-120px)] overflow-hidden rounded-xl border border-white/5 shadow-2xl ring-1 ring-white/5">
                {/* Left Sidebar - File Explorer */}
                <div className="w-72 border-r border-white/5 flex flex-col bg-neutral-900/50">
                    <div className="p-4 border-b border-white/5 space-y-4">
                        <div className="flex items-center gap-2 text-primary">
                            <BrainCircuit className="w-5 h-5" />
                            <h2 className="font-semibold tracking-tight">Economy Intel</h2>
                        </div>
                        <div className="relative">
                            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Filter mission store..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-8 h-9 bg-black/20 border-white/10 focus-visible:ring-primary/50 text-xs"
                            />
                        </div>
                    </div>
                    <ScrollArea className="flex-1">
                        <div className="p-2 space-y-1">
                            <Button
                                variant="ghost"
                                className={cn(
                                    "w-full justify-start h-10 px-3 transition-all duration-200",
                                    selectedView === "global"
                                        ? "bg-primary/20 text-primary shadow-[0_0_15px_-3px_var(--primary)] border border-primary/20"
                                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                )}
                                onClick={() => handleSelectView("global")}
                            >
                                <LayoutDashboard className="w-4 h-4 mr-3" />
                                <span className="font-medium">Global Settings</span>
                            </Button>

                            <div className="pt-4 pb-2">
                                <h3 className="px-3 text-[10px] font-bold text-muted-foreground/70 mb-2 uppercase tracking-widest flex items-center gap-2">
                                    <span className="w-1 h-1 rounded-full bg-cyan-500/50" />
                                    Intelligence
                                </h3>
                                <Button
                                    variant="ghost"
                                    className={cn(
                                        "w-full justify-start h-10 px-3 transition-all duration-200",
                                        selectedView === "clusters"
                                            ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/20 shadow-[0_0_15px_-3px_rgba(6,182,212,0.5)]"
                                            : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                    )}
                                    onClick={() => handleSelectView("clusters")}
                                >
                                    <Layers className="w-4 h-4 mr-3" />
                                    <span className="font-medium">Smart Clustering</span>
                                </Button>
                                <Button
                                    variant="ghost"
                                    className={cn(
                                        "w-full justify-start h-10 px-3 transition-all duration-200",
                                        selectedView === "diagnostics"
                                            ? "bg-red-500/20 text-red-400 border border-red-500/20 shadow-[0_0_15px_-3px_rgba(239,68,68,0.5)]"
                                            : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                    )}
                                    onClick={() => handleSelectView("diagnostics")}
                                >
                                    <AlertCircle className="w-4 h-4 mr-3" />
                                    <span className="font-medium">Audit report</span>
                                </Button>
                            </div>

                            <div className="pt-4 pb-2">
                                <h3 className="px-3 text-[10px] font-bold text-muted-foreground/70 mb-2 uppercase tracking-widest flex items-center gap-2">
                                    <span className="w-1 h-1 rounded-full bg-amber-500/50" />
                                    Mission Store
                                </h3>
                                <div className="space-y-0.5">
                                    {filteredFiles.map((file) => (
                                        <Button
                                            key={file}
                                            variant="ghost"
                                            className={cn(
                                                "w-full justify-start h-8 px-3 font-mono text-xs transition-colors",
                                                selectedFile === file
                                                    ? "bg-white/10 text-white border-l-2 border-primary rounded-l-none"
                                                    : "text-muted-foreground/80 hover:text-white hover:bg-white/5"
                                            )}
                                            onClick={() => handleSelectFile(file)}
                                        >
                                            <FileText className={cn("w-3 h-3 mr-3", file.includes(".json") ? "text-yellow-500" : "text-blue-500")} />
                                            {file}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </ScrollArea>
                    <div className="p-3 border-t border-white/5 bg-black/20 text-[10px] text-muted-foreground flex justify-between">
                        <span className="flex items-center gap-1.5 font-bold tracking-tighter text-white/50 uppercase">
                            <Shield className="w-3 h-3 text-green-500" />
                            v1.28 INTEGRATED
                        </span>
                        <span>{files.length} Modules</span>
                    </div>
                </div>

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0 bg-transparent relative">
                    {/* Atmospheric Background */}
                    <div className="absolute inset-0 bg-gradient-to-br from-purple-900/5 via-transparent to-amber-900/5 pointer-events-none" />
                    <div className="absolute inset-0 bg-[url('/grid-pattern.svg')] opacity-5 pointer-events-none" />

                    <header className="h-14 border-b border-white/5 flex items-center px-6 justify-between bg-black/20 backdrop-blur-sm z-10">
                        <div className="flex items-center gap-2 text-sm">
                            <span className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Economic MildlyAwesome</span>
                            <ChevronRight className="w-4 h-4 text-muted-foreground/50" />
                            <span className={cn("font-medium", "text-foreground capitalize")}>
                                {selectedFile || selectedView}
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            {selectedView === "clusters" && <Badge variant="outline" className="text-[10px] border-cyan-500/20 text-cyan-400">Semantic Engine ON</Badge>}
                            {selectedView === "diagnostics" && <Badge variant="outline" className="text-[10px] border-red-500/20 text-red-400">Deep Audit Active</Badge>}
                            <span className="text-xs px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-500 font-medium tracking-tight">
                                {config?.server_name || 'Server'} Config Active
                            </span>
                        </div>
                    </header>


                    <main className="flex-1 overflow-hidden p-6 relative z-10">
                        {renderContent()}
                    </main>
                </div>
            </div>
        </PageContainer>
    );

    function renderContent() {
        switch (selectedView) {
            case "global":
                return (
                    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="space-y-2 mb-8">
                            <h1 className="text-4xl font-bold tracking-tight text-white drop-shadow-lg">
                                Economic <span className="text-primary italic">MildlyAwesome</span>
                            </h1>
                            <p className="text-muted-foreground text-lg max-w-2xl">
                                Configure high-level multipliers and server limits.
                                <span className="block mt-1 text-sm text-cyan-500/80 font-mono">INTELLIGENCE LAYER ACTIVE: Monitoring 20,000+ spawn points.</span>
                            </p>
                        </div>
                        <GlassCard className="p-8 border-white/10 shadow-2xl bg-black/40 backdrop-blur-xl ring-1 ring-white/5 relative overflow-hidden group">
                            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-transparent to-primary/20 opacity-0 group-hover:opacity-100 transition-opacity duration-1000 blur-xl" />
                            <div className="relative">
                                <EconomyConfigForm />
                            </div>
                        </GlassCard>
                    </div>
                );
            case "files":
                return selectedFile ? (
                    <div className="h-full flex flex-col animate-in fade-in duration-300">
                        <EconomyFileEditor filename={selectedFile} />
                    </div>
                ) : null;
            case "clusters":
                return (
                    <div className="max-w-5xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">
                        <EconomySmartView />
                    </div>
                );
            case "diagnostics":
                return (
                    <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500 h-full">
                        <EconomyDiagnostics />
                    </div>
                );
            default:
                return null;
        }
    }
}

export default EconomyPage;
