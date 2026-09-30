import { AreaGraph } from '@/features/overview/components/area-graph';

const BOT_API_INTERNAL = process.env.BOT_API_URL || 'http://bot:43200';

async function getStats() {
  try {
    const res = await fetch(`${BOT_API_INTERNAL}/stats`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (err) {
    console.error("[AUTONOMOUS_DIAGNOSTIC] Failed to fetch stats (@area_stats):", err);
    return [];
  }
}

export default async function AreaStats() {
  const stats = await getStats();
  return <AreaGraph data={stats} />;
}

