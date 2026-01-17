import { Plugin, WorkspaceLeaf } from 'obsidian';
import { AioSettings, DEFAULT_SETTINGS, Task } from './types';
import { AioSettingTab } from './settings';
import { VaultService } from './services/VaultService';
import { TaskService } from './services/TaskService';
import { TaskListView, TASK_LIST_VIEW_TYPE } from './views/TaskListView';
import { InboxView, INBOX_VIEW_TYPE } from './views/InboxView';
import { QuickAddModal } from './modals/QuickAddModal';
import { TaskEditModal } from './modals/TaskEditModal';

export default class AioPlugin extends Plugin {
  settings: AioSettings;
  vaultService: VaultService;
  taskService: TaskService;

  async onload(): Promise<void> {
    await this.loadSettings();

    // Initialize services
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);

    // Ensure AIO folder structure exists
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
    // Cleanup
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
    // Reinitialize services with new settings
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);
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
   */
  private getCurrentTask(): Task | null {
    const file = this.app.workspace.getActiveFile();
    if (!file) return null;

    // Check if file is in the Tasks folder
    if (!file.path.includes(`${this.settings.aioFolderPath}/Tasks`)) {
      return null;
    }

    // Parse the file as a task
    // Note: This is sync but we could cache tasks for better performance
    return null; // TODO: Implement async task lookup
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
