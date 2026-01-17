/**
 * Task status values matching the Python CLI.
 */
export type TaskStatus = 'inbox' | 'next' | 'waiting' | 'scheduled' | 'someday' | 'completed';

/**
 * Location context for a task (code reference).
 */
export interface TaskLocation {
  file?: string;
  line?: number;
  url?: string;
}

/**
 * Task model matching the Python CLI frontmatter schema.
 */
export interface Task {
  /** 4-character alphanumeric ID */
  id: string;
  /** Always 'task' */
  type: 'task';
  /** Current task status */
  status: TaskStatus;
  /** Task title (from markdown heading) */
  title: string;
  /** Due date in ISO format */
  due?: string;
  /** Project wikilink */
  project?: string;
  /** Assigned person wikilink */
  assignedTo?: string;
  /** Person we're waiting on */
  waitingOn?: string;
  /** Task IDs that block this task */
  blockedBy: string[];
  /** Task IDs this task blocks */
  blocks: string[];
  /** Code location context */
  location?: TaskLocation;
  /** Tags for categorization */
  tags: string[];
  /** Time estimate (e.g., "2h", "30m") */
  timeEstimate?: string;
  /** Jira issue key */
  jiraKey?: string;
  /** Creation timestamp ISO datetime */
  created: string;
  /** Last update timestamp ISO datetime */
  updated: string;
  /** Completion timestamp ISO datetime */
  completed?: string;
  /** Markdown body content (excluding frontmatter) */
  content: string;
  /** File path relative to vault root */
  path: string;
}

/**
 * Options for creating a new task.
 */
export interface CreateTaskOptions {
  due?: string;
  project?: string;
  status?: TaskStatus;
  tags?: string[];
  timeEstimate?: string;
}

/**
 * Plugin settings interface.
 */
export interface AioSettings {
  /** Path to AIO folder relative to vault root */
  aioFolderPath: string;
  /** Default status for new tasks */
  defaultStatus: TaskStatus;
  /** Date display format */
  dateFormat: string;
}

/**
 * Default plugin settings.
 */
export const DEFAULT_SETTINGS: AioSettings = {
  aioFolderPath: 'AIO',
  defaultStatus: 'inbox',
  dateFormat: 'YYYY-MM-DD',
};

/**
 * Mapping of status to folder name.
 */
export const STATUS_FOLDERS: Record<TaskStatus, string> = {
  inbox: 'Inbox',
  next: 'Next',
  waiting: 'Waiting',
  scheduled: 'Scheduled',
  someday: 'Someday',
  completed: 'Completed',
};

/**
 * Characters used for ID generation (excludes ambiguous: 0, 1, I, O).
 */
export const ID_CHARS = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
