"use client"

import * as React from "react"
import { ReloadIcon, HandIcon, CircleBackslashIcon } from "@radix-ui/react-icons"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { GlassCard } from "@/components/ui/glass-card"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function ServerControlCard() {
    const [loading, setLoading] = React.useState(false)
    const [banGamertag, setBanGamertag] = React.useState("")

    async function handleServerAction(action: 'restart' | 'stop') {
        if (!confirm(`Are you sure you want to ${action} the server?`)) return

        setLoading(true)
        try {
            const res = await fetch('/api/server/action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action }),
            })
            const data = await res.json()

            if (!res.ok) throw new Error(data.error || 'Failed to execute action')

            toast.success(`Server ${action} command sent successfully`, {
                description: data.message || "The server is processing your request."
            })
        } catch (error) {
            toast.error('Operation Failed', {
                description: error instanceof Error ? error.message : "Unknown error"
            })
        } finally {
            setLoading(false)
        }
    }

    async function handleBan() {
        if (!banGamertag.trim()) return
        if (!confirm(`Ban player ${banGamertag}?`)) return

        setLoading(true)
        try {
            const res = await fetch('/api/server/ban', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gamertag: banGamertag }),
            })
            const data = await res.json()

            if (!res.ok) throw new Error(data.error || 'Failed to ban player')

            toast.success(`Player banned`, {
                description: data.message || `User ${banGamertag} has been added to ban list.`
            })
            setBanGamertag("")
        } catch (error) {
            toast.error('Ban Failed', {
                description: error instanceof Error ? error.message : "Unknown error"
            })
        } finally {
            setLoading(false)
        }
    }

    return (
        <GlassCard className="w-full h-full p-0">
            <CardHeader>
                <CardTitle className="text-xl text-primary flex items-center gap-2">
                    <ReloadIcon className="w-5 h-5" /> Server Operations
                </CardTitle>
                <CardDescription>
                    Execute heavy administrative tasks on the Nitrado server.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Tabs defaultValue="actions" className="w-full">
                    <TabsList className="grid w-full grid-cols-2 bg-black/40">
                        <TabsTrigger value="actions">Power</TabsTrigger>
                        <TabsTrigger value="moderation">Moderation</TabsTrigger>
                    </TabsList>

                    <TabsContent value="actions" className="space-y-4 mt-4">
                        <div className="flex flex-col gap-4">
                            <Button
                                variant="outline"
                                className="w-full border-yellow-500/50 hover:bg-yellow-500/10 hover:text-yellow-400 text-yellow-500 transition-all font-mono"
                                onClick={() => handleServerAction('restart')}
                                disabled={loading}
                            >
                                <ReloadIcon className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                                Restart Server
                            </Button>
                            <Button
                                variant="destructive"
                                className="w-full bg-red-900/20 hover:bg-red-900/40 border border-red-900 text-red-500 font-mono"
                                onClick={() => handleServerAction('stop')}
                                disabled={loading}
                            >
                                <HandIcon className="mr-2 h-4 w-4" />
                                Stop Server
                            </Button>
                        </div>
                    </TabsContent>

                    <TabsContent value="moderation" className="space-y-4 mt-4">
                        <div className="grid w-full gap-2">
                            <Label htmlFor="gamertag">Ban Player</Label>
                            <div className="flex w-full gap-2">
                                <Input
                                    id="gamertag"
                                    placeholder="Gamertag / User ID"
                                    value={banGamertag}
                                    onChange={(e) => setBanGamertag(e.target.value)}
                                    disabled={loading}
                                    className="font-mono bg-black/20"
                                />
                                <Button
                                    type="submit"
                                    className="bg-destructive hover:bg-destructive/80 text-white"
                                    onClick={handleBan}
                                    disabled={loading || !banGamertag.trim()}
                                >
                                    <CircleBackslashIcon className="w-4 h-4 mr-2" />
                                    Ban
                                </Button>
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">
                                Banning adds the ID to the server's generic ban list. Requires restart to apply fully? (Verify)
                            </p>
                        </div>
                    </TabsContent>
                </Tabs>
            </CardContent>
        </GlassCard>
    )
}
export default ServerControlCard;

export { ServerControlCard };
