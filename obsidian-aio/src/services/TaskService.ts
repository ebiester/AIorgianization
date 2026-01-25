import { App, TFile, TFolder, normalizePath } from 'obsidian';
import { Task, TaskStatus, CreateTaskOptions, ID_CHARS, AioSettings } from '../types';
import { VaultService } from './VaultService';
import { DaemonClient, DaemonUnavailableError } from './DaemonClient';

/**
 * Service for task CRUD operations.
 *
 * Supports two modes:
 * - Daemon mode: All operations go through the daemon HTTP API (fast, centralized)
 * - Fallback mode: Direct file operations (read-only when daemon unavailable)
 */
export class TaskService {
  private vaultService: VaultService;
  private daemonClient: DaemonClient;
  private _useDaemon: boolean;

  constructor(
    private app: App,
    private settings: AioSettings
  ) {
    this.vaultService = new VaultService(app, settings);
    this.daemonClient = new DaemonClient(settings);
    this._useDaemon = settings.useDaemon;
  }

  /**
   * Whether daemon mode is enabled and connected.
   */
  get isDaemonConnected(): boolean {
    return this._useDaemon && this.daemonClient.isConnected;
  }

  /**
   * Get the daemon client (for status checks).
   */
  get daemon(): DaemonClient {
    return this.daemonClient;
  }

  /**
   * Update settings and reconnect if needed.
   */
  updateSettings(settings: AioSettings): void {
    this.settings = settings;
    this._useDaemon = settings.useDaemon;
    this.daemonClient.updateSettings(settings);
    this.vaultService = new VaultService(this.app, settings);
  }

  /**
   * Check daemon connection and update status.
   */
  async checkDaemonConnection(): Promise<boolean> {
    if (!this._useDaemon) {
      return false;
    }
    return this.daemonClient.testConnection();
  }

  /**
   * Generate a unique 4-character task ID.
   */
  generateId(): string {
    let id = '';
    for (let i = 0; i < 4; i++) {
      const index = Math.floor(Math.random() * ID_CHARS.length);
      id += ID_CHARS[index];
    }
    return id;
  }

  /**
   * Generate a unique ID that doesn't collide with existing tasks.
   */
  async generateUniqueId(): Promise<string> {
    const existingIds = new Set<string>();
    const tasks = await this.listTasks();
    tasks.forEach(t => existingIds.add(t.id.toUpperCase()));

    let attempts = 0;
    while (attempts < 100) {
      const id = this.generateId();
      if (!existingIds.has(id.toUpperCase())) {
        return id;
      }
      attempts++;
    }
    throw new Error('Failed to generate unique ID after 100 attempts');
  }

  /**
   * List all tasks, optionally filtered by status.
   */
  async listTasks(status?: TaskStatus): Promise<Task[]> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        return await this.daemonClient.listTasks(status);
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    return this.listTasksFromFiles(status);
  }

  /**
   * List tasks from files (fallback mode).
   */
  private async listTasksFromFiles(status?: TaskStatus): Promise<Task[]> {
    const tasks: Task[] = [];

    const statuses: TaskStatus[] = status
      ? [status]
      : ['inbox', 'next', 'waiting', 'scheduled', 'someday', 'completed'];

    for (const s of statuses) {
      const folderPath = this.vaultService.getStatusPath(s);
      const statusTasks = await this.getTasksFromFolder(folderPath);
      tasks.push(...statusTasks);
    }

    return tasks;
  }

  /**
   * Get all task files from a folder recursively.
   */
  private async getTasksFromFolder(folderPath: string): Promise<Task[]> {
    const tasks: Task[] = [];
    const folder = this.app.vault.getAbstractFileByPath(folderPath);

    if (!(folder instanceof TFolder)) {
      return tasks;
    }

    const files = this.getAllMarkdownFiles(folder);

    for (const file of files) {
      try {
        const task = await this.parseTaskFile(file);
        if (task) {
          tasks.push(task);
        }
      } catch (e) {
        console.error(`Error parsing task file ${file.path}:`, e);
      }
    }

    return tasks;
  }

  /**
   * Recursively get all markdown files from a folder.
   */
  private getAllMarkdownFiles(folder: TFolder): TFile[] {
    const files: TFile[] = [];

    for (const child of folder.children) {
      if (child instanceof TFile && child.extension === 'md') {
        files.push(child);
      } else if (child instanceof TFolder) {
        files.push(...this.getAllMarkdownFiles(child));
      }
    }

    return files;
  }

  /**
   * Parse a task file into a Task object.
   */
  async parseTaskFile(file: TFile): Promise<Task | null> {
    const content = await this.app.vault.read(file);
    const { frontmatter, body } = this.parseFrontmatter(content);

    if (frontmatter.type !== 'task') {
      return null;
    }

    // Extract title from first heading or filename
    let title = frontmatter.title || '';
    if (!title) {
      const headingMatch = body.match(/^#\s+(.+)$/m);
      if (headingMatch) {
        title = headingMatch[1];
      } else {
        title = file.basename;
      }
    }

    return {
      id: frontmatter.id || '',
      type: 'task',
      status: frontmatter.status || 'inbox',
      title,
      due: frontmatter.due,
      project: frontmatter.project,
      assignedTo: frontmatter.assignedTo,
      waitingOn: frontmatter.waitingOn,
      blockedBy: frontmatter.blockedBy || [],
      blocks: frontmatter.blocks || [],
      location: frontmatter.location,
      tags: frontmatter.tags || [],
      timeEstimate: frontmatter.timeEstimate,
      created: frontmatter.created || new Date().toISOString(),
      updated: frontmatter.updated || new Date().toISOString(),
      completed: frontmatter.completed,
      content: body,
      path: file.path,
    };
  }

  /**
   * Parse YAML frontmatter from markdown content.
   */
  private parseFrontmatter(content: string): { frontmatter: Record<string, any>; body: string } {
    const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);

    if (!match) {
      return { frontmatter: {}, body: content };
    }

    const yamlStr = match[1];
    const body = match[2];

    try {
      const frontmatter = this.parseYaml(yamlStr);
      return { frontmatter, body };
    } catch {
      return { frontmatter: {}, body: content };
    }
  }

  /**
   * Simple YAML parser for frontmatter.
   */
  private parseYaml(yamlStr: string): Record<string, any> {
    const result: Record<string, any> = {};
    const lines = yamlStr.split('\n');
    let currentKey = '';
    let inArray = false;
    let arrayValue: string[] = [];

    for (const line of lines) {
      // Array item
      if (line.match(/^\s+-\s+/)) {
        const value = line.replace(/^\s+-\s+/, '').trim();
        arrayValue.push(this.parseValue(value));
        continue;
      }

      // If we were in an array, save it
      if (inArray && currentKey) {
        result[currentKey] = arrayValue;
        inArray = false;
        arrayValue = [];
      }

      // Key-value pair
      const kvMatch = line.match(/^(\w+):\s*(.*)$/);
      if (kvMatch) {
        const key = kvMatch[1];
        const value = kvMatch[2].trim();

        if (value === '' || value === '[]') {
          // Empty value or empty array, check if next line is array
          currentKey = key;
          inArray = true;
          arrayValue = [];
          if (value === '[]') {
            result[key] = [];
            inArray = false;
          }
        } else {
          result[key] = this.parseValue(value);
        }
      }
    }

    // Handle trailing array
    if (inArray && currentKey) {
      result[currentKey] = arrayValue;
    }

    return result;
  }

  /**
   * Parse a YAML value.
   */
  private parseValue(value: string): any {
    // Null
    if (value === 'null' || value === '~') {
      return null;
    }
    // Boolean
    if (value === 'true') return true;
    if (value === 'false') return false;
    // Number
    if (/^-?\d+$/.test(value)) return parseInt(value, 10);
    if (/^-?\d+\.\d+$/.test(value)) return parseFloat(value);
    // Quoted string
    if ((value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))) {
      return value.slice(1, -1);
    }
    // Plain string
    return value;
  }

  /**
   * Get a task by ID.
   */
  async getTask(id: string): Promise<Task | null> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getTask(id);
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    const tasks = await this.listTasksFromFiles();
    return tasks.find((t) => t.id.toUpperCase() === id.toUpperCase()) || null;
  }

  /**
   * Create a new task.
   */
  async createTask(title: string, options: CreateTaskOptions = {}): Promise<Task> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        return await this.daemonClient.createTask(title, options);
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    return this.createTaskInFiles(title, options);
  }

  /**
   * Create a task directly in files (fallback mode).
   */
  private async createTaskInFiles(
    title: string,
    options: CreateTaskOptions = {}
  ): Promise<Task> {
    const id = await this.generateUniqueId();
    const now = new Date().toISOString();
    const status = options.status || this.settings.defaultStatus;

    const task: Task = {
      id,
      type: 'task',
      status,
      title,
      due: options.due,
      project: options.project,
      blockedBy: [],
      blocks: [],
      tags: options.tags || [],
      timeEstimate: options.timeEstimate,
      created: now,
      updated: now,
      content: `# ${title}\n\n`,
      path: '', // Will be set below
    };

    // Generate file path
    const folderPath = this.vaultService.getStatusPath(status);
    await this.vaultService.ensureFolderExists(folderPath);

    const filename = this.vaultService.generateTaskFilename(title);
    task.path = normalizePath(`${folderPath}/${filename}`);

    // Write the file
    const content = this.serializeTask(task);
    await this.app.vault.create(task.path, content);

    return task;
  }

  /**
   * Update an existing task.
   */
  async updateTask(task: Task): Promise<void> {
    task.updated = new Date().toISOString();
    const content = this.serializeTask(task);

    const file = this.app.vault.getAbstractFileByPath(task.path);
    if (!(file instanceof TFile)) {
      throw new Error(`Task file not found: ${task.path}`);
    }

    await this.app.vault.modify(file, content);
  }

  /**
   * Mark a task as completed.
   */
  async completeTask(id: string): Promise<void> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        await this.daemonClient.completeTask(id);
        return;
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    await this.completeTaskInFiles(id);
  }

  /**
   * Complete a task directly in files (fallback mode).
   */
  private async completeTaskInFiles(id: string): Promise<void> {
    const task = await this.getTask(id);
    if (!task) {
      throw new Error(`Task not found: ${id}`);
    }

    const now = new Date();
    task.status = 'completed';
    task.completed = now.toISOString();
    task.updated = now.toISOString();

    // Move to completed folder with year/month structure
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const completedPath = this.vaultService.getCompletedPath(year, month);
    await this.vaultService.ensureFolderExists(completedPath);

    const oldPath = task.path;
    const filename = oldPath.split('/').pop() || '';
    task.path = normalizePath(`${completedPath}/${filename}`);

    // Write updated content and move file
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof TFile)) {
      throw new Error(`Task file not found: ${oldPath}`);
    }

    await this.app.vault.modify(file, content);
    await this.app.fileManager.renameFile(file, task.path);
  }

  /**
   * Change a task's status.
   */
  async changeStatus(id: string, newStatus: TaskStatus): Promise<void> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        if (newStatus === 'completed') {
          await this.daemonClient.completeTask(id);
        } else if (newStatus === 'next') {
          await this.daemonClient.startTask(id);
        } else if (newStatus === 'someday') {
          await this.daemonClient.deferTask(id);
        } else {
          // For other statuses, fall through to file-based approach
          // (daemon API doesn't have endpoints for waiting/scheduled directly)
          throw new DaemonUnavailableError('Status not supported via daemon');
        }
        return;
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    await this.changeStatusInFiles(id, newStatus);
  }

  /**
   * Change task status directly in files (fallback mode).
   */
  private async changeStatusInFiles(id: string, newStatus: TaskStatus): Promise<void> {
    const task = await this.getTask(id);
    if (!task) {
      throw new Error(`Task not found: ${id}`);
    }

    if (newStatus === 'completed') {
      return this.completeTaskInFiles(id);
    }

    task.status = newStatus;
    task.updated = new Date().toISOString();

    // Move to new status folder
    const newFolderPath = this.vaultService.getStatusPath(newStatus);
    await this.vaultService.ensureFolderExists(newFolderPath);

    const oldPath = task.path;
    const filename = oldPath.split('/').pop() || '';
    task.path = normalizePath(`${newFolderPath}/${filename}`);

    // Write updated content and move file
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof TFile)) {
      throw new Error(`Task file not found: ${oldPath}`);
    }

    await this.app.vault.modify(file, content);
    if (oldPath !== task.path) {
      await this.app.fileManager.renameFile(file, task.path);
    }
  }

  /**
   * Serialize a task to markdown with frontmatter.
   */
  private serializeTask(task: Task): string {
    const frontmatter: Record<string, any> = {
      id: task.id,
      type: task.type,
      status: task.status,
    };

    // Add optional fields only if they have values
    if (task.due) frontmatter.due = task.due;
    if (task.project) frontmatter.project = task.project;
    if (task.assignedTo) frontmatter.assignedTo = task.assignedTo;
    if (task.waitingOn) frontmatter.waitingOn = task.waitingOn;
    frontmatter.blockedBy = task.blockedBy;
    frontmatter.blocks = task.blocks;
    if (task.location) frontmatter.location = task.location;
    frontmatter.tags = task.tags;
    if (task.timeEstimate) frontmatter.timeEstimate = task.timeEstimate;
    frontmatter.created = task.created;
    frontmatter.updated = task.updated;
    if (task.completed) frontmatter.completed = task.completed;

    const yaml = this.serializeYaml(frontmatter);
    return `---\n${yaml}---\n\n${task.content}`;
  }

  /**
   * Serialize an object to YAML.
   */
  private serializeYaml(obj: Record<string, any>): string {
    const lines: string[] = [];

    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === undefined) {
        lines.push(`${key}: null`);
      } else if (Array.isArray(value)) {
        if (value.length === 0) {
          lines.push(`${key}: []`);
        } else {
          lines.push(`${key}:`);
          for (const item of value) {
            lines.push(`  - ${this.serializeValue(item)}`);
          }
        }
      } else if (typeof value === 'object') {
        lines.push(`${key}:`);
        for (const [k, v] of Object.entries(value)) {
          lines.push(`  ${k}: ${this.serializeValue(v)}`);
        }
      } else {
        lines.push(`${key}: ${this.serializeValue(value)}`);
      }
    }

    return lines.join('\n') + '\n';
  }

  /**
   * Serialize a value for YAML.
   */
  private serializeValue(value: any): string {
    if (value === null || value === undefined) {
      return 'null';
    }
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false';
    }
    if (typeof value === 'number') {
      return value.toString();
    }
    if (typeof value === 'string') {
      // Quote strings that need it
      if (
        value.includes(':') ||
        value.includes('#') ||
        value.includes('\n') ||
        value.startsWith('[[') ||
        value.match(/^\d/)
      ) {
        return `"${value.replace(/"/g, '\\"')}"`;
      }
      return value;
    }
    return String(value);
  }

  /**
   * Get project names for dropdowns.
   */
  async getProjectNames(): Promise<string[]> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getProjectNames();
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    return this.vaultService.getProjects();
  }

  /**
   * Get people names for dropdowns.
   */
  async getPeopleNames(): Promise<string[]> {
    // Try daemon first if enabled
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getPeopleNames();
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
        // Fall through to file-based approach
      }
    }

    // Fallback to file-based approach
    return this.vaultService.getPeople();
  }
}
