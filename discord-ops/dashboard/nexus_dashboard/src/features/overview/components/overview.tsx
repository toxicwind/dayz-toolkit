'use client';

import { PageContainer } from '@/components/layout/page-container';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
  CardAction
} from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AreaGraph } from './area-graph';
import { BarGraph } from './bar-graph';
import { PieGraph } from './pie-graph';
import { RecentActivity } from './recent-sales';
import { IconTrendingUp, IconActivity, IconSkull, IconUsers, IconBuildingCommunity } from '@tabler/icons-react';
import { Badge } from '@/components/ui/badge';
import React, { useEffect, useState } from 'react';

export function OverViewPage() {
  const [stats, setStats] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchStats = async () => {
    try {
      const [statsRes, trendsRes, profilesRes] = await Promise.all([
        fetch('/api/stats/overview'),
        fetch('/api/stats/trends?window=24'),
        fetch('/api/survival/profiles')
      ]);
      const statsData = await statsRes.json();
      const trendsData = await trendsRes.json();
      const profilesData = await profilesRes.json();
      setStats(statsData);
      setTrends(trendsData.trends || []);
      setProfiles(profilesData.profiles || []);
    } catch (err) {
      console.error("Failed to fetch overview stats:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 10000); // 10s polling
    return () => clearInterval(interval);
  }, []);

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col space-y-2'>
        <div className='flex items-center justify-between space-y-2'>
          <h2 className='text-2xl font-bold tracking-tight'>
            OPERATIONAL OVERVIEW <span className="text-primary italic animate-pulse">LIVE</span>
          </h2>
          <div className='hidden items-center space-x-2 md:flex'>
            <Button size="sm" variant="outline" onClick={fetchStats}>Manual Sync</Button>
            <Button size="sm">Download PDF</Button>
          </div>
        </div>
        <Tabs defaultValue='overview' className='space-y-4'>
          <TabsList>
            <TabsTrigger value='overview'>Overview</TabsTrigger>
            <TabsTrigger value='analytics' disabled>
              Deep Analytics (Coming Soon)
            </TabsTrigger>
          </TabsList>
          <TabsContent value='overview' className='space-y-4'>
            <div className='*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4'>
              
              <Card className='@container/card border-primary/20 bg-primary/5'>
                <CardHeader>
                  <CardDescription className="flex items-center gap-2">
                    <IconActivity className="size-4 text-emerald-500" /> ACTIVE PLAYERS
                  </CardDescription>
                  <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                    {stats?.active_players ?? 0} <span className="text-muted-foreground text-sm font-normal">/ {stats?.max_players ?? 60}</span>
                  </CardTitle>
                  <CardAction>
                    <Badge variant={stats?.server_status === 'ONLINE' ? 'default' : 'destructive'} className="animate-pulse">
                      {stats?.server_status ?? 'OFFLINE'}
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className='flex-col items-start gap-1.5 text-sm'>
                  <div className='line-clamp-1 flex gap-2 font-medium'>
                    Real-time Query Sync <IconTrendingUp className='size-4 text-emerald-500' />
                  </div>
                </CardFooter>
              </Card>

              <Card className='@container/card'>
                <CardHeader>
                  <CardDescription className="flex items-center gap-2">
                    <IconUsers className="size-4 text-primary" /> TOTAL PROFILES
                  </CardDescription>
                  <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                    {stats?.total_profiles?.toLocaleString() ?? 0}
                  </CardTitle>
                  <CardAction>
                    <Badge variant='outline'>
                      Unique Survivors
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className='flex-col items-start gap-1.5 text-sm'>
                  <div className='line-clamp-1 flex gap-2 font-medium'>
                    Historical database depth
                  </div>
                </CardFooter>
              </Card>

              <Card className='@container/card'>
                <CardHeader>
                  <CardDescription className="flex items-center gap-2">
                    <IconSkull className="size-4 text-rose-500" /> TOTAL KILLS
                  </CardDescription>
                  <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                    {stats?.total_kills?.toLocaleString() ?? 0}
                  </CardTitle>
                  <CardAction>
                    <Badge variant='outline' className="text-rose-500 border-rose-500/20">
                      Combat Intensity
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className='flex-col items-start gap-1.5 text-sm'>
                  <div className='line-clamp-1 flex gap-2 font-medium'>
                    Cumulative Server Lethality
                  </div>
                </CardFooter>
              </Card>

              <Card className='@container/card'>
                <CardHeader>
                  <CardDescription className="flex items-center gap-2">
                    <IconBuildingCommunity className="size-4 text-amber-500" /> STRUCTURES
                  </CardDescription>
                  <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                    {stats?.total_structures?.toLocaleString() ?? 0}
                  </CardTitle>
                  <CardAction>
                    <Badge variant='outline' className="text-amber-500 border-amber-500/20">
                      Persistent Grid
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className='flex-col items-start gap-1.5 text-sm'>
                  <div className='line-clamp-1 flex gap-2 font-medium'>
                    Infrastructure expansion active
                  </div>
                </CardFooter>
              </Card>
            </div>

            <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-7'>
              <div className='col-span-4'>
                <BarGraph data={trends} />
              </div>
              <Card className='col-span-4 md:col-span-3'>
                <RecentActivity />
              </Card>
              <div className='col-span-4'>
                <AreaGraph data={trends} />
              </div>
              <div className='col-span-4 md:col-span-3'>
                <PieGraph data={profiles.map(p => ({ ...p, pattern: p.activity_pattern }))} />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  );
}

export default OverViewPage;

