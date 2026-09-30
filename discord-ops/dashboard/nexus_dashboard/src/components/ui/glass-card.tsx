import React from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
    children: React.ReactNode;
    blur?: 'sm' | 'md' | 'lg' | 'xl';
    opacity?: number;
}

const blurMap = {
    sm: 'backdrop-blur-sm',
    md: 'backdrop-blur-md',
    lg: 'backdrop-blur-lg',
    xl: 'backdrop-blur-xl',
};

export const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
    ({ className, children, blur = 'md', opacity = 10, ...props }, ref) => {
        return (
            <div
                ref={ref}
                className={cn(
                    'relative overflow-hidden rounded-xl border border-white/20 bg-white/10 shadow-xl transition-all hover:bg-white/15',
                    blurMap[blur],
                    className
                )}
                style={{ backgroundColor: `rgba(255, 255, 255, ${opacity / 100})` }}
                {...props}
            >
                <div className="relative z-10">{children}</div>
                {/* Subtle inner glow */}
                <div className="absolute inset-0 pointer-events-none bg-gradient-to-tr from-white/5 to-transparent opa-20" />
            </div>
        );
    }
);

GlassCard.displayName = 'GlassCard';
export default GlassCard;

export { GlassCard };
