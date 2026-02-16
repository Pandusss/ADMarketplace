import { useState } from 'react';
import { Coins, Megaphone, CalendarDays, Timer, Banknote, Landmark, Palette, CircleCheck, Hourglass } from 'lucide-react';
import { Button, Card, Text } from '../../ui';
import { formatTON } from '../../utils/format';
import { confirmDeal } from '../../api/client';
import { tgInitData } from '../../api/client';

interface DealConfirmationCardProps {
    deal: any;
    isAdvertiser: boolean;
    canConfirm: boolean;
    onConfirmSuccess: () => void;
}

export function DealConfirmationCard({ deal, isAdvertiser, canConfirm, onConfirmSuccess }: DealConfirmationCardProps) {
    const [isActing, setIsActing] = useState(false);
    const [error, setError] = useState('');

    const myConfirmed = isAdvertiser ? deal.deal_confirmed_by_advertiser : deal.deal_confirmed_by_channel;
    const otherConfirmed = isAdvertiser ? deal.deal_confirmed_by_channel : deal.deal_confirmed_by_advertiser;

    const handleConfirm = async () => {
        setIsActing(true);
        setError('');
        try {
            await confirmDeal(deal.id);
            onConfirmSuccess();
        } catch (e: any) {
            setError(e.message || 'Failed to confirm deal');
        } finally {
            setIsActing(false);
        }
    };

    const formatDuration = (hours: number | null | undefined) => {
        if (!hours) return '—';
        if (hours >= 24) return `${hours / 24} day${hours / 24 !== 1 ? 's' : ''}`;
        return `${hours} hour${hours !== 1 ? 's' : ''}`;
    };

    return (
        <Card style={{ padding: 16, border: '1px solid var(--color-accent-primary)', background: 'var(--tg-theme-secondary-bg-color)' }}>
            <Text type="title2" weight="bold" style={{ marginBottom: 16 }}>Final Confirmation</Text>

            <div style={{ display: 'grid', gap: 14 }}>
                {/* Summary grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    <div>
                        <Text type="caption" color="secondary"><Coins size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Price</Text>
                        <Text type="text" weight="medium">{formatTON(deal.price_ton)}</Text>
                    </div>
                    <div>
                        <Text type="caption" color="secondary"><Megaphone size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Channel</Text>
                        <Text type="text" weight="medium">{deal.channel_name || deal.channel_id}</Text>
                    </div>
                    <div>
                        <Text type="caption" color="secondary"><CalendarDays size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Publish at</Text>
                        <Text type="text" weight="medium">
                            {deal.scheduled_at ? new Date(deal.scheduled_at).toLocaleString() : '—'}
                        </Text>
                    </div>
                    <div>
                        <Text type="caption" color="secondary"><Timer size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Post duration</Text>
                        <Text type="text" weight="medium">{formatDuration(deal.post_duration_hours)}</Text>
                    </div>
                </div>

                {/* Auto-release explanation */}
                <div style={{ padding: '10px 12px', background: 'color-mix(in srgb, var(--color-accent-primary) 8%, transparent)', borderRadius: 10 }}>
                    <Text type="caption" color="secondary">
                        <Banknote size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Funds will be automatically released {formatDuration(deal.post_duration_hours)} after publication, if the post is still live.
                    </Text>
                </div>

                {/* Seller wallet */}
                {deal.seller_wallet && (
                    <div>
                        <Text type="caption" color="secondary"><Landmark size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Seller wallet</Text>
                        <Text type="caption" style={{ fontSize: 11, wordBreak: 'break-all', opacity: 0.7 }}>{deal.seller_wallet}</Text>
                    </div>
                )}

                {/* Creative Preview */}
                {(deal.creative_preview_text || deal.creative_preview_has_media) && (
                    <div style={{ padding: 10, background: 'var(--tg-theme-bg-color)', borderRadius: 8 }}>
                        <Text type="caption" color="secondary" style={{ marginBottom: 6, display: 'block' }}><Palette size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Creative Preview</Text>
                        {deal.creative_preview_has_media && (
                            <img
                                src={`/api/deals/${deal.id}/preview-media?i=0&initData=${encodeURIComponent(tgInitData())}`}
                                alt="Preview"
                                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                                style={{ width: '100%', maxHeight: 150, objectFit: 'cover', borderRadius: 8, marginBottom: 6 }}
                            />
                        )}
                        {deal.creative_preview_text && (
                            <Text type="caption" color="secondary">
                                <span dangerouslySetInnerHTML={{ __html: deal.creative_preview_text }} />
                            </Text>
                        )}
                    </div>
                )}

                {/* Status Indicators */}
                <div style={{ display: 'flex', gap: 12 }}>
                    <div style={{ flex: 1, padding: 8, borderRadius: 6, background: myConfirmed ? 'rgba(0,255,0,0.1)' : 'rgba(255,165,0,0.1)', textAlign: 'center' }}>
                        <Text type="caption" weight="bold">{myConfirmed ? <><CircleCheck size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />You confirmed</> : <><Hourglass size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Waiting for you</>}</Text>
                    </div>
                    <div style={{ flex: 1, padding: 8, borderRadius: 6, background: otherConfirmed ? 'rgba(0,255,0,0.1)' : 'rgba(255,165,0,0.1)', textAlign: 'center' }}>
                        <Text type="caption" weight="bold">{otherConfirmed ? <><CircleCheck size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Partner confirmed</> : <><Hourglass size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />Waiting for partner</>}</Text>
                    </div>
                </div>

                {error && <Text type="caption" style={{ color: 'var(--color-danger)' }}>{error}</Text>}

                {canConfirm && (
                    <Button
                        onClick={handleConfirm}
                        isLoading={isActing}
                        disabled={isActing}
                    >
                        Confirm & Schedule
                    </Button>
                )}

                {myConfirmed && !otherConfirmed && (
                    <Text type="caption" color="secondary" style={{ textAlign: 'center' }}>
                        Waiting for the other party to confirm...
                    </Text>
                )}
            </div>
        </Card>
    );
}
