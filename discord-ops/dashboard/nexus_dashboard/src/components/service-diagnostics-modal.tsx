'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Activity, Clock, AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react';
import { GlassCard } from './ui/glass-card';

interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'error' | 'offline';
  latency?: number;
  uptime?: number;
  lastCheck: string;
  errorCount?: number;
  lastActivity?: string;
  message?: string;
}

interface Node {
  id: string;
  label: string;
  type: string;
  category: string;
  description: string;
  color: string;
}

interface ServiceDiagnosticsModalProps {
  node: Node | null;
  health: ServiceHealth | null;
  onClose: () => void;
}

const STATUS_COLORS = {
  healthy: '#10b981',
  degraded: '#f59e0b',
  error: '#ef4444',
  offline: '#6b7280'
};

export function ServiceDiagnosticsModal({ node, health, onClose }: ServiceDiagnosticsModalProps) {
  if (!node || !health) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-2xl"
        >
          <GlassCard className="p-6" opacity={10}>
            {/* Header */}
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white uppercase tracking-wider mb-1">
                  {node.label}
                </h2>
                <p className="text-sm text-neutral-400">{node.description}</p>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-neutral-400" />
              </button>
            </div>

            {/* Status Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-4 h-4 text-neutral-400" />
                  <span className="text-xs text-neutral-500 uppercase">Status</span>
                </div>
                <div
                  className="text-lg font-bold uppercase"
                  style={{ color: STATUS_COLORS[health.status] }}
                >
                  {health.status}
                </div>
              </div>

              {health.latency !== undefined && (
                <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-4 h-4 text-neutral-400" />
                    <span className="text-xs text-neutral-500 uppercase">Latency</span>
                  </div>
                  <div className="text-lg font-bold text-white">
                    {health.latency}
                    <span className="text-sm text-neutral-400 ml-1">ms</span>
                  </div>
                </div>
              )}

              {health.uptime !== undefined && (
                <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp className="w-4 h-4 text-neutral-400" />
                    <span className="text-xs text-neutral-500 uppercase">Uptime</span>
                  </div>
                  <div className="text-lg font-bold text-white">
                    {health.uptime.toFixed(1)}
                    <span className="text-sm text-neutral-400 ml-1">%</span>
                  </div>
                </div>
              )}

              <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-neutral-400" />
                  <span className="text-xs text-neutral-500 uppercase">Last Check</span>
                </div>
                <div className="text-sm font-bold text-white">
                  {new Date(health.lastCheck).toLocaleTimeString()}
                </div>
              </div>
            </div>

            {/* Details */}
            <div className="space-y-4">
              {/* Service Info */}
              <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
                  Service Information
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Type:</span>
                    <span className="text-white capitalize">{node.type.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-500">Category:</span>
                    <span className="text-white capitalize">{node.category.replace('_', ' ')}</span>
                  </div>
                  {health.message && (
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Message:</span>
                      <span className="text-white">{health.message}</span>
                    </div>
                  )}
                  {health.errorCount !== undefined && (
                    <div className="flex justify-between">
                      <span className="text-neutral-500">Error Count:</span>
                      <span className={health.errorCount > 0 ? 'text-red-400' : 'text-green-400'}>
                        {health.errorCount}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Performance Metrics */}
              {health.latency !== undefined && (
                <div className="bg-black/40 rounded-lg p-4 border border-white/10">
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
                    Performance
                  </h3>
                  <div className="space-y-3">
                    {/* Latency Bar */}
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-neutral-500">Response Time</span>
                        <span className="text-white">{health.latency}ms</span>
                      </div>
                      <div className="h-2 bg-black/60 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min((health.latency / 1000) * 100, 100)}%` }}
                          className="h-full rounded-full"
                          style={{
                            backgroundColor:
                              health.latency < 100
                                ? '#10b981'
                                : health.latency < 500
                                ? '#f59e0b'
                                : '#ef4444'
                          }}
                        />
                      </div>
                    </div>

                    {/* Health Score */}
                    <div>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-neutral-500">Health Score</span>
                        <span className="text-white">
                          {health.status === 'healthy'
                            ? '100%'
                            : health.status === 'degraded'
                            ? '75%'
                            : health.status === 'error'
                            ? '25%'
                            : '0%'}
                        </span>
                      </div>
                      <div className="h-2 bg-black/60 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{
                            width:
                              health.status === 'healthy'
                                ? '100%'
                                : health.status === 'degraded'
                                ? '75%'
                                : health.status === 'error'
                                ? '25%'
                                : '0%'
                          }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: STATUS_COLORS[health.status] }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {health.status !== 'healthy' && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />
                    <div>
                      <h3 className="text-sm font-bold text-amber-500 uppercase tracking-wider mb-1">
                        Recommendations
                      </h3>
                      <ul className="text-sm text-amber-200/80 space-y-1 list-disc list-inside">
                        {health.status === 'offline' && (
                          <>
                            <li>Check if the service is running</li>
                            <li>Verify network connectivity</li>
                            <li>Review service logs for errors</li>
                          </>
                        )}
                        {health.status === 'error' && (
                          <>
                            <li>Check service logs for error details</li>
                            <li>Verify configuration settings</li>
                            <li>Consider restarting the service</li>
                          </>
                        )}
                        {health.status === 'degraded' && (
                          <>
                            <li>Monitor latency trends</li>
                            <li>Check system resource usage</li>
                            <li>Review recent changes</li>
                          </>
                        )}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="mt-6 pt-4 border-t border-white/10 flex justify-between items-center">
              <div className="text-xs text-neutral-500">
                Service ID: <span className="text-neutral-400 font-mono">{node.id}</span>
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-bold text-white uppercase tracking-wider transition-colors"
              >
                Close
              </button>
            </div>
          </GlassCard>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
export default ServiceDiagnosticsModal;

export { ServiceDiagnosticsModal };
