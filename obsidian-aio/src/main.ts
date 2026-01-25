import { Plugin, WorkspaceLeaf, Notice } from 'obsidian';
import { AioSettings, DEFAULT_SETTINGS, Task } from './types';
import { AioSettingTab } from './settings';
import { VaultService } from './services/VaultService';
import { TaskService } from './services/TaskService';
import { TaskListView, TASK_LIST_VIEW_TYPE } from './views/TaskListView';
import { InboxView, INBOX_VIEW_TYPE } from './views/InboxView';
import { QuickAddModal } from './modals/QuickAddModal';
import { TaskEditModal } from './modals/TaskEditModal';

/** Interval for daemon health checks (30 seconds). */
const HEALTH_CHECK_INTERVAL = 30000;

export default class AioPlugin extends Plugin {
  settings: AioSettings;
  vaultService: VaultService;
  taskService: TaskService;
  private statusBarItem: HTMLElement | null = null;
  private healthCheckInterval: number | null = null;

  async onload(): Promise<void> {
    await this.loadSettings();

    // Initialize services
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);

    // Add status bar item for daemon status
    this.statusBarItem = this.addStatusBarItem();
    this.updateStatusBar(false);

    // Check daemon connection
    await this.checkDaemonConnection();

    // Start periodic health checks
    this.startHealthChecks();

    // Ensure AIO folder structure exists (for fallback mode)
    await this.vaultService.ensureAioStructure();

    // Register views
    this.registerView(
      TASK_LIST_VIEW_TYPE,
      (leaf) => new TaskListView(leaf, this)
    );

    this.registerView(
      INBOX_VIEW_TYPE,
      (leaf) => new InboxView(leaf, this)
    );

    // Add ribbon icons
    this.addRibbonIcon('check-square', 'Open AIO Tasks', () => {
      this.activateView(TASK_LIST_VIEW_TYPE);
    });

    this.addRibbonIcon('inbox', 'Open AIO Inbox', () => {
      this.activateView(INBOX_VIEW_TYPE);
    });

    // Register commands
    this.addCommand({
      id: 'aio-add-task',
      name: 'Add task',
      callback: () => this.openQuickAddModal(),
    });

    this.addCommand({
      id: 'aio-open-tasks',
      name: 'Open tasks',
      callback: () => this.activateView(TASK_LIST_VIEW_TYPE),
    });

    this.addCommand({
      id: 'aio-open-inbox',
      name: 'Open inbox',
      callback: () => this.activateView(INBOX_VIEW_TYPE),
    });

    this.addCommand({
      id: 'aio-complete-task',
      name: 'Complete current task',
      checkCallback: (checking: boolean) => {
        const task = this.getCurrentTask();
        if (task) {
          if (!checking) {
            this.taskService.completeTask(task.id).then(() => {
              this.refreshViews();
            });
          }
          return true;
        }
        return false;
      },
    });

    this.addCommand({
      id: 'aio-start-task',
      name: 'Start current task (move to Next)',
      checkCallback: (checking: boolean) => {
        const task = this.getCurrentTask();
        if (task && task.status !== 'next' && task.status !== 'completed') {
          if (!checking) {
            this.taskService.changeStatus(task.id, 'next').then(() => {
              this.refreshViews();
            });
          }
          return true;
        }
        return false;
      },
    });

    this.addCommand({
      id: 'aio-defer-task',
      name: 'Defer current task (move to Someday)',
      checkCallback: (checking: boolean) => {
        const task = this.getCurrentTask();
        if (task && task.status !== 'someday' && task.status !== 'completed') {
          if (!checking) {
            this.taskService.changeStatus(task.id, 'someday').then(() => {
              this.refreshViews();
            });
          }
          return true;
        }
        return false;
      },
    });

    this.addCommand({
      id: 'aio-wait-task',
      name: 'Wait on current task (move to Waiting)',
      checkCallback: (checking: boolean) => {
        const task = this.getCurrentTask();
        if (task && task.status !== 'waiting' && task.status !== 'completed') {
          if (!checking) {
            this.taskService.changeStatus(task.id, 'waiting').then(() => {
              this.refreshViews();
            });
          }
          return true;
        }
        return false;
      },
    });

    this.addCommand({
      id: 'aio-schedule-task',
      name: 'Schedule current task',
      checkCallback: (checking: boolean) => {
        const task = this.getCurrentTask();
        if (task && task.status !== 'scheduled' && task.status !== 'completed') {
          if (!checking) {
            this.taskService.changeStatus(task.id, 'scheduled').then(() => {
              this.refreshViews();
            });
          }
          return true;
        }
        return false;
      },
    });

    // Add settings tab
    this.addSettingTab(new AioSettingTab(this.app, this));
  }

  onunload(): void {
    // Stop health checks
    this.stopHealthChecks();

    // Detach all AIO views to prevent "plugin no longer active" errors on restart
    this.app.workspace.detachLeavesOfType(TASK_LIST_VIEW_TYPE);
    this.app.workspace.detachLeavesOfType(INBOX_VIEW_TYPE);
  }

  /**
   * Check daemon connection and update status bar.
   */
  private async checkDaemonConnection(): Promise<void> {
    if (!this.settings.useDaemon) {
      this.updateStatusBar(false, 'disabled');
      return;
    }

    const connected = await this.taskService.checkDaemonConnection();
    this.updateStatusBar(connected);

    if (connected) {
      const health = this.taskService.daemon.lastHealthCheck;
      if (health) {
        console.log(`AIO: Connected to daemon v${health.version}, ${health.cache.task_count} tasks cached`);
      }
    }
  }

  /**
   * Start periodic health checks.
   */
  private startHealthChecks(): void {
    if (this.healthCheckInterval) {
      return;
    }

    this.healthCheckInterval = window.setInterval(async () => {
      await this.checkDaemonConnection();
    }, HEALTH_CHECK_INTERVAL);

    // Register for cleanup
    this.registerInterval(this.healthCheckInterval);
  }

  /**
   * Stop periodic health checks.
   */
  private stopHealthChecks(): void {
    if (this.healthCheckInterval) {
      window.clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }

  /**
   * Update the status bar with daemon connection status.
   */
  private updateStatusBar(connected: boolean, mode?: 'disabled'): void {
    if (!this.statusBarItem) {
      return;
    }

    if (mode === 'disabled') {
      this.statusBarItem.setText('AIO: Local');
      this.statusBarItem.setAttribute('title', 'Daemon mode disabled - using local files');
      this.statusBarItem.removeClass('aio-connected', 'aio-disconnected');
      return;
    }

    if (connected) {
      this.statusBarItem.setText('AIO: Connected');
      this.statusBarItem.setAttribute('title', 'Connected to AIO daemon');
      this.statusBarItem.addClass('aio-connected');
      this.statusBarItem.removeClass('aio-disconnected');
    } else {
      this.statusBarItem.setText('AIO: Offline');
      this.statusBarItem.setAttribute('title', 'Daemon not available - read-only mode');
      this.statusBarItem.addClass('aio-disconnected');
      this.statusBarItem.removeClass('aio-connected');
    }
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    // Reinitialize services with new settings
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService.updateSettings(this.settings);
    // Re-check daemon connection
    await this.checkDaemonConnection();
  }

  /**
   * Activate a view in the right sidebar.
   */
  async activateView(viewType: string): Promise<void> {
    const { workspace } = this.app;

    let leaf: WorkspaceLeaf | null = null;
    const leaves = workspace.getLeavesOfType(viewType);

    if (leaves.length > 0) {
      // View already open, reveal it
      leaf = leaves[0];
    } else {
      // Create new leaf in right sidebar
      leaf = workspace.getRightLeaf(false);
      if (leaf) {
        await leaf.setViewState({ type: viewType, active: true });
      }
    }

    if (leaf) {
      workspace.revealLeaf(leaf);
    }
  }

  /**
   * Open the Quick Add modal.
   */
  openQuickAddModal(): void {
    new QuickAddModal(this.app, this, () => {
      this.refreshViews();
    }).open();
  }

  /**
   * Open the Task Edit modal.
   */
  openTaskEditModal(task: Task): void {
    new TaskEditModal(this.app, this, task, () => {
      this.refreshViews();
    }).open();
  }

  /**
   * Get the current task from the active file.
   * Uses Obsidian's metadata cache for synchronous access.
   */
  private getCurrentTask(): Task | null {
    const file = this.app.workspace.getActiveFile();
    if (!file) return null;

    // Check if file is in the Tasks folder
    if (!file.path.includes(`${this.settings.aioFolderPath}/Tasks`)) {
      return null;
    }

    // Use Obsidian's metadata cache for synchronous frontmatter access
    const cache = this.app.metadataCache.getFileCache(file);
    if (!cache?.frontmatter) {
      return null;
    }

    const fm = cache.frontmatter;

    // Verify this is a task file
    if (fm.type !== 'task') {
      return null;
    }

    // Extract title from first heading in cache or filename
    let title = fm.title || '';
    if (!title && cache.headings && cache.headings.length > 0) {
      title = cache.headings[0].heading;
    }
    if (!title) {
      title = file.basename;
    }

    return {
      id: fm.id || '',
      type: 'task',
      status: fm.status || 'inbox',
      title,
      due: fm.due,
      project: fm.project,
      assignedTo: fm.assignedTo,
      waitingOn: fm.waitingOn,
      blockedBy: fm.blockedBy || [],
      blocks: fm.blocks || [],
      location: fm.location,
      tags: fm.tags || [],
      timeEstimate: fm.timeEstimate,
      created: fm.created || new Date().toISOString(),
      updated: fm.updated || new Date().toISOString(),
      completed: fm.completed,
      content: '', // Not needed for command palette checks
      path: file.path,
    };
  }

  /**
   * Refresh all open AIO views.
   */
  private refreshViews(): void {
    // Refresh task list views
    for (const leaf of this.app.workspace.getLeavesOfType(TASK_LIST_VIEW_TYPE)) {
      const view = leaf.view as TaskListView;
      view.refresh();
    }

    // Refresh inbox views
    for (const leaf of this.app.workspace.getLeavesOfType(INBOX_VIEW_TYPE)) {
      const view = leaf.view as InboxView;
      view.refresh();
    }
  }
}
