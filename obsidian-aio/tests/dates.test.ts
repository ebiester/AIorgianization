import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  parseDate,
  formatRelativeDate,
  isOverdue,
  isDueToday,
  isDueThisWeek,
  formatIsoDate,
  InvalidDateError,
} from '../src/utils/dates';

describe('parseDate', () => {
  // Use a fixed date for deterministic tests: Saturday, June 15, 2024
  const mockDate = new Date('2024-06-15T12:00:00');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('ISO format', () => {
    it('parses YYYY-MM-DD format', () => {
      const result = parseDate('2024-01-15');
      expect(formatIsoDate(result)).toBe('2024-01-15');
    });

    it('throws for invalid ISO date', () => {
      expect(() => parseDate('2024-13-45')).toThrow(InvalidDateError);
    });
  });

  describe('relative dates', () => {
    it('parses "today"', () => {
      const result = parseDate('today');
      expect(formatIsoDate(result)).toBe('2024-06-15');
    });

    it('parses "Today" (case insensitive)', () => {
      const result = parseDate('Today');
      expect(formatIsoDate(result)).toBe('2024-06-15');
    });

    it('parses "tomorrow"', () => {
      const result = parseDate('tomorrow');
      expect(formatIsoDate(result)).toBe('2024-06-16');
    });

    it('parses "yesterday"', () => {
      const result = parseDate('yesterday');
      expect(formatIsoDate(result)).toBe('2024-06-14');
    });

    it('parses "next week"', () => {
      const result = parseDate('next week');
      expect(formatIsoDate(result)).toBe('2024-06-22');
    });
  });

  describe('in X days/weeks', () => {
    it('parses "in 1 day"', () => {
      const result = parseDate('in 1 day');
      expect(formatIsoDate(result)).toBe('2024-06-16');
    });

    it('parses "in 3 days"', () => {
      const result = parseDate('in 3 days');
      expect(formatIsoDate(result)).toBe('2024-06-18');
    });

    it('parses "in 2 weeks"', () => {
      const result = parseDate('in 2 weeks');
      expect(formatIsoDate(result)).toBe('2024-06-29');
    });

    it('parses "in 1 week"', () => {
      const result = parseDate('in 1 week');
      expect(formatIsoDate(result)).toBe('2024-06-22');
    });
  });

  describe('day names', () => {
    // June 15, 2024 is a Saturday
    it('parses "monday" as next Monday', () => {
      const result = parseDate('monday');
      expect(formatIsoDate(result)).toBe('2024-06-17'); // Monday
      expect(result.getDay()).toBe(1);
    });

    it('parses "friday"', () => {
      const result = parseDate('friday');
      expect(formatIsoDate(result)).toBe('2024-06-21'); // Friday
      expect(result.getDay()).toBe(5);
    });

    it('parses "next monday"', () => {
      const result = parseDate('next monday');
      expect(formatIsoDate(result)).toBe('2024-06-24'); // Next Monday (skips the immediate one)
    });

    it('parses "next friday"', () => {
      const result = parseDate('next friday');
      expect(formatIsoDate(result)).toBe('2024-06-28');
    });
  });

  describe('end of period', () => {
    it('parses "end of week" / "eow" as Friday', () => {
      const result = parseDate('eow');
      expect(result.getDay()).toBe(5); // Friday
    });

    it('parses "end of month" / "eom"', () => {
      const result = parseDate('eom');
      expect(formatIsoDate(result)).toBe('2024-06-30');
    });

    it('parses "end of year" / "eoy"', () => {
      const result = parseDate('eoy');
      expect(formatIsoDate(result)).toBe('2024-12-31');
    });
  });

  describe('error cases', () => {
    it('throws InvalidDateError for empty string', () => {
      expect(() => parseDate('')).toThrow(InvalidDateError);
    });

    it('throws InvalidDateError for whitespace only', () => {
      expect(() => parseDate('   ')).toThrow(InvalidDateError);
    });

    it('throws InvalidDateError for unparseable strings', () => {
      expect(() => parseDate('not a date')).toThrow(InvalidDateError);
      expect(() => parseDate('gibberish xyz')).toThrow(InvalidDateError);
    });
  });
});

describe('formatRelativeDate', () => {
  const mockDate = new Date(2024, 5, 15, 12, 0, 0);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('formats today', () => {
    // Use Date constructor with components to ensure local time
    expect(formatRelativeDate(new Date(2024, 5, 15))).toBe('today');
  });

  it('formats tomorrow', () => {
    expect(formatRelativeDate(new Date(2024, 5, 16))).toBe('tomorrow');
  });

  it('formats yesterday', () => {
    expect(formatRelativeDate(new Date(2024, 5, 14))).toBe('yesterday');
  });

  it('formats days ago', () => {
    expect(formatRelativeDate(new Date(2024, 5, 10))).toContain('days ago');
  });

  it('formats day name for dates within 7 days', () => {
    // June 17, 2024 is a Monday
    const result = formatRelativeDate(new Date(2024, 5, 17));
    expect(result).toBe('Monday');
  });

  it('formats "next [day]" for dates 7-14 days out', () => {
    // June 22, 2024 is a Saturday (7 days from June 15)
    const result = formatRelativeDate(new Date(2024, 5, 22));
    expect(result).toContain('Saturday');
  });

  it('formats month/day for dates beyond 14 days', () => {
    const result = formatRelativeDate(new Date(2024, 6, 15));
    expect(result).toMatch(/Jul 15|July 15/);
  });
});

describe('isOverdue', () => {
  const mockDate = new Date(2024, 5, 15, 12, 0, 0);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns true for past dates', () => {
    expect(isOverdue(new Date(2024, 5, 14))).toBe(true);
    expect(isOverdue(new Date(2024, 5, 1))).toBe(true);
  });

  it('returns false for today', () => {
    expect(isOverdue(new Date(2024, 5, 15))).toBe(false);
  });

  it('returns false for future dates', () => {
    expect(isOverdue(new Date(2024, 5, 16))).toBe(false);
    expect(isOverdue(new Date(2024, 11, 31))).toBe(false);
  });
});

describe('isDueToday', () => {
  const mockDate = new Date(2024, 5, 15, 12, 0, 0);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns true for today', () => {
    expect(isDueToday(new Date(2024, 5, 15))).toBe(true);
    expect(isDueToday(new Date(2024, 5, 15, 23, 59, 59))).toBe(true);
    expect(isDueToday(new Date(2024, 5, 15, 0, 0, 0))).toBe(true);
  });

  it('returns false for other dates', () => {
    expect(isDueToday(new Date(2024, 5, 14))).toBe(false);
    expect(isDueToday(new Date(2024, 5, 16))).toBe(false);
  });
});

describe('isDueThisWeek', () => {
  const mockDate = new Date(2024, 5, 15, 12, 0, 0);

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(mockDate);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns true for today', () => {
    expect(isDueThisWeek(new Date(2024, 5, 15))).toBe(true);
  });

  it('returns true for dates within 7 days', () => {
    expect(isDueThisWeek(new Date(2024, 5, 18))).toBe(true);
    expect(isDueThisWeek(new Date(2024, 5, 22))).toBe(true);
  });

  it('returns false for dates beyond 7 days', () => {
    expect(isDueThisWeek(new Date(2024, 5, 23))).toBe(false);
    expect(isDueThisWeek(new Date(2024, 6, 1))).toBe(false);
  });

  it('returns false for past dates', () => {
    expect(isDueThisWeek(new Date(2024, 5, 14))).toBe(false);
  });
});

describe('formatIsoDate', () => {
  it('formats date as YYYY-MM-DD', () => {
    expect(formatIsoDate(new Date(2024, 5, 15, 12, 30, 45))).toBe('2024-06-15');
  });

  it('handles dates at midnight', () => {
    expect(formatIsoDate(new Date(2024, 0, 1, 0, 0, 0))).toBe('2024-01-01');
  });

  it('handles dates just before midnight', () => {
    expect(formatIsoDate(new Date(2024, 11, 31, 23, 59, 59))).toBe('2024-12-31');
  });
});
