import React from 'react';

export function CardHeaderRow({ children, className, style }: { children: React.ReactNode, className?: string, style?: React.CSSProperties }) {
    return (
        <div className={className} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, ...style }}>
            {children}
        </div>
    );
}
