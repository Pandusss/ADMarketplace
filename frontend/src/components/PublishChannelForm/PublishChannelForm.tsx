import { useEffect, useState } from 'react';
import { Button, Select, Text } from '../../ui';
import { apiFetch } from '../../api/client';
import styles from '../Forms.module.scss';
import { useNavigate } from 'react-router-dom';

interface PublishChannelFormProps {
    onSuccess: () => void;
    eligibleMyChannels: any[];
    myChannelsError?: string;
}

export function PublishChannelForm({ onSuccess, eligibleMyChannels, myChannelsError }: PublishChannelFormProps) {
    const navigate = useNavigate();
    const unpublishedChannels = eligibleMyChannels.filter(c => !c.is_published);

    const [publishTargetId, setPublishTargetId] = useState<string>(unpublishedChannels[0]?.id || '');
    const [publishSubmitting, setPublishSubmitting] = useState(false);
    const [publishError, setPublishError] = useState<string>('');

    const [walletAddress, setWalletAddress] = useState<string | null>(null);
    const [isLoadingProfile, setIsLoadingProfile] = useState(true);

    useEffect(() => {
        let cancelled = false;
        async function checkWallet() {
            try {
                const r = await apiFetch('/profile', { method: 'GET' });
                if (r.ok) {
                    const data = await r.json();
                    if (!cancelled) setWalletAddress(data.wallet_address || '');
                }
            } catch (e) {
                console.error('Failed to load profile for wallet check', e);
            } finally {
                if (!cancelled) setIsLoadingProfile(false);
            }
        }
        checkWallet();
        return () => { cancelled = true; };
    }, []);

    async function submitPublish() {
        if (!publishTargetId) {
            setPublishError('Please select a channel to publish.');
            return;
        }
        if (publishSubmitting) return;
        setPublishError('');

        setPublishSubmitting(true);
        try {
            const r = await apiFetch(`/channels/${publishTargetId}/publish`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            });
            if (!r.ok) throw new Error(await r.text());
            onSuccess();
        } catch (e: any) {
            setPublishError(String(e?.message || e || 'Failed to publish'));
        } finally {
            setPublishSubmitting(false);
        }
    }

    if (isLoadingProfile) {
        return (
            <div className={styles.form}>
                <Text type="text" color="secondary" style={{ textAlign: 'center', padding: '10px 0' }}>
                    Checking wallet status...
                </Text>
            </div>
        );
    }

    if (!walletAddress) {
        return (
            <div className={styles.form}>
                <Text type="text" color="secondary" style={{ textAlign: 'center', padding: '10px 0' }}>
                    You must connect your TON wallet before you can publish a channel and receive payouts.
                </Text>
                <Button onClick={() => navigate('/wallet')}>
                    Go to Wallet
                </Button>
            </div>
        );
    }

    if (unpublishedChannels.length === 0) {
        return (
            <div className={styles.form}>
                <Text type="text" color="secondary" style={{ textAlign: 'center', padding: '10px 0' }}>
                    {eligibleMyChannels.length === 0
                        ? "You don't have any verified channels yet. Add and verify a channel in My Assets first."
                        : "All your verified channels are already published in the feed."}
                </Text>
                <Button variant="secondary" onClick={() => navigate('/assets')}>
                    Go to My Assets
                </Button>
            </div>
        );
    }

    return (
        <div className={styles.form}>
            <Text type="caption" color="secondary" style={{ marginBottom: 4 }}>
                Select a verified channel to list it in the global feed.
            </Text>

            {myChannelsError && (
                <div className={styles.formError}>{myChannelsError}</div>
            )}

            <Select
                label="Verified channel"
                value={publishTargetId}
                onChange={(e) => setPublishTargetId(e.target.value)}
            >
                {unpublishedChannels.map((c) => (
                    <option key={c.id} value={c.id}>
                        {c.name || c.title || c.id}
                    </option>
                ))}
            </Select>

            {publishError && (
                <div className={styles.formError}>{publishError}</div>
            )}

            <Button isLoading={publishSubmitting} disabled={publishSubmitting} onClick={submitPublish}>
                Publish channel
            </Button>
        </div>
    );
}
