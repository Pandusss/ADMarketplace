import { useEffect, useState } from 'react';
import { Megaphone } from 'lucide-react';
import { RatingBadge } from '../../ui/RatingBadge/RatingBadge';
import { Button, Card, CardStack, StarRating, Text } from '../../ui';
import { formatTON } from '../../utils/format';
import { apiFetch } from '../../api/client';
import styles from './ProfilePage.module.scss';

type Profile = {
  id: string;
  display_name: string;
  telegram_username: string | null;
  wallet_address: string;
  total_earned_ton: number;
  successful_deals_count: number;
  successful_purchases_count: number;
  rating_avg: number;
  rating_count: number;
  rating_advertiser_avg: number;
  rating_advertiser_count: number;
  rating_owner_avg: number;
  rating_owner_count: number;
};

type Channel = {
  id: string;
  name: string;
  handle: string;
  rating_avg: number;
  rating_count: number;
  avatar_file_id: string | null;
};

type Campaign = {
  id: string;
  title: string;
  brief: string;
  rating_avg: number;
  rating_count: number;
  owner_rating_avg: number;
  owner_rating_count: number;
};

export function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [activeTab, setActiveTab] = useState<'channels' | 'campaigns'>('channels');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [profRes, chanRes, campRes] = await Promise.all([
          apiFetch('/profile', { method: 'GET' }),
          apiFetch('/channels/my/list', { method: 'GET' }),
          apiFetch('/campaigns/my', { method: 'GET' })
        ]);

        if (!profRes.ok) throw new Error(await profRes.text());
        const profData = (await profRes.json()) as Profile;
        if (!cancelled) setProfile(profData);

        if (chanRes.ok) {
          const chanData = (await chanRes.json()) as Channel[];
          if (!cancelled) setChannels(chanData);
        }

        if (campRes.ok) {
          const campData = (await campRes.json()) as Campaign[];
          if (!cancelled) setCampaigns(campData);
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(String(e?.message || e || 'Failed to load profile'));
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error && !profile) {
    return (
      <div className={styles.page}>
        <div className={`${styles.content} noScrollbar`}>
          <Text type="text" color="danger">
            {error}
          </Text>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className={styles.page}>
        <div className={`${styles.content} noScrollbar`}>
          <Text type="text" color="secondary">
            Loading...
          </Text>
        </div>
      </div>
    );
  }

  const tg = (window as any).Telegram?.WebApp;
  const user = tg?.initDataUnsafe?.user;
  const avatarUrl = user?.photo_url;

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <CardStack>
          <Card>
            <div className={styles.header}>
              {avatarUrl ? (
                <img src={avatarUrl} alt="Avatar" className={styles.avatar} />
              ) : (
                <div className={styles.avatarPlaceholder}>
                  {profile.display_name.charAt(0).toUpperCase()}
                </div>
              )}
              <div className={styles.headerInfo}>
                <Text type="title" weight="bold">
                  {profile.display_name}
                </Text>
                {profile.telegram_username && (
                  <Text type="caption" color="secondary">
                    @{profile.telegram_username}
                  </Text>
                )}
                <div className={styles.ratingSection}>
                  {profile.rating_advertiser_count > 0 && (
                    <div className={styles.ratingBadgeWrapper}>
                      <RatingBadge
                        ratingAvg={profile.rating_advertiser_avg}
                        ratingCount={profile.rating_advertiser_count}
                        reviewsEndpoint={`/users/${profile.id}/reviews?role=advertiser`}
                        label="As Advertiser"
                      />
                      <Text type="caption" color="secondary">As Advertiser</Text>
                    </div>
                  )}
                  {profile.rating_owner_count > 0 && (
                    <div className={styles.ratingBadgeWrapper}>
                      <RatingBadge
                        ratingAvg={profile.rating_owner_avg}
                        ratingCount={profile.rating_owner_count}
                        reviewsEndpoint={`/users/${profile.id}/reviews?role=owner`}
                        label="As Publisher"
                      />
                      <Text type="caption" color="secondary">As Publisher</Text>
                    </div>
                  )}
                  {profile.rating_advertiser_count === 0 && profile.rating_owner_count === 0 && profile.rating_count > 0 && (
                    <RatingBadge
                      ratingAvg={profile.rating_avg}
                      ratingCount={profile.rating_count}
                      reviewsEndpoint={`/users/${profile.id}/reviews`}
                      label="Overall Rating"
                    />
                  )}
                </div>
              </div>
            </div>
          </Card>

          <div className={styles.tabsContainer}>
            <div className={styles.tabs}>
              <button
                className={`${styles.tab} ${activeTab === 'channels' ? styles.activeTab : ''}`}
                onClick={() => setActiveTab('channels')}
              >
                Channels ({channels.length})
              </button>
              <button
                className={`${styles.tab} ${activeTab === 'campaigns' ? styles.activeTab : ''}`}
                onClick={() => setActiveTab('campaigns')}
              >
                Campaigns ({campaigns.length})
              </button>
            </div>
          </div>

          {activeTab === 'channels' && (
            <>
              {channels.length > 0 ? (
                <Card>
                  <div className={styles.section}>
                    {channels.map(ch => (
                      <div key={ch.id} className={styles.channelItem}>
                        {ch.avatar_file_id ? (
                          <img
                            src={`/api/channels/${ch.id}/avatar`}
                            alt={ch.name}
                            className={styles.channelAvatar}
                          />
                        ) : (
                          <div className={styles.channelAvatarPlaceholder}>
                            {ch.name.charAt(0).toUpperCase()}
                          </div>
                        )}
                        <div className={styles.channelInfo}>
                          <Text type="text" weight="bold">{ch.name}</Text>
                          <Text type="caption" color="secondary">@{ch.handle}</Text>
                        </div>
                        <RatingBadge
                          ratingAvg={ch.rating_avg}
                          ratingCount={ch.rating_count}
                          reviewsEndpoint={`/channels/${ch.id}/reviews`}
                          label={`${ch.name} Reviews`}
                        />
                      </div>
                    ))}
                  </div>
                </Card>
              ) : (
                <Card>
                  <Text type="text" color="secondary" style={{ textAlign: 'center', padding: '20px 0' }}>No channels yet</Text>
                </Card>
              )}
            </>
          )}

          {activeTab === 'campaigns' && (
            <>
              {campaigns.length > 0 ? (
                <Card>
                  <div className={styles.section}>
                    {campaigns.map(camp => (
                      <div key={camp.id} className={styles.channelItem}>
                        <div className={styles.channelAvatarPlaceholder} style={{ borderRadius: '8px' }}>
                          <Megaphone size={18} />
                        </div>
                        <div className={styles.channelInfo}>
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
                </Card>
              ) : (
                <Card>
                  <Text type="text" color="secondary" style={{ textAlign: 'center', padding: '20px 0' }}>No campaigns yet</Text>
                </Card>
              )}
            </>
          )}
        </CardStack>
      </div>
    </div>
  );
}
