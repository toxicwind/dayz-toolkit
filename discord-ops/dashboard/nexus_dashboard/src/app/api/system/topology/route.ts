import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://bot:43200';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/system/topology`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      cache: 'no-store'
    });

    if (!response.ok) {
      // Fallback to static topology if backend not available
      return NextResponse.json(getStaticTopology());
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Topology API Error:', error);
    // Return static topology as fallback
    return NextResponse.json(getStaticTopology());
  }
}

// Static topology definition based on actual architecture
// Static topology definition based on actual architecture
function getStaticTopology() {
  return {
    nodes: [
      // Layer 1: Infrastructure (External) - Leftmost (x=5)
      {
        id: 'game_server',
        label: 'DayZ Server',
        type: 'external',
        category: 'infrastructure',
        x: 5,
        y: 30,
        color: '#3b82f6', // Blue
        description: 'DayZ game server (Host: 85.190.156.145)'
      },
      {
        id: 'nitrado_api',
        label: 'Provider API',
        type: 'external_api',
        category: 'infrastructure',
        x: 5,
        y: 70,
        color: '#64748b', // Slate
        description: 'Nitrado server management API'
      },

      // Layer 2: Ingestion & Gateways (x=25)
      {
        id: 'a2s_query',
        label: 'A2S Listener',
        type: 'data_source',
        category: 'monitoring',
        x: 25,
        y: 20,
        color: '#8b5cf6', // Violet
        description: 'Real-time valve query protocol listener'
      },
      {
        id: 'ftp_client',
        label: 'Log Harvester',
        type: 'data_source',
        category: 'storage',
        x: 25,
        y: 80,
        color: '#10b981', // Emerald
        description: 'FTP client for log ingestion and config sync'
      },

      // Layer 3: Persistence & Storage (x=50)
      {
        id: 'tracking_db',
        label: 'Player Intel DB',
        type: 'database',
        category: 'storage',
        x: 50,
        y: 35,
        color: '#06b6d4', // Cyan
        description: 'SQLite database for tracking aliases and sessions'
      },
      {
        id: 'mysql_logs',
        label: 'Activity Warehouse',
        type: 'database',
        category: 'storage',
        x: 50,
        y: 75,
        color: '#14b8a6', // Teal
        description: 'MySQL database for structured ADM logs'
      },

      // Layer 4: Analytics & Intelligence (x=75)
      {
        id: 'economy_intel',
        label: 'Eco-Sim',
        type: 'analytics',
        category: 'intelligence',
        x: 75,
        y: 30,
        color: '#a855f7', // Purple
        description: 'Loot economy simulation and analysis'
      },
      {
        id: 'survival_analytics',
        label: 'Survival Profiler',
        type: 'analytics',
        category: 'intelligence',
        x: 75,
        y: 80,
        color: '#d946ef', // Fuchsia
        description: 'Player behavior profiling engine'
      },

      // Layer 5: Interfaces - Rightmost (x=95)
      {
        id: 'discord_bot',
        label: 'Discord Ops',
        type: 'interface',
        category: 'user_interface',
        x: 95,
        y: 40,
        color: '#5865F2', // Discord Blurple
        description: 'Operations bot interface'
      },
      {
        id: 'dashboard',
        label: 'Command Center',
        type: 'interface',
        category: 'user_interface',
        x: 95,
        y: 70,
        color: '#f43f5e', // Rose
        description: 'Live Operations Dashboard'
      }
    ],
    connections: [
      // Infrastructure to Ingestion
      { from: 'game_server', to: 'a2s_query', type: 'data_flow', label: 'UDP/Query' },
      { from: 'nitrado_api', to: 'ftp_client', type: 'dependency', label: 'Auth' },

      // Ingestion to Storage
      { from: 'a2s_query', to: 'tracking_db', type: 'data_flow', label: 'Telemetry' },
      { from: 'ftp_client', to: 'mysql_logs', type: 'data_flow', label: 'Parse/Store' },
      { from: 'ftp_client', to: 'economy_intel', type: 'data_flow', label: 'XML Sync' },

      // Storage to Intelligence
      { from: 'tracking_db', to: 'economy_intel', type: 'data_flow', label: 'Context' },
      { from: 'tracking_db', to: 'survival_analytics', type: 'data_flow', label: 'Sessions' },
      { from: 'mysql_logs', to: 'survival_analytics', type: 'data_flow', label: 'History' },

      // Intelligence/Storage to Interfaces
      { from: 'tracking_db', to: 'discord_bot', type: 'data_flow', label: 'Alerts' },
      { from: 'economy_intel', to: 'dashboard', type: 'data_flow', label: 'Heatmaps' },
      { from: 'survival_analytics', to: 'dashboard', type: 'data_flow', label: 'Metrics' },

      // Control / Feedback Loops
      { from: 'dashboard', to: 'nitrado_api', type: 'management', label: 'Restart/Stop' }
    ],
    categories: {
      infrastructure: { label: 'Infrastructure', color: '#64748b' },
      monitoring: { label: 'Ingestion', color: '#8b5cf6' },
      control: { label: 'Control', color: '#ec4899' },
      storage: { label: 'Persistence', color: '#06b6d4' },
      intelligence: { label: 'Intelligence', color: '#a855f7' },
      user_interface: { label: 'Interface', color: '#f43f5e' }
    }
  };
}
