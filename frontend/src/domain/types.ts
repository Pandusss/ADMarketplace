export interface Campaign {
    id: string;
    owner_id: string;
    title: string;
    brief: string;
    category: string;
    language: string;
    budget_ton: number;
    desired_views_24h?: number | null;
    template_id: string;
    creative_mode: 'template' | 'custom_task';
    creative_instructions?: string;
    status: string;
    rating_avg: number;
    rating_count: number;
    created_at: string;
}

export interface Channel {
    id: string;
    name: string;
    handle: string;
    description?: string;
    subscribers_count?: number;
    avg_views?: number;
    avg_views_24h?: number;
    avg_views_7d?: number;
    premium_share?: number;
    growth_7d?: number;
    last_stats_update?: string;
    verified_stats?: boolean;
    category?: string;
    language?: string;
    price_per_post_ton?: number;
    is_verified?: boolean;
    is_published?: boolean;
    owner_id?: string;
    // New High-Fidelity Analytics
    avg_views_per_post?: number;
    median_views?: number;
    engagement_rate?: number;
    median_er?: number;
    posts_per_day?: number;
    ad_reach_estimate?: number;
    stability_score?: number;
    followers_trend_percent?: number;
    subs_today?: number;
    subs_week?: number;
    subs_month?: number;
    joins_24h?: number;
    leaves_24h?: number;
    reach_12h?: number;
    reach_24h?: number;
    reach_48h?: number;
    err_24h_percent?: number;
    posts_total?: number;
    posts_yesterday?: number;
    posts_week?: number;
    posts_month?: number;
    channel_created_at?: string;
    avg_forwards?: number;
    avg_replies?: number;
    avg_reactions?: number;
    // New Stats
    premium_subscribers_count?: number;
    region_stats?: Record<string, number>;
    // Posting settings
    posting_timezone?: string;
    posting_window_start?: string;
    posting_window_end?: string;
    posting_slot_minutes?: number;

    // UI/CamelCase Aliases (for components like ChannelCard)
    subscribersCount?: number;
    avgViews?: number;
    stabilityScore?: number;
    verifiedStats?: boolean;
    ownerId?: string;
    premiumSubscribersCount?: number;
    regionStats?: Record<string, number>;
}

export type ChannelCategory = 'Crypto' | 'Gaming' | 'Business' | 'News' | 'Lifestyle';
export type ChannelLanguage = 'EN' | 'RU' | 'ES' | 'DE' | 'UA';

export type DealStatus =
    | 'draft'
    | 'negotiation'
    | 'pending_payment'
    | 'funds_held'
    | 'creative_draft'
    | 'creative_review'
    | 'approved'
    | 'scheduling'
    | 'awaiting_confirmation'
    | 'scheduled'
    | 'posted'
    | 'verified'
    | 'released'
    | 'cancelled'
    | 'refunded';

export interface Listing {
    id: string;
    channelId: string;
    category: ChannelCategory;
    language: ChannelLanguage;
    pricePerPostTON: number;
    isPublished: boolean;
}

export interface CampaignOffer {
    id: string;
    campaign_id: string;
    channel_id: string;
    status: 'pending' | 'accepted' | 'rejected' | 'completed';
    created_at: string;
    post_link?: string;
}

export interface User {
    id: string;
    username?: string;
    first_name?: string;
    last_name?: string;
    is_admin: boolean;
    wallet_address?: string;
}

export interface Template {
    id: string;
    name: string;
    content: string;
    category: string;
    tags: string[];
}

export interface PostAnalytics {
    post_id: number;
    date: string;
    views: number;
    forwards: number;
    replies: number;
    reactions: string; // JSON string
    content_type: string;
    has_links: boolean;
}
