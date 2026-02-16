import React from 'react';
import styles from './Select.module.scss';

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    hint?: string;
    error?: string;
}

export function Select({ label, hint, error, className, children, ...props }: SelectProps) {
    return (
        <div className={`${styles.field} ${className || ''}`}>
            {label && <label className={styles.label}>{label}</label>}
            <div className={styles.wrapper}>
                <select className={styles.select} {...props}>
                    {children}
                </select>
                <div className={styles.arrow}>▼</div>
            </div>
            {error && <span className={styles.error}>{error}</span>}
            {hint && <span className={styles.hint}>{hint}</span>}
        </div>
    );
}
