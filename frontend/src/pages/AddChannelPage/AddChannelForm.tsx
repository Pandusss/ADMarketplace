import { useEffect, useMemo, useRef, useState } from 'react';
import { Badge, Button, Card, InfoTooltip, Input, Select, Text, Textarea } from '../../ui';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import { apiFetch } from '../../api/client';
import styles from './AddChannelForm.module.scss';

function apiBaseUrl(): string {
    const v = (import.meta as any).env?.VITE_API_BASE_URL as string | undefined;
    return (v?.trim() || '').replace(/\/$/, '');
}

function apiUrl(path: string): string {
    const base = apiBaseUrl();
    if (base) return `${base}/api${path}`;
    return `/api${path}`;
}

export function AddChannelForm({ onSuccess }: { onSuccess: () => void }) {
    const [step, setStep] = useState<1 | 2>(1);
    const [addBotUrl, setAddBotUrl] = useState<string | null>(null);
    const [verificationToken, setVerificationToken] = useState<string | null>(null);
    const [addBotError, setAddBotError] = useState<string | null>(null);
    const [isLoadingAddBotUrl, setIsLoadingAddBotUrl] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const pollIntervalRef = useRef<number | null>(null);
    const [detectedTitle, setDetectedTitle] = useState<string | null>(null);
    const [detectedHandle, setDetectedHandle] = useState<string | null>(null);
    const [isVerified, setIsVerified] = useState(false);

    // Step 2 fields
    const [category, setCategory] = useState<ChannelCategory>('Crypto');
    const [language, setLanguage] = useState<ChannelLanguage>('EN');
    const [pricePerPostTON, setPricePerPostTON] = useState('150');
    const [priceTopHourTON, setPriceTopHourTON] = useState('20');
    const [topPriceStepPct, setTopPriceStepPct] = useState('0');
    const [description, setDescription] = useState('');
    const [startTime, setStartTime] = useState('10:00');
    const [endTime, setEndTime] = useState('20:00');
    const [saveError, setSaveError] = useState<string | null>(null);
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

    function tgInitData(): string {
        return ((window as any).Telegram?.WebApp?.initData as string | undefined) || '';
    }

    function openTelegramLink(url: string) {
        const tg = (window as any).Telegram?.WebApp;
        if (tg?.openTelegramLink) {
            tg.openTelegramLink(url);
        } else {
            window.location.href = url;
        }
    }

    async function initVerificationAndGetLink(): Promise<{ url: string; token: string } | null> {
        setIsLoadingAddBotUrl(true);
        setAddBotError(null);
        try {
            const initData = tgInitData();
            if (!initData) {
                setAddBotError('Open this page inside Telegram Mini App (initData is missing in a regular browser).');
                return null;
            }

            const token = `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
            const r = await fetch(apiUrl('/channels/verification/init'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ initData, token }),
            });
            if (!r.ok) {
                const body = await r.text().catch(() => '');
                throw new Error(body || `HTTP ${r.status}`);
            }
            const data = (await r.json()) as { add_bot_url?: string; token?: string };
            const url = data.add_bot_url?.trim() || null;
            const serverToken = data.token?.trim() || token;
            setAddBotUrl(url);
            setVerificationToken(serverToken);
            if (!url) setAddBotError('Backend did not return add_bot_url');
            return url ? { url, token: serverToken } : null;
        } catch (e) {
            setAddBotUrl(null);
            setVerificationToken(null);
            const msg = e instanceof Error ? e.message : String(e);
            setAddBotError(msg || 'Failed to load bot link.');
            return null;
        } finally {
            setIsLoadingAddBotUrl(false);
        }
    }

    useEffect(() => {
        if (!verificationToken || step !== 1 || isVerified) return;
        if (pollIntervalRef.current != null) return;

        setIsPolling(true);
        let cancelled = false;

        const interval = window.setInterval(async () => {
            try {
                const r = await fetch(apiUrl('/channels/verification/status'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ initData: tgInitData(), token: verificationToken }),
                });
                if (!r.ok) return;
                const data = (await r.json()) as {
                    verified?: boolean;
                    channel_title?: string | null;
                    channel_username?: string | null;
                };
                if (cancelled) return;
                if (data.verified) {
                    setDetectedTitle(data.channel_title || 'Detected Channel');
                    setDetectedHandle(data.channel_username || null);
                    setIsVerified(true);
                    if (pollIntervalRef.current != null) {
                        window.clearInterval(pollIntervalRef.current);
                        pollIntervalRef.current = null;
                    }
                    setIsPolling(false);
                }
            } catch {
                // keep polling
            }
        }, 2000);

        pollIntervalRef.current = interval;
        return () => {
            cancelled = true;
            if (pollIntervalRef.current != null) {
                window.clearInterval(pollIntervalRef.current);
                pollIntervalRef.current = null;
            }
            setIsPolling(false);
        };
    }, [isVerified, step, verificationToken]);

    const detected = useMemo(() => {
        return {
            name: detectedTitle || 'Detected Channel',
            handle: detectedHandle || '',
        };
    }, [detectedHandle, detectedTitle]);

    const canPublish = parseTonAmount(pricePerPostTON) > 0;

    async function completeStep2(): Promise<void> {
        if (!verificationToken) return;
        setIsSaving(true);
        setSaveError(null);
        try {
            const initData = tgInitData();
            const price = parseTonAmount(pricePerPostTON);
            const r = await apiFetch('/channels/verification/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    initData,
                    token: verificationToken,
                    category,
                    language,
                    pricePerPostTON: Number.isFinite(price) ? price : 0,
                    priceTopHourTON: Number.isFinite(parseTonAmount(priceTopHourTON)) ? parseTonAmount(priceTopHourTON) : 0,
                    topPriceStepPct: Number.isFinite(parseTonAmount(topPriceStepPct)) ? parseTonAmount(topPriceStepPct) : 0,
                    description,
                    postingWindowStart: startTime,
                    postingWindowEnd: endTime,
                    postingSlotMinutes: 30,
                }),
            });
            if (!r.ok) throw new Error(await r.text());
            onSuccess();
        } catch (e: any) {
            setSaveError(String(e?.message || e || 'Failed to save channel'));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <div className={styles.container}>

            <div className={styles.steps} aria-label="Add channel steps">
                <div className={`${styles.stepPill} ${step === 1 ? styles.active : ''}`}>1) Verification</div>
                <div className={`${styles.stepPill} ${step === 2 ? styles.active : ''}`}>2) Setup</div>
            </div>

            {step === 1 ? (
                <div className={styles.stepContent}>
                    <Text type="text" color="secondary" style={{ marginBottom: 16, display: 'block' }}>
                        Add our bot as an admin in your Telegram channel, then come back here.
                    </Text>

                    {verificationToken && !isVerified && !addBotError ? (
                        <Text type="caption" color="secondary" style={{ marginBottom: 12, display: 'block' }}>
                            Waiting for confirmation from Telegram… (this can take a few seconds)
                        </Text>
                    ) : null}

                    {isVerified ? (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 16 }}>
                            <div>
                                <Text type="text">
                                    <b>{detectedHandle ? `@${detectedHandle}` : detectedTitle || 'Channel'}</b>
                                </Text>
                                <Text type="caption" color="secondary">
                                    Verified
                                </Text>
                            </div>
                            <Badge tone="success">Verified</Badge>
                        </div>
                    ) : null}

                    {addBotError ? (
                        <Text type="caption" color="secondary" style={{ marginBottom: 16, display: 'block' }}>
                            {addBotError}
                        </Text>
                    ) : !isVerified ? (
                        <Text type="caption" color="secondary" style={{ marginBottom: 16, display: 'block' }}>
                            This will open Telegram and ask you to pick a channel.
                        </Text>
                    ) : null}

                    {!isVerified && (
                        <Button
                            isLoading={isLoadingAddBotUrl}
                            onClick={() => {
                                void (async () => {
                                    const res = addBotUrl && verificationToken ? { url: addBotUrl, token: verificationToken } : await initVerificationAndGetLink();
                                    if (!res?.url) return;
                                    openTelegramLink(res.url);
                                })();
                            }}
                            style={{ marginBottom: 12 }}
                        >
                            Add bot to channel
                        </Button>
                    )}

                    <Button disabled={!isVerified} onClick={() => setStep(2)}>
                        Continue
                    </Button>
                </div>
            ) : (
                <div className={styles.stepContent}>
                    <Text type="caption" color="secondary" style={{ marginBottom: 12, display: 'block' }}>
                        Detected: <b>@{detected.handle}</b>
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

                    {saveError ? (
                        <Text type="caption" color="secondary" style={{ marginTop: 12, display: 'block' }}>
                            {saveError}
                        </Text>
                    ) : null}

                    <div style={{ marginTop: 24 }}>
                        <Button disabled={!canPublish || isSaving} isLoading={isSaving} onClick={completeStep2}>
                            Save channel
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}
