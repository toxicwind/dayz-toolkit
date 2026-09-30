'use client';

import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis
} from 'recharts';
import {
    ChartConfig,
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent
} from '@/components/ui/chart';
import { GlassCard } from '@/components/ui/glass-card';

const chartConfig = {
    players: {
        label: 'Live Players',
        color: 'hsl(var(--chart-1))'
    }
} satisfies ChartConfig;

export function StatsAreaChart({ data }: { data: any[] }) {
    return (
        <GlassCard className="p-6 h-[400px]" opacity={5}>
            <h3 className="text-lg font-medium text-white mb-4">Player Population (24h)</h3>
            <ChartContainer config={chartConfig} className="h-[320px] w-full">
                <AreaChart
                    data={data}
                    margin={{
                        left: 12,
                        right: 12,
                        top: 12,
                        bottom: 12
                    }}
                >
                    <defs>
                        <linearGradient id="fillPlayers" x1="0" y1="0" x2="0" y2="1">
                            <stop
                                offset="5%"
                                stopColor="var(--color-players)"
                                stopOpacity={0.8}
                            />
                            <stop
                                offset="95%"
                                stopColor="var(--color-players)"
                                stopOpacity={0.1}
                            />
                        </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                        dataKey="timestamp"
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                        tickFormatter={(value) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        stroke="rgba(255,255,255,0.4)"
                    />
                    <YAxis
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                        stroke="rgba(255,255,255,0.4)"
                    />
                    <ChartTooltip
                        cursor={false}
                        content={<ChartTooltipContent hideLabel />}
                    />
                    <Area
                        dataKey="players"
                        type="natural"
                        fill="url(#fillPlayers)"
                        fillOpacity={0.4}
                        stroke="var(--color-players)"
                        stackId="a"
                    />
                </AreaChart>
            </ChartContainer>
        </GlassCard>
    );
}
