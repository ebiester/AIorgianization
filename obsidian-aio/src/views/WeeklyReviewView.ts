import { ItemView, Notice, TFile, WorkspaceLeaf, normalizePath, setIcon } from 'obsidian';
import type AioPlugin from '../main';
import { Task, TaskStatus } from '../types';
import { DaemonOfflineError } from '../services/DaemonClient';

export const WEEKLY_REVIEW_VIEW_TYPE = 'aio-weekly-review';

type ReviewStepId = 'inbox' | 'projects' | 'waiting' | 'someday' | 'complete';

interface ReviewStep {
  id: ReviewStepId;
  title: string;
}

const REVIEW_STEPS: ReviewStep[] = [
  { id: 'inbox', title: 'Inbox' },
  { id: 'projects', title: 'Projects' },
  { id: 'waiting', title: 'Waiting For' },
  { id: 'someday', title: 'Someday' },
  { id: 'complete', title: 'Complete' },
];

export class WeeklyReviewView extends ItemView {
  private plugin: AioPlugin;
  private currentStepIndex = 0;

  constructor(leaf: WorkspaceLeaf, plugin: AioPlugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType(): string {
    return WEEKLY_REVIEW_VIEW_TYPE;
  }

  getDisplayText(): string {
    return 'AIO Weekly Review';
  }

  getIcon(): string {
    return 'rotate-ccw';
  }

  async onOpen(): Promise<void> {
    await this.refresh();
  }

  async onClose(): Promise<void> {
    // No resources to release.
  }

  async refresh(): Promise<void> {
    const container = this.containerEl.children[1];
    container.empty();

    container.createEl('div', { cls: 'aio-weekly-review-container' }, async (el) => {
      el.createEl('div', { cls: 'aio-weekly-review-header' }, (header) => {
        header.createEl('h4', { text: 'Weekly Review' });
        header.createEl('span', {
          cls: 'aio-weekly-review-step-count',
          text: `${this.currentStepIndex + 1} of ${REVIEW_STEPS.length}`,
        });
      });

      this.renderStepTabs(el);

      const step = REVIEW_STEPS[this.currentStepIndex];
      if (step.id === 'inbox') {
        await this.renderInboxStep(el);
      } else if (step.id === 'projects') {
        await this.renderProjectsStep(el);
      } else if (step.id === 'waiting') {
        await this.renderWaitingStep(el);
      } else if (step.id === 'someday') {
        await this.renderTaskStep(el, 'someday');
      } else {
        await this.renderCompleteStep(el);
      }

      this.renderNavigation(el);
    });
  }

  private renderStepTabs(container: HTMLElement): void {
    container.createEl('div', { cls: 'aio-review-steps' }, (tabs) => {
      REVIEW_STEPS.forEach((step, index) => {
        const tab = tabs.createEl('button', {
          cls: `aio-review-step ${index === this.currentStepIndex ? 'is-active' : ''}`,
          text: step.title,
        });
        tab.addEventListener('click', async () => {
          this.currentStepIndex = index;
          await this.refresh();
        });
      });
    });
  }

  private async renderInboxStep(container: HTMLElement): Promise<void> {
    const tasks = await this.plugin.taskService.listTasks('inbox');
    container.createEl('div', { cls: 'aio-review-panel' }, (panel) => {
      panel.createEl('h5', { text: 'Process Inbox' });
      if (tasks.length === 0) {
        panel.createEl('p', { cls: 'aio-review-empty', text: 'Inbox is empty.' });
        return;
      }

      for (const task of tasks) {
        this.renderReviewTask(panel, task, true);
      }
    });
  }

  private async renderProjectsStep(container: HTMLElement): Promise<void> {
    const projects = await this.plugin.taskService.getProjectNames();
    const nextTasks = await this.plugin.taskService.listTasks('next');

    container.createEl('div', { cls: 'aio-review-panel' }, (panel) => {
      panel.createEl('h5', { text: 'Review Projects' });
      if (projects.length === 0) {
        panel.createEl('p', { cls: 'aio-review-empty', text: 'No projects found.' });
        return;
      }

      for (const project of projects) {
        const projectTasks = nextTasks.filter((task) => task.project?.includes(project));
        panel.createEl('div', { cls: 'aio-review-project' }, (row) => {
          row.createEl('span', { cls: 'aio-review-project-name', text: project });
          row.createEl('span', {
            cls: projectTasks.length > 0 ? 'aio-review-ok' : 'aio-review-warning',
            text: projectTasks.length > 0
              ? `${projectTasks.length} next action${projectTasks.length === 1 ? '' : 's'}`
              : 'No next action',
          });
        });
      }
    });
  }

  private async renderWaitingStep(container: HTMLElement): Promise<void> {
    const groups = await this.plugin.taskService.listWaitingGroups();
    container.createEl('div', { cls: 'aio-review-panel' }, (panel) => {
      panel.createEl('h5', { text: 'Review Waiting For' });
      if (groups.length === 0) {
        panel.createEl('p', { cls: 'aio-review-empty', text: 'No waiting tasks.' });
        return;
      }

      for (const group of groups) {
        panel.createEl('div', { cls: 'aio-review-person-group' }, (section) => {
          section.createEl('h6', { text: group.person });
          for (const task of group.tasks) {
            this.renderReviewTask(section, task, false);
          }
        });
      }
    });
  }

  private async renderTaskStep(container: HTMLElement, status: TaskStatus): Promise<void> {
    const tasks = await this.plugin.taskService.listTasks(status);
    container.createEl('div', { cls: 'aio-review-panel' }, (panel) => {
      panel.createEl('h5', { text: 'Review Someday' });
      if (tasks.length === 0) {
        panel.createEl('p', { cls: 'aio-review-empty', text: 'No someday tasks.' });
        return;
      }

      for (const task of tasks) {
        this.renderReviewTask(panel, task, false);
      }
    });
  }

  private async renderCompleteStep(container: HTMLElement): Promise<void> {
    const lastReview = await this.getLastReviewLine();
    container.createEl('div', { cls: 'aio-review-panel aio-review-complete-panel' }, (panel) => {
      panel.createEl('h5', { text: 'Finish Review' });
      if (lastReview) {
        panel.createEl('p', { cls: 'aio-review-last', text: `Last review: ${lastReview}` });
      }
      const completeBtn = panel.createEl('button', { cls: 'mod-cta aio-review-complete-btn' });
      setIcon(completeBtn, 'check');
      completeBtn.createSpan({ text: 'Mark review complete' });
      completeBtn.addEventListener('click', async () => {
        await this.recordReviewCompletion();
        new Notice('Weekly review recorded.');
        await this.refresh();
      });
    });
  }

  private renderReviewTask(container: HTMLElement, task: Task, includeActions: boolean): void {
    container.createEl('div', { cls: 'aio-review-task' }, (row) => {
      row.createEl('div', { cls: 'aio-review-task-main' }, (main) => {
        main.createEl('span', { cls: 'aio-review-task-title', text: task.title });
        const meta = [task.id, task.due ? `due ${task.due}` : '', task.project || '']
          .filter(Boolean)
          .join(' · ');
        main.createEl('span', { cls: 'aio-review-task-meta', text: meta });
      });

      if (!includeActions) {
        return;
      }

      const actions = row.createEl('div', { cls: 'aio-review-task-actions' });
      this.addStatusAction(actions, task, 'next', 'Start');
      this.addStatusAction(actions, task, 'someday', 'Defer');
      this.addStatusAction(actions, task, 'completed', 'Done');
    });
  }

  private addStatusAction(
    container: HTMLElement,
    task: Task,
    status: TaskStatus,
    label: string
  ): void {
    const button = container.createEl('button', { text: label });
    if (this.plugin.isReadOnly) {
      button.addClass('aio-disabled');
      return;
    }

    button.addEventListener('click', async () => {
      try {
        if (status === 'completed') {
          await this.plugin.taskService.completeTask(task.id);
        } else {
          await this.plugin.taskService.changeStatus(task.id, status);
        }
        await this.refresh();
      } catch (e) {
        if (e instanceof DaemonOfflineError) {
          new Notice('Cannot update task: daemon is offline.');
        } else {
          new Notice(`Error: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
      }
    });
  }

  private renderNavigation(container: HTMLElement): void {
    container.createEl('div', { cls: 'aio-review-navigation' }, (nav) => {
      const prev = nav.createEl('button', { text: 'Back' });
      prev.disabled = this.currentStepIndex === 0;
      prev.addEventListener('click', async () => {
        this.currentStepIndex = Math.max(0, this.currentStepIndex - 1);
        await this.refresh();
      });

      const next = nav.createEl('button', {
        cls: 'mod-cta',
        text: this.currentStepIndex === REVIEW_STEPS.length - 1 ? 'Done' : 'Next',
      });
      next.addEventListener('click', async () => {
        if (this.currentStepIndex === REVIEW_STEPS.length - 1) {
          this.leaf.detach();
          return;
        }
        this.currentStepIndex = Math.min(REVIEW_STEPS.length - 1, this.currentStepIndex + 1);
        await this.refresh();
      });
    });
  }

  private async recordReviewCompletion(): Promise<void> {
    const dashboardPath = this.plugin.vaultService.getDashboardPath();
    await this.plugin.vaultService.ensureFolderExists(dashboardPath);

    const logPath = normalizePath(`${dashboardPath}/weekly-review-log.md`);
    const file = this.app.vault.getAbstractFileByPath(logPath);
    const line = `- ${new Date().toISOString()} weekly review completed`;

    if (file instanceof TFile) {
      const existing = await this.app.vault.read(file);
      await this.app.vault.modify(file, `${existing.trimEnd()}\n${line}\n`);
      return;
    }

    await this.app.vault.create(logPath, `# Weekly Review Log\n\n${line}\n`);
  }

  private async getLastReviewLine(): Promise<string | null> {
    const logPath = normalizePath(`${this.plugin.vaultService.getDashboardPath()}/weekly-review-log.md`);
    const file = this.app.vault.getAbstractFileByPath(logPath);
    if (!(file instanceof TFile)) {
      return null;
    }

    const content = await this.app.vault.read(file);
    const entries = content.split('\n').filter((line) => line.startsWith('- '));
    return entries.length > 0 ? entries[entries.length - 1].replace(/^- /, '') : null;
  }
}
