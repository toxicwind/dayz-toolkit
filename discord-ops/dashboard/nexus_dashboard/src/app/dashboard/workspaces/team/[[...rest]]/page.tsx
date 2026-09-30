'use client';

import { PageContainer } from '@/components/layout/page-container';
import { OrganizationProfile } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { useTheme } from 'next-themes';

export function TeamPage() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <PageContainer
      pageTitle='Team Management'
      pageDescription='Manage your workspace team, members, roles, security and more.'
    >
      <div className='rounded-lg border p-8 text-center'>
        <p className='text-muted-foreground'>Clerk Organization Profile is temporarily disabled.</p>
      </div>
      {/* <OrganizationProfile
        appearance={{
          baseTheme: isDark ? dark : undefined
        }}
      /> */}

    </PageContainer>
  );
}
export default TeamPage;
