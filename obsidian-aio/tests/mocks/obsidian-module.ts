/**
 * Mock module for 'obsidian' package.
 * This file is aliased in vitest.config.ts to replace the real obsidian module.
 */

export { MockApp as App, MockTFile as TFile, MockTFolder as TFolder, normalizePath } from './obsidian';

// Re-export the mock classes under their original names
import { MockApp, MockTFile, MockTFolder, MockVault, MockFileManager, normalizePath } from './obsidian';

// Additional exports that obsidian module might have
export class Plugin {
  app: MockApp;
  manifest: { id: string; name: string; version: string };

  constructor(app: MockApp, manifest: { id: string; name: string; version: string }) {
    this.app = app;
    this.manifest = manifest;
  }

  loadData(): Promise<unknown> {
    return Promise.resolve({});
  }

  saveData(_data: unknown): Promise<void> {
    return Promise.resolve();
  }
}

export class PluginSettingTab {
  app: MockApp;
  plugin: Plugin;
  containerEl: HTMLElement;

  constructor(app: MockApp, plugin: Plugin) {
    this.app = app;
    this.plugin = plugin;
    this.containerEl = document.createElement('div');
  }

  display(): void {}
  hide(): void {}
}

export class Notice {
  constructor(_message: string, _timeout?: number) {}
}

export class Modal {
  app: MockApp;
  contentEl: HTMLElement;

  constructor(app: MockApp) {
    this.app = app;
    this.contentEl = document.createElement('div');
  }

  open(): void {}
  close(): void {}
}

export class Setting {
  settingEl: HTMLElement;
  infoEl: HTMLElement;
  nameEl: HTMLElement;
  descEl: HTMLElement;
  controlEl: HTMLElement;

  constructor(_containerEl: HTMLElement) {
    this.settingEl = document.createElement('div');
    this.infoEl = document.createElement('div');
    this.nameEl = document.createElement('div');
    this.descEl = document.createElement('div');
    this.controlEl = document.createElement('div');
  }

  setName(_name: string): this {
    return this;
  }

  setDesc(_desc: string): this {
    return this;
  }

  addText(_cb: (component: unknown) => unknown): this {
    return this;
  }

  addToggle(_cb: (component: unknown) => unknown): this {
    return this;
  }

  addDropdown(_cb: (component: unknown) => unknown): this {
    return this;
  }

  addButton(_cb: (component: unknown) => unknown): this {
    return this;
  }
}

// Export types that might be used
export type { MockApp, MockTFile, MockTFolder, MockVault, MockFileManager };
