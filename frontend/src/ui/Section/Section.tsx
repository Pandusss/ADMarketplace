import React from 'react';
import { Text } from '../Text/Text';

interface SectionProps {
    title?: string;
    children: React.ReactNode;
}

export function Section({ title, children }: SectionProps) {
    return (
        <div style={{ marginBottom: 24 }}>
            {title && (
                <Text type="title2" style={{ marginBottom: 12, paddingLeft: 4 }}>
                    {title}
                </Text>
            )}
            {children}
        </div>
    );
}
