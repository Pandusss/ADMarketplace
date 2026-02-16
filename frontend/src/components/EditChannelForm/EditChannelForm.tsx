import { useState } from 'react';
import { Button, InfoTooltip, Input, Select, Text, Textarea } from '../../ui';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import { apiFetch } from '../../api/client';
import styles from './EditChannelForm.module.scss';

interface EditChannelFormProps {
    channel: {
        id: string;
        name: string;
        handle: string;
        category?: string;
        language?: string;
        price_per_post_ton: number;
        price_top_hour_ton?: number;
        description: string;
        posting_window_start?: string;
        posting_window_end?: string;
    };
    onSuccess: (updatedChannel: any) => void;
    onCancel: () => void;
}

export function EditChannelForm({ channel, onSuccess, onCancel }: EditChannelFormProps) {
    const [category, setCategory] = useState<ChannelCategory>((channel.category as ChannelCategory) || 'Crypto');
    const [language, setLanguage] = useState<ChannelLanguage>((channel.language as ChannelLanguage) || 'EN');
    const [pricePerPostTON, setPricePerPostTON] = useState(channel.price_per_post_ton.toString());
    const [priceTopHourTON, setPriceTopHourTON] = useState((channel as any).price_top_hour_ton?.toString() || '0');
    const [topPriceStepPct, setTopPriceStepPct] = useState((channel as any).top_price_step_pct?.toString() || '0');
    const [description, setDescription] = useState(channel.description || '');
    const [startTime, setStartTime] = useState(channel.posting_window_start || '10:00');
    const [endTime, setEndTime] = useState(channel.posting_window_end || '20:00');
    const [error, setError] = useState<string | null>(null);
    const [isSaving, setIsSaving] = useState(false);

    function sanitizeTonAmountInput(raw: string): string {
        const cleaned = raw.replace(/[^\d.,]/g, '');
        const withDots = cleaned.replace(/,/g, '.');
        const parts = withDots.split('.');
        if (parts.length <= 1) return withDots;
        return `${parts[0]}.${parts.slice(1).join('')}`;
    }

    function parseTonAmount(raw: string): number {
        const normalized = sanitizeTonAmountInput(raw).trim();
        const n = Number(normalized || '0');
        return Number.isFinite(n) ? n : 0;
    }

    const canSave = parseTonAmount(pricePerPostTON) > 0;

    async function handleSave() {
        setIsSaving(true);
        setError(null);
        try {
            const price = parseTonAmount(pricePerPostTON);
            const r = await apiFetch(`/channels/${channel.id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category,
                    language,
                    price_per_post_ton: price,
                    price_top_hour_ton: parseTonAmount(priceTopHourTON),
                    top_price_step_pct: parseTonAmount(topPriceStepPct),
                    description,
                    posting_window_start: startTime,
                    posting_window_end: endTime,
                }),
            });
            if (!r.ok) throw new Error(await r.text());
            const updated = await r.json();
            onSuccess(updated);
        } catch (e: any) {
            setError(String(e?.message || e || 'Failed to update channel'));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <div className={styles.container}>
            <Text type="caption" color="secondary" style={{ marginBottom: 12, display: 'block' }}>
                Editing: <b>@{channel.handle}</b>
            </Text>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
                <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value as ChannelCategory)}>
                    <option value="Crypto">Crypto</option>
                    <option value="Gaming">Gaming</option>
                    <option value="Business">Business</option>
                    <option value="News">News</option>
                    <option value="Lifestyle">Lifestyle</option>
                </Select>

                <Select label="Language" value={language} onChange={(e) => setLanguage(e.target.value as ChannelLanguage)}>
                    <option value="EN">EN</option>
                    <option value="RU">RU</option>
                    <option value="ES">ES</option>
                    <option value="DE">DE</option>
                    <option value="UA">UA</option>
                </Select>

                <Input
                    label="Per post (TON)"
                    inputMode="decimal"
                    type="text"
                    placeholder="e.g. 10.5"
                    value={pricePerPostTON}
                    onChange={(e) => setPricePerPostTON(sanitizeTonAmountInput(e.target.value))}
                />

                <Input
                    label="Extra Top hour (TON)"
                    inputMode="decimal"
                    type="text"
                    placeholder="e.g. 5"
                    value={priceTopHourTON}
                    onChange={(e) => setPriceTopHourTON(sanitizeTonAmountInput(e.target.value))}
                />

                <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 4, marginBottom: 6 }}>
                        <span style={{ fontSize: 13, lineHeight: '16px', color: 'var(--color-foreground-secondary)' }}>Top Price Step (%)</span>
                        <InfoTooltip
                            title="Step escalation"
                            content="Each next hour of Top costs more than the previous one by this percentage. This helps protect your channel feed from being locked by a single advertiser for too long."
                            align="center"
                            position="bottom"
                        />
                    </div>
                    <Input
                        inputMode="decimal"
                        type="text"
                        placeholder="e.g. 10"
                        value={topPriceStepPct}
                        onChange={(e) => setTopPriceStepPct(sanitizeTonAmountInput(e.target.value))}
                        hint="Every next hour becomes more expensive by this %"
                    />
                </div>

                <div style={{ display: 'flex', gap: 10 }}>
                    <Input
                        label="Posting start (UTC)"
                        type="time"
                        value={startTime}
                        onChange={(e) => setStartTime(e.target.value)}
                    />
                    <Input
                        label="Posting end (UTC)"
                        type="time"
                        value={endTime}
                        onChange={(e) => setEndTime(e.target.value)}
                    />
                </div>

                <Textarea
                    label="Description"
                    placeholder="What is the channel about?"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                />
            </div>

            {error ? (
                <Text type="caption" color="secondary" style={{ marginTop: 12, display: 'block', color: 'var(--color-state-destructive)' }}>
                    {error}
                </Text>
            ) : null}

            <div style={{ display: 'flex', gap: 8, marginTop: 24 }}>
                <Button variant="secondary" onClick={onCancel} disabled={isSaving}>
                    Cancel
                </Button>
                <Button disabled={!canSave || isSaving} isLoading={isSaving} onClick={handleSave}>
                    Save Changes
                </Button>
            </div>
        </div>
    );
}
