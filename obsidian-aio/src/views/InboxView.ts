import { ItemView, WorkspaceLeaf, setIcon } from 'obsidian';
import type AioPlugin from '../main';
import { Task } from '../types';

export const INBOX_VIEW_TYPE = 'aio-inbox';

export class InboxView extends ItemView {
  private plugin: AioPlugin;
  private inboxTasks: Task[] = [];
  private currentIndex: number = 0;
  private skippedCount: number = 0;

  constructor(leaf: WorkspaceLeaf, plugin: AioPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return INBOX_VIEW_TYPE;
  }

  getDisplayText(): string {
    return 'AIO Inbox';
  }

  getIcon(): string {
    return 'inbox';
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
    this.skippedCount = 0;

    container.createEl('div', { cls: 'aio-inbox-container' }, async (el) => {
      // Header
      el.createEl('div', { cls: 'aio-inbox-header' }, (header) => {
        header.createEl('h4', { text: 'Process Inbox', cls: 'aio-inbox-title' });
      });

      // Load inbox tasks
      try {
        this.inboxTasks = await this.plugin.taskService.listTasks('inbox');

        if (this.inboxTasks.length === 0) {
          this.renderInboxZero(el);
        } else {
          this.renderCurrentTask(el);
        }
      } catch (e) {
        el.createEl('div', { cls: 'aio-error', text: `Error loading inbox: ${e}` });
      }
    });
  }

  private renderInboxZero(container: HTMLElement): void {
    container.createEl('div', { cls: 'aio-inbox-zero' }, (el) => {
      el.createEl('div', { cls: 'aio-inbox-zero-icon', text: '🎉' });
      el.createEl('h3', { text: 'Inbox Zero!' });
      el.createEl('p', { text: 'All tasks have been processed. Great job!' });

      const addBtn = el.createEl('button', { cls: 'mod-cta', text: 'Add new task' });
      addBtn.addEventListener('click', () => {
        this.plugin.openQuickAddModal();
      });
    });
  }

  private renderCurrentTask(container: HTMLElement): void {
    const task = this.inboxTasks[this.currentIndex];

    // Progress indicator
    container.createEl('div', { cls: 'aio-inbox-progress' }, (progress) => {
      progress.createEl('span', {
        text: `${this.currentIndex + 1} of ${this.inboxTasks.length}`,
      });
      const bar = progress.createEl('div', { cls: 'aio-progress-bar' });
      bar.createEl('div', {
        cls: 'aio-progress-fill',
        attr: { style: `width: ${((this.currentIndex + 1) / this.inboxTasks.length) * 100}%` },
      });
    });

    // Task card
    container.createEl('div', { cls: 'aio-inbox-card' }, (card) => {
      // Task title
      const titleEl = card.createEl('h3', { cls: 'aio-inbox-task-title', text: task.title });
      titleEl.addEventListener('click', () => {
        const file = this.app.vault.getAbstractFileByPath(task.path);
        if (file) {
          this.app.workspace.getLeaf(false).openFile(file as any);
        }
      });

      // Task metadata
      card.createEl('div', { cls: 'aio-inbox-task-meta' }, (meta) => {
        if (task.due) {
          meta.createEl('span', { cls: 'aio-due-date', text: `Due: ${task.due}` });
        }
        if (task.project) {
          const projectName = task.project.replace(/^\[\[/, '').replace(/\]\]$/, '');
          meta.createEl('span', { cls: 'aio-project', text: projectName });
        }
        meta.createEl('span', { cls: 'aio-task-id', text: `#${task.id}` });
      });

      // Task content preview
      if (task.content) {
        const preview = task.content
          .replace(/^#\s+.*$/m, '') // Remove title heading
          .trim()
          .substring(0, 200);
        if (preview) {
          card.createEl('div', { cls: 'aio-inbox-preview', text: preview });
        }
      }
    });

    // Action buttons
    container.createEl('div', { cls: 'aio-inbox-actions' }, (actions) => {
      // Start (move to Next)
      const startBtn = actions.createEl('button', { cls: 'aio-inbox-action mod-cta' });
      startBtn.createEl('span', { cls: 'aio-action-icon' }, (span) => setIcon(span, 'play'));
      startBtn.createEl('span', { text: 'Start' });
      startBtn.createEl('span', { cls: 'aio-action-hint', text: '→ Next' });
      startBtn.addEventListener('click', () => this.handleAction('next'));

      // Defer (move to Someday)
      const deferBtn = actions.createEl('button', { cls: 'aio-inbox-action' });
      deferBtn.createEl('span', { cls: 'aio-action-icon' }, (span) => setIcon(span, 'clock'));
      deferBtn.createEl('span', { text: 'Defer' });
      deferBtn.createEl('span', { cls: 'aio-action-hint', text: '→ Someday' });
      deferBtn.addEventListener('click', () => this.handleAction('someday'));

      // Wait (move to Waiting)
      const waitBtn = actions.createEl('button', { cls: 'aio-inbox-action' });
      waitBtn.createEl('span', { cls: 'aio-action-icon' }, (span) => setIcon(span, 'user'));
      waitBtn.createEl('span', { text: 'Wait' });
      waitBtn.createEl('span', { cls: 'aio-action-hint', text: '→ Waiting' });
      waitBtn.addEventListener('click', () => this.handleAction('waiting'));

      // Schedule
      const scheduleBtn = actions.createEl('button', { cls: 'aio-inbox-action' });
      scheduleBtn.createEl('span', { cls: 'aio-action-icon' }, (span) => setIcon(span, 'calendar'));
      scheduleBtn.createEl('span', { text: 'Schedule' });
      scheduleBtn.createEl('span', { cls: 'aio-action-hint', text: '→ Scheduled' });
      scheduleBtn.addEventListener('click', () => this.handleAction('scheduled'));

      // Complete
      const completeBtn = actions.createEl('button', { cls: 'aio-inbox-action' });
      completeBtn.createEl('span', { cls: 'aio-action-icon' }, (span) => setIcon(span, 'check'));
      completeBtn.createEl('span', { text: 'Done' });
      completeBtn.createEl('span', { cls: 'aio-action-hint', text: '→ Completed' });
      completeBtn.addEventListener('click', () => this.handleAction('completed'));
    });

    // Skip button
    container.createEl('div', { cls: 'aio-inbox-skip' }, (el) => {
      const skipBtn = el.createEl('button', { cls: 'aio-skip-btn', text: 'Skip for now' });
      skipBtn.addEventListener('click', () => {
        this.skippedCount++;
        if (this.skippedCount >= this.inboxTasks.length) {
          // User has skipped through all tasks - show review complete message
          this.renderReviewComplete(container);
          return;
        }
        this.currentIndex = (this.currentIndex + 1) % this.inboxTasks.length;
        this.refresh();
      });
    });
  }

  private renderReviewComplete(container: HTMLElement): void {
    container.empty();

    container.createEl('div', { cls: 'aio-inbox-container' }, (el) => {
      el.createEl('div', { cls: 'aio-inbox-header' }, (header) => {
        header.createEl('h4', { text: 'Process Inbox', cls: 'aio-inbox-title' });
      });

      el.createEl('div', { cls: 'aio-inbox-review-complete' }, (content) => {
        content.createEl('div', { cls: 'aio-inbox-zero-icon', text: '📋' });
        content.createEl('h3', { text: 'Review Complete' });
        content.createEl('p', {
          text: `You've reviewed all ${this.inboxTasks.length} task${this.inboxTasks.length === 1 ? '' : 's'} in your inbox.`
        });

        const btnContainer = content.createEl('div', { cls: 'aio-review-complete-actions' });

        const reviewAgainBtn = btnContainer.createEl('button', { cls: 'mod-cta', text: 'Review again' });
        reviewAgainBtn.addEventListener('click', () => {
          this.skippedCount = 0;
          this.currentIndex = 0;
          this.refresh();
        });

        const closeBtn = btnContainer.createEl('button', { text: 'Close' });
        closeBtn.addEventListener('click', () => {
          this.leaf.detach();
        });
      });
    });
  }

  private async handleAction(newStatus: 'next' | 'someday' | 'waiting' | 'scheduled' | 'completed'): Promise<void> {
    const task = this.inboxTasks[this.currentIndex];

    try {
      if (newStatus === 'completed') {
        await this.plugin.taskService.completeTask(task.id);
      } else {
        await this.plugin.taskService.changeStatus(task.id, newStatus);
      }

      // Remove processed task from list
      this.inboxTasks.splice(this.currentIndex, 1);

      // Adjust index if needed
      if (this.currentIndex >= this.inboxTasks.length) {
        this.currentIndex = 0;
      }

      await this.refresh();
    } catch (e) {
      console.error('Error processing task:', e);
    }
  }
}
