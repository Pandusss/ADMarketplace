import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, Input, Select, Text, BottomSheet, PublicProfileSheet } from '../../ui';
import { FeedChannelCard, CampaignCard } from '../../ui';
import { ChannelStats } from '../../components/ChannelStats/ChannelStats';
import { formatTON } from '../../utils/format';
import { CampaignDetails, Campaign } from '../../components/CampaignDetails/CampaignDetails';
import { CreateCampaignForm } from '../../components/CreateCampaignForm/CreateCampaignForm';
import { PublishChannelForm } from '../../components/PublishChannelForm/PublishChannelForm';
import { FilterPopup, ChannelFilters, CampaignFilters } from '../../components/FilterPopup/FilterPopup';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import styles from './FeedPage.module.scss';
import { apiFetch } from '../../api/client';
import { Plus, SlidersHorizontal, Search } from 'lucide-react';

type FeedMode = 'buy' | 'sell';


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

export function FeedPage() {
  const navigate = useNavigate();
  const currentUserId = useMemo(() => {
    const tgUserId = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id;
    return tgUserId ? `tg_${tgUserId}` : null;
  }, []);
  const [notice, setNotice] = useState<{ title: string; message: string } | null>(null);
  const [removeCampaign, setRemoveCampaign] = useState<Campaign | null>(null);
  const [removing, setRemoving] = useState(false);
  const [mode, setMode] = useState<FeedMode>(() => {
    const raw = localStorage.getItem('feed_mode');
    if (raw === 'buy' || raw === 'sell') return raw;
    if (raw === 'channels') return 'sell';
    return 'buy';
  });
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filtersByMode, setFiltersByMode] = useState<{ buy: CampaignFilters; sell: ChannelFilters }>(() => {
    try {
      const saved = localStorage.getItem('feed_filters');
      const parsed = saved ? JSON.parse(saved) : { buy: {}, sell: {} };
      return {
        buy: { onlyMy: false, ...parsed.buy },
        sell: { onlyMy: false, ...parsed.sell }
      };
    } catch {
      return { buy: { onlyMy: false }, sell: { onlyMy: false } };
    }
  });
  const [searchQuery, setSearchQuery] = useState('');

  const [channels, setChannels] = useState<any[] | null>(null);
  const [channelsError, setChannelsError] = useState<string>('');

  const [campaigns, setCampaigns] = useState<Campaign[] | null>(null);
  const [campaignsError, setCampaignsError] = useState<string>('');

  const [myChannels, setMyChannels] = useState<any[] | null>(null);
  const [myChannelsError, setMyChannelsError] = useState<string>('');

  const [applyCampaign, setApplyCampaign] = useState<Campaign | null>(null);
  const [applyChannelId, setApplyChannelId] = useState<string>('');
  const [applyError, setApplyError] = useState<string>('');
  const [applySubmitting, setApplySubmitting] = useState(false);

  const [publishingChannel, setPublishingChannel] = useState<boolean>(false);
  const [isCreatingCampaign, setIsCreatingCampaign] = useState(false);
  const [statsChannel, setStatsChannel] = useState<any | null>(null);
  const [viewingCampaign, setViewingCampaign] = useState<Campaign | null>(null);
  const [profileUserId, setProfileUserId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await apiFetch('/channels', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as any[];
        if (!cancelled) setChannels(data);
      } catch (e: any) {
        if (!cancelled) {
          setChannels([]);
          setChannelsError(String(e?.message || e || 'Failed to load channels'));
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await apiFetch('/campaigns', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as Campaign[];
        if (!cancelled) setCampaigns(data);
      } catch (e: any) {
        if (!cancelled) {
          setCampaigns([]);
          setCampaignsError(String(e?.message || e || 'Failed to load campaigns'));
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    localStorage.setItem('feed_mode', mode);
    setFiltersOpen(false);
    setApplyCampaign(null);
    setApplyError('');
    setSearchQuery('');
  }, [mode]);

  useEffect(() => {
    let cancelled = false;
    async function loadMyChannels() {
      try {
        const r = await apiFetch('/my/channels', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as any[];
        if (!cancelled) setMyChannels(data);
      } catch (e: any) {
        if (!cancelled) {
          setMyChannels([]);
          setMyChannelsError(String(e?.message || e || 'Failed to load your channels'));
        }
      }
    }
    loadMyChannels();
    return () => { cancelled = true; };
  }, []);

  // Save filters to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('feed_filters', JSON.stringify(filtersByMode));
  }, [filtersByMode]);

  const channelFilters = filtersByMode.sell;
  const campaignFilters = filtersByMode.buy;

  const sellItems = useMemo(() => {
    const data = channels || [];
    return data.filter((c) => {
      // Search query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!c.name?.toLowerCase().includes(q) && !c.handle?.toLowerCase().includes(q)) return false;
      }

      // Category filter
      if (channelFilters.category && c.category !== channelFilters.category) return false;

      // Language filter
      if (channelFilters.language && c.language !== channelFilters.language) return false;

      // Price range
      if (channelFilters.minPrice !== undefined && (c.price_per_post_ton || 0) < channelFilters.minPrice) return false;
      if (channelFilters.maxPrice !== undefined && (c.price_per_post_ton || 0) > channelFilters.maxPrice) return false;

      // Subscribers range
      if (channelFilters.minSubscribers !== undefined && (c.subscribers_count || 0) < channelFilters.minSubscribers) return false;
      if (channelFilters.maxSubscribers !== undefined && (c.subscribers_count || 0) > channelFilters.maxSubscribers) return false;

      // Views range
      if (channelFilters.minViews !== undefined && (c.avg_views || 0) < channelFilters.minViews) return false;
      if (channelFilters.maxViews !== undefined && (c.avg_views || 0) > channelFilters.maxViews) return false;

      // Stability score (normalized to 0-100 if stored as 0-1)
      const stability = (c.stability_score || 0) <= 1 ? (c.stability_score || 0) * 100 : (c.stability_score || 0);
      if (channelFilters.minStability !== undefined && stability < channelFilters.minStability) return false;

      // Engagement Rate
      if (channelFilters.minEngagementRate !== undefined && (c.engagement_rate || 0) < channelFilters.minEngagementRate) return false;

      // Rating
      if (channelFilters.minRating !== undefined && (c.rating_avg || 0) < channelFilters.minRating) return false;

      // Only my channels
      if (channelFilters.onlyMy && currentUserId && String(c.owner_id) !== String(currentUserId)) return false;

      return true;
    });
  }, [channels, channelFilters, searchQuery]);

  const buyItems = useMemo(() => {
    const data = campaigns || [];
    return data.filter((c) => {
      // Search query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!c.title?.toLowerCase().includes(q) && !c.brief?.toLowerCase().includes(q)) return false;
      }

      // Category filter
      if (campaignFilters.category && String(c.category || '') !== campaignFilters.category) return false;

      // Language filter
      if (campaignFilters.language && String(c.language || '') !== campaignFilters.language) return false;

      // Budget range
      if (campaignFilters.minBudget !== undefined && (c.budget_ton || 0) < campaignFilters.minBudget) return false;
      if (campaignFilters.maxBudget !== undefined && (c.budget_ton || 0) > campaignFilters.maxBudget) return false;

      // Views range
      if (campaignFilters.minViews !== undefined && (c.desired_views_24h || 0) < campaignFilters.minViews) return false;
      if (campaignFilters.maxViews !== undefined && (c.desired_views_24h || 0) > campaignFilters.maxViews) return false;

      // Creative mode
      if (campaignFilters.creativeMode && c.creative_mode !== campaignFilters.creativeMode) return false;

      // Rating
      if (campaignFilters.minRating !== undefined && (c.rating_avg || 0) < campaignFilters.minRating) return false;

      // Only my campaigns
      if (campaignFilters.onlyMy && currentUserId && String(c.owner_id) !== String(currentUserId)) return false;

      return true;
    });
  }, [campaigns, campaignFilters, searchQuery]);

  // Count active filters
  const activeFiltersCount = useMemo(() => {
    const filters = mode === 'buy' ? campaignFilters : channelFilters;
    let count = 0;

    if (filters.category) count++;
    if (filters.language) count++;
    if (filters.onlyMy) count++;
    if (filters.onlyMy) count++;

    if (mode === 'sell') {
      const cf = filters as ChannelFilters;
      if (cf.minPrice !== undefined) count++;
      if (cf.maxPrice !== undefined) count++;
      if (cf.minSubscribers !== undefined) count++;
      if (cf.maxSubscribers !== undefined) count++;
      if (cf.minViews !== undefined) count++;
      if (cf.maxViews !== undefined) count++;
      if (cf.minStability !== undefined) count++;
      if (cf.minEngagementRate !== undefined) count++;
      if (cf.minRating !== undefined) count++;
    } else {
      const cf = filters as CampaignFilters;
      if (cf.minBudget !== undefined) count++;
      if (cf.maxBudget !== undefined) count++;
      if (cf.minViews !== undefined) count++;
      if (cf.maxViews !== undefined) count++;
      if (cf.creativeMode !== undefined) count++;
      if (cf.minRating !== undefined) count++;
    }

    return count;
  }, [mode, channelFilters, campaignFilters]);

  const channelsToPublish = useMemo(() => {
    const data = myChannels || [];
    const publishedIds = new Set((channels || []).map(c => String(c.id)));
    return data.filter((c) =>
      Boolean(c.is_verified) &&
      !c.is_published &&
      !publishedIds.has(String(c.id))
    );
  }, [myChannels, channels]);

  const channelsToOffer = useMemo(() => {
    return myChannels || [];
  }, [myChannels]);

  async function submitApply() {
    if (!applyCampaign) return;
    if (applySubmitting) return;
    setApplyError('');

    try {
      const profileRes = await apiFetch('/profile', { method: 'GET' });
      if (profileRes.ok) {
        const profile = await profileRes.json();
        const wallet = String(profile?.wallet_address || '').trim();
        if (!wallet) {
          setNotice({
            title: 'Wallet required',
            message: 'Please set your TON wallet address in Wallet before submitting an offer. You need it to receive payouts.',
          });
          return;
        }
      }
    } catch { }

    const channelId = applyChannelId.trim();
    if (!channelId) {
      setApplyError('Choose a channel to apply with.');
      return;
    }



    setApplySubmitting(true);
    try {
      const r = await apiFetch(`/campaigns/${applyCampaign.id}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          channel_id: channelId,
          offer_price_ton: 0,
          message: '',
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setApplyCampaign(null);
      setApplyChannelId('');
      setApplyChannelId('');
      setNotice({ title: 'Offer sent', message: 'Your offer was submitted. Redirecting...' });
      setTimeout(() => {
        navigate('/deals', { replace: true });
      }, 1000);
    } catch (e: any) {
      setApplyError(String(e?.message || e || 'Failed to apply'));
    } finally {
      setApplySubmitting(false);
    }
  }

  async function confirmRemove() {
    if (!removeCampaign || removing) return;
    setRemoving(true);
    try {
      const r = await apiFetch(`/campaigns/${removeCampaign.id}`, { method: 'DELETE' });
      if (!r.ok) throw new Error(await r.text());
      setCampaigns((prev) => (prev ? prev.filter((x) => x.id !== removeCampaign.id) : prev));
      setApplyCampaign((prev) => (prev?.id === removeCampaign.id ? null : prev));
      setRemoveCampaign(null);
      setNotice({ title: 'Removed', message: 'Campaign was removed.' });
    } catch (e: any) {
      setNotice({ title: 'Error', message: String(e?.message || e || 'Failed to remove campaign') });
    } finally {
      setRemoving(false);
    }
  }

  async function handleUnpublish(channelId: string) {
    if (!channelId) return;
    try {
      const r = await apiFetch(`/channels/${channelId}/unpublish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!r.ok) throw new Error(await r.text());

      // Update local state
      setChannels(prev => prev ? prev.filter(c => String(c.id) !== channelId) : prev);
      setNotice({ title: 'Removed', message: 'Channel was unpublished from Feed.' });
    } catch (e: any) {
      setNotice({ title: 'Error', message: String(e?.message || e || 'Failed to unpublish') });
    }
  }


  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <Text type="title">Marketplace</Text>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              variant="primary"
              size="small"
              fullWidth={false}
              style={{ padding: 8 }}
              onClick={() => {
                if (mode === 'buy') {
                  // Post Ads (Viewing Channels) -> Publish Channel
                  setPublishingChannel(true);
                } else {
                  // Accept Ads (Viewing Campaigns) -> Create Campaign
                  setIsCreatingCampaign(true);
                }
              }}
            >
              <Plus size={20} />
            </Button>
          </div>
        </div>

        <div className={styles.segmented} role="tablist" aria-label="Feed mode">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'buy'}
            className={`${styles.segmentedItem} ${mode === 'buy' ? styles.active : ''}`}
            onClick={() => setMode('buy')}
          >
            Post Ads
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'sell'}
            className={`${styles.segmentedItem} ${mode === 'sell' ? styles.active : ''}`}
            onClick={() => setMode('sell')}
          >
            Accept Ads
          </button>
        </div>

        <div className={styles.searchRow}>
          <div style={{ flex: 1 }}>
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={mode === 'buy' ? 'Search channels...' : 'Search campaigns...'}
              icon={<Search size={16} />}
            />
          </div>
          <button className={styles.filtersButton} onClick={() => setFiltersOpen(true)}>
            <SlidersHorizontal size={20} />
            {activeFiltersCount > 0 && (
              <span className={styles.filterBadge}>{activeFiltersCount}</span>
            )}
          </button>
        </div>
      </div>

      <div className={styles.content}>
        <AnimatePresence mode="wait">
          {mode === 'buy' ? ( /* Post Ads -> Buy Ads -> Show Channels */
            <motion.div
              key="buy-list"
              className={styles.list}
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {channelsError && (
                <Card><Text type="text" color="danger">{channelsError}</Text></Card>
              )}
              {channels === null && !channelsError && (
                <Card><Text type="text" color="secondary">Loading...</Text></Card>
              )}
              {channels !== null && sellItems.length === 0 && !channelsError && (
                <Card>
                  <Text type="text" color="secondary" style={{ textAlign: 'center', padding: 20 }}>
                    No channels found
                  </Text>
                </Card>
              )}
              {sellItems.map((c: any) => (
                <motion.div key={String(c.id)} variants={itemVariants as any}>
                  <FeedChannelCard
                    title={c.name}
                    handle={c.handle}
                    avatarUrl={c.avatar_file_id ? `/api/channels/${c.id}/avatar` : undefined}
                    subscribers={c.subscribers_count || 0}
                    avgViews={c.avg_views || 0}
                    engagementRate={c.engagement_rate || 0}
                    category={c.category || 'Other'}
                    language={c.language || 'EN'}
                    price={c.price_per_post_ton || 0}
                    isVerified={Boolean(c.verified_stats)}
                    ratingAvg={c.rating_avg || 0}
                    ratingCount={c.rating_count || 0}
                    channelId={c.id}
                    ownerId={c.owner_id}
                    onOfferDeal={
                      currentUserId && c.owner_id === currentUserId
                        ? undefined
                        : () => navigate(`/start-deal/${c.id}`)
                    }
                    onUnpublish={
                      currentUserId && c.owner_id === currentUserId
                        ? () => handleUnpublish(c.id)
                        : undefined
                    }
                    onClick={() => setStatsChannel(c)}
                    onViewProfile={
                      currentUserId && c.owner_id === currentUserId
                        ? undefined
                        : () => setProfileUserId(c.owner_id)
                    }
                  />
                </motion.div>
              ))}
            </motion.div>
          ) : ( /* Accept Ads -> Sell Ads -> Show Campaigns */
            <motion.div
              key="sell-list"
              className={styles.list}
              variants={containerVariants}
              initial="hidden"
              animate="visible"
            >
              {campaignsError && (
                <Card><Text type="text" color="danger">{campaignsError}</Text></Card>
              )}
              {campaigns === null && !campaignsError && (
                <Card><Text type="text" color="secondary">Loading...</Text></Card>
              )}
              {campaigns !== null && buyItems.length === 0 && !campaignsError && (
                <Card>
                  <Text type="text" color="secondary" style={{ textAlign: 'center', padding: 20 }}>
                    No campaigns found
                  </Text>
                </Card>
              )}
              {buyItems.map((c: any) => (
                <motion.div key={String(c.id)} variants={itemVariants as any}>
                  <CampaignCard
                    title={c.title}
                    brief={c.brief}
                    budget={c.budget_ton}
                    desiredViews={c.desired_views_24h}
                    category={c.category}
                    language={c.language}
                    showBrief={false}
                    ownerRatingAvg={c.owner_rating_avg || 0}
                    ownerRatingCount={c.owner_rating_count || 0}
                    ownerId={c.owner_id}
                    ratingAvg={c.rating_avg || 0}
                    ratingCount={c.rating_count || 0}
                    campaignId={c.id}
                    onApply={
                      currentUserId && c.owner_id === currentUserId
                        ? undefined // Owner cannot apply
                        : () => {
                          setApplyCampaign(c);
                          setApplyError('');
                          setApplyChannelId(channelsToOffer[0]?.id || '');
                        }
                    }
                    onRemove={
                      currentUserId && c.owner_id === currentUserId
                        ? () => setRemoveCampaign(c)
                        : undefined
                    }
                    onClick={() => setViewingCampaign(c)}
                    onViewProfile={
                      currentUserId && c.owner_id === currentUserId
                        ? undefined
                        : () => setProfileUserId(c.owner_id)
                    }
                  />
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>


      <FilterPopup
        isOpen={filtersOpen}
        onClose={() => setFiltersOpen(false)}
        mode={mode === 'buy' ? 'channels' : 'campaigns'}
        channelFilters={channelFilters}
        campaignFilters={campaignFilters}
        onApply={(filters) => {
          setFiltersByMode((prev) => ({
            ...prev,
            [mode === 'buy' ? 'sell' : 'buy']: filters,
          }));
        }}
        onReset={() => {
          setFiltersByMode((prev) => ({
            ...prev,
            [mode === 'buy' ? 'sell' : 'buy']: {},
          }));
        }}
      />


      {applyCampaign && (
        <div className={styles.filtersOverlay} role="dialog" aria-modal="true" aria-label="Offer to campaign">
          <div className={styles.filtersHeader} style={{ padding: 16, borderBottom: '1px solid #efeff3', backgroundColor: 'var(--tg-theme-bg-color, #ffffff)', borderTopLeftRadius: 20, borderTopRightRadius: 20 }}>
            <Text type="title">Offer</Text>
            <Button variant="secondary" size="small" fullWidth={false} onClick={() => setApplyCampaign(null)}>
              Close
            </Button>
          </div>

          <div className={styles.sheet} style={{ borderRadius: 0 }}>
            <Text type="caption" color="secondary" style={{ marginBottom: 10, display: 'block' }}>
              Offer to campaign {applyCampaign.title?.trim() ? applyCampaign.title : applyCampaign.id}
            </Text>

            {myChannelsError && (
              <Text type="caption" color="danger" style={{ marginBottom: 10, display: 'block' }}>
                {myChannelsError}
              </Text>
            )}

            {channelsToOffer.length === 0 ? (
              <>
                <Text type="text" color="secondary">
                  You need a verified channel to make an offer. Add and verify your channel first.
                </Text>
                <Button variant="secondary" onClick={() => navigate('/assets')}>
                  Go to My Assets
                </Button>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Select label="Your channel" value={applyChannelId} onChange={(e) => setApplyChannelId(e.target.value)}>
                  {channelsToOffer.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name || c.title || c.id}
                    </option>
                  ))}
                </Select>

                <Button isLoading={applySubmitting} disabled={applySubmitting} onClick={submitApply}>
                  Submit offer
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      <BottomSheet
        isOpen={isCreatingCampaign}
        onClose={() => setIsCreatingCampaign(false)}
        title="New Buy Ad"
      >
        <CreateCampaignForm
          onSuccess={() => {
            setIsCreatingCampaign(false);
            setNotice({ title: 'Success', message: 'Campaign created!' });
            // Refresh campaigns
            apiFetch('/campaigns', { method: 'GET' })
              .then(r => r.json())
              .then(data => setCampaigns(data))
              .catch(() => { });
          }}
        />
      </BottomSheet>

      <BottomSheet
        isOpen={publishingChannel}
        onClose={() => setPublishingChannel(false)}
        title="Publish Channel"
      >
        <PublishChannelForm
          eligibleMyChannels={channelsToPublish}
          myChannelsError={myChannelsError}
          onSuccess={() => {
            setPublishingChannel(false);
            setNotice({ title: 'Published', message: 'Channel is now live in Feed.' });
            // Refresh channels
            apiFetch('/channels', { method: 'GET' })
              .then(r => r.json())
              .then(data => setChannels(data))
              .catch(() => { });

            // Also refresh my channels to update is_published status
            apiFetch('/my/channels', { method: 'GET' })
              .then(r => r.json())
              .then(data => setMyChannels(data))
              .catch(() => { });
          }}
        />
      </BottomSheet>

      <BottomSheet
        isOpen={Boolean(statsChannel)}
        onClose={() => setStatsChannel(null)}
        title="Channel Details"
      >
        {statsChannel && (
          <div style={{ paddingBottom: 20 }}>
            <ChannelStats channel={statsChannel} />
            <div style={{ marginTop: 20, padding: '0 4px' }}>
              <Button
                onClick={() => {
                  navigate(`/start-deal/${statsChannel.id}`);
                  setStatsChannel(null);
                }}
              >
                Offer Deal
              </Button>
            </div>
          </div>
        )}
      </BottomSheet>

      <BottomSheet
        isOpen={Boolean(viewingCampaign)}
        onClose={() => setViewingCampaign(null)}
        title="Campaign Details"
      >
        {viewingCampaign && (
          <div style={{ paddingBottom: 20 }}>
            <CampaignDetails campaign={viewingCampaign} />
            <div style={{ marginTop: 20, padding: '0 4px' }}>
              <Button
                disabled={currentUserId === viewingCampaign.owner_id}
                onClick={() => {
                  setApplyCampaign(viewingCampaign);
                  setViewingCampaign(null);
                  setApplyError('');
                  setApplyChannelId(channelsToOffer[0]?.id || '');
                }}
              >
                {currentUserId === viewingCampaign.owner_id ? 'Your Campaign' : 'Make Offer'}
              </Button>
            </div>
          </div>
        )}
      </BottomSheet>

      {
        notice && (
          <div className={styles.centerOverlay}>
            <div className={styles.centerCard}>
              <Card>
                <Text type="text">{notice.message}</Text>
                <Button variant="secondary" onClick={() => setNotice(null)} style={{ marginTop: 14 }}>OK</Button>
              </Card>
            </div>
          </div>
        )
      }

      {
        removeCampaign && (
          <div className={styles.centerOverlay}>
            <div className={styles.centerCard}>
              <Card>
                <Text type="text" style={{ marginTop: 2 }}>
                  {removeCampaign.title?.trim() ? `Remove campaign “${removeCampaign.title.trim()}”?` : 'Remove this campaign?'}
                </Text>
                <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
                  <Button variant="secondary" fullWidth={false} disabled={removing} onClick={() => setRemoveCampaign(null)}>
                    Cancel
                  </Button>
                  <Button variant="danger" fullWidth={false} isLoading={removing} disabled={removing} onClick={confirmRemove}>
                    Remove
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        )
      }

      {
        profileUserId && (
          <PublicProfileSheet
            isOpen={!!profileUserId}
            onClose={() => setProfileUserId(null)}
            userId={profileUserId}
          />
        )
      }
    </div >
  );
}
