import { SecurityWidget } from "@/components/dashboard/security-widget";
import PageContainer from "@/components/layout/page-container";
import { TacticalMap } from "@/components/dashboard/tactical-map";
import { LiveOpsPanel } from "@/components/dashboard/live-ops-panel";

async function getConfig() {
    const baseUrl = typeof window === 'undefined' ? 'http://localhost:3000' : (process.env.NEXT_PUBLIC_APP_URL || '');
    const res = await fetch(`${baseUrl}/api/server/config`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
}

// Separate fetch for security status on server side
async function getSecurityStatus() {
    try {
        const res = await fetch("http://bot:43200/security/scan", {
            cache: "no-store",
            next: { revalidate: 0 },
        });
        if (!res.ok) return { scan_result: { status: "unknown" } };
        return res.json();
    } catch (e) {
        return { scan_result: { status: "unknown" } };
    }
}

export default async function OverviewPage() {
    const [config, securityData] = await Promise.all([getConfig(), getSecurityStatus()]);
    const serverName = config?.server_name || 'DayZ Ops';
    const securityStatus = securityData.scan_result?.status === "ready" ? "ACTIVE" : "OFFLINE";

    return (
        <PageContainer scrollable={true}>
            <div className="space-y-6">
                <div className="flex items-center justify-between">
                    <h2 className="text-3xl font-bold tracking-tight text-white italic uppercase tracking-tighter italic">
                        {serverName} <span className="text-primary">OPS</span>
                    </h2>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-1 space-y-6">
                        <TacticalMap />
                        <SecurityWidget status={securityStatus} threatLevel="LOW" />
                    </div>
                    <div className="lg:col-span-2">
                        <LiveOpsPanel />
                    </div>
                </div>
            </div>
        </PageContainer>
    );
}

