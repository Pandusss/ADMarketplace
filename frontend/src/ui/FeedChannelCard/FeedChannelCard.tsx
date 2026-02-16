import { Button } from '../Button/Button';
import { Badge } from '../Badge/Badge';
import { RatingBadge } from '../RatingBadge/RatingBadge';
import { CheckCircle2, Users, Eye, BarChart3, VenetianMask } from 'lucide-react';
import { formatCompactNumber } from '../../utils/format'; // Assuming utility exists, otherwise implement local helper
import styles from './FeedChannelCard.module.scss';
import { formatTON } from '../../utils/format';
import { motion } from 'framer-motion';

export interface FeedChannelCardProps {
    title: string;
    handle: string;
    avatarUrl?: string;
    isVerified?: boolean;
    subscribers: number;
    avgViews: number;
    engagementRate: number;
    category: string;
    language: string;
    price: number;
    ratingAvg?: number;
    ratingCount?: number;
    channelId?: string;
    ownerId?: string;
    onOfferDeal?: () => void;
    onUnpublish?: () => void;
    onClick?: () => void;
    onViewProfile?: () => void;
}

export function FeedChannelCard({
    title,
    handle,
    avatarUrl,
    isVerified,
    subscribers,
    avgViews,
    engagementRate,
    category,
    language,
    price,
    ratingAvg,
    ratingCount,
    channelId,
    ownerId,
    onOfferDeal,
    onUnpublish,
    onClick,
    onViewProfile,
}: FeedChannelCardProps) {


    return (
        <motion.div
            className={styles.card}
            onClick={onClick}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') onClick?.();
            }}
            whileTap={{ scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400, damping: 17 }}
        >
            <div className={styles.header}>
                <div className={styles.infoSection}>
                    <div className={styles.avatarWrapper}>
                        <div className={styles.avatar}>
                            {avatarUrl ? (
                                <img src={avatarUrl} alt={title} className={styles.avatarImage} />
                            ) : (
                                title.charAt(0)
                            )}
                        </div>
                    </div>

                    <div className={styles.texts}>
                        <div className={styles.titleRow}>
                            <h3 className={styles.title}>{title}</h3>
                            {isVerified && (
                                <CheckCircle2 size={14} className={styles.verifiedCheck} />
                            )}
                        </div>
                        <div className={styles.handle}>{handle ? `@${handle}` : 'Private'}</div>
                    </div>
                </div>

                {onUnpublish && (
                    <div className={styles.offerButton}>
                        <Button
                            variant="secondary"
                            size="small"
                            onClick={(e) => {
                                e.stopPropagation();
                                onUnpublish();
                            }}
                            fullWidth={false}
                            style={{ color: 'var(--color-foreground-danger)' }}
                        >
                            Take Down
                        </Button>
                    </div>
                )}
                {!onUnpublish && onOfferDeal && (
                    <div className={styles.offerButton}>
                        <Button
                            variant="primary" /* Ensure primary for blue color */
                            size="small"
                            onClick={(e) => {
                                e.stopPropagation();
                                onOfferDeal();
                            }}
                            fullWidth={false}
                        >
                            Offer Deal
                        </Button>
                    </div>
                )}
            </div>

            <div className={styles.stats}>
                <div className={styles.statItem}>
                    <Users size={14} />
                    <span>{formatCompactNumber(subscribers)}</span>
                </div>
                <div className={styles.statItem}>
                    <Eye size={14} />
                    <span>{formatCompactNumber(avgViews)}</span>
                </div>
                <div className={styles.statItem}>
                    <BarChart3 size={14} />
                    <span>{engagementRate || 0}% ER</span>
                </div>
                {ratingAvg !== undefined && ratingCount !== undefined && channelId && (
                    <div className={styles.statItem}>
                        <RatingBadge
                            ratingAvg={ratingAvg}
                            ratingCount={ratingCount}
                            reviewsEndpoint={`/channels/${channelId}/reviews`}
                            label="Channel Reviews"
                        />
                    </div>
                )}
            </div>

            <div className={styles.footer}>
                <div className={styles.badges}>
                    <Badge tone="default">{category || 'Any'}</Badge>
                    <Badge tone="default" mode="outline">{language || 'Any'}</Badge>
                </div>
                <div className={styles.footerRight}>
                    {onViewProfile && (
                        <button
                            className={styles.viewProfileBtn}
                            onClick={(e) => { e.stopPropagation(); onViewProfile(); }}
                        >
                            <VenetianMask size={18} />
                            <span>Publisher</span>
                        </button>
                    )}
                    <div className={styles.price}>
                        {formatTON(price)}
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
