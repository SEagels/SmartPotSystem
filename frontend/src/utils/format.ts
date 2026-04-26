import dayjs from 'dayjs';

export function formatDateTime(iso: string): string {
  return dayjs(iso).format('MM-DD HH:mm');
}

export function formatDate(iso: string): string {
  return dayjs(iso).format('YYYY-MM-DD');
}

export function formatPercent(v: number, decimals = 1): string {
  return `${v.toFixed(decimals)}%`;
}

export function formatSensorValue(v: number | undefined | null, unit: string): string {
  if (v == null) return '--';
  return `${v.toFixed(1)} ${unit}`;
}

export function nowISO(): string {
  return dayjs().toISOString();
}

export function daysAgo(n: number): string {
  return dayjs().subtract(n, 'day').startOf('day').toISOString();
}
