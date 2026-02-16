import { useState, useMemo, useEffect } from 'react';
import { Button, Input, Select, Text } from '../../ui';
import { apiFetch } from '../../api/client';
import { Campaign } from './CampaignDetails';
import styles from '../Forms.module.scss';
import { useNavigate } from 'react-router-dom';

interface ApplyCampaignFormProps {
    campaign: Campaign;
    onSuccess: () => void;
    onErrorConfirm?: (error: string) => void;
}

export function ApplyCampaignForm({ campaign, onSuccess }: ApplyCampaignFormProps) {
    const navigate = useNavigate();
    const [myChannels, setMyChannels] = useState<any[] | null>(null);
    const [myChannelsError, setMyChannelsError] = useState<string>('');
    const [applyChannelId, setApplyChannelId] = useState<string>('');
    const [applyOffer, setApplyOffer] = useState<string>('');
    const [applyMessage, setApplyMessage] = useState<string>('');
    const [applyError, setApplyError] = useState<string>('');
    const [applySubmitting, setApplySubmitting] = useState(false);

    useEffect(() => {
        let cancelled = false;
        async function loadMyChannels() {
            try {
                const r = await apiFetch('/my/channels', { method: 'GET' });
                if (!r.ok) throw new Error(await r.text());
                const data = (await r.json()) as any[];
                if (!cancelled) {
                    setMyChannels(data);
                    const verified = data.filter(c => c.is_verified);
                    if (verified.length > 0) setApplyChannelId(verified[0].id);
                }
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

    const eligibleMyChannels = useMemo(() => {
        const data = myChannels || [];
        return data.filter((c) => Boolean(c.is_verified) !== false);
    }, [myChannels]);

    async function submitApply() {
        if (applySubmitting) return;
        setApplyError('');

        const channelId = applyChannelId.trim();
        if (!channelId) {
            setApplyError('Choose a channel to apply with.');
            return;
        }

        const offerNum = applyOffer.trim() ? Number(applyOffer.trim().replace(',', '.')) : 0;
        if (Number.isNaN(offerNum) || offerNum < 0) {
            setApplyError('Offer price must be a number.');
            return;
        }

        setApplySubmitting(true);
        try {
            const r = await apiFetch(`/campaigns/${campaign.id}/apply`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    channel_id: channelId,
                    offer_price_ton: offerNum,
                    message: applyMessage.trim() || '',
                }),
            });
            if (!r.ok) throw new Error(await r.text());
            onSuccess();
        } catch (e: any) {
            setApplyError(String(e?.message || e || 'Failed to apply'));
        } finally {
            setApplySubmitting(false);
        }
    }

    if (myChannels === null) return <Text type="text" color="secondary">Loading your channels...</Text>;

    if (eligibleMyChannels.length === 0) {
        return (
            <div className={styles.form}>
                <Text type="text" color="secondary" style={{ marginBottom: 12 }}>
                    You need a verified channel to make an offer. Add and verify your channel first.
                </Text>
                <Button variant="secondary" onClick={() => navigate('/assets')}>
                    Go to My Assets
                </Button>
            </div>
        );
    }

    return (
        <div className={styles.form}>
            <Select label="Your channel" value={applyChannelId} onChange={(e) => setApplyChannelId(e.target.value)}>
                {eligibleMyChannels.map((c) => (
                    <option key={c.id} value={c.id}>
                        {c.name || c.title || c.id}
                    </option>
                ))}
            </Select>

            <Input
                label="Offer price (TON)"
                value={applyOffer}
                onChange={(e) => setApplyOffer(e.target.value)}
                placeholder="e.g. 10"
                inputMode="decimal"
            />
            <Input
                label="Message (optional)"
                value={applyMessage}
                onChange={(e) => setApplyMessage(e.target.value)}
                placeholder="Short note"
            />

            {applyError && <div className={styles.formError}>{applyError}</div>}
            {myChannelsError && <div className={styles.formError}>{myChannelsError}</div>}

            <Button isLoading={applySubmitting} disabled={applySubmitting} onClick={submitApply} style={{ marginTop: 8 }}>
                Submit offer
            </Button>
        </div>
    );
}
