import * as chrono from 'chrono-node';

export class InvalidDateError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InvalidDateError';
  }
}

/**
 * Parse a natural language date string.
 * Mirrors Python's aio/utils/dates.py parse_date()
 *
 * Supports formats like:
 * - "tomorrow", "today", "yesterday"
 * - "next monday", "friday"
 * - "in 3 days", "in a week", "in 2 months"
 * - "end of week", "end of month", "end of year"
 * - ISO format: "2024-01-15"
 * - Absolute: "January 15", "Jan 15, 2024"
 */
export function parseDate(dateStr: string): Date {
  if (!dateStr?.trim()) {
    throw new InvalidDateError('Date string cannot be empty');
  }

  // Handle "end of week" / "eow" manually (chrono doesn't support this)
  const lower = dateStr.toLowerCase().trim();
  if (lower === 'end of week' || lower === 'eow') {
    return getEndOfWeek();
  }
  if (lower === 'end of month' || lower === 'eom') {
    return getEndOfMonth();
  }
  if (lower === 'end of year' || lower === 'eoy') {
    return getEndOfYear();
  }

  // Use chrono-node with forwardDate to match Python's PREFER_DATES_FROM: "future"
  const result = chrono.parseDate(dateStr, new Date(), { forwardDate: true });

  if (!result) {
    throw new InvalidDateError(`Could not parse date: ${dateStr}`);
  }

  return result;
}

/**
 * Format a date as a relative string for display.
 * Mirrors Python's format_relative_date()
 */
export function formatRelativeDate(d: Date): string {
  const today = startOfDay(new Date());
  const target = startOfDay(d);
  const delta = Math.round(
    (target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (delta < -1) return `${Math.abs(delta)} days ago`;
  if (delta === -1) return 'yesterday';
  if (delta === 0) return 'today';
  if (delta === 1) return 'tomorrow';
  if (delta < 7) return d.toLocaleDateString('en-US', { weekday: 'long' });
  if (delta < 14)
    return 'next ' + d.toLocaleDateString('en-US', { weekday: 'long' });
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Check if a date is in the past.
 */
export function isOverdue(d: Date): boolean {
  return startOfDay(d) < startOfDay(new Date());
}

/**
 * Check if a date is today.
 */
export function isDueToday(d: Date): boolean {
  return startOfDay(d).getTime() === startOfDay(new Date()).getTime();
}

/**
 * Check if a date is within the next 7 days (including today).
 */
export function isDueThisWeek(d: Date): boolean {
  const today = startOfDay(new Date());
  const target = startOfDay(d);
  const weekFromNow = new Date(today);
  weekFromNow.setDate(weekFromNow.getDate() + 7);
  return target >= today && target <= weekFromNow;
}

/**
 * Format a date as ISO 8601 (YYYY-MM-DD).
 */
export function formatIsoDate(d: Date): string {
  return d.toISOString().split('T')[0];
}

// Helper: Get start of day (midnight)
function startOfDay(d: Date): Date {
  const result = new Date(d);
  result.setHours(0, 0, 0, 0);
  return result;
}

// Helper: Get next Friday (or Friday next week if today is Friday-Sunday)
function getEndOfWeek(): Date {
  const today = new Date();
  const dayOfWeek = today.getDay();
  let daysUntilFriday = 5 - dayOfWeek;
  if (daysUntilFriday <= 0) {
    daysUntilFriday += 7;
  }
  const friday = new Date(today);
  friday.setDate(today.getDate() + daysUntilFriday);
  return friday;
}

// Helper: Get last day of current month
function getEndOfMonth(): Date {
  const today = new Date();
  return new Date(today.getFullYear(), today.getMonth() + 1, 0);
}

// Helper: Get December 31 of current year
function getEndOfYear(): Date {
  const today = new Date();
  return new Date(today.getFullYear(), 11, 31);
}
