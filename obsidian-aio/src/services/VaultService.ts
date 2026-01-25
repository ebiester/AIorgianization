import { App, TFolder, normalizePath } from 'obsidian';
import { TaskStatus, STATUS_FOLDERS, AioSettings } from '../types';

/**
 * Service for vault path utilities and AIO folder operations.
 */
export class VaultService {
  constructor(
    private app: App,
    private settings: AioSettings
  ) {}

  /**
   * Get the base AIO folder path.
   */
  getAioPath(): string {
    return this.settings.aioFolderPath;
  }

  /**
   * Get the Tasks folder path.
   */
  getTasksPath(): string {
    return normalizePath(`${this.getAioPath()}/Tasks`);
  }

  /**
   * Get the folder path for a specific task status.
   */
  getStatusPath(status: TaskStatus): string {
    const folder = STATUS_FOLDERS[status];
    return normalizePath(`${this.getTasksPath()}/${folder}`);
  }

  /**
   * Get the completed tasks folder path for a specific year/month.
   */
  getCompletedPath(year: number, month: number): string {
    const monthStr = month.toString().padStart(2, '0');
    return normalizePath(`${this.getTasksPath()}/Completed/${year}/${monthStr}`);
  }

  /**
   * Get the Projects folder path.
   */
  getProjectsPath(): string {
    return normalizePath(`${this.getAioPath()}/Projects`);
  }

  /**
   * Get the People folder path.
   */
  getPeoplePath(): string {
    return normalizePath(`${this.getAioPath()}/People`);
  }

  /**
   * Get the Dashboard folder path.
   */
  getDashboardPath(): string {
    return normalizePath(`${this.getAioPath()}/Dashboard`);
  }

  /**
   * Get the Archive folder path.
   */
  getArchivePath(): string {
    return normalizePath(`${this.getAioPath()}/Archive`);
  }

  /**
   * Ensure a folder exists, creating it if necessary.
   */
  async ensureFolderExists(path: string): Promise<void> {
    const normalizedPath = normalizePath(path);
    const folder = this.app.vault.getAbstractFileByPath(normalizedPath);

    if (!folder) {
      try {
        await this.app.vault.createFolder(normalizedPath);
      } catch (e) {
        // Ignore "Folder already exists" errors (race condition)
        if (e instanceof Error && !e.message.includes('Folder already exists')) {
          throw e;
        }
      }
    } else if (!(folder instanceof TFolder)) {
      throw new Error(`Path exists but is not a folder: ${normalizedPath}`);
    }
  }

  /**
   * Ensure the AIO folder structure exists.
   */
  async ensureAioStructure(): Promise<void> {
    // Create base folders
    await this.ensureFolderExists(this.getAioPath());
    await this.ensureFolderExists(this.getTasksPath());
    await this.ensureFolderExists(this.getProjectsPath());
    await this.ensureFolderExists(this.getPeoplePath());
    await this.ensureFolderExists(this.getDashboardPath());
    await this.ensureFolderExists(this.getArchivePath());

    // Create status folders
    for (const status of Object.keys(STATUS_FOLDERS) as TaskStatus[]) {
      if (status === 'completed') {
        // Completed folder will have year/month subfolders created on demand
        await this.ensureFolderExists(normalizePath(`${this.getTasksPath()}/Completed`));
      } else {
        await this.ensureFolderExists(this.getStatusPath(status));
      }
    }
  }

  /**
   * Generate a filename for a task.
   */
  generateTaskFilename(title: string, date: Date = new Date()): string {
    const dateStr = date.toISOString().split('T')[0];
    const slug = this.slugify(title);
    return `${dateStr}-${slug}.md`;
  }

  /**
   * Convert a title to a URL-friendly slug.
   */
  private slugify(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
      .substring(0, 50);
  }

  /**
   * Get all project names from the Projects folder.
   */
  async getProjects(): Promise<string[]> {
    const projectsPath = this.getProjectsPath();
    const folder = this.app.vault.getAbstractFileByPath(projectsPath);

    if (!(folder instanceof TFolder)) {
      return [];
    }

    return folder.children
      .filter(f => f.name.endsWith('.md'))
      .map(f => f.name.replace('.md', ''));
  }

  /**
   * Get all people names from the People folder.
   */
  async getPeople(): Promise<string[]> {
    const peoplePath = this.getPeoplePath();
    const folder = this.app.vault.getAbstractFileByPath(peoplePath);

    if (!(folder instanceof TFolder)) {
      return [];
    }

    return folder.children
      .filter(f => f.name.endsWith('.md'))
      .map(f => f.name.replace('.md', ''));
  }
}
