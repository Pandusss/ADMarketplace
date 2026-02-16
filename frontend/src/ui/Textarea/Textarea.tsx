import React from 'react';
import styles from './Textarea.module.scss';
import { Text } from '../Text/Text';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label?: string;
    hint?: string;
    error?: string;
}

export function Textarea({ label, hint, error, className, ...props }: TextareaProps) {
    return (
        <div className={`${styles.field} ${className || ''}`}>
            {label && <label className={styles.label}>{label}</label>}
            <textarea className={styles.input} {...props} />
            {error && <span className={styles.error}>{error}</span>}
            {hint && <span className={styles.hint}>{hint}</span>}
        </div>
    );
}
