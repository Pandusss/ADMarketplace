import { useState, useEffect } from 'react';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { apiFetch } from '../../api/client';
import styles from './RatingBadge.module.scss';

interface Review {
  id: string;
  reviewer_name: string;
  rating: number;
  comment: string;
  created_at: string;
}

interface RatingBadgeProps {
  ratingAvg: number;
  ratingCount: number;
  /** API endpoint to fetch reviews, e.g. "/channels/ch_123/reviews" or "/users/tg_123/reviews" */
  reviewsEndpoint: string;
  label?: string;
}

export function RatingBadge({ ratingAvg, ratingCount, reviewsEndpoint, label }: RatingBadgeProps) {
  const [open, setOpen] = useState(false);
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || reviews !== null) return;
    let cancelled = false;
    setLoading(true);
    apiFetch(reviewsEndpoint, { method: 'GET' })
      .then(r => r.json())
      .then(data => {
        if (!cancelled) setReviews(data || []);
      })
      .catch(() => {
        if (!cancelled) setReviews([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [open, reviewsEndpoint]);

  if (ratingCount === 0) {
    return <span className={styles.noRating}>★ New</span>;
  }

  function formatDate(iso: string) {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return '';
    }
  }

  function renderStars(rating: number, size: 'small' | 'summary' = 'small') {
    const cls = size === 'summary' ? styles.summaryStar : styles.reviewStar;
    return (
      <span className={size === 'summary' ? styles.summaryStars : styles.reviewStars}>
        {[1, 2, 3, 4, 5].map(s => (
          <span key={s} className={`${cls} ${s <= Math.round(rating) ? styles.reviewStarFilled : styles.reviewStarEmpty}`}>★</span>
        ))}
      </span>
    );
  }

  return (
    <>
      <span
        className={styles.badge}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        role="button"
        tabIndex={0}
      >
        <span className={styles.starIcon}>★</span>
        <span className={styles.ratingValue}>{ratingAvg.toFixed(1)}</span>
        <span className={styles.ratingCount}>({ratingCount})</span>
      </span>

      <BottomSheet isOpen={open} onClose={() => setOpen(false)} title={label || 'Reviews'}>
        <div>
          <div className={styles.summarySection}>
            <span className={styles.summaryRating}>{ratingAvg.toFixed(1)}</span>
            <div className={styles.summaryMeta}>
              {renderStars(ratingAvg, 'summary')}
              <span className={styles.summaryCount}>{ratingCount} {ratingCount === 1 ? 'review' : 'reviews'}</span>
            </div>
          </div>

          {loading && <div className={styles.emptyReviews}>Loading...</div>}

          {!loading && reviews && reviews.length === 0 && (
            <div className={styles.emptyReviews}>No reviews yet</div>
          )}

          {!loading && reviews && reviews.length > 0 && (
            <div className={styles.reviewsList}>
              {reviews.map(r => (
                <div key={r.id} className={styles.reviewItem}>
                  <div className={styles.reviewHeader}>
                    <span className={styles.reviewerName}>{r.reviewer_name || 'Anonymous'}</span>
                    <span className={styles.reviewDate}>{formatDate(r.created_at)}</span>
                  </div>
                  {renderStars(r.rating)}
                  {r.comment && <div className={styles.reviewComment}>{r.comment}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      </BottomSheet>
    </>
  );
}
