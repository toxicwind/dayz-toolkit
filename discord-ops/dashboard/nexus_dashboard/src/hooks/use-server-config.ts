'use client';

import { useState, useEffect } from 'react';

export interface ServerConfig {
    org_id: string;
    server_name: string;
    platform: string;
    region: string;
    status: string;
    version: string;
}

export function useServerConfig() {
    const [config, setConfig] = useState<ServerConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<Error | null>(null);

    useEffect(() => {
        const fetchConfig = async () => {
            try {
                const res = await fetch('/api/server/config');
                if (!res.ok) throw new Error('Failed to fetch server config');
                const data = await res.json();
                setConfig(data);
            } catch (err) {
                setError(err instanceof Error ? err : new Error('Unknown error'));
                // Fallback to defaults if backend is down
                setConfig({
                    org_id: 'ezstreet',
                    server_name: 'EZStreet',
                    platform: 'pc',
                    region: 'US-LA',
                    status: 'ONLINE',
                    version: '1.0.0-PROVENANCE'
                });
            } finally {
                setLoading(false);
            }
        };

        fetchConfig();
    }, []);

    return { config, loading, error };
}
