import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, CardStack, Input, Select, Text, Textarea } from '../../ui';
import { apiFetch } from '../../api/client';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import styles from './CreateCampaignPage.module.scss';

type Template = {
  id: string;
  title: string;
  has_content: boolean;
  waiting_for_content: boolean;
};

export function CreateCampaignPage() {
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [brief, setBrief] = useState('');
  const [category, setCategory] = useState<ChannelCategory | ''>('');
  const [language, setLanguage] = useState<ChannelLanguage | ''>('');
  const [budgetTON, setBudgetTON] = useState<string>('');
  const [templateId, setTemplateId] = useState<string>('');
  const [creativeMode, setCreativeMode] = useState<'template' | 'custom_task'>('template');
  const [creativeInstructions, setCreativeInstructions] = useState('');

  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [templatesError, setTemplatesError] = useState<string>('');

  const [error, setError] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
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
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const usableTemplates = useMemo(() => (templates || []).filter((t) => t.has_content && !t.waiting_for_content), [templates]);

  async function handleCreate() {
    if (isSaving) return;
    setError('');

    const t = title.trim();
    if (!t) {
      setError('Title is required.');
      return;
    }
    const b = brief.trim();
    if (!b) {
      setError('Brief is required.');
      return;
    }

    const budget = budgetTON.trim() ? Number(budgetTON.trim().replace(',', '.')) : 0;
    if (Number.isNaN(budget) || budget < 0) {
      setError('Price per post must be a number.');
      return;
    }

    if (creativeMode === 'template') {
      if (!templateId.trim()) {
        setError('Template is required.');
        return;
      }
    } else {
      if (!creativeInstructions.trim()) {
        setError('By Prompt is required.');
        return;
      }
    }

    setIsSaving(true);
    try {
      const payload: Record<string, unknown> = {
        title: t,
        brief: b,
        category: category || undefined,
        language: language || undefined,
        budget_ton: budget || 0,
        creative_mode: creativeMode,
        template_id: creativeMode === 'template' ? templateId : '',
        creative_instructions: creativeMode === 'custom_task' ? creativeInstructions : undefined,
      };
      const r = await apiFetch('/campaigns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!r.ok) throw new Error(await r.text());
      localStorage.setItem('feed_mode', 'buy');
      navigate('/feed');
    } catch (e: any) {
      setError(String(e?.message || e || 'Failed to create campaign'));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={`${styles.content} noScrollbar`}>
        <div className={styles.header}>
          <Text type="title">New Buy Ad</Text>
          <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
            Back
          </Button>
        </div>

        <CardStack>
          {error && (
            <Card>
              <Text type="title2">Can’t create</Text>
              <Text type="text" color="secondary">
                {error}
              </Text>
            </Card>
          )}

          <Card>
            <div className={styles.form}>
              <Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Promo for new product" />
              <Textarea
                label="Brief"
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder="What do you want to advertise? Any constraints, desired audience, links, etc."
              />

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value as ChannelCategory | '')}>
                  <option value="">Any</option>
                  <option value="Crypto">Crypto</option>
                  <option value="Gaming">Gaming</option>
                  <option value="Business">Business</option>
                  <option value="News">News</option>
                  <option value="Lifestyle">Lifestyle</option>
                </Select>

                <Select label="Language" value={language} onChange={(e) => setLanguage(e.target.value as ChannelLanguage | '')}>
                  <option value="">Any</option>
                  <option value="EN">EN</option>
                  <option value="RU">RU</option>
                  <option value="ES">ES</option>
                  <option value="DE">DE</option>
                  <option value="UA">UA</option>
                </Select>
              </div>

              <Input
                label="Price per post (TON)"
                value={budgetTON}
                onChange={(e) => setBudgetTON(e.target.value)}
                placeholder="e.g. 10"
                inputMode="decimal"
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
                  label="Prompt"
                  value={creativeInstructions}
                  onChange={(e) => setCreativeInstructions(e.target.value)}
                  placeholder="Describe what the post should be about, required links, tone of voice, etc."
                />
              )}

              <Button isLoading={isSaving} disabled={isSaving} onClick={handleCreate}>
                Create Buy Ad
              </Button>
            </div>
          </Card>
        </CardStack>
      </div>
    </div>
  );
}
