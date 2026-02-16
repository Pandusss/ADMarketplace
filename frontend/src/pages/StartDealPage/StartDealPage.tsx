import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Input, Select, Text, Textarea } from '../../ui';
import { formatTON } from '../../utils/format';
import styles from './StartDealPage.module.scss';
import { apiFetch } from '../../api/client';

type Template = {
  id: string;
  title: string;
  has_content: boolean;
  waiting_for_content: boolean;
};

export function StartDealPage() {
  const { channelId } = useParams<{ channelId: string }>();
  const navigate = useNavigate();

  const [brief, setBrief] = useState('');
  const [title, setTitle] = useState('');

  const [postDurationHours, setPostDurationHours] = useState<number>(24);
  const [creativeMode, setCreativeMode] = useState<'template' | 'custom_task'>('custom_task');
  const [templateId, setTemplateId] = useState<string>('');
  const [creativeInstructions, setCreativeInstructions] = useState('');

  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [templatesError, setTemplatesError] = useState<string>('');

  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>('');
  const [dealId, setDealId] = useState<string>('');
  const [channel, setChannel] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!channelId) return;
      try {
        const r = await apiFetch(`/channels/${channelId}`, { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = await r.json();
        if (!cancelled) setChannel(data);
      } catch (e: any) {
        if (!cancelled) setError(String(e?.message || e || 'Failed to load channel'));
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [channelId]);

  useEffect(() => {
    let cancelled = false;
    async function loadTemplates() {
      try {
        const r = await apiFetch('/templates', { method: 'GET' });
        if (!r.ok) throw new Error(await r.text());
        const data = (await r.json()) as Template[];
        if (!cancelled) setTemplates(data);
      } catch (e: any) {
        if (!cancelled) {
          setTemplates([]);
          setTemplatesError(String(e?.message || e || 'Failed to load templates'));
        }
      }
    }
    loadTemplates();
    return () => {
      cancelled = true;
    };
  }, []);

  const usableTemplates = useMemo(() => (templates || []).filter((t) => t.has_content && !t.waiting_for_content), [templates]);

  useEffect(() => {
    if (submitted && dealId) {
      const t = setTimeout(() => {
        navigate(`/deals/${dealId}`, { replace: true });
      }, 700);
      return () => clearTimeout(t);
    }
  }, [submitted, dealId, navigate]);

  const view = useMemo(() => {
    if (!channel) return null;
    return {
      id: channel.id,
      name: channel.name,
      handle: channel.handle,
      pricePerPostTON: channel.price_per_post_ton || 0,
    };
  }, [channel]);

  if (!view) {
    return (
      <div className={styles.page}>
        <div className={styles.content}>
          <div className={styles.header}>
            <Text type="title">Send Offer</Text>
          </div>
          <Card>
            <Text type="text" color="secondary">
              {error || 'Channel not found.'}
            </Text>
            <Button variant="secondary" onClick={() => navigate('/feed')}>
              Back to Feed
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  const canSubmit = title.trim().length >= 1 && brief.trim().length >= 10 && (
    creativeMode === 'template' ? !!templateId : !!creativeInstructions.trim()
  );

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">Send Offer</Text>
          <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
            Back
          </Button>
        </div>

        <Text type="caption" color="secondary">
          Channel: <b>{view.name}</b> (@{view.handle})
        </Text>

        {submitted && (
          <Card>
            <Text type="title2">Offer sent</Text>
            <Text type="text" color="secondary">
              Your offer was sent to the channel owner. They will review and respond soon.
            </Text>
          </Card>
        )}

        <Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <Input
              label="Campaign title"
              placeholder="Short title for your campaign"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <Textarea
              label="Campaign brief"
              placeholder="What are you promoting? Include key points, tone, links, and any restrictions."
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              hint="Keep it short and specific — basic info for the deal."
            />

            <Select label="Creative Type" value={creativeMode} onChange={(e) => setCreativeMode(e.target.value as 'template' | 'custom_task')}>
              <option value="template">Use existing template</option>
              <option value="custom_task">By Prompt</option>
            </Select>

            {creativeMode === 'template' ? (
              <Select
                label="Template"
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                required
                hint={
                  templatesError
                    ? undefined
                    : templates === null
                      ? 'Loading templates…'
                      : usableTemplates.length === 0
                        ? 'No ready templates'
                        : undefined
                }
                error={templatesError || undefined}
              >
                <option value="" disabled>
                  Select template
                </option>
                {usableTemplates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </Select>
            ) : (
              <Textarea
                label="Instructions"
                value={creativeInstructions}
                onChange={(e) => setCreativeInstructions(e.target.value)}
                placeholder="Describe what the post should be about, required links, tone of voice, etc."
              />
            )}


            {/* Post duration removed - defaults to 24h, negotiable later */}

            <Input label="Price (read-only)" value={formatTON(view.pricePerPostTON)} readOnly />
          </div>
        </Card>

        <Button
          disabled={!canSubmit || isSubmitting}
          isLoading={isSubmitting}
          onClick={async () => {
            setIsSubmitting(true);
            setError('');
            try {
              const r = await apiFetch(`/channels/${view.id}/offer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  message: '',
                  campaign_title: title.trim(),
                  campaign_brief: brief.trim(),
                  creative_mode: creativeMode,
                  template_id: creativeMode === 'template' ? templateId : undefined,
                  creative_instructions: creativeMode === 'custom_task' ? creativeInstructions : undefined,
                }),
              });
              if (!r.ok) throw new Error(await r.text());
              const offer = await r.json();
              // Redirect to channel offers page instead of deal page
              setSubmitted(true);
              setTimeout(() => {
                navigate('/deals', { replace: true });
              }, 700);
            } catch (e: any) {
              setError(String(e?.message || e || 'Failed to send offer'));
            } finally {
              setIsSubmitting(false);
            }
          }}
        >
          Send Offer
        </Button>

        {error ? (
          <Card>
            <Text type="text" color="secondary" style={{ color: 'var(--color-danger)' }}>
              {error}
            </Text>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
