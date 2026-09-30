import { BarGraph } from '@/features/overview/components/bar-graph';

const BOT_API_INTERNAL = process.env.BOT_API_URL || 'http://bot:43200';

async function getStats() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/stats`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (err) {
    console.error("[AUTONOMOUS_DIAGNOSTIC] Failed to fetch stats (@bar_stats):", err);
    return [];
  }
}

export default async function BarStats() {
  const stats = await getStats();
  return <BarGraph data={stats} />;
}

