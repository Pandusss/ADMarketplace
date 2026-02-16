export function apiUrl(path: string): string {
  const base = (import.meta as any).env?.VITE_API_BASE_URL as string | undefined;
  if (base) return `${base}/api${path}`;
  return `/api${path}`;
}

export function tgInitData(): string {
  const w = window as any;
  return String(w?.Telegram?.WebApp?.initData || '');
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers || {});
  const initData = tgInitData();
  if (initData) headers.set('X-Tg-Init-Data', initData);
  return fetch(apiUrl(path), { ...init, headers });
}

export async function confirmDeal(dealId: string): Promise<any> {
  const res = await apiFetch(`/deals/${dealId}/confirm-deal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to confirm deal');
  }
  return res.json();
}
