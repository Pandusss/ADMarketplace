import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge, BottomSheet, Button, Card, RatingBadge, Text } from '../../ui';
import { formatCompactNumber, formatDate, formatTON } from '../../utils/format';
import styles from './CampaignOfferDetailsPage.module.scss';
import { apiFetch } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';
import { ChannelStats } from '../../components/ChannelStats/ChannelStats';
import { prettyDealStatus } from '../../domain/dealStatus';

type CampaignOfferDetail = {
    id: string;
    status: string;
    created_at?: string | null;
    offer_price_ton: number;
    message?: string;
    deal_id?: string | null;
    campaign_id: string;
    campaign_title?: string;
    creative_mode?: string;
    creative_instructions?: string;
    applicant_id?: string;
    applicant_rating_avg?: number;
    applicant_rating_count?: number;
    campaign_owner_id?: string;
    campaign_owner_display_name?: string;
    campaign_owner_username?: string | null;
    campaign_owner_rating_avg?: number;
    campaign_owner_rating_count?: number;
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

export function CampaignOfferDetailsPage() {
    const { offerId } = useParams<{ offerId: string }>();
    const navigate = useNavigate();
    const [offer, setOffer] = useState<CampaignOfferDetail | null>(null);
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
                const r = await apiFetch(`/campaign-offers/${offerId}`, { method: 'GET' });
                if (!r.ok) throw new Error(await r.text());
                const data = (await r.json()) as CampaignOfferDetail;
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
        return { isIncoming };
    }, [offer]);

    async function startDeal() {
        if (!offerId || isStarting) return;
        setIsStarting(true);
        setActionError('');
        try {
            const r = await apiFetch(`/campaign-offers/${offerId}/start-deal`, { method: 'POST' });
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

    async function rejectOffer() {
        if (!offerId || isStarting) return;
        setIsStarting(true);
        setActionError('');
        try {
            const r = await apiFetch(`/campaign-offers/${offerId}`, { method: 'DELETE' });
            if (!r.ok) throw new Error(await r.text());
            navigate('/deals');
        } catch (e: any) {
            setActionError(String(e?.message || e || 'Failed to reject offer'));
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
                message: 'This channel has no public @handle, so it can\'t be opened directly. Ask the owner for a public link.',
            });
            return;
        }
        openTelegramLink(`https://t.me/${h}`);
    }

    if (!offer || !view) {
        return (
            <div className={styles.page}>
                <div className={styles.content}>
                    <Text type="title">Offer</Text>
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
    const campaignTitle = offer.campaign_title?.trim() || offer.campaign_id;
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
                    ) : (
                        <div className={styles.channelBlock} style={{ cursor: 'default' }}>
                            <div className={styles.channelAvatar}>A</div>
                            <div className={styles.channelInfo}>
                                <div className={styles.channelNameRow}>
                                    <span className={styles.channelName}>Advertiser</span>
                                </div>
                                <div className={styles.channelStats}>
                                    <RatingBadge
                                        ratingAvg={offer.campaign_owner_rating_avg || 0}
                                        ratingCount={offer.campaign_owner_rating_count || 0}
                                        reviewsEndpoint={`/users/${offer.campaign_owner_id}/reviews?role=advertiser`}
                                        label="Advertiser Reviews"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    <div className={styles.termsGrid}>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Campaign</Text>
                            <Text type="text" weight="medium">{campaignTitle}</Text>
                        </div>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Mode</Text>
                            <Text type="text" weight="medium">{isCustomTask ? 'By Prompt' : 'Template'}</Text>
                        </div>
                        <div className={styles.termCell}>
                            <Text type="caption" color="secondary">Duration</Text>
                            <Text type="text" weight="medium">—</Text>
                        </div>
                    </div>

                    <div className={styles.priceBlock}>
                        <Text type="caption" color="secondary" weight="medium">Offer Price</Text>
                        <Text type="title2" weight="bold">{formatTON(offer.offer_price_ton || 0)}</Text>
                    </div>

                    {offer.message && (
                        <div
                            className={styles.briefButton}
                            onClick={() => setAlertModal({ isOpen: true, title: 'Message', message: offer.message || '' })}
                        >
                            <Text type="text" color="secondary">Message</Text>
                            <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
                        </div>
                    )}

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
                    ) : offer.can_start_deal ? (
                        <>
                            <Button variant="primary" isLoading={isStarting} disabled={isStarting} onClick={startDeal}>
                                Accept & Start Deal
                            </Button>
                            <Button variant="outline" isLoading={isStarting} disabled={isStarting} onClick={rejectOffer}>
                                Reject
                            </Button>
                        </>
                    ) : (
                        offer.viewer_role === 'my' && offer.status === 'pending' && (
                            <Button variant="outline" isLoading={isStarting} disabled={isStarting} onClick={rejectOffer}>
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
