import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, TrendingUp, Users, Eye, Globe, MapPin } from 'lucide-react';
import { Badge, Button, Card, CardHeaderRow, CardStack, Text, BottomSheet } from '../../ui';
import { ChannelStats } from '../../components/ChannelStats/ChannelStats';
import { EditChannelForm } from '../../components/EditChannelForm/EditChannelForm';
import { apiFetch, tgInitData } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';
import styles from './MyChannelsPage.module.scss';
import { Channel } from '../../domain/types';

interface MyChannel {
  id: string;
  avatar_file_id?: string;
  name: string;
  handle: string;
  description: string;
  subscribers_count: number;
  avg_views: number;
  avg_views_24h: number;
  avg_views_7d: number;
  premium_share: number;
  growth_7d: number;
  last_stats_update?: string;
  verified_stats: boolean;
  category?: string;
  language?: string;
  price_per_post_ton: number;
  is_verified: boolean;
  is_published: boolean;
  owner_id: string;
  avg_views_per_post?: number;
  median_views?: number;
  engagement_rate?: number;
  median_er?: number;
  posts_per_day?: number;
  ad_reach_estimate?: number;
  followers_trend_percent?: number;
  subs_today?: number;
  subs_week?: number;
  subs_month?: number;
  joins_24h?: number;
  leaves_24h?: number;
  reach_12h?: number;
  reach_24h?: number;
  reach_48h?: number;
  err_24h_percent?: number;
  posts_total?: number;
  posts_yesterday?: number;
  posts_week?: number;
  posts_month?: number;
  channel_created_at?: string;
  avg_forwards?: number;
  avg_replies?: number;
  avg_reactions?: number;
  stability_score?: number;
  premium_subscribers_count?: number;
  region_stats?: Record<string, number>;
}

export function MyChannelsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const navigate = useNavigate();
  const [channels, setChannels] = useState<MyChannel[] | null>(null);
  const [error, setError] = useState<string>('');
  const [viewingStats, setViewingStats] = useState<MyChannel | null>(null);
  const [editingChannel, setEditingChannel] = useState<MyChannel | null>(null);
  const [scanning, setScanning] = useState<string | null>(null);

  const [alertModal, setAlertModal] = useState<{ isOpen: boolean; title?: string; message: string }>({
    isOpen: false,
    message: '',
  });

  const tg = useMemo(() => (window as any).Telegram?.WebApp, []);

  const fetchChannels = async () => {
    try {
      const response = await apiFetch('/my/channels', { method: 'GET' });
      if (!response.ok) throw new Error('Failed to fetch channels');
      const data = await response.json();
      setChannels(data);
      setError('');
    } catch (err: any) {
      setChannels([]);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  useEffect(() => {
    fetchChannels();
  }, []);

  const handleTogglePublish = async (channel: MyChannel) => {
    try {
      const endpoint = channel.is_published ? 'unpublish' : 'publish';
      const response = await apiFetch(`/channels/${channel.id}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData: tgInitData() })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to update channel status');
      }

      const updated = await response.json();
      setChannels(prev => prev ? prev.map(c => c.id === updated.id ? { ...c, is_published: updated.is_published } : c) : null);
      if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } catch (err: any) {
      setAlertModal({ isOpen: true, title: 'Error', message: err.message });
    }
  };

  const handleRescan = async (channelId: string) => {
    try {
      setScanning(channelId);
      const response = await apiFetch(`/rescan-analytics/${channelId}`, {
        method: 'POST'
      });

      if (!response.ok) throw new Error('Rescan failed');

      const updatedChannel = await response.json();
      setChannels(prev => prev ? prev.map(c => c.id === channelId ? updatedChannel : c) : null);
      if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    } catch (err: any) {
      setAlertModal({ isOpen: true, title: 'Error', message: 'Failed to trigger scan. Please try again later.' });
    } finally {
      setScanning(null);
    }
  };

  function renderContent() {
    if (error) {
      return (
        <Card>
          <Text type="title2">Can’t load channels</Text>
          <Text type="text" color="secondary">{error}</Text>
        </Card>
      );
    }

    if (channels === null) {
      return (
        <Card>
          <Text type="title2">Loading…</Text>
        </Card>
      );
    }

    if (channels.length === 0) {
      return (
        <Card>
          <Text type="title2">No channels found</Text>
          <Text type="text" color="secondary">
            Tap the <strong>+</strong> button in the top right corner to add your first channel and start receiving advertisement offers.
          </Text>
        </Card>
      );
    }

    return (
      <CardStack>
        {channels.map(channel => (
          <Card
            key={channel.id}
            onClick={() => setViewingStats(channel)}
            style={{ cursor: 'pointer', paddingBottom: 16 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center', minWidth: 0 }}>
                <div style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-fill-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  flexShrink: 0,
                  border: '1px solid var(--color-border-separator)'
                }}>
                  {channel.avatar_file_id ? (
                    <img
                      src={`/api/channels/${channel.id}/avatar`}
                      alt={channel.name}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <Text weight="bold" color="secondary">{channel.name.charAt(0)}</Text>
                  )}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Text type="title2" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: 16 }}>{channel.name}</Text>
                    {channel.is_verified && (
                      <CheckCircle2 size={14} style={{ color: '#31a3ff', flexShrink: 0 }} />
                    )}
                  </div>
                  <Text type="caption" color="secondary" style={{ fontSize: 13 }}>{channel.handle ? `@${channel.handle}` : 'Private'}</Text>
                </div>
              </div>
              <div style={{ flexShrink: 0, marginLeft: 12 }}>
                <Button
                  size="small"
                  variant="primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingChannel(channel);
                  }}
                  fullWidth={false}
                  style={{ padding: '6px 12px', height: 32, fontSize: 13, minWidth: 64 }}
                >
                  EDIT
                </Button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 16, paddingLeft: 2 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <Users size={14} color="var(--color-foreground-secondary)" />
                <Text type="caption" weight="medium" style={{ fontSize: 13 }}>{channel.subscribers_count.toLocaleString()}</Text>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <TrendingUp size={14} color="var(--color-foreground-secondary)" />
                <Text type="caption" weight="medium" style={{ fontSize: 13 }}>{channel.engagement_rate || 0}% ER</Text>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: 6 }}>
                <Badge tone="default">{channel.category || 'General'}</Badge>
                <Badge tone="default" mode="outline">{channel.language || 'EN'}</Badge>
                {channel.is_published ? (
                  <Badge tone="success">Live</Badge>
                ) : (
                  <Badge tone="default">Hidden</Badge>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Text type="title2" style={{ fontSize: 16, color: 'var(--color-accent-primary)' }}>{channel.price_per_post_ton} TON</Text>
              </div>
            </div>
          </Card>
        ))}
      </CardStack>
    );
  }

  return (
    <>
      <AlertModal
        isOpen={alertModal.isOpen}
        title={alertModal.title}
        message={alertModal.message}
        onClose={() => setAlertModal({ isOpen: false, message: '' })}
      />

      <BottomSheet
        isOpen={Boolean(viewingStats)}
        onClose={() => setViewingStats(null)}
        title="Channel Statistics"
      >
        {viewingStats && (
          <ChannelStats
            channel={viewingStats}
          />
        )}
      </BottomSheet>

      <BottomSheet
        isOpen={Boolean(editingChannel)}
        onClose={() => setEditingChannel(null)}
        title="Edit Channel Settings"
      >
        {editingChannel && (
          <EditChannelForm
            channel={editingChannel}
            onSuccess={(updated) => {
              setChannels(prev => prev ? prev.map(c => c.id === updated.id ? { ...c, ...updated } : c) : null);
              setEditingChannel(null);
            }}
            onCancel={() => setEditingChannel(null)}
          />
        )}
      </BottomSheet>

      {embedded ? (
        <div className={styles.embedded}>{renderContent()}</div>
      ) : (
        <div className={styles.page}>
          <div className={`${styles.content} noScrollbar`}>
            <div className={styles.header}>
              <Text type="title">My Channels</Text>
              <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
                Back
              </Button>
            </div>
            {renderContent()}
          </div>
        </div>
      )}
    </>
  );
}
