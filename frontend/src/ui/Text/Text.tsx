import React from 'react';
import cn from 'classnames';
import styles from './Text.module.scss';

export interface TextProps {
  children: React.ReactNode | string;
  type?: 'hero' | 'title' | 'title2' | 'text' | 'caption';
  align?: 'left' | 'center' | 'right';
  color?: 'primary' | 'secondary' | 'tertiary' | 'accent' | 'danger';
  weight?: 'normal' | 'medium' | 'bold';
  href?: string;
  as?: 'p' | 'span' | 'div' | 'a';
  uppercase?: boolean;
  onClick?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

export const Text: React.FC<TextProps> = ({
  children,
  type = 'text',
  align = 'left',
  color = 'primary',
  weight = 'normal',
  href,
  as,
  uppercase,
  onClick,
  className,
  style,
}) => {
  const Component = (as || (href ? 'a' : 'p')) as 'p' | 'span' | 'div' | 'a';
  return (
    <Component
      className={cn(
        styles.container,
        styles[type],
        styles[align],
        styles[color],
        styles[weight],
        uppercase && styles.uppercase,
        onClick && styles.clickable,
        className
      )}
      {...(href && { href })}
      onClick={onClick}
      style={style}
    >
      {children}
    </Component>
  );
};

// Convenience alias: product requirements mention "Typography"
export const Typography = Text;

