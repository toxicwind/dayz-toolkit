'use client';

import { IconTrendingUp } from '@tabler/icons-react';
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import React from 'react';
import { format } from 'date-fns';

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '@/components/ui/card';
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent
} from '@/components/ui/chart';

const chartConfig = {
  players: {
    label: 'Survivors',
    color: 'var(--primary)'
  },
  capacity: {
    label: 'Capacity',
    color: 'var(--primary-light)'
  }
} satisfies ChartConfig;

export function AreaGraph({ data = [] }: { data?: any[] }) {
  const chartData = React.useMemo(() => {
    return data.map(d => ({
      time: d.timestamp,
      players: d.player_count,
      capacity: d.max_players
    }));
  }, [data]);

  return (
    <Card className='@container/card'>
      <CardHeader>
        <CardTitle>POPULATION DENSITY</CardTitle>
        <CardDescription>
          Survivor presence over the observation window
        </CardDescription>
      </CardHeader>
      <CardContent className='px-2 pt-4 sm:px-6 sm:pt-6'>
        <ChartContainer
          config={chartConfig}
          className='aspect-auto h-[250px] w-full'
        >
          <AreaChart
            data={chartData}
            margin={{
              left: 12,
              right: 12
            }}
          >
            <defs>
              <linearGradient id='fillPlayers' x1='0' y1='0' x2='0' y2='1'>
                <stop
                  offset='5%'
                  stopColor='var(--primary)'
                  stopOpacity={0.8}
                />
                <stop
                  offset='95%'
                  stopColor='var(--primary)'
                  stopOpacity={0.1}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} opacity={0.1} />
            <XAxis
              dataKey='time'
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => format(new Date(value), 'HH:mm')}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator='dot' labelFormatter={(value) => format(new Date(value), 'HH:mm:ss')} />}
            />
            <Area
              dataKey='players'
              type='natural'
              fill='url(#fillPlayers)'
              stroke='var(--primary)'
              stackId='a'
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
      <CardFooter>
        <div className='flex w-full items-start gap-2 text-sm'>
          <div className='grid gap-2'>
            <div className='flex items-center gap-2 leading-none font-medium'>
              Live Telemetry Feed <IconTrendingUp className='h-4 w-4' />
            </div>
            <div className='text-muted-foreground flex items-center gap-2 leading-none'>
              Last 24 Hours
            </div>
          </div>
        </div>
      </CardFooter>
    </Card>
  );
}
export default AreaGraph;

