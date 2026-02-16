import { Button } from '../Button/Button';
import { Badge } from '../Badge/Badge';
import { RatingBadge } from '../RatingBadge/RatingBadge';
import { Eye, Coins, Bitcoin, Gamepad2, Briefcase, Newspaper, Heart, LayoutGrid, VenetianMask } from 'lucide-react';
import { formatCompactNumber, formatTON } from '../../utils/format';
import { motion } from 'framer-motion';
import styles from './CampaignCard.module.scss';

export interface CampaignCardProps {
    title: string;
    brief: string;
    budget: number;
    desiredViews?: number | null;
    category: string;
    language: string;
    showBrief?: boolean;
    ratingAvg?: number;
    ratingCount?: number;
    ownerRatingAvg?: number;
    ownerRatingCount?: number;
    ownerId?: string;
    campaignId?: string;
    onApply?: () => void;
    onRemove?: () => void;
    onClick?: () => void;
    onViewProfile?: () => void;
}

export function CampaignCard({
    title,
    brief,
    budget,
    desiredViews,
    category,
    language,
    showBrief = true,
    ratingAvg,
    ratingCount,
    ownerRatingAvg,
    ownerRatingCount,
    ownerId,
    campaignId,
    onApply,
    onRemove,
    onClick,
    onViewProfile
}: CampaignCardProps) {
    const getCategoryIcon = (cat: string) => {
        switch (cat) {
            case 'Crypto': return <Bitcoin size={24} />;
            case 'Gaming': return <Gamepad2 size={24} />;
            case 'Business': return <Briefcase size={24} />;
            case 'News': return <Newspaper size={24} />;
            case 'Lifestyle': return <Heart size={24} />;
            default: return <LayoutGrid size={24} />;
        }
    };

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
                            {getCategoryIcon(category)}
                        </div>
                    </div>

                    <div className={styles.texts}>
                        <div className={styles.titleRow}>
                            <h3 className={styles.title}>{title}</h3>
                        </div>
                        <div className={styles.handle}>Advertiser Campaign</div>
                    </div>
                </div>

                {onRemove && (
                    <div className={styles.applyButton}>
                        <Button
                            variant="secondary"
                            size="small"
                            onClick={(e) => {
                                e.stopPropagation();
                                onRemove();
                            }}
                            fullWidth={false}
                            style={{ color: 'var(--color-foreground-danger)' }}
                        >
                            Remove
                        </Button>
                    </div>
                )}
                {!onRemove && onApply && (
                    <div className={styles.applyButton}>
                        <Button
                            variant="primary"
                            size="small"
                            onClick={(e) => {
                                e.stopPropagation();
                                onApply();
                            }}
                            fullWidth={false}
                        >
                            Apply
                        </Button>
                    </div>
                )}
            </div>

            {showBrief && brief && (
                <div className={styles.description}>
                    {brief}
                </div>
            )}

            <div className={styles.stats}>
                {desiredViews && desiredViews > 0 && (
                    <div className={styles.statItem}>
                        <Eye size={14} />
                        <span>{formatCompactNumber(desiredViews)} views</span>
                    </div>
                )}
                {(ratingAvg !== undefined && ratingCount !== undefined && campaignId) && (
                    <div className={styles.statItem}>
                        <RatingBadge
                            ratingAvg={ratingAvg}
                            ratingCount={ratingCount}
                            reviewsEndpoint={`/campaigns/${campaignId}/reviews`}
                            label="Campaign Reviews"
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
                            <span>Advertiser</span>
                        </button>
                    )}
                    <div className={styles.price}>
                        {formatTON(budget)}
                    </div>
                </div>
            </div>
        </motion.div>
    );
}
