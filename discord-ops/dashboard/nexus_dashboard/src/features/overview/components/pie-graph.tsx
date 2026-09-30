'use client';

import * as React from 'react';
import { IconTrendingUp } from '@tabler/icons-react';
import { Label, Pie, PieChart } from 'recharts';

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
  survivors: {
    label: 'Survivors'
  },
  aggressive: {
    label: 'Aggressive',
    color: 'var(--primary)'
  },
  explorer: {
    label: 'Explorer',
    color: 'var(--primary-light)'
  },
  builder: {
    label: 'Builder',
    color: 'var(--primary-lighter)'
  },
  defensive: {
    label: 'Defensive',
    color: 'var(--primary-dark)'
  },
  other: {
    label: 'Unknown',
    color: 'var(--primary-darker)'
  }
} satisfies ChartConfig;

export function PieGraph({ data = [] }: { data?: any[] }) {
  // Categorize profiles based on their pattern
  const chartData = React.useMemo(() => {
    const counts = {
      aggressive: 0,
      explorer: 0,
      builder: 0,
      defensive: 0,
      other: 0
    };

    if (!data || data.length === 0) {
      return [
        { pattern: 'aggressive', count: 0, fill: 'var(--primary)' },
        { pattern: 'explorer', count: 0, fill: 'var(--color-explorer)' },
        { pattern: 'builder', count: 0, fill: 'var(--color-builder)' },
        { pattern: 'defensive', count: 0, fill: 'var(--color-defensive)' }
      ];
    }

    data.forEach((profile) => {
      const pattern = profile.pattern?.toLowerCase() || 'other';
      if (pattern in counts) {
        counts[pattern as keyof typeof counts]++;
      } else {
        counts.other++;
      }
    });

    return [
      { pattern: 'aggressive', count: counts.aggressive, fill: 'var(--primary)' },
      { pattern: 'explorer', count: counts.explorer, fill: 'var(--color-explorer)' },
      { pattern: 'builder', count: counts.builder, fill: 'var(--color-builder)' },
      { pattern: 'defensive', count: counts.defensive, fill: 'var(--color-defensive)' }
    ];
  }, [data]);

  const totalSurvivors = React.useMemo(() => {
    return data?.length || 0;
  }, [data]);

  return (
    <Card className='@container/card'>
      <CardHeader>
        <CardTitle>Player Playstyles</CardTitle>
        <CardDescription>
          <span className='hidden @[540px]/card:block'>
            Behavioral analysis based on telemetry data
          </span>
          <span className='@[540px]/card:hidden'>Player Meta</span>
        </CardDescription>
      </CardHeader>
      <CardContent className='px-2 pt-4 sm:px-6 sm:pt-6'>
        <ChartContainer
          config={chartConfig}
          className='mx-auto aspect-square h-[250px]'
        >
          <PieChart>
            <defs>
              {['aggressive', 'explorer', 'builder', 'defensive'].map(
                (pattern, index) => (
                  <linearGradient
                    key={pattern}
                    id={`fill${pattern}`}
                    x1='0'
                    y1='0'
                    x2='0'
                    y2='1'
                  >
                    <stop
                      offset='0%'
                      stopColor='var(--primary)'
                      stopOpacity={1 - index * 0.15}
                    />
                    <stop
                      offset='100%'
                      stopColor='var(--primary)'
                      stopOpacity={0.8 - index * 0.15}
                    />
                  </linearGradient>
                )
              )}
            </defs>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Pie
              data={chartData.map((item) => ({
                ...item,
                fill: `url(#fill${item.pattern})`
              }))}
              dataKey='count'
              nameKey='pattern'
              innerRadius={60}
              strokeWidth={2}
              stroke='var(--background)'
            >
              <Label
                content={({ viewBox }) => {
                  if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor='middle'
                        dominantBaseline='middle'
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className='fill-foreground text-3xl font-bold'
                        >
                          {totalSurvivors.toLocaleString()}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy || 0) + 24}
                          className='fill-muted-foreground text-sm'
                        >
                          Total Profiles
                        </tspan>
                      </text>
                    );
                  }
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className='flex-col gap-2 text-sm'>
        <div className='flex items-center gap-2 leading-none font-medium'>
          Live Aggregation Active <IconTrendingUp className='h-4 w-4' />
        </div>
        <div className='text-muted-foreground leading-none'>
          Aggregated behavior profiling OK
        </div>
      </CardFooter>
    </Card>
  );
}
export default PieGraph;

export { PieGraph };
