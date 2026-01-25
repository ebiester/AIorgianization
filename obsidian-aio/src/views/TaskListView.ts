import { ItemView, WorkspaceLeaf, setIcon, Notice } from 'obsidian';
import type AioPlugin from '../main';
import { Task, TaskStatus, STATUS_FOLDERS } from '../types';
import { DaemonOfflineError } from '../services/DaemonClient';

export const TASK_LIST_VIEW_TYPE = 'aio-task-list';

export class TaskListView extends ItemView {
  private plugin: AioPlugin;
  private currentStatus: TaskStatus | 'all' = 'all';
  private tasks: Task[] = [];

  constructor(leaf: WorkspaceLeaf, plugin: AioPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return TASK_LIST_VIEW_TYPE;
  }

  getDisplayText(): string {
    return 'AIO Tasks';
  }

  getIcon(): string {
    return 'check-square';
  }

  async onOpen(): Promise<void> {
    await this.refresh();
  }

  async onClose(): Promise<void> {
    // Cleanup if needed
  }

  async refresh(): Promise<void> {
    const container = this.containerEl.children[1];
    container.empty();

    const isReadOnly = this.plugin.isReadOnly;

    container.createEl('div', { cls: 'aio-task-list-container' }, (el) => {
      // Show read-only banner if daemon is offline
      if (isReadOnly) {
        el.createEl('div', {
          cls: 'aio-readonly-banner',
          text: 'Read-only: daemon offline. Run "aio daemon start" to enable writes.',
        });
      }

      // Header with title and add button
      el.createEl('div', { cls: 'aio-task-list-header' }, (header) => {
        header.createEl('h4', { text: 'Tasks', cls: 'aio-task-list-title' });
        const addBtn = header.createEl('button', { cls: 'aio-add-btn', attr: { 'aria-label': 'Add task' } });
        setIcon(addBtn, 'plus');
        if (isReadOnly) {
          addBtn.addClass('aio-disabled');
          addBtn.setAttribute('title', 'Daemon offline - cannot add tasks');
        } else {
          addBtn.addEventListener('click', () => {
            this.plugin.openQuickAddModal();
          });
        }
      });

      // Status filter tabs
      el.createEl('div', { cls: 'aio-status-tabs' }, (tabs) => {
        this.createTab(tabs, 'all', 'All');
        this.createTab(tabs, 'inbox', 'Inbox');
        this.createTab(tabs, 'next', 'Next');
        this.createTab(tabs, 'waiting', 'Waiting');
        this.createTab(tabs, 'scheduled', 'Scheduled');
        this.createTab(tabs, 'someday', 'Someday');
      });

      // Task list container
      el.createEl('div', { cls: 'aio-task-list' }, async (listEl) => {
        await this.renderTasks(listEl);
      });
    });
  }

  private createTab(container: HTMLElement, status: TaskStatus | 'all', label: string): void {
    const tab = container.createEl('button', {
      cls: `aio-status-tab ${this.currentStatus === status ? 'is-active' : ''}`,
      text: label,
    });

    tab.addEventListener('click', async () => {
      this.currentStatus = status;
      await this.refresh();
    });
  }

  private async renderTasks(container: HTMLElement): Promise<void> {
    try {
      if (this.currentStatus === 'all') {
        this.tasks = await this.plugin.taskService.listTasks();
      } else {
        this.tasks = await this.plugin.taskService.listTasks(this.currentStatus);
      }

      // Sort by due date (tasks with due dates first, then by date)
      this.tasks.sort((a, b) => {
        if (a.due && b.due) {
          return a.due.localeCompare(b.due);
        }
        if (a.due) return -1;
        if (b.due) return 1;
        return a.created.localeCompare(b.created);
      });

      if (this.tasks.length === 0) {
        container.createEl('div', { cls: 'aio-empty-state', text: 'No tasks found' });
        return;
      }

      for (const task of this.tasks) {
        this.renderTask(container, task);
      }
    } catch (e) {
      container.createEl('div', { cls: 'aio-error', text: `Error loading tasks: ${e}` });
    }
  }

  private renderTask(container: HTMLElement, task: Task): void {
    const taskEl = container.createEl('div', { cls: 'aio-task-item' });
    const isReadOnly = this.plugin.isReadOnly;

    // Checkbox
    const checkbox = taskEl.createEl('input', {
      cls: 'aio-task-checkbox',
      attr: { type: 'checkbox' },
    });
    checkbox.checked = task.status === 'completed';
    if (isReadOnly) {
      checkbox.disabled = true;
      checkbox.setAttribute('title', 'Daemon offline - cannot complete tasks');
    } else {
      checkbox.addEventListener('change', async () => {
        if (checkbox.checked) {
          try {
            await this.plugin.taskService.completeTask(task.id);
            await this.refresh();
          } catch (e) {
            checkbox.checked = false;
            if (e instanceof DaemonOfflineError) {
              new Notice('Cannot complete task: daemon is offline.');
            } else {
              new Notice(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
            }
          }
        }
      });
    }

    // Task content
    const contentEl = taskEl.createEl('div', { cls: 'aio-task-content' });

    // Title (clickable to open file)
    const titleEl = contentEl.createEl('div', { cls: 'aio-task-title', text: task.title });
    titleEl.addEventListener('click', () => {
      const file = this.app.vault.getAbstractFileByPath(task.path);
      if (file) {
        this.app.workspace.getLeaf(false).openFile(file as any);
      }
    });

    // Metadata row
    const metaEl = contentEl.createEl('div', { cls: 'aio-task-meta' });

    // Status badge
    metaEl.createEl('span', {
      cls: `aio-status-badge aio-status-${task.status}`,
      text: STATUS_FOLDERS[task.status],
    });

    // Due date
    if (task.due) {
      const dueDate = new Date(task.due);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const isOverdue = dueDate < today;

      metaEl.createEl('span', {
        cls: `aio-due-date ${isOverdue ? 'aio-overdue' : ''}`,
        text: task.due,
      });
    }

    // Project link
    if (task.project) {
      const projectName = task.project.replace(/^\[\[/, '').replace(/\]\]$/, '');
      metaEl.createEl('span', { cls: 'aio-project', text: projectName });
    }

    // Tags
    if (task.tags.length > 0) {
      for (const tag of task.tags.slice(0, 3)) {
        metaEl.createEl('span', { cls: 'aio-tag', text: `#${tag}` });
      }
    }

    // Action buttons
    const actionsEl = taskEl.createEl('div', { cls: 'aio-task-actions' });

    if (task.status !== 'next' && task.status !== 'completed') {
      const startBtn = actionsEl.createEl('button', { cls: 'aio-action-btn', attr: { 'aria-label': 'Start' } });
      setIcon(startBtn, 'play');
      if (isReadOnly) {
        startBtn.addClass('aio-disabled');
        startBtn.setAttribute('title', 'Daemon offline - cannot change status');
      } else {
        startBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          try {
            await this.plugin.taskService.changeStatus(task.id, 'next');
            await this.refresh();
          } catch (err) {
            if (err instanceof DaemonOfflineError) {
              new Notice('Cannot start task: daemon is offline.');
            } else {
              new Notice(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
            }
          }
        });
      }
    }

    if (task.status !== 'someday' && task.status !== 'completed') {
      const deferBtn = actionsEl.createEl('button', { cls: 'aio-action-btn', attr: { 'aria-label': 'Defer' } });
      setIcon(deferBtn, 'clock');
      if (isReadOnly) {
        deferBtn.addClass('aio-disabled');
        deferBtn.setAttribute('title', 'Daemon offline - cannot change status');
      } else {
        deferBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          try {
            await this.plugin.taskService.changeStatus(task.id, 'someday');
            await this.refresh();
          } catch (err) {
            if (err instanceof DaemonOfflineError) {
              new Notice('Cannot defer task: daemon is offline.');
            } else {
              new Notice(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
            }
          }
        });
      }
    }

    // Edit button - always enabled to allow viewing, but modal will show read-only state
    const editBtn = actionsEl.createEl('button', { cls: 'aio-action-btn', attr: { 'aria-label': 'Edit' } });
    setIcon(editBtn, 'pencil');
    editBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.plugin.openTaskEditModal(task);
    });
  }
}
