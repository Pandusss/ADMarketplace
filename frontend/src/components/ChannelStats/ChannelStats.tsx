import { motion } from 'framer-motion';
import {
    Users,
    Star,
    Eye,
    TrendingUp,
    MessageSquare,
    Share2,
    Heart,
    Globe,
    Calendar,
    FileText,
    RefreshCw,
    Activity,
    CheckCircle2,
    AlertCircle,
    Zap,
    Clock
} from 'lucide-react';
import { Badge, Card, CardStack, Text, Button, InfoTooltip } from '../../ui';
import { formatCompactNumber, formatTON } from '../../utils/format';
import styles from './ChannelStats.module.scss';

// Type based on MyChannel from MyChannelsPage but slightly more generic
export interface ChannelStatsData {
    id: string;
    name: string;
    handle: string;
    description?: string;
    subscribers_count: number;
    avg_views?: number;
    avg_views_24h?: number;
    avg_views_7d?: number;
    premium_share?: number;
    engagement_rate?: number;
    stability_score?: number;
    verified_stats: boolean;
    category?: string;
    language?: string;
    price_per_post_ton?: number;

    // Detailed stats
    premium_subscribers_count?: number;
    region_stats?: Record<string, number>;
    subs_today?: number;
    subs_week?: number;
    subs_month?: number;
    joins_24h?: number;
    leaves_24h?: number;
    reach_24h?: number;
    ad_reach_estimate?: number;
    err_24h_percent?: number;
    posts_total?: number;
    posts_yesterday?: number;
    posts_week?: number;
    posts_month?: number;
    avg_forwards?: number;
    avg_replies?: number;
    avg_reactions?: number;
    channel_created_at?: string;
    last_stats_update?: string;
}

interface ChannelStatsProps {
    channel: ChannelStatsData;
}

export function ChannelStats({ channel }: ChannelStatsProps) {
    const regionEntries = Object.entries(channel.region_stats || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4);

    const growthColor = (val: number) => val >= 0 ? '#34C759' : '#FF3B30';

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.channelInfo}>
                    <Text type="title2" weight="bold">@{channel.handle}</Text>
                    <div style={{ display: 'flex', gap: 6 }}>
                        <Badge tone={channel.verified_stats ? "success" : "warning"}>
                            {channel.verified_stats ? "Verified Statistics" : "Partial Statistics"}
                        </Badge>
                        {channel.category && <Badge tone="default">{channel.category}</Badge>}
                    </div>
                </div>
            </div>

            <CardStack>
                {/* Main Stats Grid */}
                <div className={styles.grid}>
                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Users size={16} color="var(--color-accent-primary)" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Subscribers</Text>
                            <InfoTooltip
                                title="Subscribers"
                                content="Total number of members in the channel. Updated daily to track growth trends."
                                align="left"
                                position="bottom"
                            />
                        </div>
                        <Text type="title" weight="bold" className={styles.mainValue}>
                            {formatCompactNumber(channel.subscribers_count)}
                        </Text>
                        <div className={styles.growthList}>
                            <div className={styles.growthItem}>
                                <span style={{ color: growthColor(channel.subs_today || 0) }}>
                                    {(channel.subs_today || 0) > 0 ? '+' : ''}{channel.subs_today || 0}
                                </span>
                                <span className={styles.growthLabel}>today</span>
                            </div>
                            <div className={styles.growthItem}>
                                <span style={{ color: growthColor(channel.subs_week || 0) }}>
                                    {(channel.subs_week || 0) > 0 ? '+' : ''}{channel.subs_week || 0}
                                </span>
                                <span className={styles.growthLabel}>week</span>
                            </div>
                            <div className={styles.growthItem}>
                                <span style={{ color: growthColor(channel.subs_month || 0) }}>
                                    {(channel.subs_month || 0) > 0 ? '+' : ''}{channel.subs_month || 0}
                                </span>
                                <span className={styles.growthLabel}>month</span>
                            </div>
                        </div>
                    </Card>

                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Star size={16} color="#AF52DE" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Premium</Text>
                            <InfoTooltip
                                title="Premium Users"
                                content="Percentage of subscribers with an active Telegram Premium subscription. A higher share typically indicates a more high-value audience."
                                align="right"
                                position="bottom"
                            />
                        </div>
                        <Text type="title" weight="bold" className={styles.mainValue}>
                            ~{channel.premium_share?.toFixed(1) || '0'}%
                        </Text>
                    </Card>

                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Eye size={16} color="#5856D6" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Engagement</Text>
                            <InfoTooltip
                                title="Engagement Rate"
                                content={
                                    <>
                                        <div>Average percentage of subscribers who view your posts.</div>
                                        <div className={styles.formula}>ER = (Avg. Views / Subscribers) × 100</div>
                                    </>
                                }
                                align="left"
                            />
                        </div>
                        <Text type="title" weight="bold" className={styles.mainValue}>
                            ~{channel.engagement_rate || 0}%
                        </Text>
                        <div className={styles.growthList}>
                            {(channel.err_24h_percent || 0) > 0 && (
                                <div className={styles.growthItem} style={{ gap: 4 }}>
                                    <span>~{channel.err_24h_percent || 0}%</span>
                                    <span className={styles.growthLabel}>ERR 24</span>
                                    <InfoTooltip
                                        title="ERR 24h"
                                        content={
                                            <>
                                                <div>Views gained within the first 24 hours relative to subscribers.</div>
                                                <div className={styles.formula}>ERR 24 = (Views 24h / Subscribers) × 100</div>
                                            </>
                                        }
                                        align="left"
                                    />
                                </div>
                            )}
                        </div>
                    </Card>

                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <TrendingUp size={16} color="#34C759" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Stability</Text>
                            <InfoTooltip
                                title="Stability Score"
                                content="Measures how consistent the views are across different posts. 100% means every post gets almost the same reach, which is ideal for advertisers."
                                align="right"
                            />
                        </div>
                        <Text type="title" weight="bold" className={styles.mainValue}>
                            ~{channel.stability_score ? Math.round(channel.stability_score * 100) : 0}%
                        </Text>
                    </Card>
                </div>

                {/* Regional Audience */}
                {regionEntries.length > 0 && (
                    <Card>
                        <div className={styles.cardHeader} style={{ marginBottom: 12 }}>
                            <Globe size={16} color="var(--color-accent-primary)" />
                            <Text type="title2" weight="bold">Audience Regions</Text>
                        </div>
                        <div className={styles.regionGrid}>
                            {regionEntries.map(([code, count]) => (
                                <div key={code} className={styles.regionItem}>
                                    <Badge tone="default" className={styles.regionBadge}>{code.toUpperCase()}</Badge>
                                    <div className={styles.regionBarBg}>
                                        <motion.div
                                            className={styles.regionBarFill}
                                            initial={{ width: 0 }}
                                            animate={{ width: `${count}%` }}
                                            transition={{ duration: 1, ease: "easeOut" }}
                                        />
                                    </div>
                                    <span className={styles.regionValue}>{count}%</span>
                                </div>
                            ))}
                        </div>
                    </Card>
                )}

                {/* Reach & Activity */}
                <div className={styles.grid}>
                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Zap size={16} color="#FF9500" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Reach</Text>
                            <InfoTooltip
                                title="Reach"
                                content="Estimated number of unique users who see your posts. Avg Range shows the average views per post, while 24h Reach shows how many views you get in the first day."
                                align="left"
                            />
                        </div>
                        <div className={styles.miniList}>
                            <div className={styles.miniItem}>
                                <Text type="caption" color="secondary">Avg Range</Text>
                                <Text type="text" weight="bold">{formatCompactNumber(channel.ad_reach_estimate || 0)}</Text>
                            </div>
                            <div className={styles.miniItem}>
                                <Text type="caption" color="secondary">24h Reach</Text>
                                <Text type="text" weight="bold">{formatCompactNumber(channel.reach_24h || 0)}</Text>
                            </div>
                        </div>
                    </Card>

                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Clock size={16} color="#007AFF" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Creation Date</Text>
                            <InfoTooltip
                                title="Channel Age"
                                content="The approximate date when the channel was first created. Helps in assessing the long-term reliability of the channel."
                                align="right"
                            />
                        </div>
                        <div className={styles.miniList} style={{ justifyContent: 'center', height: '100%', paddingBottom: 8 }}>
                            <div style={{ textAlign: 'center' }}>
                                <Text type="text" weight="bold">
                                    {channel.channel_created_at ? new Date(channel.channel_created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : 'Unknown'}
                                </Text>
                            </div>
                        </div>
                    </Card>
                    {((channel.joins_24h || 0) !== 0 || (channel.leaves_24h || 0) !== 0) && (
                        <Card className={styles.statCard}>
                            <div className={styles.cardHeader}>
                                <Calendar size={16} color="#FF3B30" />
                                <Text type="caption" color="secondary" uppercase weight="bold">Activity</Text>
                                <InfoTooltip
                                    title="Activity"
                                    content="Tracking daily dynamics of new members joining and leaving the channel. This shows whether the audience is growing or shrinking right now."
                                    align="left"
                                />
                            </div>
                            <div className={styles.miniList}>
                                <div className={styles.miniItem}>
                                    <Text type="caption" color="secondary">Joins 24h</Text>
                                    <Text type="text" weight="bold" style={{ color: '#34C759' }}>+{channel.joins_24h || 0}</Text>
                                </div>
                                <div className={styles.miniItem}>
                                    <Text type="caption" color="secondary">Leaves 24h</Text>
                                    <Text type="text" weight="bold" style={{ color: '#FF3B30' }}>-{channel.leaves_24h || 0}</Text>
                                </div>
                            </div>
                        </Card>
                    )}
                </div>

                {/* Posts & Interaction */}
                <div className={styles.grid}>
                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <FileText size={16} color="#1e9241ff" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Publications</Text>
                        </div>
                        <Text type="title" weight="bold" className={styles.mainValue}>
                            {(channel.posts_month || 0).toLocaleString()} <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--color-foreground-secondary)' }}>/ 30d</span>
                        </Text>
                        <div className={styles.postsGrowth}>
                            <div className={styles.growthItem}>
                                <span>{channel.posts_yesterday || 0}</span>
                                <span className={styles.growthLabel}>yesterday</span>
                            </div>
                            <div className={styles.growthItem}>
                                <span>{channel.posts_week || 0}</span>
                                <span className={styles.growthLabel}>week</span>
                            </div>
                        </div>
                    </Card>

                    <Card className={styles.statCard}>
                        <div className={styles.cardHeader}>
                            <Heart size={16} color="#FF2D55" />
                            <Text type="caption" color="secondary" uppercase weight="bold">Interactions</Text>
                        </div>
                        <div className={styles.miniList}>
                            <div className={styles.miniItem}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <Heart size={12} color="var(--color-foreground-secondary)" />
                                    <Text type="caption" color="secondary">Reactions</Text>
                                </div>
                                <Text type="text" weight="bold">{channel.avg_reactions || 0}</Text>
                            </div>
                            <div className={styles.miniItem}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <Share2 size={12} color="var(--color-foreground-secondary)" />
                                    <Text type="caption" color="secondary">Shares</Text>
                                </div>
                                <Text type="text" weight="bold">{channel.avg_forwards || 0}</Text>
                            </div>
                            <div className={styles.miniItem}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <MessageSquare size={12} color="var(--color-foreground-secondary)" />
                                    <Text type="caption" color="secondary">Comments</Text>
                                </div>
                                <Text type="text" weight="bold">{channel.avg_replies || 0}</Text>
                            </div>
                        </div>
                        <Text type="caption" color="secondary" style={{ fontSize: 10, marginTop: 'auto' }}>Average per post</Text>
                    </Card>
                </div>

                <div style={{ padding: '0 4px', display: 'flex', justifyContent: 'flex-end' }}>
                    {channel.last_stats_update && (
                        <Text type="caption" color="secondary" style={{ fontSize: 10 }}>
                            Updated: {new Date(channel.last_stats_update).toLocaleString()}
                        </Text>
                    )}
                </div>
            </CardStack>

            {channel.description && (
                <div className={styles.description}>
                    <Text type="caption" color="secondary" uppercase weight="bold" style={{ marginBottom: 8, display: 'block' }}>Description</Text>
                    <Card>
                        <Text type="text" color="secondary" style={{ fontSize: 14, lineHeight: 1.5 }}>
                            {channel.description}
                        </Text>
                    </Card>
                </div>
            )}
        </div>
    );
}
