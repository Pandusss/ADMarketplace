import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge, BottomSheet, Button, Card, RatingBadge, Text } from '../../ui';
import { formatCompactNumber, formatDate, formatTON } from '../../utils/format';
import styles from './ChannelOfferDetailsPage.module.scss';
import { apiFetch } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';
import { ChannelStats } from '../../components/ChannelStats/ChannelStats';
import { prettyDealStatus } from '../../domain/dealStatus';

type ChannelOfferDetail = {
    id: string;
    status: string;
    created_at?: string | null;
    offer_price_ton: number;
    message?: string;
    deal_id?: string | null;
    campaign_title?: string;
    campaign_brief?: string;
    creative_mode?: string;
    creative_instructions?: string;
    post_duration_hours?: number;
    advertiser_id: string;
    advertiser_display_name?: string;
    advertiser_username?: string | null;
    advertiser_rating_avg?: number;
    advertiser_rating_count?: number;
    viewer_role: 'incoming' | 'my';
    can_start_deal: boolean;
    channel: {
        id: string;
        name: string;
        handle: string;
        description: string;
        subscribers_count: number;
        avg_views: number;
        verified_stats: boolean;
        category: string;
        language: string;
        price_per_post_ton: number;
        is_verified: boolean;
        is_published: boolean;
        rating_avg?: number;
        rating_count?: number;
    };
};

function tone(status: string): 'default' | 'accent' | 'success' | 'warning' | 'danger' {
    switch (status) {
        case 'accepted': return 'success';
        case 'pending': return 'warning';
        case 'rejected': return 'danger';
        case 'negotiation': return 'warning';
        case 'pending_payment': return 'warning';
        case 'creative_draft': return 'accent';
        case 'creative_review': return 'accent';
        case 'approved': return 'success';
        case 'scheduling': return 'accent';
        case 'scheduled': return 'accent';
        case 'posted': return 'default';
        case 'released': return 'success';
        case 'cancelled':
        case 'refunded': return 'danger';
        default: return 'default';
    }
}

export function ChannelOfferDetailsPage() {
    const { offerId } = useParams<{ offerId: string }>();
    const navigate = useNavigate();
    const [offer, setOffer] = useState<ChannelOfferDetail | null>(null);
    const [error, setError] = useState<string>('');
    const [isStarting, setIsStarting] = useState(false);
    const [actionError, setActionError] = useState<string>('');
    const [alertModal, setAlertModal] = useState<{ isOpen: boolean; title?: string; message: string }>({ isOpen: false, message: '' });
    const [showStats, setShowStats] = useState(false);

    const tg = useMemo(() => (window as any).Telegram?.WebApp, []);

    useEffect(() => {
        let cancelled = false;
        async function load() {
            if (!offerId) return;
            try {
                const r = await apiFetch(`/channel-offers/${offerId}`, { method: 'GET' });
                if (!r.ok) throw new Error(await r.text());
                const data = (await r.json()) as ChannelOfferDetail;
                if (!cancelled) setOffer(data);
            } catch (e: any) {
                if (!cancelled) {
                    setOffer(null);
                    setError(String(e?.message || e || 'Failed to load offer'));
                }
            }
        }
        load();
        return () => {
            cancelled = true;
        };
    }, [offerId]);

    const view = useMemo(() => {
        if (!offer) return null;
        const isIncoming = offer.viewer_role === 'incoming';
        return {
            isIncoming,
            title: offer.channel.name,
            subtitle: isIncoming ? 'Channel offer from advertiser' : 'Your channel offer',
        };
    }, [offer]);

    async function startDeal() {
        if (!offerId || isStarting) return;
        setIsStarting(true);
        setActionError('');
        try {
            const r = await apiFetch(`/channel-offers/${offerId}/start-deal`, { method: 'POST' });
            if (!r.ok) throw new Error(await r.text());
            const deal = await r.json();
            const dealId = String(deal?.id || '');
            if (dealId) navigate(`/deals/${dealId}`);
        } catch (e: any) {
            setActionError(String(e?.message || e || 'Failed to start deal'));
        } finally {
            setIsStarting(false);
        }
    }

    async function cancelOffer() {
        if (!offerId || isStarting) return;
        setIsStarting(true);
        setActionError('');
        try {
            const r = await apiFetch(`/channel-offers/${offerId}`, { method: 'DELETE' });
            if (!r.ok) throw new Error(await r.text());
            navigate('/deals');
        } catch (e: any) {
            setActionError(String(e?.message || e || 'Failed to cancel offer'));
        } finally {
            setIsStarting(false);
        }
    }

    function openTelegramLink(url: string) {
        if (tg?.openTelegramLink) tg.openTelegramLink(url);
        else window.open(url, '_blank');
    }

    function openChannelInTelegram(handle: string) {
        const h = String(handle || '').trim().replace(/^@/, '');
        if (!h) {
            setAlertModal({
                isOpen: true,
                title: 'No public link',
                message: 'This channel has no public @handle, so it cannot be opened directly.',
            });
            return;
        }
        openTelegramLink(`https://t.me/${h}`);
    }

    if (!offer || !view) {
        return (
            <div className={styles.page}>
                <div className={styles.content}>
                    <Text type="title">Channel Offer</Text>
                    <Card>
                        <Text type="text" color="secondary">
                            {error || 'Loading…'}
                        </Text>
                        <Button variant="secondary" onClick={() => navigate('/deals')}>
                            Back to Deals
                        </Button>
                    </Card>
                </div>
            </div>
        );
    }

    const ch = offer.channel;
    const isCustomTask = offer.creative_mode === 'custom_task';

    return (
        <div className={styles.page}>
            <AlertModal
                isOpen={alertModal.isOpen}
                title={alertModal.title}
                message={alertModal.message}
                buttonText="OK"
                onClose={() => setAlertModal({ isOpen: false, message: '' })}
            />
            <div className={`${styles.content} noScrollbar`}>
                <Card>
                    {/* Header */}
                    <div className={styles.offerHeader}>
                        <div className={styles.offerHeaderLeft}>
                            <Text type="title2" weight="bold">
                                {view.isIncoming ? 'Incoming Offer' : 'My Offer'}
                            </Text>
                            <Badge tone={tone(offer.status)}>{prettyDealStatus(offer.status)}</Badge>
                        </div>
                        {offer.created_at && (
                            <span className={styles.offerDate}>{formatDate(offer.created_at)}</span>
                        )}
                    </div>

                    {view.isIncoming ? (
                        <>
                            {/* Advertiser block (anonymous) */}
                            <div className={styles.channelBlock} style={{ cursor: 'default' }}>
                                <div className={styles.channelAvatar}>A</div>
                                <div className={styles.channelInfo}>
                                    <div className={styles.channelNameRow}>
                                        <span className={styles.channelName}>Advertiser</span>
                                    </div>
                                    <div className={styles.channelStats}>
                                        <RatingBadge
                                            ratingAvg={offer.advertiser_rating_avg || 0}
                                            ratingCount={offer.advertiser_rating_count || 0}
                                            reviewsEndpoint={`/users/${offer.advertiser_id}/reviews?role=advertiser`}
                                            label="Advertiser Reviews"
                                        />
                                    </div>
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            {/* Channel block (advertiser sees channel info) */}
                            <div
                                className={styles.channelBlock}
                                onClick={() => openChannelInTelegram(ch.handle)}
                            >
                                <div className={styles.channelAvatar}>
                                    {(ch.name || '?')[0]}
                                </div>
                                <div className={styles.channelInfo}>
                                    <div className={styles.channelNameRow}>
                                        <span className={styles.channelName}>{ch.name || '—'}</span>
                                        {ch.handle && (
                                            <span className={styles.channelHandle}>@{ch.handle}</span>
                                        )}
                                    </div>
                                    <div className={styles.channelStats}>
                                        {ch.subscribers_count > 0 && (
                                            <span className={styles.channelStat}>
                                                <span className={styles.channelStatIcon}>👥</span>
                                                {formatCompactNumber(ch.subscribers_count)}
                                            </span>
                                        )}
                                        {ch.avg_views > 0 && (
                                            <span className={styles.channelStat}>
                                                <span className={styles.channelStatIcon}>👁</span>
                                                {formatCompactNumber(ch.avg_views)}
                                            </span>
                                        )}
                                        <span onClick={(e) => e.stopPropagation()}>
                                            <RatingBadge
                                                ratingAvg={ch.rating_avg || 0}
                                                ratingCount={ch.rating_count || 0}
                                                reviewsEndpoint={`/channels/${ch.id}/reviews`}
                                                label="Channel Reviews"
                                            />
                                        </span>
                                    </div>
                                </div>
                                <span className={styles.channelArrow}>›</span>
                            </div>

                            <div
                                className={styles.briefButton}
                                onClick={() => setShowStats(true)}
                            >
                                <Text type="text" color="secondary">Channel Statistics</Text>
                                <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
                            </div>
                        </>
                    )}

                    {/* Terms grid */}
                    <div className={styles.termsGrid}>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Mode</Text>
                            <Text type="text" weight="medium">{isCustomTask ? 'By Prompt' : 'Template'}</Text>
                        </div>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Duration</Text>
                            <Text type="text" weight="medium">{offer.post_duration_hours || 24}h</Text>
                        </div>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Base Price</Text>
                            <Text type="text" weight="medium">{formatTON(ch.price_per_post_ton || 0)}</Text>
                        </div>
                    </div>

                    {/* Price block */}
                    <div className={styles.priceBlock}>
                        <Text type="caption" color="secondary" weight="medium">Offer Price</Text>
                        <Text type="title2" weight="bold">{formatTON(offer.offer_price_ton || 0)}</Text>
                    </div>

                    {/* Brief */}
                    {(offer.campaign_title || offer.campaign_brief) && (
                        <div
                            className={styles.briefButton}
                            onClick={() => setAlertModal({
                                isOpen: true,
                                title: offer.campaign_title || 'Campaign Brief',
                                message: (offer.campaign_title ? `Campaign: ${offer.campaign_title}\n\n` : '') + (offer.campaign_brief || '')
                            })}
                        >
                            <Text type="text" color="secondary">Campaign Brief</Text>
                            <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
                        </div>
                    )}

                    {/* Message */}
                    {offer.message && (
                        <div
                            className={styles.briefButton}
                            onClick={() => setAlertModal({ isOpen: true, title: 'Message', message: offer.message || '' })}
                        >
                            <Text type="text" color="secondary">Message</Text>
                            <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
                        </div>
                    )}

                    {/* 'By Prompt' instructions */}
                    {isCustomTask && offer.creative_instructions && (
                        <div
                            className={styles.briefButton}
                            onClick={() => setAlertModal({ isOpen: true, title: 'By Prompt', message: offer.creative_instructions || '' })}
                        >
                            <Text type="text" color="secondary">By Prompt</Text>
                            <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
                        </div>
                    )}
                </Card>

                {actionError && (
                    <Card style={{ border: '1px solid var(--color-danger, #e53935)' }}>
                        <Text type="text" style={{ color: 'var(--color-danger)' }}>
                            {actionError}
                        </Text>
                    </Card>
                )}

                <div className={styles.actions}>
                    {offer.deal_id ? (
                        <Button variant="primary" onClick={() => navigate(`/deals/${offer.deal_id}`)}>
                            Open Deal
                        </Button>
                    ) : view.isIncoming && offer.can_start_deal ? (
                        <>
                            <Button variant="primary" isLoading={isStarting} disabled={isStarting} onClick={startDeal}>
                                Accept & Start Deal
                            </Button>
                            <Button variant="outline" isLoading={isStarting} disabled={isStarting} onClick={cancelOffer}>
                                Reject
                            </Button>
                        </>
                    ) : (
                        !view.isIncoming && offer.status === 'pending' && (
                            <Button variant="outline" isLoading={isStarting} disabled={isStarting} onClick={cancelOffer}>
                                Cancel Offer
                            </Button>
                        )
                    )}
                </div>
            </div>

            <BottomSheet
                isOpen={showStats}
                onClose={() => setShowStats(false)}
                title="Channel Details"
            >
                <div style={{ paddingBottom: 20 }}>
                    <ChannelStats channel={ch as any} />
                </div>
            </BottomSheet>
        </div>
    );
}
