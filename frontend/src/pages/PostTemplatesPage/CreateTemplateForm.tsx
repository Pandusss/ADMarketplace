import { useState } from 'react';
import { Button, Input, Text } from '../../ui';
import { apiFetch } from '../../api/client';

interface CreateTemplateFormProps {
    onSuccess: () => void;
    onCancel?: () => void;
}

export function CreateTemplateForm({ onSuccess, onCancel }: CreateTemplateFormProps) {
    const [newTitle, setNewTitle] = useState('');
    const [isCreatingState, setIsCreatingState] = useState(false);
    const [error, setError] = useState('');
    const [botUsername, setBotUsername] = useState<string>('');

    // Fetch bot username on mount if needed, or assume it's passed/cached
    // reusing simple inline logic for now

    const tg = (window as any).Telegram?.WebApp;
    function openTelegramLink(url: string) {
        if (tg?.openTelegramLink) tg.openTelegramLink(url);
        else window.open(url, '_blank');
    }

    async function createAndSend() {
        setError('');
        const title = newTitle.trim();
        if (!title) {
            setError('Please enter a template name.');
            return;
        }

        setIsCreatingState(true);
        try {
            // Fetch user meta if not yet available (lazy load)
            let currentBot = botUsername;
            if (!currentBot) {
                const mr = await apiFetch('/meta', { method: 'GET' });
                if (mr.ok) {
                    const m = await mr.json();
                    currentBot = String(m.telegram_bot_username || '');
                    setBotUsername(currentBot);
                }
            }

            const r = await apiFetch('/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title }),
            });
            if (!r.ok) throw new Error(await r.text());
            const tpl = (await r.json());

            onSuccess();

            // Jump to bot
            if (currentBot) {
                openTelegramLink(`https://t.me/${currentBot}?start=tpl_${tpl.id}`);
            }
        } catch (e: any) {
            setError(String(e?.message || e || 'Failed to create template'));
        } finally {
            setIsCreatingState(false);
        }
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
            <Text type="text" color="secondary" style={{ marginBottom: 16, display: 'block' }}>
                Create a template by naming it, then send the post to the bot. Telegram is the editor; we store only message links.
            </Text>
            <Input label="Template name" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="e.g. Promo post #1" />

            {error && (
                <Text type="caption" color="danger" style={{ marginTop: 8, display: 'block' }}>
                    {error}
                </Text>
            )}

            <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
                {onCancel && (
                    <Button variant="secondary" onClick={onCancel}>Cancel</Button>
                )}
                <Button isLoading={isCreatingState} disabled={isCreatingState} onClick={createAndSend}>
                    Send post to bot
                </Button>
            </div>
        </div>
    );
}
