import { DealStatus } from './types';

// Visual timeline order (FIXED status names).
export const DEAL_STATUS_ORDER: DealStatus[] = [
  'draft',
  'negotiation',
  'pending_payment',
  'funds_held',
  'creative_draft',
  'creative_review',
  'approved',
  'scheduling',
  'awaiting_confirmation',
  'scheduled',
  'posted',
  'verified',
  'released',
  'cancelled',
  'refunded',
];

export function getDealStatusIndex(status: DealStatus) {
  const idx = DEAL_STATUS_ORDER.indexOf(status);
  return idx === -1 ? 0 : idx;
}

export function prettyDealStatus(s: DealStatus | string) {
  if (!s) return '';
  // Simple MVP label mapping; backend can provide i18n later.
  return s
    .split('_')
    .map((p: string) => (p[0] ? p[0].toUpperCase() + p.slice(1) : ''))
    .filter(Boolean)
    .join(' ');
}

