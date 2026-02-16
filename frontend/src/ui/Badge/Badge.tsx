import classNames from 'classnames';
import styles from './Badge.module.scss';

export function Badge({
  children,
  tone = 'default',
  mode = 'default',
  className,
}: {
  children: string;
  tone?: 'default' | 'accent' | 'success' | 'warning' | 'danger';
  mode?: 'default' | 'outline';
  className?: string;
}) {
  return (
    <span
      className={classNames(
        styles.badge,
        tone !== 'default' && styles[tone],
        mode === 'outline' && styles.outline,
        className
      )}
    >
      {children}
    </span>
  );
}

