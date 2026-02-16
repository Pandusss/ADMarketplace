import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, CardHeaderRow, CardStack, Text } from '../../ui';
import { apiFetch, tgInitData } from '../../api/client';
import { AlertModal } from '../../components/AlertModal/AlertModal';
import styles from './PostTemplatesPage.module.scss';

type Template = {
  id: string;
  title: string;
  has_content: boolean;
  waiting_for_content: boolean;
  creative_type?: string | null;
  creative_message_ids?: number[] | null;
  preview_text?: string;
  preview_has_media?: boolean;
  preview_count?: number;
};

export function PostTemplatesPage({ embedded = false }: { embedded?: boolean } = {}) {
  const navigate = useNavigate();
  const [items, setItems] = useState<Template[] | null>(null);
  const [error, setError] = useState<string>('');
  const [botUsername, setBotUsername] = useState<string>('');


  const [alertModal, setAlertModal] = useState<{ isOpen: boolean; title?: string; message: string }>({
    isOpen: false,
    message: '',
  });

  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; templateId: string | null; templateTitle: string }>({
    isOpen: false,
    templateId: null,
    templateTitle: '',
  });

  const tg = useMemo(() => (window as any).Telegram?.WebApp, []);
  function openTelegramLink(url: string) {
    if (tg?.openTelegramLink) tg.openTelegramLink(url);
    else window.open(url, '_blank');
  }

  async function load() {
    try {
      const r = await apiFetch('/templates', { method: 'GET' });
      if (!r.ok) throw new Error(await r.text());
      const data = (await r.json()) as Template[];
      setItems(data);
      setError('');
    } catch (e: any) {
      setItems([]);
      setError(String(e?.message || e || 'Failed to load templates'));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const mr = await apiFetch('/meta', { method: 'GET' });
        if (!mr.ok) return;
        const m = await mr.json();
        setBotUsername(String(m.telegram_bot_username || ''));
      } catch {
        // ignore
      }
    })();
  }, []);


  async function handleDelete() {
    if (!deleteConfirm.templateId) return;
    try {
      const r = await apiFetch(`/templates/${deleteConfirm.templateId}`, {
        method: 'DELETE',
      });
      if (!r.ok) throw new Error(await r.text());
      setDeleteConfirm({ isOpen: false, templateId: null, templateTitle: '' });
      await load();
    } catch (e: any) {
      setAlertModal({ isOpen: true, title: 'Failed to delete', message: String(e?.message || e || 'Failed to delete template') });
    }
  }

  function renderBody({ embedded }: { embedded: boolean }) {

    return (
      <div className={embedded ? styles.embedded : `${styles.content} noScrollbar`}>
        {!embedded && (
          <div className={styles.header}>
            <Text type="title">Post Templates</Text>
            <Button variant="secondary" size="small" fullWidth={false} onClick={() => navigate(-1)}>
              Back
            </Button>
          </div>
        )}

        {/* Inline creation card removed */}

        {error ? (
          <Card>
            <Text type="title2">Can’t load templates</Text>
            <Text type="text" color="secondary">
              {error}
            </Text>
          </Card>
        ) : items === null ? (
          <Card>
            <Text type="title2">Loading…</Text>
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <Text type="title2">No templates yet</Text>
            <Text type="text" color="secondary">
              Tap the "+" button to create your first template.
            </Text>
          </Card>
        ) : (
          <CardStack>
            {items.map((t) => (
              <Card key={t.id}>
                <CardHeaderRow>
                  <div>
                    <Text type="title2">{t.title}</Text>
                    <Text type="caption" color="secondary">
                      {t.waiting_for_content ? 'Waiting for your post in bot…' : t.has_content ? 'Ready' : 'Empty'}
                    </Text>
                  </div>
                </CardHeaderRow>

                {/* Inline preview (COMPROMISE: rendered from stored snapshot) */}
                {t.has_content ? (
                  <div style={{ marginTop: 10 }}>
                    {t.preview_has_media ? (
                      t.preview_count && t.preview_count > 1 ? (
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(3, 1fr)',
                            gap: 6,
                          }}
                        >
                          {Array.from({ length: Math.min(3, t.preview_count) }).map((_, idx) => (
                            <img
                              key={idx}
                              src={`/api/templates/${t.id}/preview-media?i=${idx}&initData=${encodeURIComponent(tgInitData())}`}
                              alt={`Preview ${idx + 1}`}
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).style.display = 'none';
                              }}
                              style={{
                                width: '100%',
                                height: 72,
                                objectFit: 'cover',
                                borderRadius: 10,
                                border: '1px solid var(--tg-theme-hint-color, #e0e0e0)',
                              }}
                            />
                          ))}
                        </div>
                      ) : (
                        <img
                          src={`/api/templates/${t.id}/preview-media?i=0&initData=${encodeURIComponent(tgInitData())}`}
                          alt="Preview"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).style.display = 'none';
                          }}
                          style={{
                            width: '100%',
                            maxHeight: 180,
                            objectFit: 'cover',
                            borderRadius: 12,
                            border: '1px solid var(--tg-theme-hint-color, #e0e0e0)',
                          }}
                        />
                      )
                    ) : null}
                    {t.preview_text ? (
                      <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                        <span className={styles.previewText} dangerouslySetInnerHTML={{ __html: t.preview_text }} />
                      </Text>
                    ) : null}
                    {t.preview_count && t.preview_count > 1 ? (
                      <Text type="caption" color="secondary" style={{ marginTop: 4, display: 'block' }}>
                        Album • {t.preview_count} items
                      </Text>
                    ) : null}
                    {!t.preview_text && !t.preview_has_media ? (
                      <Text type="caption" color="secondary" style={{ marginTop: 8, display: 'block' }}>
                        No inline preview yet. Send the template post to the bot again to generate it.
                      </Text>
                    ) : null}
                  </div>
                ) : null}

                <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                  <Button
                    variant="outline"
                    size="small"
                    fullWidth={false}
                    disabled={!botUsername || !t.has_content}
                    onClick={() => openTelegramLink(`https://t.me/${botUsername}?start=tplview_${t.id}`)}
                  >
                    Preview
                  </Button>
                  <Button
                    variant="outline"
                    size="small"
                    fullWidth={false}
                    onClick={() => setDeleteConfirm({ isOpen: true, templateId: t.id, templateTitle: t.title })}
                    style={{ color: 'var(--tg-theme-destructive-text-color, #ff3b30)' }}
                  >
                    Delete
                  </Button>
                </div>
              </Card>
            ))}
          </CardStack>
        )}
      </div>
    );
  }

  return (
    <>
      <AlertModal
        isOpen={alertModal.isOpen}
        title={alertModal.title}
        message={alertModal.message}
        onClose={() => setAlertModal({ isOpen: false, message: '' })}
      />

      <AlertModal
        isOpen={deleteConfirm.isOpen}
        title="Delete template?"
        message={`Are you sure you want to delete "${deleteConfirm.templateTitle}"? This action cannot be undone.`}
        onClose={() => setDeleteConfirm({ isOpen: false, templateId: null, templateTitle: '' })}
        buttonText="Delete"
        onButtonClick={handleDelete}
        secondaryButtonText="Cancel"
        onSecondaryButtonClick={() => setDeleteConfirm({ isOpen: false, templateId: null, templateTitle: '' })}
      />

      {embedded ? renderBody({ embedded: true }) : <div className={styles.page}>{renderBody({ embedded: false })}</div>}
    </>
  );
}

