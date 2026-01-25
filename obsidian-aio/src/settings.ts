import { App, PluginSettingTab, Setting, Notice } from 'obsidian';
import type AioPlugin from './main';
import { TaskStatus } from './types';
import { DaemonClient } from './services/DaemonClient';

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

    // ----- General Settings -----
    containerEl.createEl('h3', { text: 'General' });

    new Setting(containerEl)
      .setName('AIO Folder Path')
      .setDesc('Path to the AIO folder relative to vault root. Change this if you move your vault or want to use a different folder structure.')
      .addText(text => text
        .setPlaceholder('AIO')
        .setValue(this.plugin.settings.aioFolderPath)
        .onChange(async (value) => {
          this.plugin.settings.aioFolderPath = value || 'AIO';
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Default Status')
      .setDesc('Default status for new tasks created via Quick Add')
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
      .setDesc('Format for displaying dates (uses moment.js format)')
      .addText(text => text
        .setPlaceholder('YYYY-MM-DD')
        .setValue(this.plugin.settings.dateFormat)
        .onChange(async (value) => {
          this.plugin.settings.dateFormat = value || 'YYYY-MM-DD';
          await this.plugin.saveSettings();
        }));

    // ----- Daemon Settings -----
    containerEl.createEl('h3', { text: 'Daemon Connection' });

    containerEl.createEl('p', {
      text: 'The AIO daemon provides fast task operations and synchronization across CLI, Cursor, and Obsidian. When connected, all changes go through the daemon for consistency.',
      cls: 'setting-item-description'
    });

    new Setting(containerEl)
      .setName('Enable Daemon Mode')
      .setDesc('Use the AIO daemon for task operations. When disabled or daemon unavailable, falls back to direct file access (read-only for mutations).')
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.useDaemon)
        .onChange(async (value) => {
          this.plugin.settings.useDaemon = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName('Daemon URL')
      .setDesc('URL of the AIO daemon HTTP API')
      .addText(text => text
        .setPlaceholder('http://localhost:7432')
        .setValue(this.plugin.settings.daemonUrl)
        .onChange(async (value) => {
          this.plugin.settings.daemonUrl = value || 'http://localhost:7432';
          await this.plugin.saveSettings();
        }));

    // Connection status and test button
    const statusSetting = new Setting(containerEl)
      .setName('Connection Status')
      .setDesc('Test the connection to the AIO daemon');

    const statusEl = statusSetting.descEl.createEl('span', { cls: 'aio-connection-status' });
    this.updateConnectionStatus(statusEl);

    statusSetting.addButton(button => button
      .setButtonText('Test Connection')
      .onClick(async () => {
        button.setButtonText('Testing...');
        button.setDisabled(true);

        try {
          const client = new DaemonClient(this.plugin.settings);
          const connected = await client.testConnection();

          if (connected) {
            const health = client.lastHealthCheck;
            new Notice(`Connected to AIO daemon v${health?.version || 'unknown'}`);
            statusEl.setText(`Connected (${health?.cache.task_count || 0} tasks)`);
            statusEl.removeClass('aio-status-error');
            statusEl.addClass('aio-status-ok');
          } else {
            new Notice('Failed to connect to daemon');
            statusEl.setText('Not connected');
            statusEl.removeClass('aio-status-ok');
            statusEl.addClass('aio-status-error');
          }
        } catch (e) {
          new Notice(`Connection error: ${e instanceof Error ? e.message : 'Unknown error'}`);
          statusEl.setText('Error');
          statusEl.removeClass('aio-status-ok');
          statusEl.addClass('aio-status-error');
        } finally {
          button.setButtonText('Test Connection');
          button.setDisabled(false);
        }
      }));

    // ----- Hotkeys Section -----
    containerEl.createEl('h3', { text: 'Hotkeys' });

    containerEl.createEl('p', {
      text: 'Configure keyboard shortcuts for AIO commands. Click the button below to open Obsidian\'s hotkey settings filtered to AIO commands.',
      cls: 'setting-item-description'
    });

    new Setting(containerEl)
      .setName('Configure Hotkeys')
      .setDesc('Open Obsidian hotkey settings for AIO commands')
      .addButton(button => button
        .setButtonText('Open Hotkey Settings')
        .onClick(() => {
          // Open Obsidian settings and navigate to hotkeys tab
          // @ts-ignore - accessing internal API to open settings
          this.app.setting.open();
          // @ts-ignore - accessing internal API to switch tabs
          this.app.setting.openTabById('hotkeys');
          // Focus the search and filter to AIO
          setTimeout(() => {
            const searchEl = document.querySelector('.hotkey-search-container input') as HTMLInputElement;
            if (searchEl) {
              searchEl.value = 'AIO:';
              searchEl.dispatchEvent(new Event('input'));
            }
          }, 100);
        }));

    // Show available commands
    containerEl.createEl('h4', { text: 'Available Commands' });

    const commandList = containerEl.createEl('div', { cls: 'aio-command-list' });

    const commands = [
      { id: 'aio-add-task', name: 'Add task', desc: 'Open Quick Add modal to create a new task' },
      { id: 'aio-open-tasks', name: 'Open tasks', desc: 'Open the task list view in sidebar' },
      { id: 'aio-open-inbox', name: 'Open inbox', desc: 'Open the inbox processing view' },
      { id: 'aio-complete-task', name: 'Complete current task', desc: 'Mark the currently open task as completed' },
      { id: 'aio-start-task', name: 'Start current task', desc: 'Move the current task to Next status' },
      { id: 'aio-defer-task', name: 'Defer current task', desc: 'Move the current task to Someday status' },
      { id: 'aio-wait-task', name: 'Wait on current task', desc: 'Move the current task to Waiting status' },
      { id: 'aio-schedule-task', name: 'Schedule current task', desc: 'Move the current task to Scheduled status' },
    ];

    for (const cmd of commands) {
      const hotkey = this.getHotkeyForCommand(`aio:${cmd.id}`);

      new Setting(commandList)
        .setName(cmd.name)
        .setDesc(cmd.desc)
        .addExtraButton(button => button
          .setIcon('keyboard-glyph')
          .setTooltip(hotkey ? `Current: ${hotkey}` : 'No hotkey assigned')
          .onClick(() => {
            // @ts-ignore
            this.app.setting.open();
            // @ts-ignore
            this.app.setting.openTabById('hotkeys');
            setTimeout(() => {
              const searchEl = document.querySelector('.hotkey-search-container input') as HTMLInputElement;
              if (searchEl) {
                searchEl.value = `AIO: ${cmd.name}`;
                searchEl.dispatchEvent(new Event('input'));
              }
            }, 100);
          }));
    }

    // Add some styling
    const style = containerEl.createEl('style');
    style.textContent = `
      .aio-command-list .setting-item {
        border-bottom: 1px solid var(--background-modifier-border);
        padding: 8px 0;
      }
      .aio-command-list .setting-item:last-child {
        border-bottom: none;
      }
      .aio-command-list .setting-item-name {
        font-weight: 500;
      }
      .aio-connection-status {
        display: inline-block;
        margin-left: 8px;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        background: var(--background-modifier-border);
      }
      .aio-status-ok {
        background: var(--background-modifier-success);
        color: var(--text-success);
      }
      .aio-status-error {
        background: var(--background-modifier-error);
        color: var(--text-error);
      }
    `;
  }

  /**
   * Update the connection status display.
   */
  private async updateConnectionStatus(statusEl: HTMLElement): Promise<void> {
    if (!this.plugin.settings.useDaemon) {
      statusEl.setText('Daemon mode disabled');
      statusEl.removeClass('aio-status-ok', 'aio-status-error');
      return;
    }

    const connected = this.plugin.taskService.isDaemonConnected;
    if (connected) {
      const health = this.plugin.taskService.daemon.lastHealthCheck;
      statusEl.setText(`Connected (${health?.cache.task_count || 0} tasks)`);
      statusEl.removeClass('aio-status-error');
      statusEl.addClass('aio-status-ok');
    } else {
      statusEl.setText('Not connected');
      statusEl.removeClass('aio-status-ok');
      statusEl.addClass('aio-status-error');
    }
  }

  /**
   * Get the hotkey string for a command ID.
   */
  private getHotkeyForCommand(commandId: string): string | null {
    // @ts-ignore - accessing internal API
    const customKeys = this.app.hotkeyManager?.customKeys || {};
    const hotkeys = customKeys[commandId];

    if (hotkeys && hotkeys.length > 0) {
      const hk = hotkeys[0];
      const parts: string[] = [];
      if (hk.modifiers.includes('Mod')) parts.push('Cmd/Ctrl');
      if (hk.modifiers.includes('Ctrl')) parts.push('Ctrl');
      if (hk.modifiers.includes('Alt')) parts.push('Alt');
      if (hk.modifiers.includes('Shift')) parts.push('Shift');
      parts.push(hk.key);
      return parts.join('+');
    }

    return null;
  }
}
