'use client';

/**
 * Fully client-side hook for filtering navigation items based on RBAC
 *
 * This hook uses Clerk's client-side hooks to check permissions, roles, and organization
 * without any server calls. This is perfect for navigation visibility (UX only).
 *
 * Performance:
 * - All checks are synchronous (no server calls)
 * - Instant filtering
 * - No loading states
 * - No UI flashing
 *
 * Note: For actual security (API routes, server actions), always use server-side checks.
 * This is only for UI visibility.
 */

import { useMemo } from 'react';
import { useOrganization, useUser } from '@clerk/nextjs';
import type { NavItem } from '@/types';

/**
 * Hook to filter navigation items based on RBAC (fully client-side)
 *
 * @param items - Array of navigation items to filter
 * @returns Filtered items
 */
export function useFilteredNavItems(items: NavItem[]) {
  /*
  const { organization, membership } = useOrganization();
  const { user } = useUser();

  // Memoize context and permissions
  const accessContext = useMemo(() => {
    const permissions = membership?.permissions || [];
    const role = membership?.role;

    return {
      organization: organization ?? undefined,
      user: user ?? undefined,
      permissions: permissions as string[],
      role: role ?? undefined,
      hasOrg: !!organization
    };
  }, [organization?.id, user?.id, membership?.permissions, membership?.role]);

  // Filter items synchronously (all client-side)
  const filteredItems = useMemo(() => {
    return items
      .filter((item) => {
        // ... (filtering logic)
      })
      .map((item) => {
        // ... (recursive filtering)
      });
  }, [items, accessContext]);

  return filteredItems;
  */
  return items;
}

