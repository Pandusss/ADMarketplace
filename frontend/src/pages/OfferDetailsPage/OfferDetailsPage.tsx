import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge, Button, Card, RatingBadge, Text } from '../../ui';
import { formatCompactNumber, formatDate, formatTON } from '../../utils/format';
import styles from './OfferDetailsPage.module.scss';
import { apiFetch } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';

type OfferDetail = {
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
    default: return 'default';
  }
}

export function OfferDetailsPage() {
  const { offerId } = useParams<{ offerId: string }>();
  const navigate = useNavigate();
  const [offer, setOffer] = useState<OfferDetail | null>(null);
  const [error, setError] = useState<string>('');
  const [isStarting, setIsStarting] = useState(false);
  const [actionError, setActionError] = useState<string>('');
  const [alertModal, setAlertModal] = useState<{ isOpen: boolean; title?: string; message: string }>({ isOpen: false, message: '' });

  const tg = useMemo(() => (window as any).Telegram?.WebApp, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!offerId) return;
      try {
        const r = await apiFetch(`/campaign-applications/${offerId}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as OfferDetail;
        if (!cancelled) setOffer(data);
      } catch (e: any) {
        if (!cancelled) {
          setOffer(null);
          setError(String(e?.message || e || 'Failed to load offer'));
        }
      }
    }
    load();
    return () => { cancelled = true; };
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
      const r = await apiFetch(`/campaign-applications/${offerId}/start-deal`, { method: 'POST' });
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
      const r = await apiFetch(`/campaign-applications/${offerId}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(await r.text());
      navigate('/deals');
    } catch (e: any) {
      setActionError(String(e?.message || e || 'Failed to reject offer'));
    } finally {
      setIsStarting(false);
    }
  }

  function openChannelInTelegram(handle: string) {
    const h = String(handle || '').trim().replace(/^@/, '');
    if (!h) {
      setAlertModal({ isOpen: true, title: 'No public link', message: 'This channel has no public @handle.' });
      return;
    }
    const url = `https://t.me/${h}`;
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, '_blank');
  }

  if (!offer || !view) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <Card>
            <Text type="text" color="secondary">{error || 'Loading...'}</Text>
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
          {/* Header */}
          <div className={styles.offerHeader}>
            <div className={styles.offerHeaderLeft}>
              <Text type="title2" weight="bold">
                {view.isIncoming ? 'Incoming Offer' : 'My Offer'}
              </Text>
              <Badge tone={tone(offer.status)}>{offer.status}</Badge>
            </div>
            {offer.created_at && (
              <span className={styles.offerDate}>{formatDate(offer.created_at)}</span>
            )}
          </div>

          {/* Channel block */}
          <div className={styles.channelBlock} onClick={() => openChannelInTelegram(ch.handle)}>
            <div className={styles.channelAvatar}>{(ch.name || '?')[0]}</div>
            <div className={styles.channelInfo}>
              <div className={styles.channelNameRow}>
                <span className={styles.channelName}>{ch.name || '—'}</span>
                {ch.handle && <span className={styles.channelHandle}>@{ch.handle}</span>}
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

          {/* Badges */}
          {(ch.category || ch.language) && (
            <div className={styles.badgeRow}>
              {ch.category && <span className={styles.infoBadge}>{ch.category}</span>}
              {ch.language && <span className={styles.infoBadge}>🌐 {ch.language}</span>}
            </div>
          )}

          {/* Terms */}
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
              <Text type="caption" color="secondary">Base Price</Text>
              <Text type="text" weight="medium">{formatTON(ch.price_per_post_ton || 0)}</Text>
            </div>
          </div>

          {/* Price */}
          <div className={styles.priceBlock}>
            <Text type="caption" color="secondary" weight="medium">Offer Price</Text>
            <Text type="title2" weight="bold">{formatTON(offer.offer_price_ton || 0)}</Text>
          </div>

          {/* Expandable sections */}
          {offer.message && (
            <div className={styles.briefButton} onClick={() => setAlertModal({ isOpen: true, title: 'Message', message: offer.message || '' })}>
              <Text type="text" color="secondary">Message</Text>
              <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
            </div>
          )}

          {isCustomTask && offer.creative_instructions && (
            <div className={styles.briefButton} onClick={() => setAlertModal({ isOpen: true, title: 'By Prompt', message: offer.creative_instructions || '' })}>
              <Text type="text" color="secondary">By Prompt</Text>
              <span style={{ color: 'var(--color-foreground-secondary)', opacity: 0.5 }}>›</span>
            </div>
          )}
        </Card>

        {actionError && (
          <Card style={{ border: '1px solid var(--color-danger, #e53935)' }}>
            <Text type="text" style={{ color: 'var(--color-danger)' }}>{actionError}</Text>
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
          ) : null}
        </div>
      </div>
    </div>
  );
}
