import { Badge, Button, Card, CardHeaderRow, Text } from '../../../ui';
import { Channel, Listing } from '../../../domain/types';
import { formatCompactNumber, formatTON } from '../../../utils/format';
import styles from './ChannelCard.module.scss';

export type ChannelCardModel = {
  channel: Channel;
  listing: Listing;
};

export function ChannelCard({
  model,
  onViewChannel,
  onStartDeal,
  onUnpublish,
}: {
  model: ChannelCardModel;
  onViewChannel: () => void;
  onStartDeal: () => void;
  onUnpublish?: () => void;
}) {
  const { channel, listing } = model;

  return (
    <Card
      onClick={onViewChannel}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onViewChannel();
      }}
      style={{ cursor: 'pointer' }}
      aria-label={`View channel ${channel.name}`}
    >
      <CardHeaderRow>
        <div>
          <Text type="title2">{channel.name}</Text>
          <Text type="caption" color="secondary">
            @{channel.handle}
          </Text>
        </div>

        <Badge tone={channel.verifiedStats ? 'success' : 'default'}>
          {channel.verifiedStats ? 'Verified stats' : 'Unverified'}
        </Badge>
      </CardHeaderRow>

      <div className={styles.statsGrid}>
        <Text type="caption" color="secondary">
          Subscribers: <b>{formatCompactNumber(channel.subscribersCount || 0)}</b>
        </Text>
        <Text type="caption" color="secondary">
          Avg views: <b>{formatCompactNumber(channel.avgViews || 0)}</b>
        </Text>
        <Text type="caption" color="secondary">
          Premium: <b>{channel.premium_share ? channel.premium_share.toFixed(1) : '0'}%</b>
        </Text>
        <Text type="caption" color="secondary">
          Stability: <b>{channel.stabilityScore ? Math.round(channel.stabilityScore * 100) : 0}%</b>
        </Text>
        <Text type="caption" color="secondary">
          Language: <b>{listing.language}</b>
        </Text>
        <Text type="caption" color="secondary">
          Category: <b>{listing.category}</b>
        </Text>
        {(channel.region_stats || channel.regionStats) && (
          <Text type="caption" color="secondary">
            Regions: <b>{
              Object.entries(channel.region_stats || channel.regionStats || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 2)
                .map(([code, count]) => `${code.toUpperCase()} (${count}%)`)
                .join(', ')
            }</b>
          </Text>
        )}
      </div>

      <Text type="text" weight="medium">
        From {formatTON(listing.pricePerPostTON)} / post
      </Text>

      <div className={styles.actions}>
        {!onUnpublish && (
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onStartDeal();
            }}
          >
            Start deal
          </Button>
        )}
        {onUnpublish && (
          <Button
            variant="danger"
            onClick={(e) => {
              e.stopPropagation();
              onUnpublish();
            }}
          >
            Unpublish
          </Button>
        )}
      </div>
    </Card>
  );
}

