import { PageContainer } from '@/components/layout/page-container';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardFooter
} from '@/components/ui/card';
import { IconTrendingDown, IconTrendingUp } from '@tabler/icons-react';
import React from 'react';

const BOT_API_INTERNAL = process.env.BOT_API_URL || 'http://bot:43200';

async function getBotStatus() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/bot/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error("Failed to fetch bot status:", err);
    return null;
  }
}

async function getServerStatus() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/server/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    const data = await res.json();
    return data?.data; // Returns full gameserver object from Nitrado
  } catch (err) {
    console.error("Failed to fetch server status:", err);
    return null;
  }
}

async function getConfig() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/config`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error("Failed to fetch internal config:", err);
    return null;
  }
}

export default async function OverViewLayout({
  sales,
  pie_stats,
  bar_stats,
  area_stats
}: {
  sales: React.ReactNode;
  pie_stats: React.ReactNode;
  bar_stats: React.ReactNode;
  area_stats: React.ReactNode;
}) {
  const [config, botStatus, serverStatus] = await Promise.all([
    getConfig(),
    getBotStatus(),
    getServerStatus()
  ]);

  const serverName = config?.server_name || 'DayZ Ops';

  // Extract Nitrado server data
  const nitradoQuery = serverStatus?.query || {};
  const serverIP = serverStatus?.ip || 'N/A';
  const serverPort = serverStatus?.port || 'N/A';
  const gameVersion = nitradoQuery.server_version || serverStatus?.version || config?.version || '1.28';
  const platform = config?.platform?.toUpperCase() || 'XBOX';
  const playerCount = nitradoQuery.player_current || 0;
  const maxPlayers = nitradoQuery.player_max || 60;
  const serverStatusText = serverStatus?.status || 'unknown';

  return (
    <PageContainer>
      <div className='flex flex-1 flex-col space-y-2'>
        <div className='flex items-center justify-between space-y-2'>
          EZStreet Overview
        </div>

        <div className='*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs md:grid-cols-2 lg:grid-cols-4'>
          {/* Card 1: Discord Bot Status */}
          <Card className='@container/card'>
            <CardHeader>
              <CardDescription>Discord Bot</CardDescription>
              <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                {botStatus?.status?.toUpperCase() || 'OFFLINE'}
              </CardTitle>
              <CardAction>
                <Badge variant='outline' className={botStatus?.status === 'online' ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-red-500/10 text-red-500 border-red-500/20"}>
                  {botStatus?.status === 'online' ? <IconTrendingUp /> : <IconTrendingDown />}
                  {botStatus?.status === 'online' ? 'CONNECTED' : 'DISCONNECTED'}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className='flex-col items-start gap-1.5 text-sm'>
              <div className='line-clamp-1 flex gap-2 font-medium'>
                {botStatus?.guild || 'Unknown Guild'}
              </div>
              <div className='text-muted-foreground'>
                Latency: {botStatus?.latency || 'N/A'}
              </div>
            </CardFooter>
          </Card>

          {/* Card 2: Nitrado Server Connection */}
          <Card className='@container/card'>
            <CardHeader>
              <CardDescription>Nitrado Server</CardDescription>
              <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                {serverStatusText?.toUpperCase() || 'UNKNOWN'}
              </CardTitle>
              <CardAction>
                <Badge variant='outline' className={serverStatusText === 'started' ? "bg-green-500/10 text-green-500 border-green-500/20" : "bg-yellow-500/10 text-yellow-500 border-yellow-500/20"}>
                  {serverStatusText === 'started' ? 'RUNNING' : serverStatusText?.toUpperCase() || 'OFFLINE'}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className='flex-col items-start gap-1.5 text-sm'>
              <div className='line-clamp-1 flex gap-2 font-medium'>
                {serverIP}:{serverPort}
              </div>
              <div className='text-muted-foreground'>
                Players: {playerCount}/{maxPlayers}
              </div>
            </CardFooter>
          </Card>

          {/* Card 3: Game Version from API */}
          <Card className='@container/card'>
            <CardHeader>
              <CardDescription>Game Version</CardDescription>
              <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl'>
                {gameVersion}
              </CardTitle>
              <CardAction>
                <Badge variant='outline'>
                  {platform}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className='flex-col items-start gap-1.5 text-sm'>
              <div className='line-clamp-1 flex gap-2 font-medium'>
                Platform: {platform}
              </div>
              <div className='text-muted-foreground'>
                {serverStatusText === 'started' ? 'Live' : 'Offline'}
              </div>
            </CardFooter>
          </Card>

          {/* Card 4: Server/Team Identity */}
          <Card className='@container/card'>
            <CardHeader>
              <CardDescription>Active Server</CardDescription>
              <CardTitle className='text-2xl font-semibold tabular-nums @[250px]/card:text-3xl overflow-hidden truncate'>
                {serverName}
              </CardTitle>
              <CardAction>
                <Badge variant='outline'>
                  {config?.org_id?.toUpperCase() || 'CLUSTER'}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardFooter className='flex-col items-start gap-1.5 text-sm'>
              <div className='line-clamp-1 flex gap-2 font-medium'>
                Organization: {config?.org_id || 'cluster'}
              </div>
              <div className='text-muted-foreground'>
                {nitradoQuery.server_name || serverName}
              </div>
            </CardFooter>
          </Card>
        </div>
        <div className='grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-7'>
          <div className='col-span-4'>{bar_stats}</div>
          <div className='col-span-4 md:col-span-3'>
            {/* sales arallel routes */}
            {sales}
          </div>
          <div className='col-span-4'>{area_stats}</div>
          <div className='col-span-4 md:col-span-3'>{pie_stats}</div>
        </div>
      </div>
    </PageContainer>
  );
}

