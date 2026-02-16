import React from 'react';

export function CardStack({ children, className, style }: { children: React.ReactNode, className?: string, style?: React.CSSProperties }) {
    return (
        <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: 12, ...style }}>
            {children}
        </div>
    );
}
