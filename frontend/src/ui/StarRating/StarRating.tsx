import { useState } from 'react';
import styles from './StarRating.module.scss';

interface StarRatingProps {
  value: number;
  onChange?: (value: number) => void;
  readonly?: boolean;
  size?: number;
}

export function StarRating({ value, onChange, readonly = false, size = 28 }: StarRatingProps) {
  const [hover, setHover] = useState(0);

  return (
    <div className={styles.stars} style={{ gap: size * 0.15 }}>
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = readonly ? star <= Math.round(value) : star <= (hover || value);
        return (
          <span
            key={star}
            className={`${styles.star} ${filled ? styles.filled : ''} ${readonly ? styles.readonly : ''}`}
            style={{ fontSize: size }}
            onClick={() => { if (!readonly && onChange) onChange(star); }}
            onMouseEnter={() => { if (!readonly) setHover(star); }}
            onMouseLeave={() => { if (!readonly) setHover(0); }}
          >
            ★
          </span>
        );
      })}
    </div>
  );
}
