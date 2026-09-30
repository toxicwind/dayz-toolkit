import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'error' | 'offline';
  latency?: number;
  uptime?: number;
  lastCheck: string;
  errorCount?: number;
  lastActivity?: string;
  message?: string;
}

interface SystemHealth {
  services: Record<string, ServiceHealth>;
  overall: 'healthy' | 'degraded' | 'error' | 'offline';
  timestamp: string;
}

async function checkServiceHealth(url: string, timeout = 3000): Promise<{ status: ServiceHealth['status'], latency: number, message?: string }> {
  const startTime = Date.now();
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const response = await fetch(url, {
      signal: controller.signal,
      cache: 'no-store'
    });

    clearTimeout(timeoutId);
    const latency = Date.now() - startTime;

    if (!response.ok) {
      return { status: 'error', latency, message: `HTTP ${response.status}` };
    }

    return { status: latency > 2500 ? 'degraded' : 'healthy', latency };
  } catch (error) {
    const latency = Date.now() - startTime;
    if (error instanceof Error && error.name === 'AbortError') {
      return { status: 'error', latency, message: 'Timeout' };
    }
    return { status: 'offline', latency, message: 'Unreachable' };
  }
}

export async function GET() {
  const timestamp = new Date().toISOString();
  const services: Record<string, ServiceHealth> = {};

  // Check backend health endpoint
  const backendHealth = await checkServiceHealth(`${BACKEND_URL}/health`);
  services.backend = {
    status: backendHealth.status,
    latency: backendHealth.latency,
    lastCheck: timestamp,
    message: backendHealth.message
  };

  // If backend is reachable, get detailed service status
  if (backendHealth.status !== 'offline') {
    try {
      // Check bot status
      const botResponse = await fetch(`${BACKEND_URL}/bot/status`, { cache: 'no-store' });
      if (botResponse.ok) {
        const botData = await botResponse.json();
        services.discord_bot = {
          status: botData.status === 'online' ? 'healthy' : 'offline',
          latency: botData.latency !== 'N/A' ? parseInt(botData.latency) : undefined,
          lastCheck: timestamp,
          message: botData.guild || 'Unknown guild'
        };
      } else {
        services.discord_bot = {
          status: 'offline',
          lastCheck: timestamp,
          message: 'Bot status unavailable'
        };
      }

      // Check A2S Query (via cached bot status)
      const a2sResponse = await fetch(`${BACKEND_URL}/a2s/status`, { cache: 'no-store' });
      if (a2sResponse.ok) {
        const a2sData = await a2sResponse.json();
        services.a2s_query = {
          status: a2sData.status === 'online' ? 'healthy' : 'degraded',
          latency: 0, // Internal cache
          lastCheck: timestamp,
          message: `Players: ${a2sData.players}`
        };
      } else {
        const statsHealth = await checkServiceHealth(`${BACKEND_URL}/a2s/status`);
        services.a2s_query = {
          status: statsHealth.status,
          latency: statsHealth.latency,
          lastCheck: timestamp,
          message: 'A2S Cache Unavailable'
        };
      }



      // Check Tracking DB (via intelligence endpoint)
      const intelHealth = await checkServiceHealth(`${BACKEND_URL}/intelligence/players`);
      services.tracking_db = {
        status: intelHealth.status,
        latency: intelHealth.latency,
        lastCheck: timestamp,
        message: intelHealth.message
      };

      // Check FTP Client (via nitrado logs endpoint which uses FTP)
      const ftpHealth = await checkServiceHealth(`${BACKEND_URL}/nitrado/logs`);
      services.ftp_client = {
        status: ftpHealth.status,
        latency: ftpHealth.latency,
        lastCheck: timestamp,
        message: ftpHealth.message || 'FTP connection active'
      };

      // Check Nitrado API (via server status)
      const nitradoHealth = await checkServiceHealth(`${BACKEND_URL}/server/status`);
      services.nitrado_api = {
        status: nitradoHealth.status,
        latency: nitradoHealth.latency,
        lastCheck: timestamp,
        message: nitradoHealth.message
      };

      // Check Economy Intelligence (correct path without /server prefix)
      const economyHealth = await checkServiceHealth(`${BACKEND_URL}/economy/intelligence/clusters`);
      services.economy_intel = {
        status: economyHealth.status,
        latency: economyHealth.latency,
        lastCheck: timestamp,
        message: economyHealth.message
      };

      // Check Survival Analytics
      const survivalHealth = await checkServiceHealth(`${BACKEND_URL}/survival/metrics`);
      services.survival_analytics = {
        status: survivalHealth.status,
        latency: survivalHealth.latency,
        lastCheck: timestamp,
        message: survivalHealth.message
      };

      // Check MySQL Logs (via bot logs which queries activity_logs table)
      const mysqlHealth = await checkServiceHealth(`${BACKEND_URL}/bot/logs`);
      services.mysql_logs = {
        status: mysqlHealth.status,
        latency: mysqlHealth.latency,
        lastCheck: timestamp,
        message: mysqlHealth.message || 'Activity logs accessible'
      };

      // Game server status based on server/status endpoint
      // Game server status uses A2S status
      services.game_server = {
        status: services.a2s_query.status,
        latency: services.a2s_query.latency,
        lastCheck: timestamp,
        message: services.a2s_query.message || 'DayZ server query active'
      };

      // Dashboard is always healthy if this endpoint responds
      services.dashboard = {
        status: 'healthy',
        latency: 0,
        lastCheck: timestamp,
        message: 'Active'
      };

    } catch (error) {
      console.error('Error checking service health:', error);
    }
  } else {
    // Backend is offline, mark all services as unknown
    const offlineServices = [
      'discord_bot', 'a2s_query', 'tracking_db',
      'ftp_client', 'nitrado_api', 'economy_intel', 'survival_analytics',
      'mysql_logs', 'game_server'
    ];

    offlineServices.forEach(service => {
      services[service] = {
        status: 'offline',
        lastCheck: timestamp,
        message: 'Backend unavailable'
      };
    });

    services.dashboard = {
      status: 'healthy',
      lastCheck: timestamp,
      message: 'Active (backend offline)'
    };
  }

  // Calculate overall health
  const statuses = Object.values(services).map(s => s.status);
  let overall: SystemHealth['overall'] = 'healthy';

  if (statuses.includes('offline')) {
    overall = 'offline';
  } else if (statuses.includes('error')) {
    overall = 'error';
  } else if (statuses.includes('degraded')) {
    overall = 'degraded';
  }

  const response: SystemHealth = {
    services,
    overall,
    timestamp
  };

  return NextResponse.json(response);
}
