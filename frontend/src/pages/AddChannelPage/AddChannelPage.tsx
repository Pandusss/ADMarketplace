import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge, Button, Card, Input, Select, Text, Textarea } from '../../ui';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import styles from './AddChannelPage.module.scss';
import { apiFetch } from '../../api/client';

function apiBaseUrl(): string {
  const v = (import.meta as any).env?.VITE_API_BASE_URL as string | undefined;
  // If VITE_API_BASE_URL is set, we call backend directly.
  // If it's NOT set, we use Vite dev proxy via `/api` to avoid HTTPS->HTTP mixed content.
  return (v?.trim() || '').replace(/\/$/, '');
}

function apiUrl(path: string): string {
  const base = apiBaseUrl();
  // In prod (single domain), `base` can be empty -> relative /api.
  // If base is provided, we still call `${base}/api/...` to match backend prefix.
  if (base) return `${base}/api${path}`;
  return `/api${path}`;
}

export function AddChannelPage() {
  const navigate = useNavigate();

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

  // Step 2 fields (STRICT)
  const [category, setCategory] = useState<ChannelCategory>('Crypto');
  const [language, setLanguage] = useState<ChannelLanguage>('EN');
  const [pricePerPostTON, setPricePerPostTON] = useState('150');
  const [description, setDescription] = useState('');
  const [startTime, setStartTime] = useState('10:00');
  const [endTime, setEndTime] = useState('20:00');
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function sanitizeTonAmountInput(raw: string): string {
    // Allow digits + one decimal separator (either "," or ".")
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
    // In Telegram Mini App, this is signed and validated by backend.
    return ((window as any).Telegram?.WebApp?.initData as string | undefined) || '';
  }

  function tgDebug() {
    const tg = (window as any).Telegram?.WebApp;
    const initData = (tg?.initData as string | undefined) || '';
    const unsafe = tg?.initDataUnsafe;
    const user = unsafe?.user;
    return {
      hasTelegram: Boolean((window as any).Telegram),
      hasWebApp: Boolean(tg),
      platform: tg?.platform,
      version: tg?.version,
      initDataLen: initData.length,
      hasUnsafeUser: Boolean(user?.id),
      unsafeUserId: user?.id,
      unsafeUsername: user?.username,
    };
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
        // This flow relies on Telegram WebApp initData signature (server-side validated).
        // In a normal browser tab, initData is empty -> backend must reject it.
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
        // FastAPI returns JSON: {"detail":"..."}; show raw body for now (high signal for debugging).
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
      const base = apiBaseUrl();
      // Common dev issue: frontend is served via HTTPS (e.g. Cloudflare Tunnel / Telegram),
      // but API base URL is HTTP (localhost). Browsers block HTTPS -> HTTP fetch (Mixed Content).
      // If `base` is empty we use Vite proxy (`/api`) and should not hit mixed-content issues.
      if (window.location.protocol === 'https:' && base.startsWith('http://')) {
        setAddBotError(
          'Failed to load bot link: your app is opened via HTTPS, but API is HTTP (Mixed Content blocked). ' +
          'Expose backend via HTTPS (Cloudflare Tunnel) and set VITE_API_BASE_URL to that HTTPS URL.'
        );
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setAddBotError(msg || 'Failed to load bot link. Check that backend is running and API URL/proxy is correct.');
      }
      return null;
    } finally {
      setIsLoadingAddBotUrl(false);
    }
  }

  useEffect(() => {
    if (step !== 1) return;
    // Do not auto-init verification; user action should trigger token creation.
  }, [step]);

  const detected = useMemo(() => {
    // After admin verification, backend provides channel identity via polling.
    return {
      name: detectedTitle || 'Detected Channel',
      handle: detectedHandle || '',
    };
  }, [detectedHandle, detectedTitle]);

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
          channel_id?: string | null;
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
        // keep polling; backend may still be reloading
      }
    }, 2000);

    pollIntervalRef.current = interval;
    return () => {
      cancelled = true;
      if (pollIntervalRef.current != null) {
        window.clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      // Don't flip isPolling on every cleanup/re-render — only when token/step changes.
      setIsPolling(false);
    };
  }, [isVerified, step, verificationToken]);

  const canPublish = parseTonAmount(pricePerPostTON) > 0 && description.trim().length >= 10;

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
          description,
          postingWindowStart: startTime,
          postingWindowEnd: endTime,
          postingSlotMinutes: 30, // Default for now
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      navigate('/my-channels', { replace: true });
    } catch (e: any) {
      setSaveError(String(e?.message || e || 'Failed to save channel'));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">Add Channel</Text>
          <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
            Back
          </Button>
        </div>

        <div className={styles.steps} aria-label="Add channel steps">
          <div className={`${styles.stepPill} ${step === 1 ? styles.active : ''}`}>1) Verification</div>
          <div className={`${styles.stepPill} ${step === 2 ? styles.active : ''}`}>2) Setup</div>
        </div>

        {step === 1 ? (
          <Card>
            <Text type="title2">Step 1: Admin verification</Text>
            <Text type="text" color="secondary">
              Add our bot as an admin in your Telegram channel, then come back here.
            </Text>

            {verificationToken && !isVerified && !addBotError ? (
              <Text type="caption" color="secondary">
                Waiting for confirmation from Telegram… (this can take a few seconds)
              </Text>
            ) : null}

            {isVerified ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
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
              <Text type="caption" color="secondary">
                {addBotError}
              </Text>
            ) : !isVerified ? (
              <Text type="caption" color="secondary">
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
              >
                Add bot to channel
              </Button>
            )}

            {/* Debug panel (only when initData is missing). Helps diagnose Telegram WebApp launch issues. */}
            {addBotError?.includes('initData is missing') ? (
              <div style={{ marginTop: 8 }}>
                <Text type="caption" color="secondary">
                  Debug: {JSON.stringify(tgDebug())}
                </Text>
              </div>
            ) : null}

            <Button disabled={!isVerified} onClick={() => setStep(2)}>
              Continue
            </Button>
          </Card>
        ) : (
          <>
            <Card>
              <Text type="title2">Step 2: Channel setup</Text>
              <Text type="caption" color="secondary">
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
                  hint="Minimum ~10 characters for MVP validation."
                />
              </div>
            </Card>

            {saveError ? (
              <Text type="caption" color="secondary">
                {saveError}
              </Text>
            ) : null}

            <Button disabled={!canPublish || isSaving} isLoading={isSaving} onClick={completeStep2}>
              Save channel
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

