import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, CardHeaderRow, CardStack, Input, Select, Text } from '../../ui';
import { apiFetch, tgInitData } from '../../api/client';
import { formatTON } from '../../utils/format';
import styles from './CampaignDetailsPage.module.scss';

type Campaign = {
  id: string;
  owner_id: string;
  title: string;
  brief: string;
  category: string;
  language: string;
  budget_ton: number;
  desired_views_24h?: number | null;
  creative_mode?: string;
  creative_instructions?: string;
  post_duration_hours?: number;
  template_id: string;
  status: string;
  created_at?: string | null;
};

type Template = {
  id: string;
  title: string;
  has_content: boolean;
  waiting_for_content: boolean;
  preview_text?: string;
  preview_has_media?: boolean;
  preview_count?: number;
};

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
      <Text type="caption" color="secondary">
        {label}
      </Text>
      <Text type="text" weight="bold" style={{ textAlign: 'right' }}>
        {value}
      </Text>
    </div>
  );
}

export function CampaignDetailsPage() {
  const navigate = useNavigate();
  const { campaignId } = useParams();
  const currentUserId = useMemo(() => {
    const tgUserId = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id;
    return tgUserId ? `tg_${tgUserId}` : null;
  }, []);
  const [notice, setNotice] = useState<{ title: string; message: string } | null>(null);

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [error, setError] = useState<string>('');

  const [template, setTemplate] = useState<Template | null>(null);
  const [templateError, setTemplateError] = useState<string>('');

  const [myChannels, setMyChannels] = useState<any[] | null>(null);
  const [myChannelsError, setMyChannelsError] = useState<string>('');

  const [applyOpen, setApplyOpen] = useState(false);
  const [applyChannelId, setApplyChannelId] = useState<string>('');
  const [applyOffer, setApplyOffer] = useState<string>('');
  const [applyMessage, setApplyMessage] = useState<string>('');
  const [applyError, setApplyError] = useState<string>('');
  const [applySubmitting, setApplySubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        if (!campaignId) return;
        const r = await apiFetch(`/campaigns/${campaignId}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as Campaign;
        if (!cancelled) setCampaign(data);
      } catch (e: any) {
        if (!cancelled) setError(String(e?.message || e || 'Failed to load campaign'));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [campaignId]);

  useEffect(() => {
    let cancelled = false;
    async function loadTemplate() {
      if (!campaign?.template_id || campaign.creative_mode === 'custom_task') {
        setTemplate(null);
        return;
      }
      try {
        const r = await apiFetch(`/templates/${campaign.template_id}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const t = (await r.json()) as Template;
        if (!cancelled) setTemplate(t);
      } catch (e: any) {
        if (!cancelled) setTemplateError(String(e?.message || e || 'Template preview is not available'));
      }
    }
    loadTemplate();
    return () => {
      cancelled = true;
    };
  }, [campaign?.template_id, campaign?.creative_mode]);

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
          setMyChannelsError(String(e?.message || e || 'Failed to load your channels'));
        }
      }
    }
    loadMyChannels();
    return () => {
      cancelled = true;
    };
  }, []);

  const eligibleMyChannels = useMemo(() => {
    return myChannels || [];
  }, [myChannels]);

  async function submitApply() {
    if (!campaign) return;
    if (applySubmitting) return;
    setApplyError('');

    try {
      const profileRes = await apiFetch('/profile', { method: 'GET' });
      if (profileRes.ok) {
        const profile = await profileRes.json();
        const wallet = String(profile?.wallet_address || '').trim();
        if (!wallet) {
          setNotice({
            title: 'Wallet required',
            message: 'Please set your TON wallet address in Wallet before submitting an offer. You need it to receive payouts.',
          });
          return;
        }
      }
    } catch {
      // ignore
    }

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
      setApplyOpen(false);
      setNotice({ title: 'Offer sent', message: 'Your offer was submitted. Redirecting...' });
      setTimeout(() => {
        navigate('/deals', { replace: true });
      }, 1000);
    } catch (e: any) {
      setApplyError(String(e?.message || e || 'Failed to apply'));
    } finally {
      setApplySubmitting(false);
    }
  }

  if (error) {
    return (
      <div className={styles.page}>
        <div className={`${styles.content} noScrollbar`}>
          <Card>
            <Text type="title2">Can’t load</Text>
            <Text type="text" color="secondary">
              {error}
            </Text>
            <Button variant="secondary" onClick={() => navigate(-1)}>
              Back
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className={styles.page}>
        <div className={`${styles.content} noScrollbar`}>
          <Card>
            <Text type="title2">Loading…</Text>
          </Card>
        </div>
      </div>
    );
  }

  const initData = encodeURIComponent(tgInitData());
  const previewCount = Math.min(3, Number(template?.preview_count || 0));
  const createdLabel = campaign.created_at ? new Date(campaign.created_at).toLocaleString() : '—';
  const isCustomTask = campaign.creative_mode === 'custom_task';

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">{campaign.title || `Campaign ${campaign.id}`}</Text>
          <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
            Back
          </Button>
        </div>

        <CardStack>
          <Card>
            <CardHeaderRow>
              <div style={{ minWidth: 0 }}>
                <Text type="title2" style={{ wordBreak: 'break-word' }}>
                  {campaign.title || `Campaign ${campaign.id}`}
                </Text>
              </div>
            </CardHeaderRow>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <DetailRow value={formatTON(campaign.budget_ton || 0)} label="Price per post" />
              <DetailRow value={campaign.category || 'Any'} label="Category" />
              <DetailRow value={campaign.language || 'Any'} label="Language" />
              <DetailRow value={isCustomTask ? 'By Prompt' : 'Template'} label="Creative Mode" />
              <DetailRow value={createdLabel} label="Created" />
            </div>

            <Text type="title2" weight="bold" style={{ marginTop: 14 }}>
              Brief
            </Text>
            <Text type="text" color="secondary" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
              {campaign.brief}
            </Text>

            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <Button
                variant="outline"
                size="small"
                fullWidth={false}
                onClick={() => {
                  if (currentUserId && campaign.owner_id === currentUserId) {
                    setNotice({ title: 'Not allowed', message: "You can't make an offer to your own campaign." });
                    return;
                  }
                  setApplyOpen(true);
                }}
              >
                Offer
              </Button>
            </div>
          </Card>

          {isCustomTask ? (
            <Card>
              <Text type="title2" weight="bold" style={{ marginBottom: 10 }}>
                By Prompt
              </Text>
              <Text type="text" color="secondary" style={{ whiteSpace: 'pre-wrap' }}>
                {campaign.creative_instructions || 'No detailed instructions.'}
              </Text>
              <Text type="caption" color="secondary" style={{ marginTop: 12, display: 'block' }}>
                * In this campaign, you need to write and submit the post yourself based on the instructions above.
              </Text>
            </Card>
          ) : (
            <Card>
              <Text type="title2" weight="bold" style={{ marginBottom: 10 }}>
                Template preview
              </Text>
              {template ? (
                <>
                  {template.preview_has_media && previewCount > 0 ? (
                    template.preview_count && template.preview_count > 1 ? (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                        {Array.from({ length: previewCount }).map((_, idx) => (
                          <img
                            key={idx}
                            src={`/api/templates/${template.id}/preview-media?i=${idx}&initData=${initData}`}
                            alt={`Preview ${idx + 1}`}
                            onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                            style={{ width: '100%', height: 72, objectFit: 'cover', borderRadius: 10, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                          />
                        ))}
                      </div>
                    ) : (
                      <img
                        src={`/api/templates/${template.id}/preview-media?i=0&initData=${initData}`}
                        alt="Preview"
                        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                        style={{ width: '100%', maxHeight: 180, objectFit: 'cover', borderRadius: 12, border: '1px solid var(--tg-theme-hint-color, #e0e0e0)' }}
                      />
                    )
                  ) : null}
                  {template.preview_text ? (
                    <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                      <span dangerouslySetInnerHTML={{ __html: template.preview_text }} />
                    </Text>
                  ) : null}
                </>
              ) : (
                <Text type="text" color="secondary">
                  {templateError || 'Loading template…'}
                </Text>
              )}
            </Card>
          )}
        </CardStack>
      </div>

      {applyOpen && (
        <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Offer">
          <div className={styles.overlayHeader}>
            <Text type="title">Offer</Text>
            <Button variant="secondary" size="small" fullWidth={false} onClick={() => setApplyOpen(false)}>
              Close
            </Button>
          </div>

          <div className={styles.sheet}>
            <Card>
              {myChannelsError && (
                <Text type="caption" color="danger" style={{ marginBottom: 10, display: 'block' }}>
                  {myChannelsError}
                </Text>
              )}

              {eligibleMyChannels.length === 0 ? (
                <>
                  <Text type="text" color="secondary">
                    You need a verified channel to make an offer.
                  </Text>
                  <Button variant="secondary" onClick={() => navigate('/assets')}>
                    Go to My Assets
                  </Button>
                </>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <Select
                    label="Your channel"
                    value={applyChannelId || (eligibleMyChannels.length > 0 ? eligibleMyChannels[0].id : '')}
                    onChange={(e) => setApplyChannelId(e.target.value)}
                  >
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

                  {applyError && (
                    <Text type="caption" color="danger" style={{ display: 'block' }}>
                      {applyError}
                    </Text>
                  )}

                  <Button isLoading={applySubmitting} disabled={applySubmitting} onClick={submitApply}>
                    Submit offer
                  </Button>
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {notice && (
        <div className={styles.centerOverlay} role="dialog" aria-modal="true" aria-label="Notice">
          <div className={styles.centerCard}>
            <Card>
              <Text type="text" style={{ marginTop: 2 }}>
                {notice.message}
              </Text>
              <Button variant="secondary" onClick={() => setNotice(null)} style={{ marginTop: 14 }}>
                OK
              </Button>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
