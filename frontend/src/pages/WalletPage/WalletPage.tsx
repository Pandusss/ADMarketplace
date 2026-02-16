import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTonAddress, useTonConnectUI, useTonWallet } from '@tonconnect/ui-react';
import { ExternalLink, CheckCircle2, ChevronDown, Copy, LogOut, Wallet } from 'lucide-react';
import { Button, Card, CardStack, Text } from '../../ui';
import { apiFetch } from '../../api/client';
import { formatDate, formatTON } from '../../utils/format';
import styles from './WalletPage.module.scss';

type Profile = {
  wallet_address: string;
  total_earned_ton: number;
};

export function WalletPage() {
  const [tonConnectUI] = useTonConnectUI();
  const wallet = useTonWallet();
  const friendlyAddress = useTonAddress(true);
  const isConnected = !!wallet;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileError, setProfileError] = useState<string>('');

  const [myChannels, setMyChannels] = useState<any[] | null>(null);
  const [channelsError, setChannelsError] = useState<string>('');

  const [deals, setDeals] = useState<any[] | null>(null);
  const [dealsError, setDealsError] = useState<string>('');
  const [showAllHistory, setShowAllHistory] = useState(false);

  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const syncedAddressRef = useRef<string>('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const r = await apiFetch('/profile', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as Profile;
        if (!cancelled) setProfile(data);
      } catch (e: any) {
        if (!cancelled) setProfileError(String(e?.message || e || 'Failed to load wallet'));
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

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
          setChannelsError(String(e?.message || e || 'Failed to load your channels'));
        }
      }
    }
    loadMyChannels();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadDeals() {
      try {
        const r = await apiFetch('/deals', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as any[];
        if (!cancelled) setDeals(data);
      } catch (e: any) {
        if (!cancelled) {
          setDeals([]);
          setDealsError(String(e?.message || e || 'Failed to load payouts'));
        }
      }
    }
    loadDeals();
    return () => { cancelled = true; };
  }, []);

  const syncWalletToBackend = useCallback(async (address: string) => {
    if (syncedAddressRef.current === address) return;
    try {
      const r = await apiFetch('/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: address }),
      });
      if (!r.ok) throw new Error(await r.text());
      const data = (await r.json()) as Profile;
      setProfile(data);
      syncedAddressRef.current = address;
    } catch (e: any) {
      console.error('Failed to sync wallet:', e);
    }
  }, []);

  useEffect(() => {
    if (isConnected && friendlyAddress) {
      syncWalletToBackend(friendlyAddress);
    }
  }, [isConnected, friendlyAddress, syncWalletToBackend]);

  const handleDisconnect = useCallback(async () => {
    await tonConnectUI.disconnect();
    syncedAddressRef.current = '';
    syncWalletToBackend('');
    setIsMenuOpen(false);
  }, [tonConnectUI, syncWalletToBackend]);

  const handleCopyAddress = useCallback(() => {
    if (friendlyAddress) {
      navigator.clipboard.writeText(friendlyAddress);
      // Optional: show some feedback that it's copied
    }
    setIsMenuOpen(false);
  }, [friendlyAddress]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const formatShortAddress = (addr: string) => {
    if (!addr) return '';
    return `${addr.slice(0, 4)}...${addr.slice(-4)}`;
  };

  const ownedChannelIds = useMemo(() => new Set((myChannels || []).map((c) => c.id)), [myChannels]);

  const payouts = useMemo(() => {
    const data = deals || [];
    return data
      .filter((d) => ownedChannelIds.has(d.channel_id) && d.status === 'released')
      .map((d) => ({
        id: d.id,
        channelName: d.channel_name || d.channel_id,
        amountTON: d.price_ton || 0,
        releasedAt: d.released_at || d.updated_at || '',
        txHash: d.release_tx_hash || '',
      }))
      .sort((a, b) => (a.releasedAt < b.releasedAt ? 1 : -1));
  }, [deals, ownedChannelIds]);

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">Wallet</Text>
          <div className={styles.headerEarned}>
            <Text type="caption" color="secondary">Total earned: </Text>
            <Text type="text" weight="bold" color="accent">
              {formatTON(profile?.total_earned_ton || 0)}
            </Text>
          </div>
        </div>

        {(profileError || channelsError || dealsError) && (
          <Card>
            <Text type="title2">Can't load wallet</Text>
            <Text type="caption" color="secondary">
              {[profileError, channelsError, dealsError].filter(Boolean).join(' • ')}
            </Text>
          </Card>
        )}

        <Card className={styles.addressCard}>
          <div className={styles.addressBody}>
            {isConnected ? (
              <div ref={dropdownRef} style={{ position: 'relative' }}>
                <div className={styles.addressHeader}>
                  <div className={styles.walletIconWrapper}>
                    <Wallet size={24} />
                  </div>
                  <div className={styles.walletTitleInfo}>
                    <Text type="text" weight="bold">TON Wallet</Text>
                    <div className={styles.walletStatus}>
                      <CheckCircle2 size={14} />
                      <Text type="caption" style={{ color: 'inherit' }}>Connected</Text>
                    </div>
                  </div>
                </div>

                <button
                  className={styles.dropdownTrigger}
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                >
                  <span className={styles.walletValueShort}>
                    {formatShortAddress(friendlyAddress)}
                  </span>
                  <ChevronDown
                    size={18}
                    className={`${styles.chevronIcon} ${isMenuOpen ? styles.open : ''}`}
                  />
                </button>

                {isMenuOpen && (
                  <div className={styles.dropdownMenu}>
                    <button className={styles.menuItem} onClick={handleCopyAddress}>
                      <Copy size={18} />
                      Copy Address
                    </button>
                    <button
                      className={`${styles.menuItem} ${styles.danger}`}
                      onClick={handleDisconnect}
                    >
                      <LogOut size={18} />
                      Disconnect
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className={styles.connectWalletSection}>
                <Text type="text" color="secondary">
                  Connect your wallet to receive payouts
                </Text>
                <Button onClick={() => tonConnectUI.openModal()}>
                  Connect Wallet
                </Button>
              </div>
            )}
          </div>
        </Card>

        <div className={styles.sectionHeader}>
          <Text type="title2" weight="bold">Payout history</Text>
        </div>

        <CardStack className={styles.list}>
          {(profile === null || myChannels === null || deals === null) && !profileError && !channelsError && !dealsError && (
            <Card>
              <Text type="title2">Loading…</Text>
              <Text type="text" color="secondary">
                Fetching wallet data…
              </Text>
            </Card>
          )}

          {profile !== null && myChannels !== null && deals !== null && payouts.length === 0 && !dealsError && (
            <Card>
              <div className={styles.emptyState}>
                <Text type="title2">No payouts yet</Text>
                <Text type="text" color="secondary">
                  Payouts appear after a deal is released.
                </Text>
              </div>
            </Card>
          )}

          {(showAllHistory ? payouts : payouts.slice(0, 3)).map((p) => (
            <Card key={p.id}>
              <div className={styles.payoutCard}>
                <div className={styles.payoutMain}>
                  <div className={styles.payoutInfo}>
                    <Text type="title2" weight="bold">#{p.id}</Text>
                    {p.releasedAt && (
                      <Text type="caption" color="secondary">
                        {formatDate(p.releasedAt)}
                      </Text>
                    )}
                  </div>
                  <div className={styles.payoutAmount}>
                    <Text type="text" weight="bold" color="accent">
                      {formatTON(p.amountTON)}
                    </Text>
                  </div>
                </div>

                <div className={styles.payoutActions}>
                  {p.txHash && (
                    <a
                      href={`https://tonviewer.com/transaction/${p.txHash}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.txLink}
                    >
                      <ExternalLink size={14} />
                      <span>Tonviewer</span>
                    </a>
                  )}
                </div>
              </div>
            </Card>
          ))}

          {payouts.length > 3 && (
            <Button
              variant="outline"
              size="small"
              onClick={() => setShowAllHistory(!showAllHistory)}
              className={styles.showMoreBtn}
            >
              {showAllHistory ? 'Hide history' : `Show all (${payouts.length})`}
            </Button>
          )}
        </CardStack>
      </div>
    </div>
  );
}
