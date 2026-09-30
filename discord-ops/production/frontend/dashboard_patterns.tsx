"use client"

import React, { useEffect, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { io, Socket } from "socket.io-client"

// Production Pattern: Real-time Killfeed Table with Shadcn
// This pattern uses Socket.io to receive delta updates and keeps only the last 50 events.

interface KillEvent {
    id: string
    timestamp: string
    killer: string
    victim: string
    weapon: string
    distance: string
    location: string
}

export function RealTimeKillfeed() {
    const [events, setEvents] = useState<KillEvent[]>([])
    const [socket, setSocket] = useState<Socket | null>(null)

    useEffect(() => {
        // Connect to the backend production websocket gateway
        const s = io(process.env.NEXT_PUBLIC_WS_URL || "http://localhost:43200", {
            path: "/ws/killfeed"
        })

        s.on("kill", (event: KillEvent) => {
            setEvents(prev => [event, ...prev.slice(0, 49)])
        })

        setSocket(s)
        return () => { s.disconnect() }
    }, [])

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    Live Killfeed
                    <Badge variant="outline" className="animate-pulse bg-red-500/10 text-red-500">
                        Live
                    </Badge>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Time</TableHead>
                            <TableHead>Killer</TableHead>
                            <TableHead>Victim</TableHead>
                            <TableHead>Weapon</TableHead>
                            <TableHead>Distance</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {events.map((event) => (
                            <TableRow key={event.id} className="animate-in fade-in slide-in-from-top-1">
                                <TableCell className="font-mono text-xs">{event.timestamp}</TableCell>
                                <TableCell className="font-bold text-blue-400">{event.killer}</TableCell>
                                <TableCell className="font-bold text-red-400">{event.victim}</TableCell>
                                <TableCell>
                                    <span className="flex items-center gap-2">
                                        {/* Pattern donor: Weapon icon placeholder */}
                                        <span className="opacity-50">🔫</span> {event.weapon}
                                    </span>
                                </TableCell>
                                <TableCell>{event.distance}m</TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    )
}
