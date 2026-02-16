import { useState, useEffect } from 'react';
import { VenetianMask, Megaphone } from 'lucide-react';
import { BottomSheet } from '../BottomSheet/BottomSheet';
import { RatingBadge } from '../RatingBadge/RatingBadge';
import { Text } from '../Text/Text';
import { apiFetch } from '../../api/client';
import styles from './PublicProfileSheet.module.scss';

interface PublicChannel {
  id: string;
  title: string;
  handle: string;
  rating_avg: number;
  rating_count: number;
}

interface PublicCampaign {
  id: string;
  title: string;
  brief: string;
  rating_avg: number;
  rating_count: number;
}

interface PublicProfile {
  role_label: string;
  rating_advertiser_avg: number;
  rating_advertiser_count: number;
  rating_owner_avg: number;
  rating_owner_count: number;
  successful_deals_count: number;
  successful_purchases_count: number;
  channels: PublicChannel[];
  campaigns: PublicCampaign[];
}

interface PublicProfileSheetProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
}

export function PublicProfileSheet({ isOpen, onClose, userId }: PublicProfileSheetProps) {
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen || !userId) return;
    // Reset on open
    setProfile(null);
    setError('');
    setLoading(true);
    let cancelled = false;

    apiFetch(`/users/${userId}/public-profile`, { method: 'GET' })
      .then(r => {
        if (!r.ok) throw new Error('Failed to load profile');
        return r.json();
      })
      .then(data => {
        if (!cancelled) setProfile(data);
      })
      .catch(e => {
        if (!cancelled) setError(e.message || 'Error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [isOpen, userId]);

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title={profile?.role_label || 'Profile'}>
      <div className={styles.container}>
        {loading && <div className={styles.loading}>Loading...</div>}
        {error && <div className={styles.error}>{error}</div>}

        {profile && !loading && (
          <>
            {/* Header with avatar placeholder and role */}
            <div className={styles.header}>
              <div className={styles.avatarPlaceholder}>
                <VenetianMask size={32} />
              </div>
              <div className={styles.headerInfo}>
                <Text type="title" weight="bold">{profile.role_label}</Text>
                <div className={styles.statsRow}>
                  <span className={styles.statChip}>
                    {profile.successful_purchases_count} purchases
                  </span>
                  <span className={styles.statChip}>
                    {profile.successful_deals_count} deals
                  </span>
                </div>
              </div>
            </div>

            {/* Rating badges */}
            <div className={styles.ratingSection}>
              {(profile.rating_advertiser_count > 0 || profile.rating_owner_count > 0) ? (
                <>
                  {profile.rating_advertiser_count > 0 && (
                    <div className={styles.ratingRow}>
                      <RatingBadge
                        ratingAvg={profile.rating_advertiser_avg}
                        ratingCount={profile.rating_advertiser_count}
                        reviewsEndpoint={`/users/${userId}/reviews?role=advertiser`}
                        label="As Advertiser"
                      />
                      <span className={styles.roleLabel}>As Advertiser</span>
                    </div>
                  )}
                  {profile.rating_owner_count > 0 && (
                    <div className={styles.ratingRow}>
                      <RatingBadge
                        ratingAvg={profile.rating_owner_avg}
                        ratingCount={profile.rating_owner_count}
                        reviewsEndpoint={`/users/${userId}/reviews?role=owner`}
                        label="As Publisher"
                      />
                      <span className={styles.roleLabel}>As Publisher</span>
                    </div>
                  )}
                </>
              ) : (
                <div className={styles.noRatings}>No ratings yet</div>
              )}
            </div>

            {/* Campaigns list */}
            {profile.campaigns.length > 0 && (
              <div className={styles.section}>
                <Text type="caption" color="secondary" weight="bold" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Campaigns ({profile.campaigns.length})
                </Text>
                <div className={styles.entityList}>
                  {profile.campaigns.map(camp => (
                    <div key={camp.id} className={styles.entityItem}>
                      <div className={styles.entityIcon} style={{ borderRadius: '8px' }}><Megaphone size={18} /></div>
                      <div className={styles.entityInfo}>
                        <Text type="text" weight="bold">{camp.title}</Text>
                        <Text type="caption" color="secondary" className={styles.truncate}>
                          {camp.brief}
                        </Text>
                      </div>
                      <RatingBadge
                        ratingAvg={camp.rating_avg}
                        ratingCount={camp.rating_count}
                        reviewsEndpoint={`/campaigns/${camp.id}/reviews`}
                        label={`${camp.title} Reviews`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Channels list */}
            {profile.channels.length > 0 && (
              <div className={styles.section}>
                <Text type="caption" color="secondary" weight="bold" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Channels ({profile.channels.length})
                </Text>
                <div className={styles.entityList}>
                  {profile.channels.map(ch => (
                    <div key={ch.id} className={styles.entityItem}>
                      <div className={styles.entityIcon}>
                        {ch.title.charAt(0).toUpperCase()}
                      </div>
                      <div className={styles.entityInfo}>
                        <Text type="text" weight="bold">{ch.title}</Text>
                        <Text type="caption" color="secondary">@{ch.handle}</Text>
                      </div>
                      <RatingBadge
                        ratingAvg={ch.rating_avg}
                        ratingCount={ch.rating_count}
                        reviewsEndpoint={`/channels/${ch.id}/reviews`}
                        label={`${ch.title} Reviews`}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </BottomSheet>
  );
}
