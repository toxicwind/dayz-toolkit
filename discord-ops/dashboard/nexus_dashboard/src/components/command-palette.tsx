'use client';

import * as React from 'react';
import {
    KBarProvider,
    KBarPortal,
    KBarPositioner,
    KBarSearch,
    KBarResults,
    useMatches,
    Action
} from 'kbar';
import { useRouter } from 'next/navigation';

export function CommandPalette({ children }: { children: React.ReactNode }) {
    const router = useRouter();

    const actions: Action[] = [
        {
            id: 'home',
            name: 'Home',
            shortcut: ['h'],
            keywords: 'back home index',
            perform: () => router.push('/')
        },
        {
            id: 'dashboard',
            name: 'Dashboard Overview',
            shortcut: ['d'],
            keywords: 'stats charts overview',
            perform: () => router.push('/dashboard/overview')
        },
        {
            id: 'logs',
            name: 'Server Logs',
            // icon: FileText, // Assuming FileText is imported or defined elsewhere if needed
            keywords: 'logs server console output',
            perform: () => router.push('/dashboard/logs')
        },
    ];

    return (
        <KBarProvider actions={actions}>
            <KBarPortal>
                <KBarPositioner className="z-[99999] bg-black/40 backdrop-blur-sm p-4">
                    <div className="w-full max-w-[600px] overflow-hidden rounded-xl border border-white/20 bg-neutral-900/90 shadow-2xl">
                        <KBarSearch className="w-full bg-transparent p-4 text-lg text-white outline-none placeholder:text-neutral-500" placeholder="Type a command or search..." />
                        <RenderResults />
                    </div>
                </KBarPositioner>
            </KBarPortal>
            {children}
        </KBarProvider>
    );
}

function RenderResults() {
    const { results } = useMatches();

    return (
        <KBarResults
            items={results}
            onRender={({ item, active }) =>
                typeof item === 'string' ? (
                    <div className="px-4 py-2 text-xs font-semibold uppercase text-neutral-500">
                        {item}
                    </div>
                ) : (
                    <div
                        className={cn(
                            'flex cursor-pointer items-center justify-between px-4 py-3 transition-colors',
                            active ? 'bg-white/10 text-white' : 'text-neutral-400'
                        )}
                    >
                        <div className="flex items-center gap-2">
                            <span>{item.name}</span>
                        </div>
                        {item.shortcut?.length ? (
                            <div className="flex gap-1">
                                {item.shortcut.map((s) => (
                                    <kbd key={s} className="rounded bg-neutral-800 px-1.5 py-0.5 text-xs">
                                        {s}
                                    </kbd>
                                ))}
                            </div>
                        ) : null}
                    </div>
                )
            }
        />
    );
}

function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}
export default CommandPalette;

export { CommandPalette };
