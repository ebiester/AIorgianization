import { App, PluginSettingTab, Setting } from 'obsidian';
import type AioPlugin from './main';
import { TaskStatus } from './types';

export class AioSettingTab extends PluginSettingTab {
  plugin: AioPlugin;

  constructor(app: App, plugin: AioPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    containerEl.createEl('h2', { text: 'AIorgianization Settings' });

    new Setting(containerEl)
      .setName('AIO Folder Path')
      .setDesc('Path to the AIO folder relative to vault root')
      .addText(text => text
        .setPlaceholder('AIO')
        .setValue(this.plugin.settings.aioFolderPath)
        .onChange(async (value) => {
          this.plugin.settings.aioFolderPath = value || 'AIO';
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Default Status')
      .setDesc('Default status for new tasks')
      .addDropdown(dropdown => dropdown
        .addOption('inbox', 'Inbox')
        .addOption('next', 'Next')
        .addOption('scheduled', 'Scheduled')
        .addOption('someday', 'Someday')
        .setValue(this.plugin.settings.defaultStatus)
        .onChange(async (value) => {
          this.plugin.settings.defaultStatus = value as TaskStatus;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Date Format')
      .setDesc('Format for displaying dates')
      .addText(text => text
        .setPlaceholder('YYYY-MM-DD')
        .setValue(this.plugin.settings.dateFormat)
        .onChange(async (value) => {
          this.plugin.settings.dateFormat = value || 'YYYY-MM-DD';
          await this.plugin.saveSettings();
        }));
  }
}
