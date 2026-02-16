import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge, Button, DealCard, Text } from '../../ui';
import { prettyDealStatus, DEAL_STATUS_ORDER } from '../../domain/dealStatus';
import { formatTON } from '../../utils/format';
import styles from './DealsPage.module.scss';
import { apiFetch } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';

type DealsTab = 'my' | 'incoming';

const MILESTONE_STATUSES = new Set([
  'funds_held', 'approved', 'awaiting_confirmation', 'scheduled', 'posted', 'verified',
]);

function displayDealStatus(rawStatus: string): string {
  if (MILESTONE_STATUSES.has(rawStatus) && rawStatus !== 'released' && rawStatus !== 'cancelled' && rawStatus !== 'refunded') {
    const order = DEAL_STATUS_ORDER;
    const idx = order.indexOf(rawStatus as any);
    if (idx >= 0 && idx < order.length - 1) {
      return order[idx + 1];
    }
  }
  return rawStatus;
}

function statusTone(status: string): 'default' | 'accent' | 'success' | 'warning' | 'danger' {
  switch (status) {
    case 'pending_payment': return 'warning';
    case 'pending': return 'warning';
    case 'negotiation': return 'warning';
    case 'creative_draft': return 'accent';
    case 'creative_review': return 'accent';
    case 'approved': return 'success';
    case 'scheduling': return 'accent';
    case 'scheduled': return 'accent';
    case 'posted': return 'default';
    case 'verified': return 'default';
    case 'released': return 'success';
    case 'cancelled':
    case 'refunded': return 'danger';
    default: return 'default';
  }
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      stiffness: 300,
      damping: 24
    }
  }
};

export function DealsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<DealsTab>(() => {
    const raw = localStorage.getItem('deals_tab');
    return raw === 'incoming' ? 'incoming' : 'my';
  });

  const [profileId, setProfileId] = useState<string>('');
  const [deals, setDeals] = useState<any[] | null>(null);
  const [myCampaignOffers, setMyCampaignOffers] = useState<any[] | null>(null);
  const [incomingCampaignOffers, setIncomingCampaignOffers] = useState<any[] | null>(null);
  const [myChannelOffers, setMyChannelOffers] = useState<any[] | null>(null);
  const [incomingChannelOffers, setIncomingChannelOffers] = useState<any[] | null>(null);

  const [error, setError] = useState<string>('');
  const [startingOfferId, setStartingOfferId] = useState<string>('');
  const [cancellingOfferId, setCancellingOfferId] = useState<string>('');
  const [actionError, setActionError] = useState<string>('');
  const [cancelConfirm, setCancelConfirm] = useState<{ isOpen: boolean; offerId: string; title: string }>({
    isOpen: false,
    offerId: '',
    title: '',
  });
  const [showCompleted, setShowCompleted] = useState(false);
  const [showArchived, setShowArchived] = useState(false);

  useEffect(() => {
    localStorage.setItem('deals_tab', tab);
  }, [tab]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [p, d, myApps, incomingApps, myChOffers, incomingChOffers] = await Promise.all([
          apiFetch('/profile', { method: 'GET' }),
          apiFetch('/deals', { method: 'GET' }),
          apiFetch('/campaign-offers/my', { method: 'GET' }),
          apiFetch('/campaign-offers/incoming', { method: 'GET' }),
          apiFetch('/channel-offers/my', { method: 'GET' }),
          apiFetch('/channel-offers/incoming', { method: 'GET' }),
        ]);

        if (!p.ok) throw new Error(await p.text());
        if (!d.ok) throw new Error(await d.text());
        if (!myApps.ok) throw new Error(await myApps.text());
        if (!incomingApps.ok) throw new Error(await incomingApps.text());
        if (!myChOffers.ok) throw new Error(await myChOffers.text());
        if (!incomingChOffers.ok) throw new Error(await incomingChOffers.text());

        const profile = (await p.json()) as { id: string };
        const dealsData = (await d.json()) as any[];
        const myAppsData = (await myApps.json()) as any[];
        const incomingAppsData = (await incomingApps.json()) as any[];
        const myChOffersData = (await myChOffers.json()) as any[];
        const incomingChOffersData = (await incomingChOffers.json()) as any[];

        if (!cancelled) {
          setProfileId(String(profile.id || ''));
          setDeals(dealsData);
          setMyCampaignOffers(myAppsData);
          setIncomingCampaignOffers(incomingAppsData);
          setMyChannelOffers(myChOffersData);
          setIncomingChannelOffers(incomingChOffersData);
        }
      } catch (e: any) {
        if (!cancelled) {
          setDeals([]);
          setMyCampaignOffers([]);
          setIncomingCampaignOffers([]);
          setMyChannelOffers([]);
          setIncomingChannelOffers([]);
          setError(String(e?.message || e || 'Failed to load offers'));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const incomingDealIds = useMemo(() => {
    const ids = new Set<string>();
    (incomingCampaignOffers || []).forEach((o) => {
      if (o.deal_id) ids.add(String(o.deal_id));
    });
    (incomingChannelOffers || []).forEach((o) => {
      if (o.deal_id) ids.add(String(o.deal_id));
    });
    return ids;
  }, [incomingCampaignOffers, incomingChannelOffers]);

  const myDealIds = useMemo(() => {
    const ids = new Set<string>();
    (myCampaignOffers || []).forEach((o) => {
      if (o.deal_id) ids.add(String(o.deal_id));
    });
    (myChannelOffers || []).forEach((o) => {
      if (o.deal_id) ids.add(String(o.deal_id));
    });
    return ids;
  }, [myCampaignOffers, myChannelOffers]);

  const dealItems = useMemo(() => {
    const me = profileId;
    return (deals || [])
      .map((d) => {
        let direction: 'my' | 'incoming' = me && String(d.advertiser_id || '') === me ? 'my' : 'incoming';

        // Refine direction based on initiative:
        // If it came from an incoming application/offer, it stays incoming.
        if (incomingDealIds.has(String(d.id))) {
          direction = 'incoming';
        } else if (myDealIds.has(String(d.id))) {
          direction = 'my';
        }

        return {
          kind: 'deal' as const,
          id: String(d.id || ''),
          channelId: String(d.channel_id || ''),
          channelName: String(d.channel_name || d.channel_id || ''),
          advertiserId: String(d.advertiser_id || ''),
          status: String(d.status || ''),
          adFormat: String(d.ad_format || 'post'),
          priceTON: Number(d.price_ton || 0),
          negotiationConfirmedByAdvertiser: Boolean(d.negotiation_confirmed_by_advertiser),
          negotiationConfirmedByChannel: Boolean(d.negotiation_confirmed_by_channel),
          waitingForCreative: Boolean(d.waiting_for_creative),
          creativeMode: String(d.creative_mode || 'template'),
          createdAt: String(d.created_at || ''),
          emoji: String(d.emoji || ''),
          direction,
          isAdvertiser: me && String(d.advertiser_id || '') === me,
        };
      })
      .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
  }, [deals, profileId, incomingDealIds, myDealIds]);

  const myOffers = useMemo(() => {
    const dealPart = dealItems.filter((x) => x.direction === 'my');
    const campPart = (myCampaignOffers || [])
      .filter((a) => !a.deal_id)
      .map((a) => ({
        kind: 'campaign_offer' as const,
        id: String(a.id || ''),
        campaignId: String(a.campaign_id || ''),
        campaignTitle: String(a.campaign_title || ''),
        channelId: String(a.channel_id || ''),
        channelName: String(a.channel_name || a.channel_id || ''),
        status: String(a.status || ''),
        dealId: String(a.deal_id || ''),
        dealStatus: String(a.deal_status || ''),
        offerTON: Number(a.offer_price_ton || 0),
        message: String(a.message || ''),
        createdAt: String(a.created_at || ''),
        template_id: String(a.template_id || ''),
        template_preview_text: String(a.template_preview_text || ''),
        template_preview_has_media: Boolean(a.template_preview_has_media),
        template_preview_count: Number(a.template_preview_count || 0),
      }));
    const channelOfferPart = (myChannelOffers || [])
      .filter((a) => !a.deal_id)
      .map((a) => ({
        kind: 'channel_offer' as const,
        id: String(a.id || ''),
        channelId: String(a.channel_id || ''),
        channelName: String(a.channel_name || a.channel_id || ''),
        status: String(a.status || ''),
        dealId: String(a.deal_id || ''),
        dealStatus: String(a.deal_status || ''),
        offerTON: Number(a.offer_price_ton || 0),
        message: String(a.message || ''),
        createdAt: String(a.created_at || ''),
      }));
    return [...campPart, ...channelOfferPart, ...dealPart].sort((a: any, b: any) => (String(a.createdAt) < String(b.createdAt) ? 1 : -1));
  }, [dealItems, myCampaignOffers, myChannelOffers]);

  const incomingOffers = useMemo(() => {
    const dealPart = dealItems.filter((x) => x.direction === 'incoming');
    const campPart = (incomingCampaignOffers || [])
      .filter((a) => !a.deal_id)
      .map((a) => ({
        kind: 'campaign_offer' as const,
        id: String(a.id || ''),
        campaignId: String(a.campaign_id || ''),
        campaignTitle: String(a.campaign_title || ''),
        channelId: String(a.channel_id || ''),
        channelName: String(a.channel_name || a.channel_id || ''),
        status: String(a.status || ''),
        dealId: String(a.deal_id || ''),
        dealStatus: String(a.deal_status || ''),
        offerTON: Number(a.offer_price_ton || 0),
        message: String(a.message || ''),
        createdAt: String(a.created_at || ''),
        template_id: String(a.template_id || ''),
        template_preview_text: String(a.template_preview_text || ''),
        template_preview_has_media: Boolean(a.template_preview_has_media),
        template_preview_count: Number(a.template_preview_count || 0),
      }));
    const channelOfferPart = (incomingChannelOffers || [])
      .filter((a) => !a.deal_id)
      .map((a) => ({
        kind: 'channel_offer' as const,
        id: String(a.id || ''),
        channelId: String(a.channel_id || ''),
        channelName: String(a.channel_name || a.channel_id || ''),
        status: String(a.status || ''),
        dealId: String(a.deal_id || ''),
        dealStatus: String(a.deal_status || ''),
        offerTON: Number(a.offer_price_ton || 0),
        message: String(a.message || ''),
        createdAt: String(a.created_at || ''),
      }));
    return [...campPart, ...channelOfferPart, ...dealPart].sort((a: any, b: any) => (String(a.createdAt) < String(b.createdAt) ? 1 : -1));
  }, [dealItems, incomingCampaignOffers, incomingChannelOffers]);

  async function cancelDeal(dealId: string) {
    if (!dealId || cancellingOfferId) return;
    setCancellingOfferId(dealId);
    setActionError('');
    try {
      const r = await apiFetch(`/deals/${dealId}/cancel`, { method: 'POST' });
      if (!r.ok) throw new Error(await r.text());
      const updated = await r.json();
      setDeals((prev) => (prev ? prev.map((d) => (String(d.id || '') === dealId ? updated.deal : d)) : prev));
      setCancelConfirm({ isOpen: false, offerId: '', title: '' });
    } catch (e: any) {
      setActionError(String(e?.message || e || 'Failed to cancel deal'));
    } finally {
      setCancellingOfferId('');
    }
  }

  async function cancelOffer(offerId: string) {
    if (!offerId || cancellingOfferId) return;
    setCancellingOfferId(offerId);
    setActionError('');
    try {
      const r = await apiFetch(`/campaign-offers/${offerId}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(await r.text());
      setMyCampaignOffers((prev) => (prev ? prev.filter((x: any) => String(x.id || '') !== offerId) : prev));
      setIncomingCampaignOffers((prev) => (prev ? prev.filter((x: any) => String(x.id || '') !== offerId) : prev));
      setCancelConfirm({ isOpen: false, offerId: '', title: '' });
    } catch (e: any) {
      setActionError(String(e?.message || e || 'Failed to cancel offer'));
    } finally {
      setCancellingOfferId('');
    }
  }

  type SectionKey = 'needs_action' | 'in_progress' | 'completed' | 'archived';

  function nextStepForDeal(d: any): { label: string; needsAction: boolean } {
    const isAdv = d.isAdvertiser;
    const status = String(d.status || '');
    if (status === 'negotiation') {
      const needsAction = isAdv ? !d.negotiationConfirmedByAdvertiser : !d.negotiationConfirmedByChannel;
      if (needsAction) return { label: 'Confirm terms', needsAction: true };
      return { label: 'Waiting for other side', needsAction: false };
    }
    if (status === 'pending_payment') {
      return isAdv ? { label: 'Pay', needsAction: true } : { label: 'Waiting for payment', needsAction: false };
    }
    if (status === 'creative_draft') {
      const creativeMode = d.creativeMode || 'template';
      // In template mode: advertiser submits content. In custom_task: owner submits content.
      const actorResponsible = (creativeMode === 'template' && isAdv) || (creativeMode === 'custom_task' && !isAdv);
      if (actorResponsible && d.waitingForCreative) return { label: 'Send creative', needsAction: true };
      return { label: 'Waiting for creative', needsAction: false };
    }
    if (status === 'creative_review') {
      // Review is done by the OTHER party
      const creativeMode = d.creativeMode || 'template';
      const actorResponsible = (creativeMode === 'template' && !isAdv) || (creativeMode === 'custom_task' && isAdv);
      return actorResponsible ? { label: 'Review creative', needsAction: true } : { label: 'Waiting for review', needsAction: false };
    }
    if (status === 'approved') {
      return isAdv ? { label: 'Pick slot', needsAction: true } : { label: 'Waiting for advertiser', needsAction: false };
    }
    if (status === 'scheduling') {
      return !isAdv ? { label: 'Approve slot', needsAction: true } : { label: 'Waiting for approval', needsAction: false };
    }
    if (status === 'awaiting_confirmation') {
      const needsAction = isAdv ? !d.dealConfirmedByAdvertiser : !d.dealConfirmedByChannel;
      if (needsAction) return { label: 'Confirm deal', needsAction: true };
      return { label: 'Waiting for confirmation', needsAction: false };
    }
    if (status === 'scheduled') {
      return { label: 'Publish', needsAction: false };
    }
    if (status === 'posted') {
      return { label: 'Verification pending', needsAction: false };
    }
    if (status === 'released') return { label: 'Completed', needsAction: false };
    if (status === 'cancelled' || status === 'refunded') return { label: 'Archived', needsAction: false };
    return { label: 'Waiting', needsAction: false };
  }

  function classify(item: any, activeTab: DealsTab): { section: SectionKey; next: string; needsAction: boolean } {
    if (item.kind === 'deal') {
      const status = String(item.status || '');
      if (status === 'released') return { section: 'completed', next: 'Completed', needsAction: false };
      if (status === 'cancelled' || status === 'refunded') return { section: 'archived', next: 'Archived', needsAction: false };
      const ns = nextStepForDeal(item);
      if (status === 'negotiation') return { section: 'in_progress', next: ns.label, needsAction: ns.needsAction };
      return { section: ns.needsAction ? 'needs_action' : 'in_progress', next: ns.label, needsAction: ns.needsAction };
    }
    const st = String(item.status || '');
    const ds = String(item.dealStatus || '');
    if (st === 'rejected') return { section: 'archived', next: 'Rejected', needsAction: false };
    if (ds === 'released') return { section: 'completed', next: 'Completed', needsAction: false };
    if (ds === 'cancelled' || ds === 'refunded') return { section: 'archived', next: 'Archived', needsAction: false };

    if (activeTab === 'incoming') {
      if (!item.dealId && st === 'pending') return { section: 'needs_action', next: 'Start deal', needsAction: true };
      if (item.dealId) {
        const deal = (deals || []).find(d => String(d.id) === String(item.dealId));
        const ns = nextStepForDeal(deal ? {
          ...deal,
          isAdvertiser: profileId && String(deal.advertiser_id || '') === profileId
        } : { ...item, status: ds, isAdvertiser: false });
        if (ds === 'negotiation') return { section: 'in_progress', next: ns.label, needsAction: ns.needsAction };
        return { section: ns.needsAction ? 'needs_action' : 'in_progress', next: ns.label, needsAction: ns.needsAction };
      }
      return { section: 'in_progress', next: 'Waiting', needsAction: false };
    }
    if (st === 'pending' && !item.dealId) return { section: 'in_progress', next: 'Waiting for advertiser', needsAction: false };
    if (item.dealId) {
      const deal = (deals || []).find(d => String(d.id) === String(item.dealId));
      const ns = nextStepForDeal(deal ? {
        ...deal,
        isAdvertiser: profileId && String(deal.advertiser_id || '') === profileId
      } : { ...item, status: ds, isAdvertiser: true });
      if (ds === 'negotiation') return { section: 'in_progress', next: ns.label, needsAction: ns.needsAction };
      return { section: ns.needsAction ? 'needs_action' : 'in_progress', next: ns.label, needsAction: ns.needsAction };
    }
    return { section: 'in_progress', next: 'Waiting', needsAction: false };
  }

  const sections = useMemo(() => {
    const items = tab === 'my' ? myOffers : incomingOffers;
    const buckets: Record<SectionKey, Array<{ item: any; next: string; needsAction: boolean }>> = {
      needs_action: [],
      in_progress: [],
      completed: [],
      archived: [],
    };
    for (const it of items) {
      const c = classify(it, tab);
      buckets[c.section].push({ item: it, next: c.next, needsAction: c.needsAction });
    }
    for (const k of Object.keys(buckets) as SectionKey[]) {
      buckets[k].sort((a, b) => (String(a.item.createdAt || '') < String(b.item.createdAt || '') ? 1 : -1));
    }
    return buckets;
  }, [tab, myOffers, incomingOffers]);

  function renderItem(item: any, next: string) {
    if (item.kind === 'deal') {
      const isCompleted = item.status === 'released';
      const isArchived = item.status === 'cancelled' || item.status === 'refunded';
      const shown = displayDealStatus(item.status);
      const tone = statusTone(shown);

      return (
        <DealCard
          key={`deal_${item.id}`}
          title={item.channelName}
          description={formatTON(item.priceTON)}
          statusLabel={prettyDealStatus(shown)}
          statusTone={tone}
          footerNote={`id: ${item.id}`}
          emoji={item.emoji}
          onClick={() => navigate(`/deals/${item.id}`)}
          className={isArchived ? styles.archivedCard : isCompleted ? styles.completedCard : ''}
        />
      );
    }

    if (item.kind === 'channel_offer') {
      const isIncoming = tab === 'incoming';
      const isCompleted = item.dealId && item.dealStatus === 'released';
      const isArchived = item.status === 'rejected' || item.dealStatus === 'cancelled' || item.dealStatus === 'refunded';
      const rawSt = item.dealStatus || item.status;
      const shownSt = item.dealId ? displayDealStatus(rawSt) : rawSt;
      const statusLabel = prettyDealStatus(shownSt);
      const tone = statusTone(shownSt);

      return (
        <DealCard
          key={`ch_offer_${item.id}`}
          title={item.channelName}
          description={formatTON(item.offerTON)}
          statusLabel={statusLabel}
          statusTone={tone}
          footerNote={`id: ${item.dealId || item.id}`}
          onClick={() => navigate(item.dealId ? `/deals/${item.dealId}` : `/channel-offers/${item.id}`)}
          className={isArchived ? styles.archivedCard : isCompleted ? styles.completedCard : ''}
        />
      );
    }

    const isIncoming = tab === 'incoming';
    const campaignTitle = item.campaignTitle?.trim() || item.campaignId;
    const title = isIncoming ? (item.channelName?.trim() || item.channelId) : campaignTitle;
    const isCompleted = item.dealStatus === 'released';
    const isArchived = item.status === 'rejected' || item.dealStatus === 'cancelled' || item.dealStatus === 'refunded';
    const rawCampSt = item.dealStatus || item.status;
    const shownCampSt = item.dealId ? displayDealStatus(rawCampSt) : rawCampSt;
    const tone = statusTone(shownCampSt);
    const subtitle = formatTON(item.offerTON);

    return (
      <DealCard
        key={`camp_${item.id}`}
        title={title}
        description={subtitle}
        statusLabel={prettyDealStatus(shownCampSt)}
        statusTone={tone}
        footerNote={`id: ${item.dealId || item.id}`}
        onClick={() => navigate(item.dealId ? `/deals/${item.dealId}` : `/campaign-offers/${item.id}`)}
        className={isArchived ? styles.archivedCard : isCompleted ? styles.completedCard : ''}
      />
    );
  }

  function renderSection(title: string, key: SectionKey, opts?: { collapsible?: boolean; shownByDefault?: number }) {
    const rows = sections[key];
    if (!rows.length) return null;
    const collapsible = Boolean(opts?.collapsible);
    const expanded = key === 'completed' ? showCompleted : key === 'archived' ? showArchived : true;
    const visibleRows = collapsible && !expanded ? rows.slice(0, opts?.shownByDefault ?? rows.length) : rows;
    const hidden = collapsible ? Math.max(0, rows.length - visibleRows.length) : 0;

    return (
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionTitle}>
            <Text type="caption" color="secondary" uppercase>
              {title}
            </Text>
            <Badge tone={key === 'completed' ? 'success' : key === 'needs_action' ? 'warning' : key === 'archived' ? 'default' : 'accent'}>
              {String(rows.length)}
            </Badge>
          </div>
          {collapsible && rows.length > (opts?.shownByDefault ?? rows.length) ? (
            <button
              type="button"
              className={styles.sectionToggle}
              onClick={() => {
                if (key === 'completed') setShowCompleted((v) => !v);
                if (key === 'archived') setShowArchived((v) => !v);
              }}
            >
              {expanded ? 'Hide' : `Show ${hidden}`}
            </button>
          ) : null}
        </div>

        <motion.div
          className={styles.list}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {visibleRows.map(({ item, next }) => (
            <motion.div key={String(item.id)} variants={itemVariants as any}>
              {renderItem(item, next)}
            </motion.div>
          ))}
        </motion.div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <AlertModal
        isOpen={cancelConfirm.isOpen}
        title={cancelConfirm.offerId.startsWith('d_') ? "Cancel deal?" : "Cancel offer?"}
        message={cancelConfirm.title ? `Cancel your ${cancelConfirm.offerId.startsWith('d_') ? 'deal' : 'offer'} for “${cancelConfirm.title}”?` : `Cancel your ${cancelConfirm.offerId.startsWith('d_') ? 'deal' : 'offer'}?`}
        buttonText={cancelConfirm.offerId.startsWith('d_') ? "Cancel deal" : "Cancel offer"}
        onButtonClick={() => cancelConfirm.offerId.startsWith('d_') ? cancelDeal(cancelConfirm.offerId) : cancelOffer(cancelConfirm.offerId)}
        secondaryButtonText="Keep"
        onSecondaryButtonClick={() => setCancelConfirm({ isOpen: false, offerId: '', title: '' })}
        onClose={() => setCancelConfirm({ isOpen: false, offerId: '', title: '' })}
      />
      <div className={`${styles.header} noScrollbar`}>
        <div className={styles.headerTitleRow}>
          <Text type="title">Deals</Text>
        </div>

        <div className={styles.segmented} role="tablist" aria-label="Deals sections">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'my'}
            className={`${styles.segmentedItem} ${tab === 'my' ? styles.active : ''}`}
            onClick={() => setTab('my')}
          >
            My Offers
            {myOffers.filter(x => {
              if (x.kind === 'deal') return !['released', 'cancelled', 'refunded'].includes(x.status);
              return x.status !== 'rejected' && !['released', 'cancelled', 'refunded'].includes(x.dealStatus || '');
            }).length > 0 && (
                <span className={styles.count}>
                  {myOffers.filter(x => {
                    if (x.kind === 'deal') return !['released', 'cancelled', 'refunded'].includes(x.status);
                    return x.status !== 'rejected' && !['released', 'cancelled', 'refunded'].includes(x.dealStatus || '');
                  }).length}
                </span>
              )}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'incoming'}
            className={`${styles.segmentedItem} ${tab === 'incoming' ? styles.active : ''}`}
            onClick={() => setTab('incoming')}
          >
            Incoming
            {incomingOffers.filter(x => {
              if (x.kind === 'deal') return !['released', 'cancelled', 'refunded'].includes(x.status);
              return x.status !== 'rejected' && !['released', 'cancelled', 'refunded'].includes(x.dealStatus || '');
            }).length > 0 && (
                <span className={styles.count}>
                  {incomingOffers.filter(x => {
                    if (x.kind === 'deal') return !['released', 'cancelled', 'refunded'].includes(x.status);
                    return x.status !== 'rejected' && !['released', 'cancelled', 'refunded'].includes(x.dealStatus || '');
                  }).length}
                </span>
              )}
          </button>
        </div>
      </div>

      <div className={styles.content}>
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {error && (
              <div style={{ padding: 16, textAlign: 'center' }}>
                <Text type="text" color="danger">{error}</Text>
              </div>
            )}
            {actionError && (
              <div style={{ padding: 16, textAlign: 'center' }}>
                <Text type="text" color="danger">{actionError}</Text>
              </div>
            )}

            {(deals === null || myCampaignOffers === null || incomingCampaignOffers === null || myChannelOffers === null || incomingChannelOffers === null) && !error && (
              <div style={{ padding: 20, textAlign: 'center' }}>
                <Text type="text" color="secondary">Loading...</Text>
              </div>
            )}

            {deals !== null && myCampaignOffers !== null && incomingCampaignOffers !== null && myChannelOffers !== null && incomingChannelOffers !== null && !error && tab === 'my' && myOffers.length === 0 && (
              <div style={{ padding: 32, textAlign: 'center', opacity: 0.7 }}>
                <Text type="title2" style={{ marginBottom: 8 }}>No offers sent</Text>
                <Text type="caption" color="secondary">You haven't made any offers yet.</Text>
              </div>
            )}

            {deals !== null && myCampaignOffers !== null && incomingCampaignOffers !== null && myChannelOffers !== null && incomingChannelOffers !== null && !error && tab === 'incoming' && incomingOffers.length === 0 && (
              <div style={{ padding: 32, textAlign: 'center', opacity: 0.7 }}>
                <Text type="title2" style={{ marginBottom: 8 }}>No incoming offers</Text>
                <Text type="caption" color="secondary">Wait for advertisers to contact you.</Text>
              </div>
            )}

            {renderSection('Needs action', 'needs_action')}
            {renderSection('Active', 'in_progress')}
            {(sections['completed'].length > 0 || sections['archived'].length > 0) && <div style={{ height: 24 }} />}
            {renderSection('Completed', 'completed', { collapsible: true, shownByDefault: 2 })}
            {renderSection('Archived', 'archived', { collapsible: true, shownByDefault: 0 })}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
