'use client';

import { GlassCard } from '@/components/ui/glass-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Crosshair, Skull } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface KillEvent {
  id: string;
  killer: string;
  victim: string;
  weapon: string;
  distance: number;
  time: string;
}


export function KillfeedDisplay() {
  const [kills, setKills] = React.useState<KillEvent[]>([]);
  const [connected, setConnected] = React.useState(false);

  React.useEffect(() => {
    // Initial fetch
    const fetchKills = async () => {
      try {
        const res = await fetch('/api/killfeed');
        const data = await res.json();
        if (data.kills) {
          setKills(data.kills.map((k: any) => ({
            id: k.id.toString(),
            killer: k.killer,
            victim: k.victim,
            weapon: k.weapon || 'Unknown',
            distance: Math.round(k.distance_m || 0),
            time: new Date(k.timestamp).toLocaleTimeString()
          })));
        }
      } catch (error) {
        console.error('Failed to fetch kills:', error);
      }
    };
    fetchKills();

    // WebSocket connection
    const wsUrl = `ws://${window.location.hostname}:18780/ws/logs`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setConnected(true);
      console.log('Killfeed connected to live stream');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.level === 'combat') {
          const newKill: KillEvent = {
            id: Date.now().toString(),
            killer: data.player || 'Unknown',
            victim: data.victim || 'Unknown',
            weapon: data.weapon || 'Unknown',
            distance: Math.round(data.distance || 0),
            time: new Date().toLocaleTimeString()
          };
          setKills(prev => [newKill, ...prev].slice(0, 50));
        }
      } catch (e) {
        console.error('WS parse error:', e);
      }
    };

    socket.onclose = () => setConnected(false);
    return () => socket.close();
  }, []);

  return (
    <GlassCard className="h-full flex flex-col p-0 overflow-hidden" opacity={10}>
      <div className="p-4 border-b border-border/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Crosshair className={cn("w-4 h-4", connected ? "text-red-500 animate-pulse" : "text-muted-foreground")} />
          <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Live Combat Feed</h3>
        </div>
        {connected && <div className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" />
          STREAMING LIVE
        </div>}
      </div>
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          <AnimatePresence initial={false}>
            {kills.map((kill) => (
              <motion.div
                key={kill.id}
                initial={{ opacity: 0, x: -20, height: 0 }}
                animate={{ opacity: 1, x: 0, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex items-center justify-between text-sm group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded bg-red-500/10 flex items-center justify-center text-red-500">
                    <Skull className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-red-400">{kill.killer}</span>
                      <span className="text-muted-foreground text-xs">eliminated</span>
                      <span className="font-bold text-foreground">{kill.victim}</span>
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <span className="text-red-900/50 uppercase font-black text-[10px] tracking-tighter">Combat Result</span>
                      <span>{kill.weapon}</span>
                      <span>•</span>
                      <span>{kill.distance}m</span>
                    </div>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground font-mono">{kill.time}</span>
              </motion.div>
            ))}
          </AnimatePresence>
          {kills.length === 0 && !connected && (
            <div className="text-center py-12 text-muted-foreground italic text-xs">
              Waiting for combat telemetry...
            </div>
          )}
        </div>
      </ScrollArea>
    </GlassCard>
  );
}

// Helper for cn
import { cn } from '@/lib/utils';
import * as React from 'react';


export default KillfeedDisplay;

export { KillfeedDisplay };
