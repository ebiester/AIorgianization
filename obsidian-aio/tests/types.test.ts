import { describe, it, expect } from 'vitest';
import {
  ID_CHARS,
  STATUS_FOLDERS,
  DEFAULT_SETTINGS,
  TaskStatus,
  AioSettings,
} from '../src/types';

describe('ID_CHARS', () => {
  it('has 32 characters', () => {
    expect(ID_CHARS.length).toBe(32);
  });

  it('excludes ambiguous characters', () => {
    expect(ID_CHARS).not.toContain('0');
    expect(ID_CHARS).not.toContain('1');
    expect(ID_CHARS).not.toContain('I');
    expect(ID_CHARS).not.toContain('O');
  });

  it('contains expected characters', () => {
    // Should contain 2-9 (8 digits)
    expect(ID_CHARS).toContain('2');
    expect(ID_CHARS).toContain('3');
    expect(ID_CHARS).toContain('9');

    // Should contain A-Z except I and O (24 letters)
    expect(ID_CHARS).toContain('A');
    expect(ID_CHARS).toContain('B');
    expect(ID_CHARS).toContain('Z');
    expect(ID_CHARS).toContain('H');
    expect(ID_CHARS).toContain('J');
  });

  it('is all uppercase', () => {
    expect(ID_CHARS).toBe(ID_CHARS.toUpperCase());
  });
});

describe('STATUS_FOLDERS', () => {
  const expectedStatuses: TaskStatus[] = ['inbox', 'next', 'waiting', 'scheduled', 'someday', 'completed'];

  it('maps all statuses to folders', () => {
    for (const status of expectedStatuses) {
      expect(STATUS_FOLDERS[status]).toBeDefined();
      expect(typeof STATUS_FOLDERS[status]).toBe('string');
    }
  });

  it('has correct folder names', () => {
    expect(STATUS_FOLDERS.inbox).toBe('Inbox');
    expect(STATUS_FOLDERS.next).toBe('Next');
    expect(STATUS_FOLDERS.waiting).toBe('Waiting');
    expect(STATUS_FOLDERS.scheduled).toBe('Scheduled');
    expect(STATUS_FOLDERS.someday).toBe('Someday');
    expect(STATUS_FOLDERS.completed).toBe('Completed');
  });

  it('uses PascalCase for folder names', () => {
    for (const folder of Object.values(STATUS_FOLDERS)) {
      expect(folder[0]).toBe(folder[0].toUpperCase());
    }
  });
});

describe('DEFAULT_SETTINGS', () => {
  it('has correct default AIO folder path', () => {
    expect(DEFAULT_SETTINGS.aioFolderPath).toBe('AIO');
  });

  it('has inbox as default status', () => {
    expect(DEFAULT_SETTINGS.defaultStatus).toBe('inbox');
  });

  it('has ISO date format as default', () => {
    expect(DEFAULT_SETTINGS.dateFormat).toBe('YYYY-MM-DD');
  });

  it('has all required settings', () => {
    const settings: AioSettings = DEFAULT_SETTINGS;
    expect(settings.aioFolderPath).toBeDefined();
    expect(settings.defaultStatus).toBeDefined();
    expect(settings.dateFormat).toBeDefined();
  });
});
