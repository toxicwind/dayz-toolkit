'use client';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  CardDescription
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';
import React, { useEffect, useState } from 'react';

export function RecentActivity() {
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchActivity = async () => {
    try {
      const res = await fetch('/api/survival/activity-feed?limit=8');
      if (res.ok) {
        const data = await res.json();
        setActivities(data.activities || []);
      }
    } catch (err) {
      console.error("Failed to fetch activity feed:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActivity();
    const interval = setInterval(fetchActivity, 5000); // 5s polling for activity
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className='h-full bg-card/50 backdrop-blur-sm border-primary/10'>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-sm font-bold tracking-widest text-primary uppercase">SIGNAL FEED</CardTitle>
          <CardDescription className="text-[10px] uppercase opacity-50 tracking-tighter">Intercepted telemetry stream</CardDescription>
        </div>
        <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 animate-pulse text-[10px]">
          LIVE LINK
        </Badge>
      </CardHeader>
      <CardContent>
        <div className='space-y-4'>
          {activities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 space-y-2">
               <div className="size-2 bg-primary/20 rounded-full animate-ping" />
               <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-mono">Scanning for signals...</p>
            </div>
          ) : (
            activities.map((activity: any, index: number) => {
              const date = new Date(activity.timestamp);
              return (
                <div key={activity.id || index} className='group flex items-center space-x-3 transition-all hover:bg-primary/5 p-1 rounded-md'>
                  <div className="relative">
                     <Avatar className='h-8 w-8 border border-primary/20'>
                        <AvatarFallback className="bg-primary/10 text-primary text-[10px] font-bold">
                           {activity.player_name?.substring(0, 2).toUpperCase() || '??'}
                        </AvatarFallback>
                     </Avatar>
                     {activity.threat_detected && (
                        <span className="absolute -top-0.5 -right-0.5 block h-2 w-2 rounded-full bg-rose-500 ring-2 ring-background animate-pulse" />
                     )}
                  </div>
                  <div className='flex-1 min-w-0'>
                    <div className="flex items-center gap-2">
                       <p className='text-xs font-bold truncate tracking-tight'>{activity.player_name}</p>
                       <span className="text-[9px] px-1 bg-muted rounded uppercase font-mono opacity-60">{activity.activity_type}</span>
                    </div>
                    <p className='text-muted-foreground text-[10px] truncate italic opacity-80'>{activity.details}</p>
                  </div>
                  <div className='text-[9px] font-mono tabular-nums text-muted-foreground'>
                    {formatDistanceToNow(date, { addSuffix: true }).replace('about ', '')}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default RecentActivity;

