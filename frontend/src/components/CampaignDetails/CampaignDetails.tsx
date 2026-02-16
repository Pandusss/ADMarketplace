import { Badge, Card, CardStack, Text } from '../../ui';
import { RatingBadge } from '../../ui/RatingBadge/RatingBadge';
import { formatTON } from '../../utils/format';
import { Bitcoin, Gamepad2, Briefcase, Newspaper, Heart, LayoutGrid, Eye, Calendar, FileText, Info } from 'lucide-react';
import styles from './CampaignDetails.module.scss';
import { useMemo, useState, useEffect } from 'react';
import { apiFetch, tgInitData } from '../../api/client';

export type Campaign = {
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
    template_id: string;
    status: string;
    created_at?: string | null;
    rating_avg?: number;
    rating_count?: number;
    owner_rating_avg?: number;
    owner_rating_count?: number;
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

interface CampaignDetailsProps {
    campaign: Campaign;
}

function DetailRow({ label, value, icon }: { label: string; value: React.ReactNode; icon?: React.ReactNode }) {
    return (
        <div className={styles.detailRow}>
            <div className={styles.detailLabel}>
                {icon}
                <Text type="caption" color="secondary">{label}</Text>
            </div>
            <Text type="text" weight="bold" className={styles.detailValue}>
                {value}
            </Text>
        </div>
    );
}

export function CampaignDetails({ campaign }: CampaignDetailsProps) {
    const getCategoryIcon = (cat: string) => {
        switch (cat) {
            case 'Crypto': return <Bitcoin size={18} />;
            case 'Gaming': return <Gamepad2 size={18} />;
            case 'Business': return <Briefcase size={18} />;
            case 'News': return <Newspaper size={18} />;
            case 'Lifestyle': return <Heart size={18} />;
            default: return <LayoutGrid size={18} />;
        }
    };

    const createdLabel = campaign.created_at ? new Date(campaign.created_at).toLocaleDateString() : '—';
    const isCustomTask = campaign.creative_mode === 'custom_task';

    const [template, setTemplate] = useState<Template | null>(null);
    const [templateError, setTemplateError] = useState<string>('');

    useEffect(() => {
        let cancelled = false;
        async function loadTemplate() {
            if (!campaign?.template_id || isCustomTask) {
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
        return () => { cancelled = true; };
    }, [campaign?.template_id, isCustomTask]);

    const initData = encodeURIComponent(tgInitData());
    const previewCount = useMemo(() => Math.min(3, Number(template?.preview_count || 0)), [template]);

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <div className={styles.campaignInfo}>
                    <div className={styles.avatarWrapper}>
                        <div className={styles.avatar}>
                            {getCategoryIcon(campaign.category)}
                        </div>
                    </div>
                    <div>
                        <Text type="title2" weight="bold">{campaign.title}</Text>
                        <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center', flexWrap: 'wrap' }}>
                            <Badge tone="default">{campaign.category || 'Any'}</Badge>
                            <Badge tone="default" mode="outline">{campaign.language || 'Any'}</Badge>
                            <RatingBadge
                                ratingAvg={campaign.rating_avg || 0}
                                ratingCount={campaign.rating_count || 0}
                                reviewsEndpoint={`/campaigns/${campaign.id}/reviews`}
                                label="Campaign Reviews"
                            />
                        </div>
                    </div>
                </div>
            </div>

            <CardStack>
                <Card>
                    <div className={styles.grid}>
                        <DetailRow label="Price per post" value={formatTON(campaign.budget_ton)} icon={<Bitcoin size={14} />} />
                        <DetailRow label="Desired views" value={campaign.desired_views_24h?.toLocaleString() || 'Not specified'} icon={<Eye size={14} />} />
                        <DetailRow label="Creative" value={isCustomTask ? 'By Prompt' : 'Template'} icon={<FileText size={14} />} />
                        <DetailRow label="Created" value={createdLabel} icon={<Calendar size={14} />} />
                    </div>
                </Card>

                <div className={styles.section}>
                    <div className={styles.sectionHeader}>
                        <Info size={16} />
                        <Text type="caption" color="secondary" weight="bold" uppercase>Brief</Text>
                    </div>
                    <Card>
                        <Text type="text" color="secondary" className={styles.briefText}>
                            {campaign.brief}
                        </Text>
                    </Card>
                </div>

                {isCustomTask ? (
                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <FileText size={16} />
                            <Text type="caption" color="secondary" weight="bold" uppercase>By Prompt</Text>
                        </div>
                        <Card>
                            <Text type="text" color="secondary" className={styles.briefText}>
                                {campaign.creative_instructions || 'No detailed instructions.'}
                            </Text>
                        </Card>
                    </div>
                ) : campaign.template_id && (
                    <div className={styles.section}>
                        <div className={styles.sectionHeader}>
                            <FileText size={16} />
                            <Text type="caption" color="secondary" weight="bold" uppercase>Creative Template</Text>
                        </div>
                        <Card>
                            {template ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                    {template.preview_has_media && previewCount > 0 && (
                                        <div style={{ display: 'grid', gridTemplateColumns: previewCount > 1 ? 'repeat(3, 1fr)' : '1fr', gap: 6 }}>
                                            {Array.from({ length: previewCount }).map((_, idx) => (
                                                <img
                                                    key={idx}
                                                    src={`${import.meta.env.VITE_API_BASE_URL || ''}/api/templates/${template.id}/preview-media?i=${idx}&initData=${initData}`}
                                                    alt={`Preview ${idx + 1}`}
                                                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                                                    style={{
                                                        width: '100%',
                                                        height: previewCount > 1 ? 72 : 'auto',
                                                        maxHeight: 180,
                                                        objectFit: 'cover',
                                                        borderRadius: 10,
                                                        border: '1px solid var(--tg-theme-hint-color, #e0e0e0)'
                                                    }}
                                                />
                                            ))}
                                        </div>
                                    )}
                                    {template.preview_text && (
                                        <Text type="caption" color="secondary" style={{ lineHeight: 1.4 }}>
                                            <span dangerouslySetInnerHTML={{ __html: template.preview_text }} />
                                        </Text>
                                    )}
                                </div>
                            ) : (
                                <Text type="text" color="secondary" style={{ fontSize: 13 }}>
                                    {templateError || 'Loading template preview...'}
                                </Text>
                            )}
                        </Card>
                    </div>
                )}
            </CardStack>
        </div>
    );
}
