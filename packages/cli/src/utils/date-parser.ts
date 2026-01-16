import * as chrono from 'chrono-node';

export function parseDate(input: string): Date | null {
  const result = chrono.parseDate(input);
  return result;
}

export function formatDate(date: Date | null | undefined): string {
  if (!date) return '-';

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  const dayAfterTomorrow = new Date(today);
  dayAfterTomorrow.setDate(dayAfterTomorrow.getDate() + 2);

  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (dateOnly.getTime() === today.getTime()) {
    return 'today';
  }
  if (dateOnly.getTime() === tomorrow.getTime()) {
    return 'tomorrow';
  }

  // Check if overdue
  if (dateOnly < today) {
    const daysAgo = Math.floor((today.getTime() - dateOnly.getTime()) / (1000 * 60 * 60 * 24));
    return `${daysAgo}d overdue`;
  }

  // Within a week
  const daysUntil = Math.floor((dateOnly.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (daysUntil <= 7) {
    const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
    return dayName;
  }

  // Default format
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function formatDateTime(date: Date | null | undefined): string {
  if (!date) return '-';
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}
