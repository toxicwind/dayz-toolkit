'use client';

import { PageContainer } from '@/components/layout/page-container';
import { OrganizationList } from '@clerk/nextjs';
import { dark } from '@clerk/themes';
import { useTheme } from 'next-themes';

import { useServerConfig } from '@/hooks/use-server-config';

export function WorkspacesPage() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const { config, loading } = useServerConfig();

  return (
    <PageContainer
      pageTitle='Workspaces'
      pageDescription='Manage your workspaces and switch between them'
      isloading={loading}
    >
      <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-3'>
        <div className='rounded-lg border p-4 hover:bg-accent cursor-pointer' onClick={() => window.location.href = '/dashboard/workspaces/team'}>
          <div className='text-lg font-semibold'>{config?.server_name || 'Cluster Server'}</div>
          <div className='text-sm text-muted-foreground'>Admin Role</div>
        </div>
      </div>
      {/* <OrganizationList
        appearance={{
          baseTheme: isDark ? dark : undefined,
          elements: {
            organizationListBox: 'space-y-2',
            organizationPreview: 'rounded-lg border p-4 hover:bg-accent',
            organizationPreviewMainIdentifier: 'text-lg font-semibold',
            organizationPreviewSecondaryIdentifier:
              'text-sm text-muted-foreground'
          }
        }}
        afterSelectOrganizationUrl='/dashboard/workspaces/team'
        afterCreateOrganizationUrl='/dashboard/workspaces/team'
      /> */}

    </PageContainer>
  );
}
export default WorkspacesPage;
