import { requestUrl, RequestUrlParam } from 'obsidian';
import {
  AioSettings,
  CreateTaskOptions,
  DaemonHealthResponse,
  DaemonPerson,
  DaemonProject,
  DaemonResponse,
  DaemonTask,
  Task,
  TaskStatus,
} from '../types';

/**
 * Error thrown when daemon is not available.
 */
export class DaemonUnavailableError extends Error {
  constructor(message = 'Daemon is not available') {
    super(message);
    this.name = 'DaemonUnavailableError';
  }
}

/**
 * Error thrown when daemon returns an error response.
 */
export class DaemonApiError extends Error {
  constructor(
    public code: string,
    message: string
  ) {
    super(message);
    this.name = 'DaemonApiError';
  }
}

/**
 * HTTP client for the AIO daemon API.
 *
 * Provides methods for all daemon operations:
 * - Health check and connection status
 * - Task CRUD operations
 * - Project and people listing
 * - Dashboard retrieval
 */
export class DaemonClient {
  private baseUrl: string;
  private _isConnected = false;
  private _lastHealthCheck: DaemonHealthResponse | null = null;

  constructor(private settings: AioSettings) {
    this.baseUrl = settings.daemonUrl;
  }

  /**
   * Whether the daemon is currently connected.
   */
  get isConnected(): boolean {
    return this._isConnected;
  }

  /**
   * Last health check response.
   */
  get lastHealthCheck(): DaemonHealthResponse | null {
    return this._lastHealthCheck;
  }

  /**
   * Update settings (e.g., when daemon URL changes).
   */
  updateSettings(settings: AioSettings): void {
    this.baseUrl = settings.daemonUrl;
  }

  /**
   * Make an HTTP request to the daemon.
   */
  private async request<T>(
    method: string,
    path: string,
    body?: Record<string, unknown>
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${path}`;

    const params: RequestUrlParam = {
      url,
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (body) {
      params.body = JSON.stringify(body);
    }

    try {
      const response = await requestUrl(params);
      const data = response.json as DaemonResponse<T>;

      if (!data.ok) {
        throw new DaemonApiError(data.error.code, data.error.message);
      }

      return data.data;
    } catch (e) {
      if (e instanceof DaemonApiError) {
        throw e;
      }
      // Network error or daemon not running
      this._isConnected = false;
      throw new DaemonUnavailableError(
        e instanceof Error ? e.message : 'Failed to connect to daemon'
      );
    }
  }

  /**
   * Check if daemon is available.
   */
  async checkHealth(): Promise<DaemonHealthResponse> {
    try {
      const health = await this.request<DaemonHealthResponse>('GET', '/health');
      this._isConnected = true;
      this._lastHealthCheck = health;
      return health;
    } catch (e) {
      this._isConnected = false;
      this._lastHealthCheck = null;
      throw e;
    }
  }

  /**
   * Test connection to daemon.
   * Returns true if connected, false otherwise.
   */
  async testConnection(): Promise<boolean> {
    try {
      await this.checkHealth();
      return true;
    } catch {
      return false;
    }
  }

  // Task operations

  /**
   * List tasks with optional filtering.
   */
  async listTasks(status?: TaskStatus | 'today' | 'overdue'): Promise<Task[]> {
    const path = status ? `/tasks?status=${status}` : '/tasks';
    const result = await this.request<{ tasks: DaemonTask[]; count: number }>('GET', path);
    return result.tasks.map(this.daemonTaskToTask.bind(this));
  }

  /**
   * Get a single task by ID.
   */
  async getTask(id: string): Promise<Task | null> {
    try {
      const result = await this.request<{ task: DaemonTask }>('GET', `/tasks/${id}`);
      return this.daemonTaskToTask(result.task);
    } catch (e) {
      if (e instanceof DaemonApiError && e.code === 'TASK_NOT_FOUND') {
        return null;
      }
      throw e;
    }
  }

  /**
   * Create a new task.
   */
  async createTask(title: string, options: CreateTaskOptions = {}): Promise<Task> {
    const body: Record<string, unknown> = { title };

    if (options.due) body.due = options.due;
    if (options.project) body.project = options.project;
    if (options.status) body.status = options.status;
    if (options.tags) body.tags = options.tags;
    if (options.timeEstimate) body.time_estimate = options.timeEstimate;

    const result = await this.request<{ task: DaemonTask }>('POST', '/tasks', body);
    return this.daemonTaskToTask(result.task);
  }

  /**
   * Complete a task.
   */
  async completeTask(id: string): Promise<Task> {
    const result = await this.request<{ task: DaemonTask }>('POST', `/tasks/${id}/complete`);
    return this.daemonTaskToTask(result.task);
  }

  /**
   * Start a task (move to Next).
   */
  async startTask(id: string): Promise<Task> {
    const result = await this.request<{ task: DaemonTask }>('POST', `/tasks/${id}/start`);
    return this.daemonTaskToTask(result.task);
  }

  /**
   * Defer a task (move to Someday).
   */
  async deferTask(id: string): Promise<Task> {
    const result = await this.request<{ task: DaemonTask }>('POST', `/tasks/${id}/defer`);
    return this.daemonTaskToTask(result.task);
  }

  /**
   * Delegate a task to a person (move to Waiting).
   */
  async delegateTask(id: string, person: string): Promise<Task> {
    const result = await this.request<{ task: DaemonTask; delegated_to: string }>(
      'POST',
      `/tasks/${id}/delegate`,
      { person }
    );
    return this.daemonTaskToTask(result.task);
  }

  // Project operations

  /**
   * List all projects.
   */
  async listProjects(status?: string): Promise<DaemonProject[]> {
    const path = status ? `/projects?status=${status}` : '/projects';
    const result = await this.request<{ projects: DaemonProject[]; count: number }>('GET', path);
    return result.projects;
  }

  /**
   * Get project names for dropdown.
   */
  async getProjectNames(): Promise<string[]> {
    const projects = await this.listProjects('active');
    return projects.map((p) => p.title);
  }

  // People operations

  /**
   * List all people.
   */
  async listPeople(): Promise<DaemonPerson[]> {
    const result = await this.request<{ people: DaemonPerson[]; count: number }>('GET', '/people');
    return result.people;
  }

  /**
   * Get people names for dropdown.
   */
  async getPeopleNames(): Promise<string[]> {
    const people = await this.listPeople();
    return people.map((p) => p.name);
  }

  // Dashboard

  /**
   * Get dashboard content.
   */
  async getDashboard(date?: string): Promise<{ content: string; date: string }> {
    const path = date ? `/dashboard?date=${date}` : '/dashboard';
    return this.request<{ content: string; date: string }>('GET', path);
  }

  /**
   * Convert a daemon task response to a Task object.
   */
  private daemonTaskToTask(dt: DaemonTask): Task {
    return {
      id: dt.id,
      type: 'task',
      status: dt.status,
      title: dt.title,
      due: dt.due,
      project: dt.project,
      assignedTo: dt.assigned_to,
      waitingOn: dt.waiting_on,
      blockedBy: [],
      blocks: [],
      tags: dt.tags || [],
      timeEstimate: dt.time_estimate,
      created: dt.created,
      updated: dt.updated,
      completed: dt.completed,
      content: '',
      path: '',
    };
  }
}
