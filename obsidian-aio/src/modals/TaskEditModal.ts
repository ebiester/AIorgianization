import { App, Modal, Setting } from 'obsidian';
import type AioPlugin from '../main';
import { Task, TaskStatus } from '../types';

export class TaskEditModal extends Modal {
  private plugin: AioPlugin;
  private task: Task;
  private onSubmit: () => void;

  // Form state
  private title: string;
  private status: TaskStatus;
  private dueDate: string;
  private project: string;
  private assignedTo: string;
  private waitingOn: string;
  private timeEstimate: string;
  private tags: string;

  constructor(app: App, plugin: AioPlugin, task: Task, onSubmit: () => void) {
    super(app);
    this.plugin = plugin;
    this.task = task;
    this.onSubmit = onSubmit;

    // Initialize form state from task
    this.title = task.title;
    this.status = task.status;
    this.dueDate = task.due || '';
    this.project = task.project?.replace(/^\[\[Projects\//, '').replace(/\]\]$/, '') || '';
    this.assignedTo = task.assignedTo?.replace(/^\[\[People\//, '').replace(/\]\]$/, '') || '';
    this.waitingOn = task.waitingOn || '';
    this.timeEstimate = task.timeEstimate || '';
    this.tags = task.tags.join(', ');
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass('aio-task-edit-modal');

    contentEl.createEl('h2', { text: 'Edit Task' });

    // Task ID (read-only)
    contentEl.createEl('div', { cls: 'aio-task-id-display', text: `ID: ${this.task.id}` });

    // Title
    new Setting(contentEl)
      .setName('Title')
      .addText(text => text
        .setValue(this.title)
        .onChange((value) => {
          this.title = value;
        }));

    // Status
    new Setting(contentEl)
      .setName('Status')
      .addDropdown(dropdown => dropdown
        .addOption('inbox', 'Inbox')
        .addOption('next', 'Next')
        .addOption('waiting', 'Waiting')
        .addOption('scheduled', 'Scheduled')
        .addOption('someday', 'Someday')
        .addOption('completed', 'Completed')
        .setValue(this.status)
        .onChange((value) => {
          this.status = value as TaskStatus;
        }));

    // Due Date
    new Setting(contentEl)
      .setName('Due Date')
      .setDesc('YYYY-MM-DD format')
      .addText(text => text
        .setPlaceholder('YYYY-MM-DD')
        .setValue(this.dueDate)
        .onChange((value) => {
          this.dueDate = value;
        }));

    // Project
    new Setting(contentEl)
      .setName('Project')
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

    // Assigned To
    new Setting(contentEl)
      .setName('Assigned To')
      .addDropdown(async (dropdown) => {
        dropdown.addOption('', '(None)');

        const people = await this.plugin.vaultService.getPeople();
        for (const person of people) {
          dropdown.addOption(person, person);
        }

        dropdown.setValue(this.assignedTo);
        dropdown.onChange((value) => {
          this.assignedTo = value;
        });
      });

    // Waiting On
    new Setting(contentEl)
      .setName('Waiting On')
      .setDesc('Person or thing you are waiting for')
      .addText(text => text
        .setValue(this.waitingOn)
        .onChange((value) => {
          this.waitingOn = value;
        }));

    // Time Estimate
    new Setting(contentEl)
      .setName('Time Estimate')
      .setDesc('e.g., 30m, 2h, 1d')
      .addText(text => text
        .setPlaceholder('2h')
        .setValue(this.timeEstimate)
        .onChange((value) => {
          this.timeEstimate = value;
        }));

    // Tags
    new Setting(contentEl)
      .setName('Tags')
      .setDesc('Comma-separated list')
      .addText(text => text
        .setPlaceholder('backend, urgent')
        .setValue(this.tags)
        .onChange((value) => {
          this.tags = value;
        }));

    // Buttons
    const buttonContainer = contentEl.createEl('div', { cls: 'aio-modal-buttons' });

    const cancelBtn = buttonContainer.createEl('button', { text: 'Cancel' });
    cancelBtn.addEventListener('click', () => {
      this.close();
    });

    const saveBtn = buttonContainer.createEl('button', { cls: 'mod-cta', text: 'Save' });
    saveBtn.addEventListener('click', () => {
      this.save();
    });

    // Delete button (with confirmation)
    const deleteBtn = buttonContainer.createEl('button', { cls: 'mod-warning', text: 'Delete' });
    deleteBtn.addEventListener('click', async () => {
      if (confirm(`Are you sure you want to delete "${this.task.title}"?`)) {
        const file = this.app.vault.getAbstractFileByPath(this.task.path);
        if (file) {
          await this.app.vault.delete(file);
          this.onSubmit();
          this.close();
        }
      }
    });
  }

  private async save(): Promise<void> {
    if (!this.title.trim()) {
      return;
    }

    try {
      // Update task fields
      this.task.title = this.title;
      this.task.due = this.dueDate || undefined;
      this.task.project = this.project ? `[[Projects/${this.project}]]` : undefined;
      this.task.assignedTo = this.assignedTo ? `[[People/${this.assignedTo}]]` : undefined;
      this.task.waitingOn = this.waitingOn || undefined;
      this.task.timeEstimate = this.timeEstimate || undefined;
      this.task.tags = this.tags
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);

      // Update content with new title
      this.task.content = this.task.content.replace(/^#\s+.+$/m, `# ${this.title}`);

      // Check if status changed
      if (this.status !== this.task.status) {
        // Save first, then change status (which moves the file)
        await this.plugin.taskService.updateTask(this.task);
        await this.plugin.taskService.changeStatus(this.task.id, this.status);
      } else {
        await this.plugin.taskService.updateTask(this.task);
      }

      this.onSubmit();
      this.close();
    } catch (e) {
      console.error('Error saving task:', e);
    }
  }

  onClose(): void {
    const { contentEl } = this;
    contentEl.empty();
  }
}
