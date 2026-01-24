import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MockApp, MockTFolder, normalizePath as mockNormalizePath } from './mocks/obsidian';
import { DEFAULT_SETTINGS, AioSettings } from '../src/types';

// We need to mock the obsidian module before importing VaultService
vi.mock('obsidian', () => ({
  App: vi.fn(),
  TFolder: vi.fn(),
  normalizePath: (path: string) => path.replace(/\\/g, '/').replace(/\/+/g, '/').replace(/^\/|\/$/g, ''),
}));

// Import VaultService after mocking
import { VaultService } from '../src/services/VaultService';

describe('VaultService', () => {
  let app: MockApp;
  let settings: AioSettings;
  let vaultService: VaultService;

  beforeEach(() => {
    app = new MockApp();
    settings = { ...DEFAULT_SETTINGS };
    vaultService = new VaultService(app as any, settings);
  });

  describe('getAioPath', () => {
    it('returns configured AIO folder path', () => {
      expect(vaultService.getAioPath()).toBe('AIO');
    });

    it('respects custom settings', () => {
      const customSettings = { ...DEFAULT_SETTINGS, aioFolderPath: 'MyTasks' };
      const customService = new VaultService(app as any, customSettings);
      expect(customService.getAioPath()).toBe('MyTasks');
    });
  });

  describe('getTasksPath', () => {
    it('returns Tasks path under AIO folder', () => {
      expect(vaultService.getTasksPath()).toBe('AIO/Tasks');
    });
  });

  describe('getStatusPath', () => {
    it('returns correct path for inbox', () => {
      expect(vaultService.getStatusPath('inbox')).toBe('AIO/Tasks/Inbox');
    });

    it('returns correct path for next', () => {
      expect(vaultService.getStatusPath('next')).toBe('AIO/Tasks/Next');
    });

    it('returns correct path for waiting', () => {
      expect(vaultService.getStatusPath('waiting')).toBe('AIO/Tasks/Waiting');
    });

    it('returns correct path for scheduled', () => {
      expect(vaultService.getStatusPath('scheduled')).toBe('AIO/Tasks/Scheduled');
    });

    it('returns correct path for someday', () => {
      expect(vaultService.getStatusPath('someday')).toBe('AIO/Tasks/Someday');
    });

    it('returns correct path for completed', () => {
      expect(vaultService.getStatusPath('completed')).toBe('AIO/Tasks/Completed');
    });
  });

  describe('getCompletedPath', () => {
    it('returns year/month path structure', () => {
      expect(vaultService.getCompletedPath(2024, 1)).toBe('AIO/Tasks/Completed/2024/01');
      expect(vaultService.getCompletedPath(2024, 12)).toBe('AIO/Tasks/Completed/2024/12');
    });

    it('pads single-digit months with zero', () => {
      expect(vaultService.getCompletedPath(2024, 6)).toBe('AIO/Tasks/Completed/2024/06');
    });
  });

  describe('getProjectsPath', () => {
    it('returns Projects path under AIO folder', () => {
      expect(vaultService.getProjectsPath()).toBe('AIO/Projects');
    });
  });

  describe('getPeoplePath', () => {
    it('returns People path under AIO folder', () => {
      expect(vaultService.getPeoplePath()).toBe('AIO/People');
    });
  });

  describe('getDashboardPath', () => {
    it('returns Dashboard path under AIO folder', () => {
      expect(vaultService.getDashboardPath()).toBe('AIO/Dashboard');
    });
  });

  describe('getArchivePath', () => {
    it('returns Archive path under AIO folder', () => {
      expect(vaultService.getArchivePath()).toBe('AIO/Archive');
    });
  });

  describe('ensureFolderExists', () => {
    it('creates folder if it does not exist', async () => {
      await vaultService.ensureFolderExists('AIO/Tasks/Inbox');
      expect(app.vault.hasFolder('AIO/Tasks/Inbox')).toBe(true);
    });

    it('creates parent folders recursively', async () => {
      await vaultService.ensureFolderExists('AIO/Tasks/Completed/2024/06');
      expect(app.vault.hasFolder('AIO')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Completed')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Completed/2024')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Completed/2024/06')).toBe(true);
    });

    it('does nothing if folder already exists', async () => {
      await vaultService.ensureFolderExists('AIO/Tasks');
      // Should not throw
      await vaultService.ensureFolderExists('AIO/Tasks');
      expect(app.vault.hasFolder('AIO/Tasks')).toBe(true);
    });
  });

  describe('ensureAioStructure', () => {
    it('creates all required folders', async () => {
      await vaultService.ensureAioStructure();

      // Base folders
      expect(app.vault.hasFolder('AIO')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks')).toBe(true);
      expect(app.vault.hasFolder('AIO/Projects')).toBe(true);
      expect(app.vault.hasFolder('AIO/People')).toBe(true);
      expect(app.vault.hasFolder('AIO/Dashboard')).toBe(true);
      expect(app.vault.hasFolder('AIO/Archive')).toBe(true);

      // Status folders
      expect(app.vault.hasFolder('AIO/Tasks/Inbox')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Next')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Waiting')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Scheduled')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Someday')).toBe(true);
      expect(app.vault.hasFolder('AIO/Tasks/Completed')).toBe(true);
    });
  });

  describe('generateTaskFilename', () => {
    it('generates filename with date prefix and slugified title', () => {
      const date = new Date('2024-06-15T12:00:00');
      const filename = vaultService.generateTaskFilename('My Task Title', date);
      expect(filename).toBe('2024-06-15-my-task-title.md');
    });

    it('slugifies special characters', () => {
      const date = new Date('2024-06-15T12:00:00');
      const filename = vaultService.generateTaskFilename("Review John's PR #123!", date);
      expect(filename).toBe('2024-06-15-review-john-s-pr-123.md');
    });

    it('truncates long titles', () => {
      const date = new Date('2024-06-15T12:00:00');
      const longTitle = 'This is a very long task title that should be truncated to avoid filesystem issues with overly long filenames';
      const filename = vaultService.generateTaskFilename(longTitle, date);
      // Date prefix is 11 chars (2024-06-15-), .md is 3 chars, slug max is 50
      expect(filename.length).toBeLessThanOrEqual(11 + 50 + 3);
    });

    it('handles unicode characters', () => {
      const date = new Date('2024-06-15T12:00:00');
      const filename = vaultService.generateTaskFilename('Review cafe menu', date);
      expect(filename).toBe('2024-06-15-review-cafe-menu.md');
    });

    it('uses current date if none provided', () => {
      const filename = vaultService.generateTaskFilename('Test Task');
      expect(filename).toMatch(/^\d{4}-\d{2}-\d{2}-test-task\.md$/);
    });
  });

  describe('with custom AIO path', () => {
    beforeEach(() => {
      const customSettings = { ...DEFAULT_SETTINGS, aioFolderPath: 'Work/Tasks' };
      vaultService = new VaultService(app as any, customSettings);
    });

    it('uses custom path for all folders', () => {
      expect(vaultService.getAioPath()).toBe('Work/Tasks');
      expect(vaultService.getTasksPath()).toBe('Work/Tasks/Tasks');
      expect(vaultService.getProjectsPath()).toBe('Work/Tasks/Projects');
      expect(vaultService.getStatusPath('inbox')).toBe('Work/Tasks/Tasks/Inbox');
    });
  });
});
