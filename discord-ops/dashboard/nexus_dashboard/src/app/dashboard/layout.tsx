import { KBar } from '@/components/kbar';
import { AppSidebar } from '@/components/layout/app-sidebar';
import { Header } from '@/components/layout/header';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import type { Metadata } from 'next';
import { cookies } from 'next/headers';

export const metadata: Metadata = {
  title: 'Next Shadcn Dashboard Starter',
  description: 'Basic dashboard with Next.js and Shadcn'
};

import { auth } from '@clerk/nextjs/server';

import { redirect } from 'next/navigation';

export default async function DashboardLayout({
  children
}: {
  children: React.ReactNode;
}) {
  const { userId } = await auth();

  if (!userId) {
    redirect('/auth/sign-in');
  }

  // Multi-user access control (matches proxy.ts)
  const ALLOWED_USERS = [
    'user_37Nl8EHyPWT4Xce2S26OxKPw04h', // Chris
    process.env.CLERK_CHRIS_ID
  ].filter(Boolean);

  if (!ALLOWED_USERS.includes(userId)) {
    console.error(`[LAYOUT] 🚫 FORBIDDEN: User ${userId} not in allowed list`);
    redirect('/');
  }

  console.log(`[LAYOUT] ✅ AUTHORIZED: User ${userId}`);

  // Persisting the sidebar state in the cookie.
  const cookieStore = await cookies();
  const defaultOpen = cookieStore.get("sidebar_state")?.value === "true"
  return (
    <KBar>
      <SidebarProvider defaultOpen={defaultOpen}>
        <AppSidebar />
        <SidebarInset>
          <Header />
          {/* page main content */}
          {children}
          {/* page main content ends */}
        </SidebarInset>
      </SidebarProvider>
    </KBar>
  );
}

