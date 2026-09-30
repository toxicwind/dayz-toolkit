'use client';
import {
  Activity,
  BarChart3,
  Bot,
  Globe,
  LayoutDashboard,
  MessageSquare,
  Search,
  Settings,
  Shield,
  ShieldAlert,
  Terminal,
  Users
} from 'lucide-react';
import * as React from 'react';

import { NavMain } from '@/components/nav-main';
import { NavUser } from '@/components/nav-user';
import { TeamSwitcher } from '@/components/team-switcher';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail
} from '@/components/ui/sidebar';

// Emergent Navigation Data
const data = {
  user: {
    name: 'Admin',
    email: 'admin@dayz-ops.local',
    avatar: '/avatars/admin.png'
  },
  teams: [
    {
      name: 'DayZ Ops',
      logo: Globe,
      plan: 'Production'
    }
  ],
  navMain: [
    {
      title: 'Analytics',
      url: '/dashboard',
      icon: LayoutDashboard,
      isActive: true,
      items: [
        {
          title: 'Live Overview',
          url: '/dashboard/overview',
          icon: Activity
        },
        {
          title: 'Player Stats',
          url: '/dashboard/stats',
          icon: Users
        },
        {
          title: 'Server Health',
          url: '/dashboard/health',
          icon: BarChart3
        }
      ]
    },
    {
      title: 'Operations',
      url: '#',
      icon: Terminal,
      items: [
        {
          title: 'RCON Console',
          url: '/dashboard/rcon',
          icon: Terminal
        },
        {
          title: 'Global Logs',
          url: '/dashboard/logs',
          icon: Search
        },
        {
          title: 'Ban Manager',
          url: '/dashboard/bans',
          icon: ShieldAlert
        }
      ]
    },
    {
      title: 'Bot Control',
      url: '#',
      icon: Bot,
      items: [
        {
          title: 'Status & Uptime',
          url: '/dashboard/bot',
          icon: Activity
        },
        {
          title: 'Broadcast',
          url: '/dashboard/broadcast',
          icon: MessageSquare
        }
      ]
    },
    {
      title: 'System',
      url: '#',
      icon: Settings,
      items: [
        {
          title: 'Configuration',
          url: '/dashboard/settings',
          icon: Settings
        },
        {
          title: 'Security',
          url: '/dashboard/security',
          icon: Shield
        }
      ]
    }
  ],
  projects: []
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible='icon' {...props} className="border-r-0 bg-transparent">
      {/* Emergent Glassmorphism Background */}
      <div className="absolute inset-0 bg-neutral-950/80 backdrop-blur-2xl border-r border-white/5 z-0 pointer-events-none" />

      <SidebarHeader className="relative z-10 pt-4">
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>

      <SidebarContent className="relative z-10 px-2">
        <NavMain items={data.navMain} />
      </SidebarContent>

      <SidebarFooter className="relative z-10 pb-4">
        <NavUser user={data.user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
