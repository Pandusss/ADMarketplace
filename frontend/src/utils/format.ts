export function formatCompactNumber(n: number) {
  return new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

export function formatTON(amount: number | undefined | null) {
  if (amount == null || isNaN(amount)) {
    return '0.00 TON';
  }
  return `${amount.toFixed(2)} TON`;
}

export function formatDate(dateString: string | undefined | null) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

