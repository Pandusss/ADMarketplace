import { useState, useRef, useEffect, useCallback } from 'react';
import { Info } from 'lucide-react';
import styles from './InfoTooltip.module.scss';

interface InfoTooltipProps {
    title: string;
    content: React.ReactNode;
    align?: 'left' | 'right' | 'center';
    position?: 'top' | 'bottom';
}

export function InfoTooltip({ title, content, align = 'left', position = 'top' }: InfoTooltipProps) {
    const [isOpen, setIsOpen] = useState(false);
    const triggerRef = useRef<HTMLButtonElement>(null);
    const tooltipRef = useRef<HTMLDivElement>(null);

    const handleClickOutside = useCallback((event: Event) => {
        const target = event.target as Node;
        // Close if click is outside both the trigger button and the tooltip bubble
        if (
            triggerRef.current && !triggerRef.current.contains(target) &&
            tooltipRef.current && !tooltipRef.current.contains(target)
        ) {
            setIsOpen(false);
        }
    }, []);

    useEffect(() => {
        if (!isOpen) return;

        document.addEventListener('pointerdown', handleClickOutside);
        return () => {
            document.removeEventListener('pointerdown', handleClickOutside);
        };
    }, [isOpen, handleClickOutside]);

    return (
        <div className={styles.container}>
            <button
                ref={triggerRef}
                className={`${styles.trigger} ${isOpen ? styles.active : ''}`}
                onClick={(e) => {
                    e.stopPropagation();
                    setIsOpen(!isOpen);
                }}
                type="button"
            >
                <Info size={14} />
            </button>

            {isOpen && (
                <div
                    ref={tooltipRef}
                    className={`${styles.tooltip} ${styles[align]} ${styles[position]}`}
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className={styles.header}>
                        <Info size={12} color="var(--color-accent-primary)" />
                        <span className={styles.title}>{title}</span>
                    </div>
                    <div className={styles.content}>
                        {content}
                    </div>
                </div>
            )}
        </div>
    );
}
