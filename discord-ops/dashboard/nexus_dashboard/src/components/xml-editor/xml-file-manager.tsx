'use client';

import { useState, useEffect } from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { Loader2, Save, FileText, RefreshCw, GitCompare, RotateCcw, Eye, Code2, Split, AlertTriangle, CheckCircle2, Info, Search, Download, BarChart3, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { XmlSyntaxHighlighter } from './xml-syntax-highlighter';
import { validateXml, getXmlStats, ValidationResult } from '@/lib/xml-utils';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface XmlFileManagerProps {
    filter: string | RegExp;
    title: string;
}

export function XmlFileManager({ filter, title }: XmlFileManagerProps) {
    const [files, setFiles] = useState<string[]>([]);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState('');
    const [vanillaContent, setVanillaContent] = useState<string | null>(null);
    const [hasVanilla, setHasVanilla] = useState(false);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [initialLoading, setInitialLoading] = useState(true);
    const [viewMode, setViewMode] = useState<'edit' | 'compare' | 'split'>('edit');
    const [isDirty, setIsDirty] = useState(false);
    const [validation, setValidation] = useState<ValidationResult | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [showStats, setShowStats] = useState(false);

    const fetchFiles = async () => {
        try {
            const res = await fetch('/api/files/xml');
            const allFiles = await res.json();

            let filteredFiles = allFiles;
            if (typeof filter === 'string') {
                filteredFiles = allFiles.filter((f: string) => f.includes(filter));
            } else if (filter instanceof RegExp) {
                filteredFiles = allFiles.filter((f: string) => filter.test(f));
            }

            setFiles(filteredFiles.sort());
        } catch (error) {
            toast.error('Failed to load file list');
        } finally {
            setInitialLoading(false);
        }
    };

    useEffect(() => {
        fetchFiles();
    }, [filter]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Ctrl+S or Cmd+S to save
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                if (selectedFile && !saving && !loading) {
                    saveFile();
                }
            }
            // Ctrl+F or Cmd+F to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                e.preventDefault();
                const searchInput = document.querySelector('input[placeholder="Search in file..."]') as HTMLInputElement;
                searchInput?.focus();
            }
            // Escape to clear search
            if (e.key === 'Escape' && searchQuery) {
                setSearchQuery('');
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [selectedFile, saving, loading, searchQuery]);

    const loadFile = async (filename: string) => {
        setLoading(true);
        setIsDirty(false);
        try {
            // Load current file
            const res = await fetch(`/api/files/xml?file=${filename}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            setFileContent(data.content);
            setSelectedFile(filename);

            // Try to load vanilla version
            try {
                const vanillaRes = await fetch(`/api/files/xml/vanilla?file=${filename}`);
                const vanillaData = await vanillaRes.json();
                if (vanillaData.available) {
                    setVanillaContent(vanillaData.content);
                    setHasVanilla(true);
                } else {
                    setVanillaContent(null);
                    setHasVanilla(false);
                }
            } catch (e) {
                setVanillaContent(null);
                setHasVanilla(false);
            }

            // Validate loaded content
            const validationResult = validateXml(data.content);
            setValidation(validationResult);
        } catch (e) {
            toast.error('Failed to load file content');
        } finally {
            setLoading(false);
        }
    };

    // Validate on content change
    useEffect(() => {
        if (fileContent && selectedFile) {
            const validationResult = validateXml(fileContent);
            setValidation(validationResult);
        }
    }, [fileContent, selectedFile]);

    const saveFile = async () => {
        if (!selectedFile) return;
        setSaving(true);
        try {
            const res = await fetch('/api/files/xml', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file: selectedFile, content: fileContent })
            });

            if (!res.ok) throw new Error('Failed to save');

            toast.success('File saved successfully');
            setIsDirty(false);
        } catch (e) {
            toast.error('Failed to save file');
        } finally {
            setSaving(false);
        }
    };

    const resetToVanilla = () => {
        if (vanillaContent) {
            setFileContent(vanillaContent);
            setIsDirty(true);
            toast.success('Reset to vanilla version');
        }
    };

    const getDiffStats = () => {
        if (!hasVanilla || !vanillaContent) return null;
        const currentLines = fileContent.split('\n').length;
        const vanillaLines = vanillaContent.split('\n').length;
        const diffLines = Math.abs(currentLines - vanillaLines);
        const isModified = fileContent !== vanillaContent;
        return { currentLines, vanillaLines, diffLines, isModified };
    };

    const exportDiff = () => {
        if (!selectedFile || !hasVanilla || !vanillaContent) return;

        const diffContent = `# Diff Report: ${selectedFile}\n` +
            `Generated: ${new Date().toISOString()}\n\n` +
            `## Statistics\n` +
            `- Current Lines: ${fileContent.split('\n').length}\n` +
            `- Vanilla Lines: ${vanillaContent.split('\n').length}\n` +
            `- Modified: ${fileContent !== vanillaContent ? 'Yes' : 'No'}\n\n` +
            `## Current Content\n\`\`\`xml\n${fileContent}\n\`\`\`\n\n` +
            `## Vanilla Content\n\`\`\`xml\n${vanillaContent}\n\`\`\`\n`;

        const blob = new Blob([diffContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${selectedFile.replace('.xml', '')}_diff.md`;
        a.click();
        URL.revokeObjectURL(url);
        toast.success('Diff exported successfully');
    };

    const highlightSearch = (text: string) => {
        if (!searchQuery) return text;
        const regex = new RegExp(`(${searchQuery})`, 'gi');
        return text.replace(regex, '⟪$1⟫');
    };

    const diffStats = getDiffStats();

    return (
        <div className="space-y-6 h-[calc(100vh-100px)] flex flex-col">
            <div className="flex justify-between items-center shrink-0">
                <div className="flex items-center gap-3">
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-primary to-primary/50 bg-clip-text text-transparent">
                        {title}
                    </h1>
                    {diffStats?.isModified && (
                        <Badge variant="outline" className="border-amber-500/30 text-amber-500 text-xs">
                            Modified
                        </Badge>
                    )}
                    {isDirty && (
                        <Badge variant="outline" className="border-orange-500/30 text-orange-500 text-xs">
                            Unsaved
                        </Badge>
                    )}
                    {validation && !validation.valid && (
                        <Badge variant="outline" className="border-red-500/30 text-red-500 text-xs flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            {validation.errors.length} Error{validation.errors.length > 1 ? 's' : ''}
                        </Badge>
                    )}
                    {validation && validation.valid && validation.warnings.length > 0 && (
                        <Badge variant="outline" className="border-yellow-500/30 text-yellow-500 text-xs flex items-center gap-1">
                            <Info className="h-3 w-3" />
                            {validation.warnings.length} Warning{validation.warnings.length > 1 ? 's' : ''}
                        </Badge>
                    )}
                    {validation && validation.valid && validation.warnings.length === 0 && (
                        <Badge variant="outline" className="border-green-500/30 text-green-500 text-xs flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Valid
                        </Badge>
                    )}
                </div>
                <div className="flex gap-2 items-center">
                    {selectedFile && (
                        <>
                            <div className="relative">
                                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    placeholder="Search in file..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-8 h-9 w-48 bg-black/20 border-white/10"
                                />
                                {searchQuery && (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                                        onClick={() => setSearchQuery('')}
                                    >
                                        <X className="h-3 w-3" />
                                    </Button>
                                )}
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShowStats(!showStats)}
                                className={cn(showStats && "bg-primary/10 border-primary/30")}
                            >
                                <BarChart3 className="h-4 w-4 mr-2" />
                                Stats
                            </Button>
                            {hasVanilla && (
                                <Button variant="outline" size="sm" onClick={exportDiff}>
                                    <Download className="h-4 w-4 mr-2" />
                                    Export Diff
                                </Button>
                            )}
                        </>
                    )}
                    <Button variant="outline" size="sm" onClick={fetchFiles} disabled={initialLoading}>
                        <RefreshCw className={cn("h-4 w-4 mr-2", initialLoading && "animate-spin")} />
                        Refresh
                    </Button>
                    {selectedFile && hasVanilla && (
                        <Button variant="outline" size="sm" onClick={resetToVanilla}>
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Reset to Vanilla
                        </Button>
                    )}
                    {selectedFile && (
                        <Button onClick={saveFile} disabled={saving || loading} className="min-w-[100px]">
                            {saving ? (
                                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                            ) : (
                                <Save className="h-4 w-4 mr-2" />
                            )}
                            Save
                        </Button>
                    )}
                </div>
            </div>

            {/* Stats Panel */}
            {selectedFile && showStats && (() => {
                const stats = getXmlStats(fileContent);
                return (
                    <GlassCard className="p-4 border-primary/10">
                        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-primary">{stats.lines}</div>
                                <div className="text-xs text-muted-foreground">Lines</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-400">{stats.elements}</div>
                                <div className="text-xs text-muted-foreground">Elements</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-400">{stats.attributes}</div>
                                <div className="text-xs text-muted-foreground">Attributes</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-purple-400">{stats.comments}</div>
                                <div className="text-xs text-muted-foreground">Comments</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-amber-400">{stats.sizeKb}</div>
                                <div className="text-xs text-muted-foreground">KB</div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-cyan-400">
                                    {diffStats ? `${diffStats.diffLines > 0 ? '+' : ''}${diffStats.currentLines - diffStats.vanillaLines}` : 'N/A'}
                                </div>
                                <div className="text-xs text-muted-foreground">vs Vanilla</div>
                            </div>
                        </div>
                    </GlassCard>
                );
            })()}

            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 flex-1 min-h-0">
                <GlassCard className="md:col-span-1 flex flex-col overflow-hidden border-primary/10">
                    <div className="p-4 border-b border-white/5 bg-white/5">
                        <h2 className="font-semibold flex items-center gap-2">
                            <FileText className="h-4 w-4 text-primary" />
                            Files ({files.length})
                        </h2>
                    </div>
                    <ScrollArea className="flex-1">
                        <div className="p-2 space-y-1">
                            {files.map((file) => (
                                <Button
                                    key={file}
                                    variant={selectedFile === file ? "secondary" : "ghost"}
                                    className={cn(
                                        "w-full justify-start text-xs truncate h-9",
                                        selectedFile === file && "bg-primary/20 hover:bg-primary/30 text-primary-foreground"
                                    )}
                                    onClick={() => loadFile(file)}
                                >
                                    {file.replace('custom/', '')}
                                </Button>
                            ))}
                        </div>
                    </ScrollArea>
                </GlassCard>

                <GlassCard className="md:col-span-3 flex flex-col overflow-hidden border-primary/10">
                    <div className="p-4 border-b border-white/5 bg-white/5 flex justify-between items-center">
                        <div className="flex items-center gap-3">
                            <span className="text-sm font-medium text-muted-foreground">
                                {selectedFile || 'Select a file to edit'}
                            </span>
                            {diffStats && (
                                <div className="flex items-center gap-2 text-xs">
                                    <span className="text-muted-foreground">
                                        {diffStats.currentLines} lines
                                    </span>
                                    {diffStats.isModified && (
                                        <span className="text-amber-500">
                                            ({diffStats.diffLines > 0 ? '+' : ''}{diffStats.currentLines - diffStats.vanillaLines} from vanilla)
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            {loading && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                            {selectedFile && hasVanilla && (
                                <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)} className="w-auto">
                                    <TabsList className="h-8">
                                        <TabsTrigger value="edit" className="text-xs px-2 h-7">
                                            <Code2 className="h-3 w-3 mr-1" />
                                            Edit
                                        </TabsTrigger>
                                        <TabsTrigger value="compare" className="text-xs px-2 h-7">
                                            <Eye className="h-3 w-3 mr-1" />
                                            Compare
                                        </TabsTrigger>
                                        <TabsTrigger value="split" className="text-xs px-2 h-7">
                                            <Split className="h-3 w-3 mr-1" />
                                            Split
                                        </TabsTrigger>
                                    </TabsList>
                                </Tabs>
                            )}
                        </div>
                    </div>
                    <div className="flex-1 min-h-0 bg-black/20">
                        {selectedFile ? (
                            <>
                                {viewMode === 'edit' && (
                                    <div className="h-full flex flex-col">
                                        {validation && (validation.errors.length > 0 || validation.warnings.length > 0) && (
                                            <div className="p-3 space-y-2 border-b border-white/5 bg-black/30 max-h-48 overflow-auto">
                                                {validation.errors.map((error, idx) => (
                                                    <Alert key={`error-${idx}`} variant="destructive" className="py-2">
                                                        <AlertTriangle className="h-4 w-4" />
                                                        <AlertTitle className="text-sm">Error</AlertTitle>
                                                        <AlertDescription className="text-xs">{error}</AlertDescription>
                                                    </Alert>
                                                ))}
                                                {validation.warnings.map((warning, idx) => (
                                                    <Alert key={`warning-${idx}`} className="py-2 border-yellow-500/30 text-yellow-500">
                                                        <Info className="h-4 w-4" />
                                                        <AlertTitle className="text-sm">Warning</AlertTitle>
                                                        <AlertDescription className="text-xs text-yellow-400/80">{warning}</AlertDescription>
                                                    </Alert>
                                                ))}
                                            </div>
                                        )}
                                        <Textarea
                                            value={fileContent}
                                            onChange={(e) => {
                                                setFileContent(e.target.value);
                                                setIsDirty(true);
                                            }}
                                            className="flex-1 w-full resize-none rounded-none border-0 bg-transparent p-4 font-mono text-sm focus-visible:ring-0 leading-relaxed text-blue-100/90"
                                            spellCheck={false}
                                        />
                                    </div>
                                )}
                                {viewMode === 'compare' && hasVanilla && (
                                    <div className="h-full overflow-auto p-4">
                                        <div className="grid grid-cols-2 gap-4 h-full">
                                            <div className="border border-green-500/20 rounded-lg overflow-hidden bg-green-500/5">
                                                <h3 className="text-xs font-semibold text-green-400 p-3 border-b border-green-500/20 flex items-center gap-2">
                                                    <GitCompare className="h-3 w-3" />
                                                    Vanilla ({vanillaContent?.split('\n').length} lines)
                                                </h3>
                                                <ScrollArea className="h-[calc(100%-2.5rem)]">
                                                    <XmlSyntaxHighlighter code={vanillaContent || ''} />
                                                </ScrollArea>
                                            </div>
                                            <div className="border border-amber-500/20 rounded-lg overflow-hidden bg-amber-500/5">
                                                <h3 className="text-xs font-semibold text-amber-400 p-3 border-b border-amber-500/20 flex items-center gap-2">
                                                    <FileText className="h-3 w-3" />
                                                    Current ({fileContent.split('\n').length} lines)
                                                </h3>
                                                <ScrollArea className="h-[calc(100%-2.5rem)]">
                                                    <XmlSyntaxHighlighter code={fileContent} />
                                                </ScrollArea>
                                            </div>
                                        </div>
                                    </div>
                                )}
                                {viewMode === 'split' && hasVanilla && (
                                    <div className="h-full flex">
                                        <div className="flex-1 border-r border-white/5">
                                            <div className="h-8 border-b border-white/5 px-3 flex items-center bg-white/5">
                                                <span className="text-xs text-muted-foreground">Current (Editable)</span>
                                            </div>
                                            <Textarea
                                                value={fileContent}
                                                onChange={(e) => {
                                                    setFileContent(e.target.value);
                                                    setIsDirty(true);
                                                }}
                                                className="h-[calc(100%-2rem)] w-full resize-none rounded-none border-0 bg-transparent p-4 font-mono text-sm focus-visible:ring-0 leading-relaxed text-blue-100/90"
                                                spellCheck={false}
                                            />
                                        </div>
                                        <div className="flex-1">
                                            <div className="h-8 border-b border-white/5 px-3 flex items-center bg-white/5">
                                                <span className="text-xs text-muted-foreground">Vanilla (Read-only)</span>
                                            </div>
                                            <ScrollArea className="h-[calc(100%-2rem)]">
                                                <pre className="p-4 font-mono text-sm text-green-100/70 whitespace-pre-wrap">
                                                    {vanillaContent}
                                                </pre>
                                            </ScrollArea>
                                        </div>
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="h-full flex items-center justify-center text-muted-foreground flex-col gap-4">
                                <FileText className="h-12 w-12 opacity-20" />
                                <p>Select a file from the list to start editing</p>
                            </div>
                        )}
                    </div>
                </GlassCard>
            </div>
        </div>
    );
}
export default XmlFileManager;

export { XmlFileManager };
