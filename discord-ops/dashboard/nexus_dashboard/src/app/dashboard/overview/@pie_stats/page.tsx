import { PieGraph } from '@/features/overview/components/pie-graph';

const BOT_API_INTERNAL = process.env.BOT_API_URL || 'http://bot:43200';

async function getSurvivalMetrics() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/survival/metrics`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (err) {
    console.error("[AUTONOMOUS_DIAGNOSTIC] Failed to fetch survival metrics (@pie_stats):", err);
    return null;
  }
}

export default async function PieStats() {
  const metrics = await getSurvivalMetrics();
  return <PieGraph data={metrics?.profiles || []} />;
}

