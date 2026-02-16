import React from 'react';
import classNames from 'classnames';
import styles from './Card.module.scss';

export function Card({
  children,
  className,
  tight,
  clickable,
  ...rest
}: {
  children: React.ReactNode;
  className?: string;
  tight?: boolean;
  clickable?: boolean;
} & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={classNames(styles.card, tight && styles.tight, clickable && styles.clickable, className)} {...rest}>
      {children}
    </div>
  );
}

export function CardStack({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={classNames(styles.stack, className)}>{children}</div>;
}

export function CardHeaderRow({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={classNames(styles.headerRow, className)}>{children}</div>;
}

