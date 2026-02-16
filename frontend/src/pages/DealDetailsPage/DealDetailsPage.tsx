import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, CardHeaderRow, InfoTooltip, RatingBadge, StarRating, Text, BottomSheet } from '../../ui';
import { Users, Eye, BarChart3, Loader2 } from 'lucide-react';
import { formatTON, formatCompactNumber, formatDate } from '../../utils/format';
import styles from './DealDetailsPage.module.scss';
import { apiFetch, tgInitData } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';
import { DealRoadmap, type RoadmapStep } from '../../components/deal/DealRoadmap';
import { DEAL_STATUS_ORDER, getDealStatusIndex, prettyDealStatus } from '../../domain/dealStatus';
import type { DealStatus } from '../../domain/types';
import { DealConfirmationCard } from './DealConfirmationCard';
import { ChannelStats } from '../../components/ChannelStats/ChannelStats';
import { motion, AnimatePresence } from 'framer-motion';

function CountdownTimer({ targetDate, onFinish, label = "Posting in" }: { targetDate: string; onFinish?: () => void; label?: string }) {
  const [timeLeft, setTimeLeft] = useState<string>('');

  useEffect(() => {
    const target = new Date(targetDate.endsWith('Z') ? targetDate : targetDate + 'Z').getTime();
    let isFinished = false;

    const update = () => {
      const now = new Date().getTime();
      const diff = target - now;

      if (diff <= 0) {
        setTimeLeft('00:00:00');
        if (!isFinished) {
          isFinished = true;
          if (onFinish) onFinish();
        }
        return;
      }

      const h = Math.floor(diff / (1000 * 60 * 60));
      const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const s = Math.floor((diff % (1000 * 60)) / 1000);

      setTimeLeft(
        `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
      );
    };

    update();
    const interval = setInterval(() => {
      update();
      if (isFinished) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [targetDate, onFinish]);

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 8,
      padding: '20px 0',
      background: 'color-mix(in srgb, var(--color-accent-primary) 5%, transparent)',
      borderRadius: 16,
      border: '1px dashed var(--color-accent-primary)',
      margin: '12px 0'
    }}>
      <Text type="caption" color="secondary" weight="medium">{label}</Text>
      <Text type="title" weight="bold" style={{ fontSize: 32, letterSpacing: 1, fontFamily: 'monospace' }}>
        {timeLeft}
      </Text>
    </div>
  );
}

export function DealDetailsPage() {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string>('');

  const [isActing, setIsActing] = useState(false);
  const [actionError, setActionError] = useState<string>('');
  const [paymentInfo, setPaymentInfo] = useState<{ escrow_address: string; amount_ton: number; network: string } | null>(null);
  const [botUsername, setBotUsername] = useState<string>('');
  const [templates, setTemplates] = useState<Array<{ id: string; title: string; has_content: boolean }> | null>(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [alertModal, setAlertModal] = useState<{ isOpen: boolean; title?: string; message: string }>({
    isOpen: false,
    message: '',
  });
  const [approveConfirm, setApproveConfirm] = useState<{ isOpen: boolean }>({
    isOpen: false,
  });
  const [cancelConfirm, setCancelConfirm] = useState<{ isOpen: boolean }>({
    isOpen: false,
  });
  const [cancelConfirmStep2, setCancelConfirmStep2] = useState<{ isOpen: boolean }>({
    isOpen: false,
  });

  const [reviewRating, setReviewRating] = useState(0);
  const [reviewComment, setReviewComment] = useState('');
  const [myReview, setMyReview] = useState<{ rating: number; comment: string } | null>(null);
  const [reviewSubmitted, setReviewSubmitted] = useState(false);

  // Variant A scheduling UI state
  const [slotsDay, setSlotsDay] = useState<string>('');
  const [slotsData, setSlotsData] = useState<any | null>(null);
  const [slotsError, setSlotsError] = useState<string>('');
  const [loadingSlots, setLoadingSlots] = useState<boolean>(false);
  const [selectedLocalSlot, setSelectedLocalSlot] = useState<string | null>(null);

  const [isEditingDuration, setIsEditingDuration] = useState(false);
  const [editedDuration, setEditedDuration] = useState(24);
  const [editedTopHours, setEditedTopHours] = useState(0);

  const [statsChannel, setStatsChannel] = useState<any | null>(null);
  const [loadingStats, setLoadingStats] = useState(false);

  const tg = useMemo(() => (window as any).Telegram?.WebApp, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mr = await apiFetch('/meta', { method: 'GET' });
        if (!mr.ok) return;
        const m = await mr.json();
        if (!cancelled) setBotUsername(String(m.telegram_bot_username || ''));
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const load = useCallback(async (cancelled: boolean = false) => {
    if (!dealId) return;
    try {
      const r = await apiFetch(`/deals/${dealId}`, { method: 'GET' });
      if (!r.ok) throw new Error(await r.text());
      const d = await r.json();
      if (!cancelled) {
        console.log(`[DealDetails] Loaded deal ${dealId} with status ${d.status}`);
        setData(d);
        if (d.escrow_address && d.status === 'pending_payment') {
          setPaymentInfo({
            escrow_address: d.escrow_address,
            amount_ton: parseFloat(d.expected_amount_ton || d.price_ton || 0),
            network: d.escrow_network || 'mainnet',
          });
        }
      }
    } catch (e: any) {
      console.error('[DealDetails] Load failed:', e);
      if (!cancelled) setError(String(e?.message || e || 'Failed to load deal'));
    }
  }, [dealId]);

  const loadStats = async (channelId: string) => {
    if (loadingStats) return;
    setLoadingStats(true);
    try {
      const r = await apiFetch(`/channels/${channelId}`, { method: 'GET' });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setStatsChannel(data);
    } catch (e) {
      console.error('Failed to load stats:', e);
      setAlertModal({
        isOpen: true,
        title: 'Error',
        message: 'Failed to load channel statistics.'
      });
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    load(cancelled);

    if (tg?.BackButton) {
      const handleBack = () => {
        navigate(-1);
      };
      tg.BackButton.show();
      tg.BackButton.onClick(handleBack);

      return () => {
        cancelled = true;
        tg.BackButton.hide();
        tg.BackButton.offClick(handleBack);
      };
    }

    return () => {
      cancelled = true;
    };
  }, [load, navigate, tg]);

  useEffect(() => {
    if (!dealId) return;

    let cancelled = false;
    let ws: WebSocket | null = null;
    let retryTimeout: number | null = null;
    let retryCount = 0;
    const maxRetries = 10;
    let heartbeatInterval: number | null = null;

    function connect() {
      if (cancelled) return;

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/deals/${dealId}/ws?initData=${encodeURIComponent(tgInitData())}`;

      console.log('[WS] Connecting to', wsUrl);
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WS] Connected');
        retryCount = 0;
        heartbeatInterval = window.setInterval(() => {
          if (ws?.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          console.log('[WS] Message received:', msg);
        } catch {
          console.log('[WS] Raw message received:', event.data);
        }
        load(cancelled);
      };

      ws.onclose = () => {
        console.log('[WS] Connection closed');
        if (heartbeatInterval) clearInterval(heartbeatInterval);
        if (!cancelled && retryCount < maxRetries) {
          retryCount++;
          const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
          console.log(`[WS] Retrying in ${delay / 1000}s...`);
          retryTimeout = window.setTimeout(connect, delay);
        }
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (ws) ws.close();
      if (retryTimeout) clearTimeout(retryTimeout);
      if (heartbeatInterval) clearInterval(heartbeatInterval);
    };
  }, [dealId, load]);


  useEffect(() => {
    if (!dealId) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await apiFetch('/templates', { method: 'GET' });
        if (!r.ok) return;
        const tpls = await r.json();
        if (!cancelled) setTemplates(tpls);
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [dealId]);

  useEffect(() => {
    if (!dealId) return;
    const st = String((data as any)?.status || '');
    if (st !== 'approved' && st !== 'scheduling') {
      setSlotsData(null);
      setSlotsError('');
      return;
    }

    const suggestedDay = (() => {
      const raw = String((data as any)?.scheduled_at || (data as any)?.preferred_publish_at || '');
      const d = raw.slice(0, 10);
      return /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : '';
    })();
    if (!slotsDay && suggestedDay) {
      setSlotsDay(suggestedDay);
      return;
    }

    let cancelled = false;
    (async () => {
      setLoadingSlots(true);
      setSlotsError('');
      try {
        const q = slotsDay ? `?day=${encodeURIComponent(slotsDay)}` : '';
        const r = await apiFetch(`/deals/${dealId}/posting-slots${q}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const d = await r.json();
        if (!cancelled) setSlotsData(d);
      } catch (e: any) {
        if (!cancelled) setSlotsError(String(e?.message || e || 'Failed to load slots'));
      } finally {
        if (!cancelled) setLoadingSlots(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [dealId, (data as any)?.status, (data as any)?.preferred_publish_at, (data as any)?.scheduled_at, slotsDay]);

  useEffect(() => {
    if (!dealId || !data || !['released', 'refunded', 'cancelled'].includes(data.status)) return;
    let cancelled = false;
    (async () => {
      try {
        const r = await apiFetch(`/deals/${dealId}/my-review`, { method: 'GET' });
        if (r.ok) {
          const review = await r.json();
          if (!cancelled && review) {
            setMyReview({ rating: review.rating, comment: review.comment });
            setReviewSubmitted(true);
          }
        }
      } catch { }
    })();
    return () => { cancelled = true; };
  }, [dealId, data?.status]);

  const deal = data;

  function openTonViewer(args: { txHash?: string | null; address?: string | null; network?: string | null }) {
    const network = args.network || 'mainnet';
    let explorerUrl: string | null = null;
    if (args.txHash) {
      explorerUrl = network === 'testnet' ? `https://testnet.tonviewer.com/transaction/${args.txHash}` : `https://tonviewer.com/transaction/${args.txHash}`;
    } else if (args.address) {
      explorerUrl = network === 'testnet' ? `https://testnet.tonviewer.com/${args.address}` : `https://tonviewer.com/${args.address}`;
    }
    if (explorerUrl) window.open(explorerUrl, '_blank');
  }

  const roadmap = useMemo(() => {
    if (!deal?.status) return null;

    const isTerminal = deal.status === 'cancelled' || deal.status === 'refunded';
    const isComplete = deal.status === 'released';

    let displayStatuses = DEAL_STATUS_ORDER.filter((s) => s !== 'cancelled' && s !== 'refunded');

    if (isTerminal) {
      const cancelledFromIdx = Math.max(0, displayStatuses.indexOf((deal.cancelled_from_status || 'negotiation') as any));
      displayStatuses = displayStatuses.slice(0, cancelledFromIdx + 1);
      displayStatuses.push(deal.status as any);
    }

    const statusForRoadmap = deal.status;
    const currentIdx = Math.max(0, displayStatuses.indexOf(statusForRoadmap as any));

    let milestonesIdx = currentIdx;
    if (!isTerminal && !isComplete) {
      const milestones: DealStatus[] = ['funds_held', 'approved', 'awaiting_confirmation', 'scheduled', 'posted', 'verified'];
      if (milestones.includes(deal.status) && milestonesIdx < displayStatuses.length - 1) {
        milestonesIdx++;
      }
    }

    const currentStep = isComplete ? displayStatuses.length + 1 : milestonesIdx + 1;
    const completedUntilStep = isComplete ? displayStatuses.length : milestonesIdx;

    const paymentWasConfirmed =
      deal.payment_confirmed_at &&
      (deal.status === 'creative_draft' || getDealStatusIndex(deal.status) > getDealStatusIndex('pending_payment'));

    const steps: RoadmapStep[] = displayStatuses.map((s, idx) => {
      const action =
        s === 'funds_held' && paymentWasConfirmed && (deal.payment_tx_hash || deal.escrow_address)
          ? {
            label: 'TX',
            onClick: () =>
              openTonViewer({
                txHash: deal.payment_tx_hash,
                address: deal.escrow_address,
                network: deal.escrow_network,
              }),
          }
          : ((s as any) === 'released' && deal.release_tx_hash) || ((s as any) === 'refunded' && deal.refund_tx_hash)
            ? {
              label: 'TX',
              onClick: () =>
                openTonViewer({
                  txHash: (s as any) === 'released' ? deal.release_tx_hash : deal.refund_tx_hash,
                  network: deal.escrow_network,
                }),
            }
            : undefined;
      const isTerminalStep = isTerminal && idx === displayStatuses.length - 1;
      return {
        id: idx + 1,
        title: prettyDealStatus(s),
        desc: idx === currentIdx ? 'Current step' : undefined,
        action,
        type: isTerminalStep ? 'error' : 'default',
      };
    });

    return { steps, currentStep, completedUntilStep };
  }, [
    deal?.status,
    deal?.cancelled_from_status,
    deal?.payment_confirmed_at,
    deal?.escrow_network,
    deal?.release_tx_hash,
    deal?.released_at,
    deal?.refund_tx_hash,
    deal?.refunded_at,
  ]);

  if (!data) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <Text type="title">Deal</Text>
          <Card>
            <Text type="text" color="secondary">
              {error || 'Deal not found.'}
            </Text>
            <Button variant="secondary" onClick={() => navigate('/deals')}>
              Back to Deals
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  const permissions = data.permissions || {};

  function openTelegramLink(url: string) {
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, '_blank');
  }

  function statusDescription() {
    switch (deal.status) {
      case 'negotiation':
        return 'Negotiation';
      case 'pending_payment':
        return 'Pending payment';
      case 'creative_draft':
        return 'Creative draft';
      case 'creative_review':
        return 'Creative review';
      case 'approved':
        return 'Approved';
      case 'scheduling':
        return 'Scheduling (waiting for approval)';
      case 'awaiting_confirmation':
        return 'Awaiting final confirmation';
      case 'scheduled':
        return 'Scheduled';
      case 'posted':
        return 'Posted';
      case 'released':
        return 'Released';
      case 'cancelled':
        return 'Cancelled';
      case 'refunded':
        return 'Refunded';
      default:
        return `Status: ${deal.status}`;
    }
  }

  function act(fn: () => Promise<void>) {
    setIsActing(true);
    setActionError('');
    fn()
      .catch((e) => setActionError(String((e as any)?.message || e || 'Action failed')))
      .finally(() => setIsActing(false));
  }

  async function handleApprove() {
    if (!dealId) return;
    setApproveConfirm({ isOpen: false });
    await act(async () => {
      const r = await apiFetch(`/deals/${dealId}/approve`, { method: 'POST' });
      if (!r.ok) throw new Error(await r.text());
      const rr = await apiFetch(`/deals/${dealId}`, { method: 'GET' });
      if (rr.ok) setData(await rr.json());
    });
  }

  async function handleSubmitTemplate() {
    if (!dealId) return;
    setApproveConfirm({ isOpen: false });
    await act(async () => {
      const r = await apiFetch(`/deals/${dealId}/submit-template`, { method: 'POST' });
      if (!r.ok) throw new Error(await r.text());
      const rr = await apiFetch(`/deals/${dealId}`, { method: 'GET' });
      if (rr.ok) setData(await rr.json());
    });
  }

  async function handleCancel() {
    if (!dealId) return;
    setCancelConfirm({ isOpen: false });
    setCancelConfirmStep2({ isOpen: false });
    await act(async () => {
      const r = await apiFetch(`/deals/${dealId}/cancel`, { method: 'POST' });
      if (!r.ok) throw new Error(await r.text());
      const rr = await apiFetch(`/deals/${dealId}`, { method: 'GET' });
      if (rr.ok) setData(await rr.json());
    });
  }

  function shiftDay(deltaDays: number) {
    const base = /^\d{4}-\d{2}-\d{2}$/.test(slotsDay || '') ? new Date(`${slotsDay}T00:00:00Z`) : new Date();
    const next = new Date(base.getTime() + deltaDays * 24 * 60 * 60 * 1000);
    const y = next.getUTCFullYear();
    const m = String(next.getUTCMonth() + 1).padStart(2, '0');
    const d = String(next.getUTCDate()).padStart(2, '0');
    setSlotsDay(`${y}-${m}-${d}`);
  }

  const isCustomTask = deal.creative_mode === 'custom_task';
  const myUserId = String((window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id || '');
  const isAdvertiser = String(deal.advertiser_id) === `tg_${myUserId}`;

  async function handleUpdateTerms() {
    if (!dealId) return;
    await act(async () => {
      const r = await apiFetch(`/deals/${dealId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          post_duration_hours: editedDuration,
          top_duration_hours: editedTopHours
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      const rr = await apiFetch(`/deals/${dealId}`, { method: 'GET' });
      if (rr.ok) setData(await rr.json());
      setIsEditingDuration(false);
    });
  }

  return (
    <>
      <AlertModal
        isOpen={alertModal.isOpen}
        title={alertModal.title}
        message={alertModal.message}
        buttonText="OK"
        onClose={() => setAlertModal({ isOpen: false, message: '' })}
      />

      <AlertModal
        isOpen={approveConfirm.isOpen}
        title="Approve creative?"
        message="Are you sure you want to approve this creative? The deal will move to the next stage."
        buttonText="Approve"
        onButtonClick={(!isCustomTask && deal?.status === 'creative_draft') ? handleSubmitTemplate : handleApprove}
        secondaryButtonText="Cancel"
        onSecondaryButtonClick={() => setApproveConfirm({ isOpen: false })}
        onClose={() => setApproveConfirm({ isOpen: false })}
      />

      <AlertModal
        isOpen={cancelConfirm.isOpen}
        title="Cancel Deal?"
        message={
          deal?.status === 'negotiation' || deal?.status === 'pending_payment'
            ? "Are you sure you want to cancel this deal?"
            : "Are you sure? Since funds are already in escrow, they will be automatically refunded to the advertiser."
        }
        buttonText="Yes, Cancel"
        onButtonClick={() => {
          setCancelConfirm({ isOpen: false });
          setCancelConfirmStep2({ isOpen: true });
        }}
        secondaryButtonText="Go Back"
        onSecondaryButtonClick={() => setCancelConfirm({ isOpen: false })}
        onClose={() => setCancelConfirm({ isOpen: false })}
      />

      <AlertModal
        isOpen={cancelConfirmStep2.isOpen}
        title="Final Confirmation"
        message="This action cannot be undone. Are you absolutely certain you want to cancel this deal?"
        buttonText="Confirm Cancellation"
        onButtonClick={handleCancel}
        secondaryButtonText="Back"
        onSecondaryButtonClick={() => {
          setCancelConfirmStep2({ isOpen: false });
          setCancelConfirm({ isOpen: true });
        }}
        onClose={() => setCancelConfirmStep2({ isOpen: false })}
      />
      <div className={styles.page}>
        <div className={`${styles.content} noScrollbar`}>

          {/* ── Deal Header ── */}
          <Card style={{ padding: '14px 16px' }}>
            <div className={styles.dealHeader}>
              <div className={styles.dealHeaderLeft}>
                <Text type="title2" weight="bold">Deal {deal.emoji} #{deal.id?.slice(0, 10)}</Text>
                <span className={styles.statusBadge}>{statusDescription()}</span>
              </div>
              {deal.created_at && (
                <span className={styles.dealDate}>{formatDate(deal.created_at)}</span>
              )}
            </div>
          </Card>

          {/* ── Channel ── */}
          <Card style={{ padding: '14px 16px' }}>
            <Text type="caption" color="secondary" weight="medium" style={{ marginBottom: 10, display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, opacity: 0.6 }}>Channel</Text>
            <div
              className={styles.channelBlock}
              onClick={() => {
                const handle = deal.channel_handle;
                if (handle) {
                  const url = `https://t.me/${handle}`;
                  const tg = (window as any).Telegram?.WebApp;
                  if (tg?.openTelegramLink) tg.openTelegramLink(url);
                  else window.open(url, '_blank');
                }
              }}
            >
              <div className={styles.channelAvatar}>
                {(deal.channel_name || deal.channel_handle || '?').charAt(0)}
              </div>
              <div className={styles.channelInfo}>
                <span className={styles.channelName}>
                  {deal.channel_handle ? `@${deal.channel_handle}` : (deal.channel_name || 'Unknown')}
                </span>
                {(deal.channel_category || deal.channel_language) && (
                  <div className={styles.channelMeta}>
                    {deal.channel_category && <span className={styles.channelMetaTag}>{deal.channel_category}</span>}
                    {deal.channel_category && deal.channel_language && <span className={styles.channelMetaDot}>·</span>}
                    {deal.channel_language && <span className={styles.channelMetaTag}>{deal.channel_language}</span>}
                  </div>
                )}
              </div>
              <div
                className={styles.statsButton}
                onClick={(e) => {
                  e.stopPropagation();
                  if (deal.channel_id) loadStats(deal.channel_id);
                }}
                title="View Statistics"
              >
                {loadingStats ? <Loader2 size={18} className={styles.spin} /> : <BarChart3 size={18} />}
              </div>
              <span className={styles.channelArrow}>›</span>
            </div>
            <div style={{ marginTop: 10 }}>
              <RatingBadge
                ratingAvg={deal.channel_rating_avg || 0}
                ratingCount={deal.channel_rating_count || 0}
                reviewsEndpoint={`/channels/${deal.channel_id}/reviews`}
              />
            </div>
          </Card>

          {/* ── Campaign / Advertiser ── */}
          <Card style={{ padding: '14px 16px' }}>
            <div className={styles.campaignSection}>
              <div className={styles.campaignRow}>
                <Text type="caption" color="secondary" weight="medium" style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, opacity: 0.6 }}>Campaign</Text>
                <div className={styles.advertiserBadge}>
                  <Text type="caption" color="secondary" weight="medium" style={{ fontSize: 11 }}>Advertiser</Text>
                  <RatingBadge
                    ratingAvg={data.advertiser_rating_avg || 0}
                    ratingCount={data.advertiser_rating_count || 0}
                    reviewsEndpoint={`/users/${deal.advertiser_id}/reviews`}
                    label="Advertiser Reviews"
                  />
                </div>
              </div>

              {deal.campaign_title && (
                <Text type="text" weight="bold" style={{ marginTop: 10, fontSize: 15 }}>
                  {deal.campaign_title}
                </Text>
              )}

              {deal.campaign_brief && (
                <div
                  className={styles.briefButton}
                  onClick={() => setAlertModal({
                    isOpen: true,
                    title: deal.campaign_title || 'Campaign Brief',
                    message: deal.campaign_brief || '',
                  })}
                >
                  <span>📋</span>
                  <Text type="text" weight="medium">Brief</Text>
                  <span className={styles.channelArrow}>›</span>
                </div>
              )}
            </div>
          </Card>

          {/* ── Deal Terms ── */}
          <Card style={{ padding: '14px 16px' }}>
            <Text type="caption" color="secondary" weight="medium" style={{ marginBottom: 12, display: 'block', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5, opacity: 0.6 }}>Deal Terms</Text>
            <div className={styles.termsGrid}>
              <div className={styles.termCell}>
                <Text type="caption" color="secondary">Format</Text>
                <Text type="text" weight="medium" style={{ textTransform: 'capitalize' }}>{deal.ad_format}</Text>
              </div>
              <div className={styles.termCell}>
                <Text type="caption" color="secondary">Mode</Text>
                <Text type="text" weight="medium">{isCustomTask ? 'By Prompt' : 'Template'}</Text>
              </div>
              <div className={styles.termCell}>
                <Text type="caption" color="secondary">Duration</Text>
                <Text type="text" weight="medium">
                  {deal.post_duration_hours || 24}h
                </Text>
              </div>
              {(deal.top_duration_hours ?? 0) > 0 && (
                <div className={styles.termCell}>
                  <Text type="caption" color="secondary">Top</Text>
                  <Text type="text" weight="medium" style={{ color: 'var(--color-accent-primary)' }}>
                    {deal.top_duration_hours}h
                  </Text>
                </div>
              )}
            </div>
            <div className={styles.totalPriceBlock}>
              <Text type="caption" color="secondary" weight="medium">Total Price</Text>
              <Text type="title2" weight="bold">{formatTON(deal.price_ton || 0)}</Text>
            </div>
          </Card>

          <Card>
            <Text type="title2">Status timeline</Text>
            {roadmap ? (
              <DealRoadmap steps={roadmap.steps} currentStep={roadmap.currentStep} completedUntilStep={roadmap.completedUntilStep} />
            ) : null}
          </Card>

          <Card className={styles.actionPanel}>
            {actionError ? (
              <Text type="caption" color="secondary" style={{ color: 'var(--color-danger)' }}>
                {actionError}
              </Text>
            ) : null}

            {deal.status === 'awaiting_confirmation' && (
              <div style={{ marginTop: 16 }}>
                <DealConfirmationCard
                  deal={deal}
                  isAdvertiser={isAdvertiser}
                  canConfirm={!!permissions.can_confirm_deal}
                  onConfirmSuccess={() => load()}
                />
              </div>
            )}

            {deal.status === 'negotiation' ? (
              isAdvertiser ? (
                <Card style={{ padding: 16 }}>
                  <Text type="title2" weight="bold" style={{ marginBottom: 4 }}>
                    Deal Terms
                  </Text>
                  <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 14 }}>
                    {deal.post_duration_hours
                      ? 'You can change the duration or wait for the channel owner to accept.'
                      : 'Choose the post duration and click Save. The channel owner will see the final price and decide.'}
                  </Text>

                  <div style={{
                    padding: 14,
                    borderRadius: 12,
                    border: '1px solid var(--color-border-separator)',
                    background: 'color-mix(in srgb, var(--color-accent-primary) 4%, var(--color-background-section))',
                  }}>
                    {isEditingDuration || !deal.post_duration_hours ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                        <div>
                          <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 8 }}>Post Duration</Text>
                          <select
                            value={editedDuration}
                            onChange={(e) => setEditedDuration(Number(e.target.value))}
                            style={{
                              width: '100%',
                              height: 44,
                              borderRadius: 10,
                              border: '1px solid var(--tg-theme-hint-color)',
                              padding: '0 12px',
                              background: 'var(--tg-theme-bg-color)',
                              color: 'var(--tg-theme-text-color)',
                              fontFamily: 'inherit',
                              fontSize: 15,
                            }}
                          >
                            <option value="1">1h</option>
                            <option value="6">6h</option>
                            <option value="12">12h</option>
                            <option value="24">24h</option>
                            <option value="48">48h</option>
                            <option value="72">72h</option>
                          </select>
                        </div>

                        <div>
                          <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 8 }}>Top duration (No interruptions)</Text>
                          <select
                            value={editedTopHours}
                            onChange={(e) => setEditedTopHours(Number(e.target.value))}
                            style={{
                              width: '100%',
                              height: 44,
                              borderRadius: 10,
                              border: '1px solid var(--tg-theme-hint-color)',
                              padding: '0 12px',
                              background: 'var(--tg-theme-bg-color)',
                              color: 'var(--tg-theme-text-color)',
                              fontFamily: 'inherit',
                              fontSize: 15,
                            }}
                          >
                            <option value="0">0h (No Top)</option>
                            <option value="1">1h</option>
                            <option value="2">2h</option>
                            <option value="3">3h</option>
                            <option value="4">4h</option>
                          </select>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                          <Text type="text" color="secondary">
                            Total: <b style={{ color: 'var(--color-foreground-primary)', fontSize: 18 }}>{formatTON((() => {
                              const basePrice = deal.channel_price_per_post_ton || 0;
                              const topPrice = deal.channel_price_top_hour_ton || 0;
                              const stepPct = deal.channel_top_price_step_pct || 0;
                              const multi = Math.ceil(editedDuration / 24);
                              const baseTotal = basePrice * multi;
                              const n = editedTopHours;
                              const topTotal = n > 0 ? (n * topPrice + topPrice * (stepPct / 100) * (n * (n - 1) / 2)) : 0;
                              return baseTotal + topTotal;
                            })())}</b>
                            {deal.channel_top_price_step_pct > 0 && (
                              <InfoTooltip
                                title="Progressive pricing"
                                content={`Each next hour of Top costs ${deal.channel_top_price_step_pct}% more than the previous one. This prevents excessively long channel locks by a single advertiser.`}
                                align="center"
                                position="top"
                              />
                            )}
                          </Text>
                        </div>

                        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                          {deal.post_duration_hours && (
                            <Button size="small" variant="secondary" fullWidth onClick={() => setIsEditingDuration(false)}>Cancel</Button>
                          )}
                          <Button size="small" fullWidth onClick={handleUpdateTerms} isLoading={isActing} disabled={isActing}>Save</Button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Text type="title" weight="bold">
                          {deal.post_duration_hours}h / {deal.top_duration_hours || 0}h
                        </Text>
                        <Button
                          size="small"
                          variant="outline"
                          fullWidth={false}
                          style={{ width: 'auto', minWidth: 100 }}
                          onClick={() => { setEditedDuration(deal.post_duration_hours || 24); setIsEditingDuration(true); }}
                        >
                          Change
                        </Button>
                      </div>
                    )}
                  </div>

                  {deal.post_duration_hours && !deal.negotiation_confirmed_by_advertiser && permissions.can_confirm_terms && (
                    <Button
                      style={{ marginTop: 14 }}
                      isLoading={isActing}
                      disabled={isActing}
                      onClick={() =>
                        act(async () => {
                          const r = await apiFetch(`/deals/${deal.id}/confirm-terms`, { method: 'POST' });
                          if (!r.ok) throw new Error(await r.text());
                          const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                          if (rr.ok) setData(await rr.json());
                        })
                      }
                    >
                      Confirm Terms
                    </Button>
                  )}

                  {deal.negotiation_confirmed_by_advertiser && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      marginTop: 14,
                      padding: '10px 12px',
                      borderRadius: 10,
                      background: 'color-mix(in srgb, var(--color-foreground-secondary) 8%, var(--color-background-section))',
                    }}>
                      <Text type="caption" color="secondary" style={{ fontSize: 12, lineHeight: 1.4 }}>
                        Waiting for the channel owner to accept. You'll get a notification once they respond.
                      </Text>
                    </div>
                  )}
                </Card>
              ) : permissions.can_accept ? (
                <Card style={{
                  padding: 16,
                  border: '1.5px solid var(--color-accent-primary)',
                  background: 'color-mix(in srgb, var(--color-accent-primary) 6%, var(--color-background-section))',
                }}>
                  <Text type="title2" weight="bold" style={{ marginBottom: 4 }}>
                    Confirm terms
                  </Text>
                  <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    Review the posting conditions and confirm if they work for you.
                  </Text>

                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: 12,
                    borderRadius: 12,
                    border: '1px solid var(--color-border-separator)',
                    background: 'color-mix(in srgb, var(--color-accent-primary) 3%, var(--color-background-section))',
                    marginBottom: 14,
                  }}>
                    <div>
                      <Text type="caption" color="secondary" style={{ fontSize: 11, marginBottom: 2, display: 'block' }}>Duration / Top</Text>
                      <Text type="title" weight="bold">{deal.post_duration_hours || 24}h / {deal.top_duration_hours || 0}h</Text>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <Text type="caption" color="secondary" style={{ fontSize: 11, marginBottom: 2, display: 'block' }}>Price</Text>
                      <Text type="title" weight="bold">{formatTON(deal.price_ton || 0)}</Text>
                    </div>
                  </div>

                  <Button
                    isLoading={isActing}
                    disabled={isActing}
                    onClick={() =>
                      act(async () => {
                        const r = await apiFetch(`/deals/${deal.id}/accept`, { method: 'POST' });
                        if (!r.ok) throw new Error(await r.text());
                        const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                        if (rr.ok) setData(await rr.json());
                      })
                    }
                  >
                    Confirm
                  </Button>
                </Card>
              ) : !isAdvertiser ? (
                <Card style={{ padding: 16 }}>
                  <Text type="title2" weight="bold" style={{ marginBottom: 4 }}>
                    Waiting for Advertiser
                  </Text>
                  <Text type="caption" color="secondary" style={{ display: 'block' }}>
                    The advertiser hasn't confirmed the post duration yet. You'll be able to accept once they do.
                  </Text>
                </Card>
              ) : null
            ) : null}

            {/* Creative intake flow */}
            {deal.status === 'creative_draft' && (
              <Card style={{ marginTop: 12, padding: 12 }}>
                {!isCustomTask ? (
                  // Template mode: Advertiser selects a template
                  <>
                    {permissions.can_use_template && !deal.creative_chat_id ? (
                      <>
                        {templates && templates.length > 0 && (
                          <div>
                            <Text type="title2" weight="bold" style={{ marginBottom: 12 }}>
                              Select template
                            </Text>
                            <select
                              value={selectedTemplateId || (deal.creative_chat_id ? 'selected' : '')}
                              disabled={!permissions.can_use_template}
                              onChange={(e) => {
                                if (e.target.value && e.target.value !== 'selected') {
                                  const tplId = e.target.value;
                                  setSelectedTemplateId(tplId);
                                  void act(async () => {
                                    const r = await apiFetch(`/deals/${deal.id}/use-template`, {
                                      method: 'POST',
                                      headers: { 'Content-Type': 'application/json' },
                                      body: JSON.stringify({ template_id: tplId }),
                                    });
                                    if (!r.ok) throw new Error(await r.text());
                                    const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                                    if (rr.ok) {
                                      setData(await rr.json());
                                      setSelectedTemplateId('');
                                    }
                                  });
                                }
                              }}
                              style={{
                                width: '100%',
                                height: 44,
                                borderRadius: 12,
                                border: '1px solid var(--tg-theme-hint-color, #e0e0e0)',
                                padding: '0 12px',
                                background: 'var(--tg-theme-bg-color, #fff)',
                                color: 'var(--tg-theme-text-color, #000)',
                                fontFamily: 'inherit',
                                marginBottom: 12,
                              }}
                            >
                              <option value="">Select template…</option>
                              {(templates || [])
                                .filter((t) => t.has_content)
                                .map((t) => (
                                  <option key={t.id} value={t.id}>
                                    {t.title}
                                  </option>
                                ))}
                            </select>
                          </div>
                        )}
                      </>
                    ) : (
                      <div style={{ padding: '8px 0' }}>
                        <Text type="text" color="secondary">
                          {deal.creative_chat_id
                            ? "Advertiser has selected a template and is finalizing it."
                            : "Waiting for the advertiser to provide the ad post."}
                        </Text>
                      </div>
                    )}

                    {permissions.can_use_template && deal.creative_chat_id && deal.creative_message_ids && (
                      <div>
                        {deal.creative_preview_has_media && (
                          <div style={{ marginBottom: 12 }}>
                            {deal.creative_preview_count && deal.creative_preview_count > 1 ? (
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                                {Array.from({ length: Math.min(3, deal.creative_preview_count) }).map((_, idx) => (
                                  <img
                                    key={idx}
                                    src={`/api/deals/${deal.id}/preview-media?i=${idx}&initData=${encodeURIComponent(tgInitData())}`}
                                    alt={`Preview ${idx + 1}`}
                                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                                    style={{ width: '100%', height: 84, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                                  />
                                ))}
                              </div>
                            ) : (
                              <img
                                src={`/api/deals/${deal.id}/preview-media?i=0&initData=${encodeURIComponent(tgInitData())}`}
                                alt="Preview"
                                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                                style={{ width: '100%', maxHeight: 180, objectFit: 'cover', borderRadius: 12, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                              />
                            )}
                          </div>
                        )}
                        {deal.creative_preview_text && (
                          <Text type="caption" color="secondary" style={{ marginBottom: 12, display: 'block' }}>
                            <span dangerouslySetInnerHTML={{ __html: deal.creative_preview_text }} />
                          </Text>
                        )}

                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                          <Button
                            isLoading={isActing}
                            disabled={isActing || !permissions.can_submit_creative}
                            onClick={() => setApproveConfirm({ isOpen: true })}
                          >
                            Approve template
                          </Button>
                          <Button
                            variant="outline"
                            isLoading={isActing}
                            disabled={isActing || !botUsername}
                            onClick={() =>
                              act(async () => {
                                const r = await apiFetch(`/deals/${deal.id}/preview-template`, { method: 'POST' });
                                if (!r.ok) throw new Error(await r.text());
                                setAlertModal({
                                  isOpen: true,
                                  title: 'Preview sent',
                                  message: 'Preview sent to channel owner in Telegram bot.',
                                });
                              })
                            }
                          >
                            Preview
                          </Button>
                          {botUsername && permissions.can_submit_creative && (
                            <Button
                              variant="secondary"
                              onClick={() => openTelegramLink(`https://t.me/${botUsername}?start=sub_${deal.id}`)}
                            >
                              Submit manually in Bot
                            </Button>
                          )}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  // By Prompt mode: Channel owner submits
                  <>
                    <Text type="title2" weight="bold">Creative Submission</Text>

                    {deal.creative_instructions && (
                      <div style={{
                        marginTop: 12,
                        marginBottom: 16,
                        padding: 16,
                        borderRadius: 12,
                        background: 'color-mix(in srgb, var(--color-background-secondary) 50%, var(--color-background-section))',
                        border: '1px dashed var(--color-border-separator)',
                      }}>
                        <Text type="caption" color="secondary" weight="bold" style={{ display: 'block', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          By Prompt
                        </Text>
                        <Text type="text" color="primary" style={{ display: 'block', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                          {deal.creative_instructions}
                        </Text>
                      </div>
                    )}

                    {permissions.can_submit_creative ? (
                      <div style={{ marginTop: 8 }}>
                        <Text type="text" color="secondary">
                          You need to write the post for this deal based on the prompt above. Send the content (text/media/album) to our bot to submit it for advertiser review.
                        </Text>
                        {botUsername && (
                          <Button
                            variant="primary"
                            onClick={() => openTelegramLink(`https://t.me/${botUsername}?start=sub_${deal.id}`)}
                            style={{ marginTop: 12 }}
                          >
                            Submit Post in Bot
                          </Button>
                        )}
                      </div>
                    ) : (
                      <div style={{ marginTop: 8 }}>
                        <Text type="text" color="secondary">
                          Waiting for the channel owner to submit the post for review.
                        </Text>
                      </div>
                    )}
                  </>
                )}
              </Card>
            )}

            {/* Creative Review */}
            {deal.status === 'creative_review' && (
              <Card style={{ marginTop: 12, padding: 12 }}>
                <Text type="title2" weight="bold">Creative Review</Text>

                {permissions.can_approve || permissions.can_request_edits ? (
                  <Text type="caption" color="secondary" style={{ marginTop: 4, display: 'block' }}>
                    Review the creative below or use Telegram preview, then approve or reject.
                  </Text>
                ) : (
                  <Text type="caption" color="secondary" style={{ marginTop: 4, display: 'block' }}>
                    {isCustomTask ? 'Waiting for advertiser review.' : 'Waiting for channel owner review.'}
                  </Text>
                )}

                {(deal.creative_preview_text || deal.creative_preview_has_media) && (
                  <div style={{ marginTop: 12 }}>
                    {deal.creative_preview_has_media && (
                      deal.creative_preview_count && deal.creative_preview_count > 1 ? (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                          {Array.from({ length: Math.min(3, deal.creative_preview_count) }).map((_, idx) => (
                            <img
                              key={idx}
                              src={`/api/deals/${deal.id}/preview-media?i=${idx}&initData=${encodeURIComponent(tgInitData())}`}
                              alt={`Preview ${idx + 1}`}
                              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                              style={{ width: '100%', height: 84, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                            />
                          ))}
                        </div>
                      ) : (
                        <img
                          src={`/api/deals/${deal.id}/preview-media?i=0&initData=${encodeURIComponent(tgInitData())}`}
                          alt="Preview"
                          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                          style={{ width: '100%', maxHeight: 200, objectFit: 'cover', borderRadius: 12, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                        />
                      )
                    )}
                    {deal.creative_preview_text && (
                      <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                        <span dangerouslySetInnerHTML={{ __html: deal.creative_preview_text }} />
                      </Text>
                    )}
                    {deal.creative_preview_count && deal.creative_preview_count > 1 && (
                      <Text type="caption" color="secondary" style={{ marginTop: 4, display: 'block' }}>
                        Album • {deal.creative_preview_count} items
                      </Text>
                    )}
                  </div>
                )}

                {botUsername && (
                  <Button
                    variant="outline"
                    size="small"
                    fullWidth={false}
                    onClick={() => openTelegramLink(`https://t.me/${botUsername}?start=deal_${deal.id}`)}
                    style={{ marginTop: 8 }}
                  >
                    View in Telegram
                  </Button>
                )}

                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  {permissions.can_approve && (
                    <Button
                      isLoading={isActing}
                      disabled={isActing}
                      onClick={() => setApproveConfirm({ isOpen: true })}
                    >
                      Approve
                    </Button>
                  )}
                  {permissions.can_request_edits && (
                    <Button
                      variant="outline"
                      isLoading={isActing}
                      disabled={isActing}
                      onClick={() =>
                        act(async () => {
                          const r = await apiFetch(`/deals/${deal.id}/request-edits`, { method: 'POST' });
                          if (!r.ok) throw new Error(await r.text());
                          const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                          if (rr.ok) setData(await rr.json());
                        })
                      }
                    >
                      Reject
                    </Button>
                  )}
                </div>
              </Card>
            )}

            {deal.status === 'scheduled' && deal.scheduled_at && (
              <Card style={{ marginTop: 12, padding: 16 }}>
                <Text type="title2" weight="bold" style={{ marginBottom: 12 }}>
                  Publication scheduled
                </Text>
                <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 16 }}>
                  The post will be automatically published at the scheduled time.
                </Text>
                <CountdownTimer
                  targetDate={deal.scheduled_at}
                  onFinish={load}
                  label="Posting in"
                />
              </Card>
            )}

            {/* Variant A scheduling */}
            {(deal.status === 'approved' || deal.status === 'scheduling') && (
              <Card style={{ marginTop: 12, padding: 12 }}>
                <Text type="title2" weight="bold" style={{ marginBottom: 6 }}>
                  Scheduling
                </Text>

                {slotsError ? (
                  <Text type="caption" color="secondary"> {slotsError} </Text>
                ) : null}

                {loadingSlots && !slotsData ? (
                  <Text type="caption" color="secondary"> Loading slots… </Text>
                ) : null}

                {slotsData ? (
                  <>
                    <Text type="caption" color="secondary" style={{ display: 'block' }}>
                      Timezone: <b>{String(slotsData.timezone || 'UTC')}</b>
                    </Text>
                    <Text type="caption" color="secondary" style={{ display: 'block', marginTop: 4 }}>
                      Window: <b>{String(slotsData.window_start || '10:00')}</b> — <b>{String(slotsData.window_end || '20:00')}</b>, slot <b>{Number(slotsData.slot_minutes || 30)}m</b>
                    </Text>

                    <div className={styles.slotsHeader}>
                      <Button variant="outline" size="small" fullWidth={false} onClick={() => shiftDay(-1)}> Prev </Button>
                      <Text type="caption" color="secondary"> {String(slotsDay || slotsData.date || '')} </Text>
                      <Button variant="outline" size="small" fullWidth={false} onClick={() => shiftDay(1)}> Next </Button>
                    </div>

                    <div className={styles.slotsGrid}>
                      {(slotsData.slots || []).map((s: any) => {
                        const isBusy = Boolean(s.busy);
                        const isRequested = Boolean(s.requested);
                        const isScheduled = Boolean(s.scheduled);
                        const isSelectedLocally = permissions.can_request_slot && selectedLocalSlot === s.local;
                        const label = String(s.local || '').slice(11);
                        const className = [
                          styles.slotBtn,
                          isBusy ? styles.slotBtnBusy : '',
                          isRequested ? styles.slotBtnRequested : '',
                          isScheduled ? styles.slotBtnScheduled : '',
                          isSelectedLocally ? styles.slotBtnSelected : '',
                        ].filter(Boolean).join(' ');

                        const canRequest = Boolean(permissions.can_request_slot);
                        const clickable = canRequest && !isBusy && !isRequested && !isScheduled;

                        return (
                          <button
                            key={String(s.key || s.local || label)}
                            className={className}
                            disabled={!clickable}
                            onClick={() => { if (!clickable) return; setSelectedLocalSlot(s.local); }}
                          >
                            {label || '—'}
                          </button>
                        );
                      })}
                    </div>

                    {permissions.can_request_slot ? (
                      <div style={{ marginTop: 10 }}>
                        <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 10 }}>
                          Tap a free slot to select it, then confirm your choice below.
                        </Text>
                        <Button
                          disabled={!selectedLocalSlot || isActing}
                          isLoading={isActing}
                          onClick={() => {
                            if (!selectedLocalSlot) return;
                            act(async () => {
                              const r = await apiFetch(`/deals/${deal.id}/request-slot`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ local_datetime: String(selectedLocalSlot) }),
                              });
                              if (!r.ok) throw new Error(await r.text());
                              const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                              if (rr.ok) {
                                setData(await rr.json());
                                setSelectedLocalSlot(null);
                              }
                            });
                          }}
                        >
                          Request selected slot
                        </Button>
                      </div>
                    ) : permissions.can_approve_slot ? (
                      <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                        The advertiser will choose a slot. After they request it, you can approve it below.
                      </Text>
                    ) : null}

                    {permissions.can_approve_slot ? (
                      <Button
                        style={{ marginTop: 10 }}
                        isLoading={isActing}
                        disabled={isActing || !(slotsData.slots || []).some((s: any) => Boolean(s.requested))}
                        onClick={() =>
                          act(async () => {
                            const r = await apiFetch(`/deals/${deal.id}/approve-slot`, { method: 'POST' });
                            if (!r.ok) throw new Error(await r.text());
                            const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                            if (rr.ok) setData(await rr.json());
                          })
                        }
                      >
                        Approve requested slot
                      </Button>
                    ) : null}
                  </>
                ) : null}

              </Card>
            )}

            {deal.status === 'posted' && deal.published_at && !deal.post_not_found && (
              <Card style={{ marginTop: 12, padding: 16 }}>
                <Text type="title2" weight="bold" style={{ marginBottom: 12 }}>
                  Verification pending
                </Text>

                <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 16 }}>
                  The bot will check the post after the duration ends. If the post is found and correct, funds will be released automatically.
                </Text>

                <CountdownTimer
                  targetDate={new Date(new Date(deal.published_at).getTime() + (deal.post_duration_hours || 24) * 60 * 60 * 1000).toISOString()}
                  onFinish={load}
                  label="Auto-release in"
                />
              </Card>
            )}

            {/* Top placement timer */}
            {deal.published_at && (deal.top_duration_hours ?? 0) > 0 && (() => {
              const topEndTime = new Date(new Date(deal.published_at).getTime() + deal.top_duration_hours * 60 * 60 * 1000);
              const topExpired = new Date() >= topEndTime;

              // Violated
              if (deal.top_violated) {
                return (
                  <Card style={{ marginTop: 12, padding: 16, border: '1px solid color-mix(in srgb, var(--color-state-destructive, #e53935) 35%, var(--color-border-separator))', background: 'color-mix(in srgb, var(--color-state-destructive, #e53935) 10%, var(--color-background-section))' }}>
                    <Text type="title2" weight="bold" style={{ marginBottom: 8, color: 'var(--color-state-destructive, #e53935)' }}>
                      ⚠️ Top placement violated
                    </Text>
                    <Text type="caption" color="secondary" style={{ display: 'block' }}>
                      New posts appeared in the channel during the top placement period ({deal.top_duration_hours}h). The channel owner has breached the agreement.
                    </Text>
                  </Card>
                );
              }

              // Passed — top period ended, not violated
              if (topExpired && !deal.top_violated) {
                return (
                  <Card style={{ marginTop: 12, padding: 16, border: '1px solid color-mix(in srgb, var(--color-state-success, #4caf50) 35%, var(--color-border-separator))', background: 'color-mix(in srgb, var(--color-state-success, #4caf50) 10%, var(--color-background-section))' }}>
                    <Text type="title2" weight="bold" style={{ marginBottom: 8, color: 'var(--color-state-success, #4caf50)' }}>
                      ✅ Top placement confirmed
                    </Text>
                    <Text type="caption" color="secondary" style={{ display: 'block' }}>
                      The post remained at the top of the channel for the full {deal.top_duration_hours}h period. No violations detected.
                    </Text>
                  </Card>
                );
              }

              // Still counting
              if (deal.status === 'posted') {
                return (
                  <Card style={{ marginTop: 12, padding: 16 }}>
                    <Text type="title2" weight="bold" style={{ marginBottom: 12 }}>
                      Top placement active
                    </Text>
                    <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 16 }}>
                      The post must stay at the top of the channel for {deal.top_duration_hours}h. No new posts are allowed during this period.
                    </Text>
                    <CountdownTimer
                      targetDate={topEndTime.toISOString()}
                      onFinish={load}
                      label="Top placement ends in"
                    />
                  </Card>
                );
              }

              return null;
            })()}

            {deal.status === 'posted' && deal.post_not_found && permissions.can_release && (
              <Card style={{ marginTop: 12, padding: 16 }}>
                <Text type="title2" weight="bold" style={{ marginBottom: 12, color: 'var(--color-warning, #f5a623)' }}>
                  ⚠️ Post not found
                </Text>

                <Text type="caption" color="secondary" style={{ display: 'block', marginBottom: 16 }}>
                  The bot could not find the published post in the channel. It may have been deleted. Would you like to release the funds to the channel owner anyway?
                </Text>

                <div style={{ display: 'flex', gap: 8 }}>
                  <Button
                    isLoading={isActing}
                    disabled={isActing}
                    onClick={() =>
                      act(async () => {
                        const r = await apiFetch(`/deals/${deal.id}/release`, { method: 'POST' });
                        if (!r.ok) throw new Error(await r.text());
                        const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                        if (rr.ok) setData(await rr.json());
                      })
                    }
                    style={{ flex: 1 }}
                  >
                    Yes, release funds
                  </Button>
                  <Button
                    isLoading={isActing}
                    disabled={isActing}
                    onClick={() =>
                      setAlertModal({ isOpen: true, title: 'Contact support', message: 'To dispute this deal, please contact @AdMarketplaceSupport in Telegram.' })
                    }
                    style={{ flex: 1, background: 'var(--color-danger, #e53935)', color: '#fff' }}
                  >
                    Dispute
                  </Button>
                </div>
              </Card>
            )}



            {deal.status === 'pending_payment' && permissions.can_pay && !paymentInfo && !deal.escrow_address && (
              <Button
                isLoading={isActing}
                disabled={isActing}
                onClick={() =>
                  act(async () => {
                    const r = await apiFetch(`/deals/${deal.id}/pay`, { method: 'POST' });
                    if (!r.ok) throw new Error(await r.text());
                    const paymentData = await r.json();
                    setPaymentInfo({
                      escrow_address: paymentData.escrow_address,
                      amount_ton: paymentData.amount_ton,
                      network: paymentData.network,
                    });
                    const rr = await apiFetch(`/deals/${deal.id}`, { method: 'GET' });
                    if (rr.ok) setData(await rr.json());
                  })
                }
              >
                Get payment instructions
              </Button>
            )}

            {/* Payment instructions card */}
            {(paymentInfo || deal.escrow_address) && deal.status === 'pending_payment' && (
              isAdvertiser ? (
                <Card style={{ marginTop: 16, padding: 16 }}>
                  <Text type="title2" style={{ marginBottom: 16 }}> Payment Instructions </Text>

                  <div style={{ marginBottom: 16 }}>
                    <Text type="caption" color="secondary" style={{ marginBottom: 8, display: 'block' }}> Amount to send: </Text>
                    <Text type="title" weight="bold" style={{ fontSize: '24px', marginBottom: 16 }}>
                      {formatTON(paymentInfo?.amount_ton || deal.expected_amount_ton || deal.price_ton || 0)}
                    </Text>
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <Text type="caption" color="secondary" style={{ marginBottom: 8, display: 'block' }}> Escrow wallet address: </Text>
                    <div
                      style={{
                        fontFamily: 'monospace',
                        fontSize: '12px',
                        wordBreak: 'break-all',
                        padding: '12px',
                        backgroundColor: 'var(--tg-theme-bg-color, #ffffff)',
                        borderRadius: '8px',
                        border: '1px solid var(--tg-theme-hint-color, #e0e0e0)',
                        marginBottom: 12,
                        cursor: 'pointer',
                      }}
                      onClick={() => {
                        const address = paymentInfo?.escrow_address || deal.escrow_address;
                        if (address && navigator.clipboard) {
                          navigator.clipboard.writeText(address);
                          setAlertModal({ isOpen: true, title: 'Copied', message: 'Address copied to clipboard' });
                        }
                      }}
                    >
                      {paymentInfo?.escrow_address || deal.escrow_address}
                    </div>
                    <Text type="caption" color="secondary" style={{ fontSize: '11px' }}>
                      Click to copy
                    </Text>
                  </div>

                  <Text type="text" color="secondary" style={{ fontSize: '13px', lineHeight: '1.5' }}>
                    Send exactly {formatTON(paymentInfo?.amount_ton || deal.expected_amount_ton || deal.price_ton || 0)} to the address above.
                    The payment will be automatically confirmed once received.
                  </Text>
                </Card>
              ) : (
                <Card style={{ marginTop: 16, padding: 16 }}>

                  <div style={{ marginBottom: 16 }}>
                    <Text type="caption" color="secondary" style={{ marginBottom: 8, display: 'block' }}> Deal Amount: </Text>
                    <Text type="title" weight="bold" style={{ fontSize: '24px', marginBottom: 16 }}>
                      {formatTON(paymentInfo?.amount_ton || deal.expected_amount_ton || deal.price_ton || 0)}
                    </Text>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <Text type="caption" color="secondary" style={{ marginBottom: 4, display: 'block' }}> Escrow Address: </Text>
                    <Text type="text" style={{ fontFamily: 'monospace', fontSize: '12px', wordBreak: 'break-all' }}>
                      {paymentInfo?.escrow_address || deal.escrow_address}
                    </Text>
                  </div>

                  <Text type="text" color="secondary" style={{ fontSize: '13px', lineHeight: '1.5' }}>
                    <br />
                    Awaiting payment from the advertiser.
                  </Text>
                </Card>
              )
            )}

            {deal.status === 'released' && (
              <Card style={{ marginTop: 12, padding: 14, border: '1px solid color-mix(in srgb, var(--color-state-success) 35%, var(--color-border-separator))', background: 'color-mix(in srgb, var(--color-state-success) 10%, var(--color-background-section))' }}>
                <Text type="title2" weight="bold" style={{ color: 'var(--color-state-success)' }}> Deal complete! </Text>
                <Text type="caption" color="secondary" style={{ marginTop: 6, display: 'block' }}> Funds were released and the deal is finished. </Text>
              </Card>
            )}

            {(deal.status === 'cancelled' || deal.status === 'refunded') && (
              <Card style={{ marginTop: 12, padding: 14, border: '1px solid color-mix(in srgb, var(--color-state-destructive) 35%, var(--color-border-separator))', background: 'color-mix(in srgb, var(--color-state-destructive) 10%, var(--color-background-section))' }}>
                <Text type="title2" weight="bold" style={{ color: 'var(--color-state-destructive)' }}>
                  Deal {deal.status === 'refunded' ? 'refunded' : 'cancelled'}
                </Text>
                <Text type="caption" color="secondary" style={{ marginTop: 6, display: 'block' }}>
                  {deal.status === 'refunded' ? 'Funds were returned to the advertiser.' : 'The deal was cancelled before payment.'}
                </Text>
              </Card>
            )}

            {(reviewSubmitted || myReview || permissions.can_review) && (
              <Card style={{ marginTop: 12, padding: 16 }}>
                <Text type="title2" weight="bold" style={{ marginBottom: 12 }}>
                  Rate this deal
                </Text>
                {reviewSubmitted || myReview ? (
                  <>
                    <StarRating value={myReview?.rating || reviewRating} readonly size={32} />
                    {(myReview?.comment || reviewComment) && (
                      <Text type="text" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                        {myReview?.comment || reviewComment}
                      </Text>
                    )}
                    <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block', opacity: 0.7 }}>
                      Your review has been submitted
                    </Text>
                  </>
                ) : (
                  <>
                    <StarRating value={reviewRating} onChange={setReviewRating} size={36} />
                    <textarea
                      placeholder="Leave a comment (optional)"
                      value={reviewComment}
                      onChange={(e) => setReviewComment(e.target.value)}
                      maxLength={500}
                      style={{
                        width: '100%',
                        minHeight: 70,
                        marginTop: 12,
                        padding: 12,
                        borderRadius: 12,
                        border: '1px solid var(--color-border-separator)',
                        background: 'var(--color-background-section)',
                        color: 'var(--color-foreground-primary)',
                        fontFamily: 'inherit',
                        fontSize: 14,
                        resize: 'vertical',
                        boxSizing: 'border-box',
                      }}
                    />
                    <Button
                      style={{ marginTop: 12 }}
                      disabled={reviewRating === 0 || isActing}
                      isLoading={isActing}
                      onClick={() => {
                        setIsActing(true);
                        setActionError('');
                        (async () => {
                          try {
                            const r = await apiFetch(`/deals/${deal.id}/review`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({ rating: reviewRating, comment: reviewComment }),
                            });
                            if (!r.ok) {
                              const err = await r.json();
                              throw new Error(err.detail || 'Failed to submit review');
                            }
                            setMyReview({ rating: reviewRating, comment: reviewComment });
                            setReviewSubmitted(true);
                          } catch (e: any) {
                            setActionError(String(e?.message || 'Failed to submit review'));
                          } finally {
                            setIsActing(false);
                          }
                        })();
                      }}
                    >
                      Submit review
                    </Button>
                  </>
                )}
              </Card>
            )}

            {permissions.can_cancel && (
              <div className={styles.dangerZone}>
                <Button
                  variant="danger"
                  onClick={() => setCancelConfirm({ isOpen: true })}
                  disabled={isActing}
                  isLoading={isActing}
                >
                  Cancel Deal
                </Button>
              </div>
            )}

          </Card>
        </div >
      </div >

      <BottomSheet
        isOpen={Boolean(statsChannel)}
        onClose={() => setStatsChannel(null)}
        title="Channel Details"
      >
        {statsChannel && (
          <div style={{ paddingBottom: 20 }}>
            <ChannelStats channel={statsChannel} />
          </div>
        )}
      </BottomSheet>
    </>
  );
}
