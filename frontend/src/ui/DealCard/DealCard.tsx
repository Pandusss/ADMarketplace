import { Badge } from '../Badge/Badge';
import { motion } from 'framer-motion';
import styles from './DealCard.module.scss';

export interface DealCardProps {
    title: string;
    description: string;
    initial?: string;
    statusLabel: string;
    statusTone: 'default' | 'accent' | 'success' | 'warning' | 'danger';
    nextAction?: string;
    footerNote?: string;
    onClick?: () => void;
    className?: string;
    emoji?: string;
}

export function DealCard({
    title,
    description,
    initial,
    statusLabel,
    statusTone,
    nextAction,
    footerNote,
    onClick,
    className = '',
    emoji,
}: DealCardProps) {

    const displayInitial = emoji || (initial ? initial.charAt(0) : title.charAt(0));

    return (
        <motion.div
            className={`${styles.card} ${className}`}
            onClick={onClick}
            role="button"
            tabIndex={0}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
            <div className={styles.header}>
                <div className={styles.left}>
                    <div className={`${styles.avatar} ${emoji ? styles.isEmoji : ''}`}>
                        {displayInitial}
                    </div>
                    <div className={styles.info}>
                        <h3 className={styles.title}>{title}</h3>
                        <span className={styles.subtitle}>{description}</span>
                    </div>
                </div>

                <div className={styles.statusWrapper}>
                    <Badge tone={statusTone}>{statusLabel}</Badge>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--tg-theme-hint-color)' }}>
                        <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                </div>
            </div>

            {footerNote && (
                <div className={styles.footerNote}>
                    <p>{footerNote}</p>
                </div>
            )}
        </motion.div>
    );
}
