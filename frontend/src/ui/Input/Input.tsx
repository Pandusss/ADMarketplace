import React, { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';
import styles from './Input.module.scss';

type BaseProps = {
  label?: string;
  hint?: string;
  error?: string;
  icon?: React.ReactNode;
};

export function Input(props: BaseProps & InputHTMLAttributes<HTMLInputElement>) {
  const { label, hint, error, icon, className, ...rest } = props;
  return (
    <div className={styles.field}>
      {label && <div className={styles.label}>{label}</div>}
      <div className={styles.inputWrapper}>
        {icon && <div className={styles.icon}>{icon}</div>}
        <input
          className={`${styles.control} ${icon ? styles.hasIcon : ''} ${className ?? ''}`}
          {...rest}
        />
      </div>
      {error ? <div className={styles.error}>{error}</div> : hint ? <div className={styles.hint}>{hint}</div> : null}
    </div>
  );
}

export function Textarea(props: BaseProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { label, hint, error, className, ...rest } = props;
  return (
    <div className={styles.field}>
      {label && <div className={styles.label}>{label}</div>}
      <textarea className={`${styles.control} ${className ?? ''}`} rows={5} {...rest} />
      {error ? <div className={styles.error}>{error}</div> : hint ? <div className={styles.hint}>{hint}</div> : null}
    </div>
  );
}

export function Select(props: BaseProps & React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { label, hint, error, className, children, ...rest } = props;
  return (
    <div className={styles.field}>
      {label && <div className={styles.label}>{label}</div>}
      <select className={`${styles.control} ${className ?? ''}`} {...rest}>
        {children}
      </select>
      {error ? <div className={styles.error}>{error}</div> : hint ? <div className={styles.hint}>{hint}</div> : null}
    </div>
  );
}

