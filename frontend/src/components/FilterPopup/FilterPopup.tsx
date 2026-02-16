import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Button, Input, Select, Text } from '../../ui';
import { ChannelCategory, ChannelLanguage } from '../../domain/types';
import styles from './FilterPopup.module.scss';

export type ChannelFilters = {
    category?: ChannelCategory;
    language?: ChannelLanguage;
    minPrice?: number;
    maxPrice?: number;
    minSubscribers?: number;
    maxSubscribers?: number;
    minViews?: number;
    maxViews?: number;
    minStability?: number;
    minEngagementRate?: number;
    minRating?: number;
    onlyMy?: boolean;
};

export type CampaignFilters = {
    category?: ChannelCategory;
    language?: ChannelLanguage;
    minBudget?: number;
    maxBudget?: number;
    minViews?: number;
    maxViews?: number;
    creativeMode?: 'template' | 'custom_task';
    minRating?: number;
    onlyMy?: boolean;
};

type FilterPopupProps = {
    isOpen: boolean;
    onClose: () => void;
    mode: 'channels' | 'campaigns';
    channelFilters?: ChannelFilters;
    campaignFilters?: CampaignFilters;
    onApply: (filters: ChannelFilters | CampaignFilters) => void;
    onReset: () => void;
};

export function FilterPopup({
    isOpen,
    onClose,
    mode,
    channelFilters = {},
    campaignFilters = {},
    onApply,
    onReset,
}: FilterPopupProps) {
    const [mounted, setMounted] = useState(false);
    const filters = mode === 'channels' ? channelFilters : campaignFilters;

    useEffect(() => {
        setMounted(true);
    }, []);

    const handleApply = () => {
        onApply(filters);
        onClose();
    };

    const handleReset = () => {
        onReset();
    };

    const updateFilter = (key: string, value: any) => {
        const updated = { ...filters, [key]: value };
        onApply(updated);
    };

    if (!mounted) return null;

    return createPortal(
        <AnimatePresence>
            {isOpen && (
                <div className={styles.wrapper}>
                    <motion.div
                        className={styles.backdrop}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                    />
                    <motion.div
                        className={styles.popup}
                        initial={{ y: '100%' }}
                        animate={{ y: 0 }}
                        exit={{ y: '100%' }}
                        transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
                    >
                        <div className={styles.handleWrapper}>
                            <div className={styles.handle} />
                        </div>

                        <div className={styles.header}>
                            <Text type="title2">Filters</Text>
                            <button className={styles.closeButton} onClick={onClose}>
                                <X size={24} />
                            </button>
                        </div>

                        <div className={styles.content}>
                            {/* Basic Filters */}
                            <div className={styles.section}>
                                <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                    Basic
                                </Text>

                                <Select
                                    label="Category"
                                    value={filters.category ?? ''}
                                    onChange={(e) => updateFilter('category', e.target.value || undefined)}
                                >
                                    <option value="">Any</option>
                                    <option value="Crypto">Crypto</option>
                                    <option value="Gaming">Gaming</option>
                                    <option value="Business">Business</option>
                                    <option value="News">News</option>
                                    <option value="Lifestyle">Lifestyle</option>
                                </Select>

                                <Select
                                    label="Language"
                                    value={filters.language ?? ''}
                                    onChange={(e) => updateFilter('language', e.target.value || undefined)}
                                >
                                    <option value="">Any</option>
                                    <option value="EN">EN</option>
                                    <option value="RU">RU</option>
                                    <option value="ES">ES</option>
                                    <option value="DE">DE</option>
                                    <option value="UA">UA</option>
                                </Select>

                                <label className={styles.checkbox}>
                                    <input
                                        type="checkbox"
                                        checked={filters.onlyMy ?? false}
                                        onChange={(e) => updateFilter('onlyMy', e.target.checked || undefined)}
                                    />
                                    <Text type="text">Show only my items</Text>
                                </label>
                            </div>

                            {/* Channel-specific filters */}
                            {mode === 'channels' && (
                                <>
                                    <div className={styles.section}>
                                        <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                            Price per Post (TON)
                                        </Text>
                                        <div className={styles.rangeInputs}>
                                            <Input
                                                label="Min"
                                                type="number"
                                                placeholder="0"
                                                value={channelFilters.minPrice ?? ''}
                                                onChange={(e) => updateFilter('minPrice', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                            <Input
                                                label="Max"
                                                type="number"
                                                placeholder="Any"
                                                value={channelFilters.maxPrice ?? ''}
                                                onChange={(e) => updateFilter('maxPrice', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.section}>
                                        <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                            Subscribers
                                        </Text>
                                        <div className={styles.rangeInputs}>
                                            <Input
                                                label="Min"
                                                type="number"
                                                placeholder="0"
                                                value={channelFilters.minSubscribers ?? ''}
                                                onChange={(e) => updateFilter('minSubscribers', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                            <Input
                                                label="Max"
                                                type="number"
                                                placeholder="Any"
                                                value={channelFilters.maxSubscribers ?? ''}
                                                onChange={(e) => updateFilter('maxSubscribers', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.section}>
                                        <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                            Average Views
                                        </Text>
                                        <div className={styles.rangeInputs}>
                                            <Input
                                                label="Min"
                                                type="number"
                                                placeholder="0"
                                                value={channelFilters.minViews ?? ''}
                                                onChange={(e) => updateFilter('minViews', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                            <Input
                                                label="Max"
                                                type="number"
                                                placeholder="Any"
                                                value={channelFilters.maxViews ?? ''}
                                                onChange={(e) => updateFilter('maxViews', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.section}>
                                        <Input
                                            label="Min Stability Score (0-100)"
                                            type="number"
                                            placeholder="0"
                                            value={channelFilters.minStability ?? ''}
                                            onChange={(e) => updateFilter('minStability', e.target.value ? Number(e.target.value) : undefined)}
                                        />
                                    </div>

                                    <div className={styles.section}>
                                        <Input
                                            label="Min Engagement Rate (%)"
                                            type="number"
                                            placeholder="0"
                                            value={channelFilters.minEngagementRate ?? ''}
                                            onChange={(e) => updateFilter('minEngagementRate', e.target.value ? Number(e.target.value) : undefined)}
                                        />
                                    </div>

                                    <div className={styles.section}>
                                        <Input
                                            label="Min Publisher Rating (0-5)"
                                            type="number"
                                            placeholder="0"
                                            step="0.1"
                                            min="0"
                                            max="5"
                                            value={channelFilters.minRating ?? ''}
                                            onChange={(e) => updateFilter('minRating', e.target.value ? Number(e.target.value) : undefined)}
                                        />
                                    </div>
                                </>
                            )}

                            {/* Campaign-specific filters */}
                            {mode === 'campaigns' && (
                                <>
                                    <div className={styles.section}>
                                        <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                            Budget (TON)
                                        </Text>
                                        <div className={styles.rangeInputs}>
                                            <Input
                                                label="Min"
                                                type="number"
                                                placeholder="0"
                                                value={campaignFilters.minBudget ?? ''}
                                                onChange={(e) => updateFilter('minBudget', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                            <Input
                                                label="Max"
                                                type="number"
                                                placeholder="Any"
                                                value={campaignFilters.maxBudget ?? ''}
                                                onChange={(e) => updateFilter('maxBudget', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.section}>
                                        <Text type="caption" color="secondary" className={styles.sectionTitle}>
                                            Desired Views (24h)
                                        </Text>
                                        <div className={styles.rangeInputs}>
                                            <Input
                                                label="Min"
                                                type="number"
                                                placeholder="0"
                                                value={campaignFilters.minViews ?? ''}
                                                onChange={(e) => updateFilter('minViews', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                            <Input
                                                label="Max"
                                                type="number"
                                                placeholder="Any"
                                                value={campaignFilters.maxViews ?? ''}
                                                onChange={(e) => updateFilter('maxViews', e.target.value ? Number(e.target.value) : undefined)}
                                            />
                                        </div>
                                    </div>

                                    <div className={styles.section}>
                                        <Select
                                            label="Creative Type"
                                            value={campaignFilters.creativeMode ?? ''}
                                            onChange={(e) => updateFilter('creativeMode', e.target.value || undefined)}
                                        >
                                            <option value="">Any</option>
                                            <option value="template">Ready-made Post</option>
                                            <option value="custom_task">By Prompt</option>
                                        </Select>
                                    </div>

                                    <div className={styles.section}>
                                        <Input
                                            label="Min Advertiser Rating (0-5)"
                                            type="number"
                                            placeholder="0"
                                            step="0.1"
                                            min="0"
                                            max="5"
                                            value={campaignFilters.minRating ?? ''}
                                            onChange={(e) => updateFilter('minRating', e.target.value ? Number(e.target.value) : undefined)}
                                        />
                                    </div>
                                </>
                            )}
                        </div>

                        <div className={styles.footer}>
                            <Button
                                variant="secondary"
                                onClick={handleReset}
                                fullWidth={false}
                                className={styles.footerBtn}
                            >
                                Reset
                            </Button>
                            <Button
                                variant="primary"
                                onClick={handleApply}
                                fullWidth={false}
                                className={styles.footerBtn}
                            >
                                Apply
                            </Button>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>,
        document.body
    );
}
