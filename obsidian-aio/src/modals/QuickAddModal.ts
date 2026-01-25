import { App, Modal, Notice, Setting } from 'obsidian';
import type AioPlugin from '../main';
import { parseDate, formatIsoDate, InvalidDateError } from '../utils/dates';
import { DaemonOfflineError } from '../services/DaemonClient';

export class QuickAddModal extends Modal {
  private plugin: AioPlugin;
  private title: string = '';
  private dueDate: string = '';
  private project: string = '';
  private onSubmit: () => void;

  constructor(app: App, plugin: AioPlugin, onSubmit: () => void) {
    super(app);
    this.plugin = plugin;
    this.onSubmit = onSubmit;
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('aio-quick-add-modal');

    contentEl.createEl('h2', { text: 'Quick Add Task' });

    // Show read-only warning if daemon is offline
    const isReadOnly = this.plugin.isReadOnly;
    if (isReadOnly) {
      contentEl.createEl('div', {
        cls: 'aio-readonly-banner',
        text: 'Daemon offline - cannot create tasks. Run "aio daemon start" to enable writes.',
      });
    }

    // Title input (autofocus)
    new Setting(contentEl)
      .setName('Title')
      .setDesc('Task title (required)')
      .addText(text => {
        text
          .setPlaceholder('What needs to be done?')
          .setValue(this.title)
          .onChange((value) => {
            this.title = value;
          });
        text.inputEl.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.submit();
          }
        });
        // Autofocus
        setTimeout(() => text.inputEl.focus(), 10);
      });

    // Due date input
    new Setting(contentEl)
      .setName('Due Date')
      .setDesc('Optional: YYYY-MM-DD or natural language (tomorrow, next friday)')
      .addText(text => text
        .setPlaceholder('tomorrow')
        .setValue(this.dueDate)
        .onChange((value) => {
          this.dueDate = value;
        }));

    // Project selector
    new Setting(contentEl)
      .setName('Project')
      .setDesc('Optional: Link to a project')
      .addDropdown(async (dropdown) => {
        dropdown.addOption('', '(None)');

        const projects = await this.plugin.vaultService.getProjects();
        for (const project of projects) {
          dropdown.addOption(project, project);
        }

        dropdown.setValue(this.project);
        dropdown.onChange((value) => {
          this.project = value;
        });
      });

    // Buttons
    const buttonContainer = contentEl.createEl('div', { cls: 'aio-modal-buttons' });

    const cancelBtn = buttonContainer.createEl('button', { text: 'Cancel' });
    cancelBtn.addEventListener('click', () => {
      this.close();
    });

    const submitBtn = buttonContainer.createEl('button', { cls: 'mod-cta', text: 'Add Task' });
    if (isReadOnly) {
      submitBtn.disabled = true;
      submitBtn.addClass('aio-disabled');
    } else {
      submitBtn.addEventListener('click', () => {
        this.submit();
      });
    }

    // Keyboard shortcut hint
    contentEl.createEl('div', {
      cls: 'aio-modal-hint',
      text: 'Press Enter to save, Esc to cancel',
    });
  }

  private async submit(): Promise<void> {
    if (!this.title.trim()) {
      return;
    }

    try {
      const options: { due?: string; project?: string } = {};

      if (this.dueDate) {
        try {
          const parsed = parseDate(this.dueDate);
          options.due = formatIsoDate(parsed);
        } catch (e) {
          if (e instanceof InvalidDateError) {
            new Notice(`Invalid date: ${this.dueDate}`);
            return;
          }
          throw e;
        }
      }

      if (this.project) {
        options.project = `[[Projects/${this.project}]]`;
      }

      await this.plugin.taskService.createTask(this.title, options);
      this.onSubmit();
      this.close();
    } catch (e) {
      if (e instanceof DaemonOfflineError) {
        new Notice('Cannot create task: daemon is offline. Run "aio daemon start" to enable writes.');
      } else {
        console.error('Error creating task:', e);
        new Notice(`Error creating task: ${e instanceof Error ? e.message : 'Unknown error'}`);
      }
    }
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
