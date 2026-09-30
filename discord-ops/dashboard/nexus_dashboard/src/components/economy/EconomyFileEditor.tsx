"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Save, RefreshCw, FileCode, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

interface EconomyFileEditorProps {
    filename: string;
}

export function EconomyFileEditor({ filename }: EconomyFileEditorProps) {
    const [content, setContent] = React.useState<string>("");
    const [loading, setLoading] = React.useState(false);
    const [saving, setSaving] = React.useState(false);
    const textareaRef = React.useRef<HTMLTextAreaElement>(null);

    const fetchFile = React.useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`/api/server/mission/files/${filename}`);
            const data = await res.json();
            if (data.content) {
                setContent(data.content);
            } else {
                toast.error(`Failed to load ${filename}`);
            }
        } catch (error) {
            toast.error(`Error fetching ${filename}`);
        } finally {
            setLoading(false);
        }
    }, [filename]);

    const saveFile = async () => {
        setSaving(true);
        try {
            const res = await fetch(`/api/server/mission/files/${filename}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content, backup: true }),
            });
            const data = await res.json();
            
            if (data.status === "success") {
                toast.success(`Saved ${filename}`);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Failed to save");
        } finally {
            setSaving(false);
        }
    };

    const copyToClipboard = () => {
        navigator.clipboard.writeText(content);
        toast.success("Copied to clipboard");
    };

    React.useEffect(() => {
        fetchFile();
    }, [fetchFile]);

    return (
        <div className="flex flex-col h-full gap-4">
            <div className="flex items-center justify-between p-4 border rounded-lg bg-background/50 backdrop-blur-sm">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-md bg-primary/10">
                        <FileCode className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                        <h3 className="font-mono text-sm font-semibold">{filename}</h3>
                        <p className="text-xs text-muted-foreground">
                            {content.length} bytes • XML
                        </p>
                    </div>
                </div>
                <div className="flex gap-2">
                     <Button variant="outline" size="sm" onClick={copyToClipboard} title="Copy Content">
                        <Copy className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" onClick={fetchFile} disabled={loading} title="Refresh">
                        <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                    </Button>
                    <Button onClick={saveFile} disabled={saving || loading} size="sm">
                        <Save className="w-4 h-4 mr-2" />
                        {saving ? "Saving..." : "Save Changes"}
                    </Button>
                </div>
            </div>

            <div className="flex-1 relative min-h-[500px] border rounded-lg overflow-hidden bg-[#0d0d0d]">
                <Textarea
                    ref={textareaRef}
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="absolute inset-0 w-full h-full p-4 font-mono text-xs leading-relaxed resize-none bg-transparent border-0 focus-visible:ring-0 text-gray-300 selection:bg-primary/20"
                    spellCheck={false}
                />
            </div>
        </div>
    );
}
export default EconomyFileEditor;

export { EconomyFileEditor };
