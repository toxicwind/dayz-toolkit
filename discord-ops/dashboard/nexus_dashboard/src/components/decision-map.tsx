'use client';

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlassCard } from './ui/glass-card';
import { Activity, AlertCircle, CheckCircle, XCircle, Wifi, WifiOff } from 'lucide-react';
import { ServiceDiagnosticsModal } from './service-diagnostics-modal';

interface Node {
    id: string;
    label: string;
    type: string;
    category: string;
    x: number;
    y: number;
    color: string;
    description: string;
}

interface Connection {
    from: string;
    to: string;
    type: string;
    label: string;
}

interface Topology {
    nodes: Node[];
    connections: Connection[];
    categories: Record<string, { label: string; color: string }>;
}

interface ServiceHealth {
    status: 'healthy' | 'degraded' | 'error' | 'offline';
    latency?: number;
    uptime?: number;
    lastCheck: string;
    errorCount?: number;
    lastActivity?: string;
    message?: string;
}

interface SystemHealth {
    services: Record<string, ServiceHealth>;
    overall: 'healthy' | 'degraded' | 'error' | 'offline';
    timestamp: string;
}

const STATUS_COLORS = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    error: '#ef4444',
    offline: '#6b7280'
};

const STATUS_ICONS = {
    healthy: CheckCircle,
    degraded: AlertCircle,
    error: XCircle,
    offline: WifiOff
};

export function DecisionMap() {
    const [topology, setTopology] = useState<Topology | null>(null);
    const [health, setHealth] = useState<SystemHealth | null>(null);
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [hoveredNode, setHoveredNode] = useState<string | null>(null);

    // Fetch topology on mount
    useEffect(() => {
        fetch('/api/system/topology')
            .then(res => res.json())
            .then(data => setTopology(data))
            .catch(err => console.error('Failed to fetch topology:', err));
    }, []);

    // Poll health status every 5 seconds
    useEffect(() => {
        const fetchHealth = () => {
            fetch('/api/system/health')
                .then(res => res.json())
                .then(data => setHealth(data))
                .catch(err => console.error('Failed to fetch health:', err));
        };

        fetchHealth();
        const interval = setInterval(fetchHealth, 5000);
        return () => clearInterval(interval);
    }, []);

    if (!topology) {
        return (
            <GlassCard className="p-8 h-[500px] relative overflow-hidden flex items-center justify-center" opacity={5}>
                <div className="flex items-center gap-3 text-neutral-400">
                    <Activity className="w-5 h-5 animate-spin" />
                    <span>Loading system topology...</span>
                </div>
            </GlassCard>
        );
    }

    const getNodeStatus = (nodeId: string): ServiceHealth['status'] => {
        return health?.services[nodeId]?.status || 'offline';
    };

    const getNodeColor = (nodeId: string): string => {
        const status = getNodeStatus(nodeId);
        return STATUS_COLORS[status];
    };

    const getNodeHealth = (nodeId: string): ServiceHealth | undefined => {
        return health?.services[nodeId];
    };

    return (
        <GlassCard className="p-8 h-[500px] relative overflow-hidden" opacity={5}>
            <div className="flex justify-between items-center mb-8">
                <h3 className="text-xl font-bold text-white tracking-widest uppercase">System Activity Map</h3>
                <div className="flex gap-4 items-center">
                    {health && (
                        <div className="flex items-center gap-2">
                            {health.overall === 'healthy' ? (
                                <Wifi className="w-4 h-4 text-green-500" />
                            ) : (
                                <WifiOff className="w-4 h-4 text-red-500" />
                            )}
                            <span className="text-xs text-neutral-400 uppercase">
                                {health.overall}
                            </span>
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-neutral-400">Live Ops</span>
                    </div>
                </div>
            </div>

            <div className="relative w-full h-[350px]">
                {/* Connections */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
                    <defs>
                        <marker
                            id="arrowhead"
                            markerWidth="10"
                            markerHeight="10"
                            refX="9"
                            refY="3"
                            orient="auto"
                        >
                            <polygon points="0 0, 10 3, 0 6" fill="rgba(255, 255, 255, 0.3)" />
                        </marker>
                    </defs>
                    {topology.connections.map((conn, i) => {
                        const from = topology.nodes.find(n => n.id === conn.from);
                        const to = topology.nodes.find(n => n.id === conn.to);
                        if (!from || !to) return null;

                        const fromStatus = getNodeStatus(from.id);
                        const toStatus = getNodeStatus(to.id);
                        const isActive = fromStatus === 'healthy' && toStatus === 'healthy';

                        return (
                            <g key={i}>
                                <motion.line
                                    x1={`${from.x}%`}
                                    y1={`${from.y}%`}
                                    x2={`${to.x}%`}
                                    y2={`${to.y}%`}
                                    stroke={isActive ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.05)'}
                                    strokeWidth={conn.type === 'bidirectional' ? '3' : '2'}
                                    strokeDasharray={conn.type === 'dependency' ? '5,5' : undefined}
                                    markerEnd={conn.type !== 'bidirectional' ? 'url(#arrowhead)' : undefined}
                                    initial={{ pathLength: 0, opacity: 0 }}
                                    animate={{ pathLength: 1, opacity: 1 }}
                                    transition={{ duration: 1.5, delay: i * 0.1 }}
                                />
                                {/* Data flow particles */}
                                <motion.circle
                                    r="3"
                                    fill="#3b82f6"
                                    animate={{
                                        offsetDistance: "100%"
                                    }}
                                    transition={{
                                        duration: 3,
                                        repeat: Infinity,
                                        ease: 'linear',
                                        delay: i * 0.5
                                    }}
                                    style={{
                                        offsetPath: `path('M ${from.x} ${from.y} L ${to.x} ${to.y}')`,
                                        offsetRotate: '0deg',
                                        // @ts-ignore - offsetDistance is valid in style but missing in types
                                        offsetDistance: "0%"
                                    }}
                                >
                                </motion.circle>
                            </g>
                        );
                    })}
                </svg>

                {/* Nodes */}
                {topology.nodes.map((node) => {
                    const nodeHealth = getNodeHealth(node.id);
                    const status = getNodeStatus(node.id);
                    const StatusIcon = STATUS_ICONS[status];
                    const isHovered = hoveredNode === node.id;
                    const isSelected = selectedNode === node.id;

                    return (
                        <motion.div
                            key={node.id}
                            className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                            style={{ left: `${node.x}%`, top: `${node.y}%`, zIndex: isHovered ? 30 : 20 }}
                            whileHover={{ scale: 1.15, zIndex: 30 }}
                            onHoverStart={() => setHoveredNode(node.id)}
                            onHoverEnd={() => setHoveredNode(null)}
                            onClick={() => setSelectedNode(isSelected ? null : node.id)}
                        >
                            {/* Node circle */}
                            <div
                                className="w-16 h-16 rounded-full border-2 flex items-center justify-center bg-black/60 backdrop-blur-xl relative transition-all group-hover:shadow-[0_0_30px_rgba(255,255,255,0.3)]"
                                style={{ borderColor: getNodeColor(node.id) }}
                            >
                                <span className="text-[9px] font-bold text-white text-center px-1 uppercase leading-tight">
                                    {node.label}
                                </span>
                                {/* Status indicator */}
                                <div
                                    className="absolute -top-1 -right-1 w-5 h-5 rounded-full border-2 border-black flex items-center justify-center"
                                    style={{ backgroundColor: getNodeColor(node.id) }}
                                >
                                    <StatusIcon className="w-3 h-3 text-black" />
                                </div>
                            </div>

                            {/* Pulse effect */}
                            <div
                                className="absolute inset-0 rounded-full opacity-20 pointer-events-none"
                                style={{
                                    backgroundColor: getNodeColor(node.id),
                                    animation: status === 'healthy' ? 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite' : 'none'
                                }}
                            />

                            {/* Tooltip on hover */}
                            <AnimatePresence>
                                {isHovered && nodeHealth && (
                                    <motion.div
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        exit={{ opacity: 0, y: 10 }}
                                        className="absolute top-20 left-1/2 -translate-x-1/2 bg-black/95 border border-white/20 px-3 py-2 rounded-lg text-xs whitespace-nowrap z-50 min-w-[200px]"
                                    >
                                        <div className="font-bold text-white mb-1">{node.label}</div>
                                        <div className="text-neutral-400 text-[10px] mb-2">{node.description}</div>
                                        <div className="space-y-1 text-[10px]">
                                            <div className="flex justify-between">
                                                <span className="text-neutral-500">Status:</span>
                                                <span className="font-bold uppercase" style={{ color: getNodeColor(node.id) }}>
                                                    {status}
                                                </span>
                                            </div>
                                            {nodeHealth.latency !== undefined && (
                                                <div className="flex justify-between">
                                                    <span className="text-neutral-500">Latency:</span>
                                                    <span className="text-white">{nodeHealth.latency}ms</span>
                                                </div>
                                            )}
                                            {nodeHealth.message && (
                                                <div className="flex justify-between">
                                                    <span className="text-neutral-500">Info:</span>
                                                    <span className="text-white truncate max-w-[120px]">{nodeHealth.message}</span>
                                                </div>
                                            )}
                                            <div className="text-neutral-600 text-[9px] mt-1">
                                                {new Date(nodeHealth.lastCheck).toLocaleTimeString()}
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    );
                })}
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 right-4 bg-black/80 border border-white/10 rounded-lg p-3 text-[10px]">
                <div className="font-bold text-white mb-2 uppercase tracking-wider">Status</div>
                <div className="space-y-1">
                    {Object.entries(STATUS_COLORS).map(([status, color]) => (
                        <div key={status} className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                            <span className="text-neutral-400 capitalize">{status}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Background glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] bg-blue-500/5 blur-[100px] pointer-events-none rounded-full" />

            {/* Diagnostics Modal */}
            {selectedNode && (
                <ServiceDiagnosticsModal
                    node={topology.nodes.find(n => n.id === selectedNode) || null}
                    health={getNodeHealth(selectedNode) || null}
                    onClose={() => setSelectedNode(null)}
                />
            )}
        </GlassCard>
    );
}
export default DecisionMap;

export { DecisionMap };
