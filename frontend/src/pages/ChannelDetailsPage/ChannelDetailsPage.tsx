import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge, Button, Card, CardStack, StarRating, Text } from '../../ui';
import { formatCompactNumber, formatTON } from '../../utils/format';
import styles from './ChannelDetailsPage.module.scss';
import { apiFetch } from '../../api/client';

export function ChannelDetailsPage() {
  const { channelId } = useParams<{ channelId: string }>();
  const navigate = useNavigate();
  const [channel, setChannel] = useState<any | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!channelId) return;
      try {
        const r = await apiFetch(`/channels/${channelId}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        if (!cancelled) setChannel(data);
      } catch (e: any) {
        if (!cancelled) {
          setChannel(null);
          setError(String(e?.message || e || 'Failed to load channel'));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [channelId]);

  const view = useMemo(() => {
    if (!channel) return null;
    return {
      id: channel.id,
      name: channel.name,
      handle: channel.handle,
      description: channel.description,
      subscribersCount: channel.subscribers_count,
      avgViews: channel.avg_views,
      stabilityScore: channel.stability_score,
      verifiedStats: Boolean(channel.verified_stats),
      category: channel.category,
      language: channel.language,
      pricePerPostTON: channel.price_per_post_ton || 0,
      premiumSubscribersCount: channel.premium_subscribers_count || 0,
      regionStats: channel.region_stats || {},
      premiumShare: channel.premium_share || 0,
      ratingAvg: channel.rating_avg || 0,
      ratingCount: channel.rating_count || 0,
    };
  }, [channel]);

  if (!view) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <Text type="title">Channel</Text>
          <Card>
            <Text type="text" color="secondary">
              {error || 'Channel not found.'}
            </Text>
            <Button variant="secondary" onClick={() => navigate('/feed')}>
              Back to Feed
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  // Format regions for display (e.g., "RU (50), EN (10)")
  const regionDisplay = Object.entries((view.regionStats as Record<string, number>) || {})
    .sort((a, b) => b[1] - a[1]) // highest count first
    .slice(0, 3) // Top 3
    .map(([code, count]) => `${code.toUpperCase()} (${count}%)`)
    .join(', ');

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">{view.name}</Text>
          <Badge tone={view.verifiedStats ? 'success' : 'default'}>
            {view.verifiedStats ? 'Verified stats' : 'Unverified'}
          </Badge>
        </div>

        <Text type="caption" color="secondary">
          @{view.handle}
        </Text>

        <CardStack>
          <Card>
            <Text type="title2">Stats</Text>
            <div className={styles.statsGrid}>
              <Text type="caption" color="secondary">
                Subscribers: <b>{formatCompactNumber(view.subscribersCount)}</b>
              </Text>
              <Text type="caption" color="secondary">
                Premium: <b>{view.premiumShare ? view.premiumShare.toFixed(1) : '0'}%</b>
              </Text>
              <Text type="caption" color="secondary">
                Avg views: <b>{formatCompactNumber(view.avgViews)}</b>
              </Text>
              <Text type="caption" color="secondary">
                Stability: <b>{view.stabilityScore ? Math.round(view.stabilityScore * 100) : 0}%</b>
              </Text>
              <Text type="caption" color="secondary">
                Language: <b>{view.language}</b>
              </Text>
              {regionDisplay && (
                <Text type="caption" color="secondary">
                  Regions: <b>{regionDisplay}</b>
                </Text>
              )}
              <Text type="caption" color="secondary">
                Category: <b>{view.category}</b>
              </Text>
              {view.ratingCount > 0 && (
                <Text type="caption" color="secondary">
                  Rating: <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <StarRating value={view.ratingAvg} readonly size={14} />
                    <b>{view.ratingAvg.toFixed(1)}</b> ({view.ratingCount})
                  </span>
                </Text>
              )}
            </div>
          </Card>

          <Card>
            <Text type="title2">Description</Text>
            <Text type="text" color="secondary">
              {view.description}
            </Text>
          </Card>

          <Card>
            <Text type="title2">Pricing</Text>
            <Text type="caption" color="secondary">
              MVP: single post
            </Text>
            <Text type="text" weight="medium">
              {formatTON(view.pricePerPostTON)} / post
            </Text>
          </Card>
        </CardStack>
      </div>

      {/* Primary CTA must be visually prominent */}
      <div className={styles.ctaWrap}>
        <Button onClick={() => navigate(`/start-deal/${view.id}`)}>Start deal</Button>
        <div className={styles.ctaMicrocopy}>
          <Text type="caption" color="secondary">
            Escrow protected
          </Text>
          <Text type="caption" color="secondary">
            No payment required at this step
          </Text>
        </div>
      </div>
    </div>
  );
}

