var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => AioPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian9 = require("obsidian");

// src/types.ts
var DEFAULT_SETTINGS = {
  aioFolderPath: "AIO",
  defaultStatus: "inbox",
  dateFormat: "YYYY-MM-DD",
  daemonUrl: "http://localhost:7432",
  useDaemon: true
};
var STATUS_FOLDERS = {
  inbox: "Inbox",
  next: "Next",
  waiting: "Waiting",
  scheduled: "Scheduled",
  someday: "Someday",
  completed: "Completed"
};
var ID_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ";

// src/settings.ts
var import_obsidian2 = require("obsidian");

// src/services/DaemonClient.ts
var import_obsidian = require("obsidian");
var DaemonUnavailableError = class extends Error {
  constructor(message = "Daemon is not available") {
    super(message);
    this.name = "DaemonUnavailableError";
  }
};
var DaemonOfflineError = class extends Error {
  constructor(operation = "operation") {
    super(`Cannot ${operation}: daemon is offline. Start the daemon with 'aio daemon start' or disable daemon mode in settings.`);
    this.name = "DaemonOfflineError";
  }
};
var DaemonApiError = class extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
    this.name = "DaemonApiError";
  }
};
var DaemonClient = class {
  constructor(settings) {
    this.settings = settings;
    this._isConnected = false;
    this._lastHealthCheck = null;
    this.baseUrl = settings.daemonUrl;
  }
  /**
   * Whether the daemon is currently connected.
   */
  get isConnected() {
    return this._isConnected;
  }
  /**
   * Last health check response.
   */
  get lastHealthCheck() {
    return this._lastHealthCheck;
  }
  /**
   * Update settings (e.g., when daemon URL changes).
   */
  updateSettings(settings) {
    this.baseUrl = settings.daemonUrl;
  }
  /**
   * Make an HTTP request to the daemon.
   */
  async request(method, path, body) {
    const url = `${this.baseUrl}/api/v1${path}`;
    const params = {
      url,
      method,
      headers: {
        "Content-Type": "application/json"
      }
    };
    if (body) {
      params.body = JSON.stringify(body);
    }
    try {
      const response = await (0, import_obsidian.requestUrl)(params);
      const data = response.json;
      if (!data.ok) {
        throw new DaemonApiError(data.error.code, data.error.message);
      }
      return data.data;
    } catch (e) {
      if (e instanceof DaemonApiError) {
        throw e;
      }
      this._isConnected = false;
      throw new DaemonUnavailableError(
        e instanceof Error ? e.message : "Failed to connect to daemon"
      );
    }
  }
  /**
   * Check if daemon is available.
   */
  async checkHealth() {
    try {
      const health = await this.request("GET", "/health");
      this._isConnected = true;
      this._lastHealthCheck = health;
      return health;
    } catch (e) {
      this._isConnected = false;
      this._lastHealthCheck = null;
      throw e;
    }
  }
  /**
   * Test connection to daemon.
   * Returns true if connected, false otherwise.
   */
  async testConnection() {
    try {
      await this.checkHealth();
      return true;
    } catch (e) {
      return false;
    }
  }
  // Task operations
  /**
   * List tasks with optional filtering.
   */
  async listTasks(status) {
    const path = status ? `/tasks?status=${status}` : "/tasks";
    const result = await this.request("GET", path);
    return result.tasks.map(this.daemonTaskToTask.bind(this));
  }
  /**
   * Get a single task by ID.
   */
  async getTask(id) {
    try {
      const result = await this.request("GET", `/tasks/${id}`);
      return this.daemonTaskToTask(result.task);
    } catch (e) {
      if (e instanceof DaemonApiError && e.code === "TASK_NOT_FOUND") {
        return null;
      }
      throw e;
    }
  }
  /**
   * Create a new task.
   */
  async createTask(title, options = {}) {
    const body = { title };
    if (options.due)
      body.due = options.due;
    if (options.project)
      body.project = options.project;
    if (options.status)
      body.status = options.status;
    if (options.tags)
      body.tags = options.tags;
    if (options.timeEstimate)
      body.time_estimate = options.timeEstimate;
    const result = await this.request("POST", "/tasks", body);
    return this.daemonTaskToTask(result.task);
  }
  /**
   * Complete a task.
   */
  async completeTask(id) {
    const result = await this.request("POST", `/tasks/${id}/complete`);
    return this.daemonTaskToTask(result.task);
  }
  /**
   * Start a task (move to Next).
   */
  async startTask(id) {
    const result = await this.request("POST", `/tasks/${id}/start`);
    return this.daemonTaskToTask(result.task);
  }
  /**
   * Defer a task (move to Someday).
   */
  async deferTask(id) {
    const result = await this.request("POST", `/tasks/${id}/defer`);
    return this.daemonTaskToTask(result.task);
  }
  /**
   * Delegate a task to a person (move to Waiting).
   */
  async delegateTask(id, person) {
    const result = await this.request(
      "POST",
      `/tasks/${id}/delegate`,
      { person }
    );
    return this.daemonTaskToTask(result.task);
  }
  // Project operations
  /**
   * List all projects.
   */
  async listProjects(status) {
    const path = status ? `/projects?status=${status}` : "/projects";
    const result = await this.request("GET", path);
    return result.projects;
  }
  /**
   * Get project names for dropdown.
   */
  async getProjectNames() {
    const projects = await this.listProjects("active");
    return projects.map((p) => p.title);
  }
  // People operations
  /**
   * List all people.
   */
  async listPeople() {
    const result = await this.request("GET", "/people");
    return result.people;
  }
  /**
   * Get people names for dropdown.
   */
  async getPeopleNames() {
    const people = await this.listPeople();
    return people.map((p) => p.name);
  }
  // Dashboard
  /**
   * Get dashboard content.
   */
  async getDashboard(date) {
    const path = date ? `/dashboard?date=${date}` : "/dashboard";
    return this.request("GET", path);
  }
  /**
   * Convert a daemon task response to a Task object.
   */
  daemonTaskToTask(dt) {
    return {
      id: dt.id,
      type: "task",
      status: dt.status,
      title: dt.title,
      due: dt.due,
      project: dt.project,
      assignedTo: dt.assigned_to,
      waitingOn: dt.waiting_on,
      blockedBy: [],
      blocks: [],
      tags: dt.tags || [],
      timeEstimate: dt.time_estimate,
      created: dt.created,
      updated: dt.updated,
      completed: dt.completed,
      content: "",
      path: ""
    };
  }
};

// src/settings.ts
var AioSettingTab = class extends import_obsidian2.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "AIorgianization Settings" });
    containerEl.createEl("h3", { text: "General" });
    new import_obsidian2.Setting(containerEl).setName("AIO Folder Path").setDesc("Path to the AIO folder relative to vault root. Change this if you move your vault or want to use a different folder structure.").addText((text) => text.setPlaceholder("AIO").setValue(this.plugin.settings.aioFolderPath).onChange(async (value) => {
      this.plugin.settings.aioFolderPath = value || "AIO";
      await this.plugin.saveSettings();
    }));
    new import_obsidian2.Setting(containerEl).setName("Default Status").setDesc("Default status for new tasks created via Quick Add").addDropdown((dropdown) => dropdown.addOption("inbox", "Inbox").addOption("next", "Next").addOption("scheduled", "Scheduled").addOption("someday", "Someday").setValue(this.plugin.settings.defaultStatus).onChange(async (value) => {
      this.plugin.settings.defaultStatus = value;
      await this.plugin.saveSettings();
    }));
    new import_obsidian2.Setting(containerEl).setName("Date Format").setDesc("Format for displaying dates (uses moment.js format)").addText((text) => text.setPlaceholder("YYYY-MM-DD").setValue(this.plugin.settings.dateFormat).onChange(async (value) => {
      this.plugin.settings.dateFormat = value || "YYYY-MM-DD";
      await this.plugin.saveSettings();
    }));
    containerEl.createEl("h3", { text: "Daemon Connection" });
    containerEl.createEl("p", {
      text: "The AIO daemon provides fast task operations and synchronization across CLI, Cursor, and Obsidian. When connected, all changes go through the daemon for consistency.",
      cls: "setting-item-description"
    });
    new import_obsidian2.Setting(containerEl).setName("Enable Daemon Mode").setDesc("Use the AIO daemon for task operations. When disabled or daemon unavailable, falls back to direct file access (read-only for mutations).").addToggle((toggle) => toggle.setValue(this.plugin.settings.useDaemon).onChange(async (value) => {
      this.plugin.settings.useDaemon = value;
      await this.plugin.saveSettings();
    }));
    new import_obsidian2.Setting(containerEl).setName("Daemon URL").setDesc("URL of the AIO daemon HTTP API").addText((text) => text.setPlaceholder("http://localhost:7432").setValue(this.plugin.settings.daemonUrl).onChange(async (value) => {
      this.plugin.settings.daemonUrl = value || "http://localhost:7432";
      await this.plugin.saveSettings();
    }));
    const statusSetting = new import_obsidian2.Setting(containerEl).setName("Connection Status").setDesc("Test the connection to the AIO daemon");
    const statusEl = statusSetting.descEl.createEl("span", { cls: "aio-connection-status" });
    this.updateConnectionStatus(statusEl);
    statusSetting.addButton((button) => button.setButtonText("Test Connection").onClick(async () => {
      button.setButtonText("Testing...");
      button.setDisabled(true);
      try {
        const client = new DaemonClient(this.plugin.settings);
        const connected = await client.testConnection();
        if (connected) {
          const health = client.lastHealthCheck;
          new import_obsidian2.Notice(`Connected to AIO daemon v${(health == null ? void 0 : health.version) || "unknown"}`);
          statusEl.setText(`Connected (${(health == null ? void 0 : health.cache.task_count) || 0} tasks)`);
          statusEl.removeClass("aio-status-error");
          statusEl.addClass("aio-status-ok");
        } else {
          new import_obsidian2.Notice("Failed to connect to daemon");
          statusEl.setText("Not connected");
          statusEl.removeClass("aio-status-ok");
          statusEl.addClass("aio-status-error");
        }
      } catch (e) {
        new import_obsidian2.Notice(`Connection error: ${e instanceof Error ? e.message : "Unknown error"}`);
        statusEl.setText("Error");
        statusEl.removeClass("aio-status-ok");
        statusEl.addClass("aio-status-error");
      } finally {
        button.setButtonText("Test Connection");
        button.setDisabled(false);
      }
    }));
    containerEl.createEl("h3", { text: "Hotkeys" });
    containerEl.createEl("p", {
      text: "Configure keyboard shortcuts for AIO commands. Click the button below to open Obsidian's hotkey settings filtered to AIO commands.",
      cls: "setting-item-description"
    });
    new import_obsidian2.Setting(containerEl).setName("Configure Hotkeys").setDesc("Open Obsidian hotkey settings for AIO commands").addButton((button) => button.setButtonText("Open Hotkey Settings").onClick(() => {
      this.app.setting.open();
      this.app.setting.openTabById("hotkeys");
      setTimeout(() => {
        const searchEl = document.querySelector(".hotkey-search-container input");
        if (searchEl) {
          searchEl.value = "AIO:";
          searchEl.dispatchEvent(new Event("input"));
        }
      }, 100);
    }));
    containerEl.createEl("h4", { text: "Available Commands" });
    const commandList = containerEl.createEl("div", { cls: "aio-command-list" });
    const commands = [
      { id: "aio-add-task", name: "Add task", desc: "Open Quick Add modal to create a new task" },
      { id: "aio-open-tasks", name: "Open tasks", desc: "Open the task list view in sidebar" },
      { id: "aio-open-inbox", name: "Open inbox", desc: "Open the inbox processing view" },
      { id: "aio-complete-task", name: "Complete current task", desc: "Mark the currently open task as completed" },
      { id: "aio-start-task", name: "Start current task", desc: "Move the current task to Next status" },
      { id: "aio-defer-task", name: "Defer current task", desc: "Move the current task to Someday status" },
      { id: "aio-wait-task", name: "Wait on current task", desc: "Move the current task to Waiting status" },
      { id: "aio-schedule-task", name: "Schedule current task", desc: "Move the current task to Scheduled status" }
    ];
    for (const cmd of commands) {
      const hotkey = this.getHotkeyForCommand(`aio:${cmd.id}`);
      new import_obsidian2.Setting(commandList).setName(cmd.name).setDesc(cmd.desc).addExtraButton((button) => button.setIcon("keyboard-glyph").setTooltip(hotkey ? `Current: ${hotkey}` : "No hotkey assigned").onClick(() => {
        this.app.setting.open();
        this.app.setting.openTabById("hotkeys");
        setTimeout(() => {
          const searchEl = document.querySelector(".hotkey-search-container input");
          if (searchEl) {
            searchEl.value = `AIO: ${cmd.name}`;
            searchEl.dispatchEvent(new Event("input"));
          }
        }, 100);
      }));
    }
    const style = containerEl.createEl("style");
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
  async updateConnectionStatus(statusEl) {
    if (!this.plugin.settings.useDaemon) {
      statusEl.setText("Daemon mode disabled");
      statusEl.removeClass("aio-status-ok", "aio-status-error");
      return;
    }
    const connected = this.plugin.taskService.isDaemonConnected;
    if (connected) {
      const health = this.plugin.taskService.daemon.lastHealthCheck;
      statusEl.setText(`Connected (${(health == null ? void 0 : health.cache.task_count) || 0} tasks)`);
      statusEl.removeClass("aio-status-error");
      statusEl.addClass("aio-status-ok");
    } else {
      statusEl.setText("Not connected");
      statusEl.removeClass("aio-status-ok");
      statusEl.addClass("aio-status-error");
    }
  }
  /**
   * Get the hotkey string for a command ID.
   */
  getHotkeyForCommand(commandId) {
    var _a;
    const customKeys = ((_a = this.app.hotkeyManager) == null ? void 0 : _a.customKeys) || {};
    const hotkeys = customKeys[commandId];
    if (hotkeys && hotkeys.length > 0) {
      const hk = hotkeys[0];
      const parts = [];
      if (hk.modifiers.includes("Mod"))
        parts.push("Cmd/Ctrl");
      if (hk.modifiers.includes("Ctrl"))
        parts.push("Ctrl");
      if (hk.modifiers.includes("Alt"))
        parts.push("Alt");
      if (hk.modifiers.includes("Shift"))
        parts.push("Shift");
      parts.push(hk.key);
      return parts.join("+");
    }
    return null;
  }
};

// src/services/VaultService.ts
var import_obsidian3 = require("obsidian");
var VaultService = class {
  constructor(app, settings) {
    this.app = app;
    this.settings = settings;
  }
  /**
   * Get the base AIO folder path.
   */
  getAioPath() {
    return this.settings.aioFolderPath;
  }
  /**
   * Get the Tasks folder path.
   */
  getTasksPath() {
    return (0, import_obsidian3.normalizePath)(`${this.getAioPath()}/Tasks`);
  }
  /**
   * Get the folder path for a specific task status.
   */
  getStatusPath(status) {
    const folder = STATUS_FOLDERS[status];
    return (0, import_obsidian3.normalizePath)(`${this.getTasksPath()}/${folder}`);
  }
  /**
   * Get the completed tasks folder path for a specific year/month.
   */
  getCompletedPath(year, month) {
    const monthStr = month.toString().padStart(2, "0");
    return (0, import_obsidian3.normalizePath)(`${this.getTasksPath()}/Completed/${year}/${monthStr}`);
  }
  /**
   * Get the Projects folder path.
   */
  getProjectsPath() {
    return (0, import_obsidian3.normalizePath)(`${this.getAioPath()}/Projects`);
  }
  /**
   * Get the People folder path.
   */
  getPeoplePath() {
    return (0, import_obsidian3.normalizePath)(`${this.getAioPath()}/People`);
  }
  /**
   * Get the Dashboard folder path.
   */
  getDashboardPath() {
    return (0, import_obsidian3.normalizePath)(`${this.getAioPath()}/Dashboard`);
  }
  /**
   * Get the Archive folder path.
   */
  getArchivePath() {
    return (0, import_obsidian3.normalizePath)(`${this.getAioPath()}/Archive`);
  }
  /**
   * Ensure a folder exists, creating it if necessary.
   */
  async ensureFolderExists(path) {
    const normalizedPath = (0, import_obsidian3.normalizePath)(path);
    const folder = this.app.vault.getAbstractFileByPath(normalizedPath);
    if (!folder) {
      try {
        await this.app.vault.createFolder(normalizedPath);
      } catch (e) {
        if (e instanceof Error && !e.message.includes("Folder already exists")) {
          throw e;
        }
      }
    } else if (!(folder instanceof import_obsidian3.TFolder)) {
      throw new Error(`Path exists but is not a folder: ${normalizedPath}`);
    }
  }
  /**
   * Ensure the AIO folder structure exists.
   */
  async ensureAioStructure() {
    await this.ensureFolderExists(this.getAioPath());
    await this.ensureFolderExists(this.getTasksPath());
    await this.ensureFolderExists(this.getProjectsPath());
    await this.ensureFolderExists(this.getPeoplePath());
    await this.ensureFolderExists(this.getDashboardPath());
    await this.ensureFolderExists(this.getArchivePath());
    for (const status of Object.keys(STATUS_FOLDERS)) {
      if (status === "completed") {
        await this.ensureFolderExists((0, import_obsidian3.normalizePath)(`${this.getTasksPath()}/Completed`));
      } else {
        await this.ensureFolderExists(this.getStatusPath(status));
      }
    }
  }
  /**
   * Generate a filename for a task.
   */
  generateTaskFilename(title, date = /* @__PURE__ */ new Date()) {
    const dateStr = date.toISOString().split("T")[0];
    const slug = this.slugify(title);
    return `${dateStr}-${slug}.md`;
  }
  /**
   * Convert a title to a URL-friendly slug.
   */
  slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").substring(0, 50);
  }
  /**
   * Get all project names from the Projects folder.
   */
  async getProjects() {
    const projectsPath = this.getProjectsPath();
    const folder = this.app.vault.getAbstractFileByPath(projectsPath);
    if (!(folder instanceof import_obsidian3.TFolder)) {
      return [];
    }
    return folder.children.filter((f) => f.name.endsWith(".md")).map((f) => f.name.replace(".md", ""));
  }
  /**
   * Get all people names from the People folder.
   */
  async getPeople() {
    const peoplePath = this.getPeoplePath();
    const folder = this.app.vault.getAbstractFileByPath(peoplePath);
    if (!(folder instanceof import_obsidian3.TFolder)) {
      return [];
    }
    return folder.children.filter((f) => f.name.endsWith(".md")).map((f) => f.name.replace(".md", ""));
  }
};

// src/services/TaskService.ts
var import_obsidian4 = require("obsidian");
var TaskService = class {
  constructor(app, settings) {
    this.app = app;
    this.settings = settings;
    this.vaultService = new VaultService(app, settings);
    this.daemonClient = new DaemonClient(settings);
    this._useDaemon = settings.useDaemon;
  }
  /**
   * Whether daemon mode is enabled and connected.
   */
  get isDaemonConnected() {
    return this._useDaemon && this.daemonClient.isConnected;
  }
  /**
   * Whether the plugin is in read-only mode.
   * Read-only when daemon mode is enabled but daemon is not connected.
   */
  get isReadOnly() {
    return this._useDaemon && !this.daemonClient.isConnected;
  }
  /**
   * Get the daemon client (for status checks).
   */
  get daemon() {
    return this.daemonClient;
  }
  /**
   * Update settings and reconnect if needed.
   */
  updateSettings(settings) {
    this.settings = settings;
    this._useDaemon = settings.useDaemon;
    this.daemonClient.updateSettings(settings);
    this.vaultService = new VaultService(this.app, settings);
  }
  /**
   * Check daemon connection and update status.
   */
  async checkDaemonConnection() {
    if (!this._useDaemon) {
      return false;
    }
    return this.daemonClient.testConnection();
  }
  /**
   * Generate a unique 4-character task ID.
   */
  generateId() {
    let id = "";
    for (let i = 0; i < 4; i++) {
      const index = Math.floor(Math.random() * ID_CHARS.length);
      id += ID_CHARS[index];
    }
    return id;
  }
  /**
   * Generate a unique ID that doesn't collide with existing tasks.
   */
  async generateUniqueId() {
    const existingIds = /* @__PURE__ */ new Set();
    const tasks = await this.listTasks();
    tasks.forEach((t) => existingIds.add(t.id.toUpperCase()));
    let attempts = 0;
    while (attempts < 100) {
      const id = this.generateId();
      if (!existingIds.has(id.toUpperCase())) {
        return id;
      }
      attempts++;
    }
    throw new Error("Failed to generate unique ID after 100 attempts");
  }
  /**
   * List all tasks, optionally filtered by status.
   */
  async listTasks(status) {
    if (this._useDaemon) {
      try {
        return await this.daemonClient.listTasks(status);
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
      }
    }
    return this.listTasksFromFiles(status);
  }
  /**
   * List tasks from files (fallback mode).
   */
  async listTasksFromFiles(status) {
    const tasks = [];
    const statuses = status ? [status] : ["inbox", "next", "waiting", "scheduled", "someday", "completed"];
    for (const s of statuses) {
      const folderPath = this.vaultService.getStatusPath(s);
      const statusTasks = await this.getTasksFromFolder(folderPath);
      tasks.push(...statusTasks);
    }
    return tasks;
  }
  /**
   * Get all task files from a folder recursively.
   */
  async getTasksFromFolder(folderPath) {
    const tasks = [];
    const folder = this.app.vault.getAbstractFileByPath(folderPath);
    if (!(folder instanceof import_obsidian4.TFolder)) {
      return tasks;
    }
    const files = this.getAllMarkdownFiles(folder);
    for (const file of files) {
      try {
        const task = await this.parseTaskFile(file);
        if (task) {
          tasks.push(task);
        }
      } catch (e) {
        console.error(`Error parsing task file ${file.path}:`, e);
      }
    }
    return tasks;
  }
  /**
   * Recursively get all markdown files from a folder.
   */
  getAllMarkdownFiles(folder) {
    const files = [];
    for (const child of folder.children) {
      if (child instanceof import_obsidian4.TFile && child.extension === "md") {
        files.push(child);
      } else if (child instanceof import_obsidian4.TFolder) {
        files.push(...this.getAllMarkdownFiles(child));
      }
    }
    return files;
  }
  /**
   * Parse a task file into a Task object.
   */
  async parseTaskFile(file) {
    const content = await this.app.vault.read(file);
    const { frontmatter, body } = this.parseFrontmatter(content);
    if (frontmatter.type !== "task") {
      return null;
    }
    let title = frontmatter.title || "";
    if (!title) {
      const headingMatch = body.match(/^#\s+(.+)$/m);
      if (headingMatch) {
        title = headingMatch[1];
      } else {
        title = file.basename;
      }
    }
    return {
      id: frontmatter.id || "",
      type: "task",
      status: frontmatter.status || "inbox",
      title,
      due: frontmatter.due,
      project: frontmatter.project,
      assignedTo: frontmatter.assignedTo,
      waitingOn: frontmatter.waitingOn,
      blockedBy: frontmatter.blockedBy || [],
      blocks: frontmatter.blocks || [],
      location: frontmatter.location,
      tags: frontmatter.tags || [],
      timeEstimate: frontmatter.timeEstimate,
      created: frontmatter.created || (/* @__PURE__ */ new Date()).toISOString(),
      updated: frontmatter.updated || (/* @__PURE__ */ new Date()).toISOString(),
      completed: frontmatter.completed,
      content: body,
      path: file.path
    };
  }
  /**
   * Parse YAML frontmatter from markdown content.
   */
  parseFrontmatter(content) {
    const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
    if (!match) {
      return { frontmatter: {}, body: content };
    }
    const yamlStr = match[1];
    const body = match[2];
    try {
      const frontmatter = this.parseYaml(yamlStr);
      return { frontmatter, body };
    } catch (e) {
      return { frontmatter: {}, body: content };
    }
  }
  /**
   * Simple YAML parser for frontmatter.
   */
  parseYaml(yamlStr) {
    const result = {};
    const lines = yamlStr.split("\n");
    let currentKey = "";
    let inArray = false;
    let arrayValue = [];
    for (const line of lines) {
      if (line.match(/^\s+-\s+/)) {
        const value = line.replace(/^\s+-\s+/, "").trim();
        arrayValue.push(this.parseValue(value));
        continue;
      }
      if (inArray && currentKey) {
        result[currentKey] = arrayValue;
        inArray = false;
        arrayValue = [];
      }
      const kvMatch = line.match(/^(\w+):\s*(.*)$/);
      if (kvMatch) {
        const key = kvMatch[1];
        const value = kvMatch[2].trim();
        if (value === "" || value === "[]") {
          currentKey = key;
          inArray = true;
          arrayValue = [];
          if (value === "[]") {
            result[key] = [];
            inArray = false;
          }
        } else {
          result[key] = this.parseValue(value);
        }
      }
    }
    if (inArray && currentKey) {
      result[currentKey] = arrayValue;
    }
    return result;
  }
  /**
   * Parse a YAML value.
   */
  parseValue(value) {
    if (value === "null" || value === "~") {
      return null;
    }
    if (value === "true")
      return true;
    if (value === "false")
      return false;
    if (/^-?\d+$/.test(value))
      return parseInt(value, 10);
    if (/^-?\d+\.\d+$/.test(value))
      return parseFloat(value);
    if (value.startsWith('"') && value.endsWith('"') || value.startsWith("'") && value.endsWith("'")) {
      return value.slice(1, -1);
    }
    return value;
  }
  /**
   * Get a task by ID.
   */
  async getTask(id) {
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getTask(id);
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
      }
    }
    const tasks = await this.listTasksFromFiles();
    return tasks.find((t) => t.id.toUpperCase() === id.toUpperCase()) || null;
  }
  /**
   * Create a new task.
   * Requires daemon connection when daemon mode is enabled.
   */
  async createTask(title, options = {}) {
    if (this._useDaemon) {
      try {
        return await this.daemonClient.createTask(title, options);
      } catch (e) {
        if (e instanceof DaemonUnavailableError) {
          throw new DaemonOfflineError("create task");
        }
        throw e;
      }
    }
    return this.createTaskInFiles(title, options);
  }
  /**
   * Create a task directly in files (fallback mode).
   */
  async createTaskInFiles(title, options = {}) {
    const id = await this.generateUniqueId();
    const now = (/* @__PURE__ */ new Date()).toISOString();
    const status = options.status || this.settings.defaultStatus;
    const task = {
      id,
      type: "task",
      status,
      title,
      due: options.due,
      project: options.project,
      blockedBy: [],
      blocks: [],
      tags: options.tags || [],
      timeEstimate: options.timeEstimate,
      created: now,
      updated: now,
      content: `# ${title}

`,
      path: ""
      // Will be set below
    };
    const folderPath = this.vaultService.getStatusPath(status);
    await this.vaultService.ensureFolderExists(folderPath);
    const filename = this.vaultService.generateTaskFilename(title);
    task.path = (0, import_obsidian4.normalizePath)(`${folderPath}/${filename}`);
    const content = this.serializeTask(task);
    await this.app.vault.create(task.path, content);
    return task;
  }
  /**
   * Update an existing task.
   * Requires daemon to be available when daemon mode is enabled.
   */
  async updateTask(task) {
    if (this._useDaemon && !this.daemonClient.isConnected) {
      throw new DaemonOfflineError("update task");
    }
    task.updated = (/* @__PURE__ */ new Date()).toISOString();
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(task.path);
    if (!(file instanceof import_obsidian4.TFile)) {
      throw new Error(`Task file not found: ${task.path}`);
    }
    await this.app.vault.modify(file, content);
  }
  /**
   * Mark a task as completed.
   * Requires daemon connection when daemon mode is enabled.
   */
  async completeTask(id) {
    if (this._useDaemon) {
      try {
        await this.daemonClient.completeTask(id);
        return;
      } catch (e) {
        if (e instanceof DaemonUnavailableError) {
          throw new DaemonOfflineError("complete task");
        }
        throw e;
      }
    }
    await this.completeTaskInFiles(id);
  }
  /**
   * Complete a task directly in files (fallback mode).
   */
  async completeTaskInFiles(id) {
    const task = await this.getTask(id);
    if (!task) {
      throw new Error(`Task not found: ${id}`);
    }
    const now = /* @__PURE__ */ new Date();
    task.status = "completed";
    task.completed = now.toISOString();
    task.updated = now.toISOString();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const completedPath = this.vaultService.getCompletedPath(year, month);
    await this.vaultService.ensureFolderExists(completedPath);
    const oldPath = task.path;
    const filename = oldPath.split("/").pop() || "";
    task.path = (0, import_obsidian4.normalizePath)(`${completedPath}/${filename}`);
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof import_obsidian4.TFile)) {
      throw new Error(`Task file not found: ${oldPath}`);
    }
    await this.app.vault.modify(file, content);
    await this.app.fileManager.renameFile(file, task.path);
  }
  /**
   * Change a task's status.
   * Requires daemon connection when daemon mode is enabled (except for statuses not supported by daemon API).
   */
  async changeStatus(id, newStatus) {
    if (this._useDaemon) {
      if (!this.daemonClient.isConnected) {
        throw new DaemonOfflineError("change task status");
      }
      try {
        if (newStatus === "completed") {
          await this.daemonClient.completeTask(id);
        } else if (newStatus === "next") {
          await this.daemonClient.startTask(id);
        } else if (newStatus === "someday") {
          await this.daemonClient.deferTask(id);
        } else {
          throw new DaemonOfflineError(`change status to ${newStatus}`);
        }
        return;
      } catch (e) {
        if (e instanceof DaemonUnavailableError) {
          throw new DaemonOfflineError("change task status");
        }
        throw e;
      }
    }
    await this.changeStatusInFiles(id, newStatus);
  }
  /**
   * Change task status directly in files (fallback mode).
   */
  async changeStatusInFiles(id, newStatus) {
    const task = await this.getTask(id);
    if (!task) {
      throw new Error(`Task not found: ${id}`);
    }
    if (newStatus === "completed") {
      return this.completeTaskInFiles(id);
    }
    task.status = newStatus;
    task.updated = (/* @__PURE__ */ new Date()).toISOString();
    const newFolderPath = this.vaultService.getStatusPath(newStatus);
    await this.vaultService.ensureFolderExists(newFolderPath);
    const oldPath = task.path;
    const filename = oldPath.split("/").pop() || "";
    task.path = (0, import_obsidian4.normalizePath)(`${newFolderPath}/${filename}`);
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof import_obsidian4.TFile)) {
      throw new Error(`Task file not found: ${oldPath}`);
    }
    await this.app.vault.modify(file, content);
    if (oldPath !== task.path) {
      await this.app.fileManager.renameFile(file, task.path);
    }
  }
  /**
   * Serialize a task to markdown with frontmatter.
   */
  serializeTask(task) {
    const frontmatter = {
      id: task.id,
      type: task.type,
      status: task.status
    };
    if (task.due)
      frontmatter.due = task.due;
    if (task.project)
      frontmatter.project = task.project;
    if (task.assignedTo)
      frontmatter.assignedTo = task.assignedTo;
    if (task.waitingOn)
      frontmatter.waitingOn = task.waitingOn;
    frontmatter.blockedBy = task.blockedBy;
    frontmatter.blocks = task.blocks;
    if (task.location)
      frontmatter.location = task.location;
    frontmatter.tags = task.tags;
    if (task.timeEstimate)
      frontmatter.timeEstimate = task.timeEstimate;
    frontmatter.created = task.created;
    frontmatter.updated = task.updated;
    if (task.completed)
      frontmatter.completed = task.completed;
    const yaml = this.serializeYaml(frontmatter);
    return `---
${yaml}---

${task.content}`;
  }
  /**
   * Serialize an object to YAML.
   */
  serializeYaml(obj) {
    const lines = [];
    for (const [key, value] of Object.entries(obj)) {
      if (value === null || value === void 0) {
        lines.push(`${key}: null`);
      } else if (Array.isArray(value)) {
        if (value.length === 0) {
          lines.push(`${key}: []`);
        } else {
          lines.push(`${key}:`);
          for (const item of value) {
            lines.push(`  - ${this.serializeValue(item)}`);
          }
        }
      } else if (typeof value === "object") {
        lines.push(`${key}:`);
        for (const [k, v] of Object.entries(value)) {
          lines.push(`  ${k}: ${this.serializeValue(v)}`);
        }
      } else {
        lines.push(`${key}: ${this.serializeValue(value)}`);
      }
    }
    return lines.join("\n") + "\n";
  }
  /**
   * Serialize a value for YAML.
   */
  serializeValue(value) {
    if (value === null || value === void 0) {
      return "null";
    }
    if (typeof value === "boolean") {
      return value ? "true" : "false";
    }
    if (typeof value === "number") {
      return value.toString();
    }
    if (typeof value === "string") {
      if (value.includes(":") || value.includes("#") || value.includes("\n") || value.startsWith("[[") || value.match(/^\d/)) {
        return `"${value.replace(/"/g, '\\"')}"`;
      }
      return value;
    }
    return String(value);
  }
  /**
   * Get project names for dropdowns.
   */
  async getProjectNames() {
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getProjectNames();
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
      }
    }
    return this.vaultService.getProjects();
  }
  /**
   * Get people names for dropdowns.
   */
  async getPeopleNames() {
    if (this._useDaemon) {
      try {
        return await this.daemonClient.getPeopleNames();
      } catch (e) {
        if (!(e instanceof DaemonUnavailableError)) {
          throw e;
        }
      }
    }
    return this.vaultService.getPeople();
  }
};

// src/views/TaskListView.ts
var import_obsidian5 = require("obsidian");
var TASK_LIST_VIEW_TYPE = "aio-task-list";
var TaskListView = class extends import_obsidian5.ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.currentStatus = "all";
    this.tasks = [];
    this.plugin = plugin;
  }
  getViewType() {
    return TASK_LIST_VIEW_TYPE;
  }
  getDisplayText() {
    return "AIO Tasks";
  }
  getIcon() {
    return "check-square";
  }
  async onOpen() {
    await this.refresh();
  }
  async onClose() {
  }
  async refresh() {
    const container = this.containerEl.children[1];
    container.empty();
    const isReadOnly = this.plugin.isReadOnly;
    container.createEl("div", { cls: "aio-task-list-container" }, (el) => {
      if (isReadOnly) {
        el.createEl("div", {
          cls: "aio-readonly-banner",
          text: 'Read-only: daemon offline. Run "aio daemon start" to enable writes.'
        });
      }
      el.createEl("div", { cls: "aio-task-list-header" }, (header) => {
        header.createEl("h4", { text: "Tasks", cls: "aio-task-list-title" });
        const addBtn = header.createEl("button", { cls: "aio-add-btn", attr: { "aria-label": "Add task" } });
        (0, import_obsidian5.setIcon)(addBtn, "plus");
        if (isReadOnly) {
          addBtn.addClass("aio-disabled");
          addBtn.setAttribute("title", "Daemon offline - cannot add tasks");
        } else {
          addBtn.addEventListener("click", () => {
            this.plugin.openQuickAddModal();
          });
        }
      });
      el.createEl("div", { cls: "aio-status-tabs" }, (tabs) => {
        this.createTab(tabs, "all", "All");
        this.createTab(tabs, "inbox", "Inbox");
        this.createTab(tabs, "next", "Next");
        this.createTab(tabs, "waiting", "Waiting");
        this.createTab(tabs, "scheduled", "Scheduled");
        this.createTab(tabs, "someday", "Someday");
      });
      el.createEl("div", { cls: "aio-task-list" }, async (listEl) => {
        await this.renderTasks(listEl);
      });
    });
  }
  createTab(container, status, label) {
    const tab = container.createEl("button", {
      cls: `aio-status-tab ${this.currentStatus === status ? "is-active" : ""}`,
      text: label
    });
    tab.addEventListener("click", async () => {
      this.currentStatus = status;
      await this.refresh();
    });
  }
  async renderTasks(container) {
    try {
      if (this.currentStatus === "all") {
        this.tasks = await this.plugin.taskService.listTasks();
      } else {
        this.tasks = await this.plugin.taskService.listTasks(this.currentStatus);
      }
      this.tasks.sort((a, b) => {
        if (a.due && b.due) {
          return a.due.localeCompare(b.due);
        }
        if (a.due)
          return -1;
        if (b.due)
          return 1;
        return a.created.localeCompare(b.created);
      });
      if (this.tasks.length === 0) {
        container.createEl("div", { cls: "aio-empty-state", text: "No tasks found" });
        return;
      }
      for (const task of this.tasks) {
        this.renderTask(container, task);
      }
    } catch (e) {
      container.createEl("div", { cls: "aio-error", text: `Error loading tasks: ${e}` });
    }
  }
  renderTask(container, task) {
    const taskEl = container.createEl("div", { cls: "aio-task-item" });
    const isReadOnly = this.plugin.isReadOnly;
    const checkbox = taskEl.createEl("input", {
      cls: "aio-task-checkbox",
      attr: { type: "checkbox" }
    });
    checkbox.checked = task.status === "completed";
    if (isReadOnly) {
      checkbox.disabled = true;
      checkbox.setAttribute("title", "Daemon offline - cannot complete tasks");
    } else {
      checkbox.addEventListener("change", async () => {
        if (checkbox.checked) {
          try {
            await this.plugin.taskService.completeTask(task.id);
            await this.refresh();
          } catch (e) {
            checkbox.checked = false;
            if (e instanceof DaemonOfflineError) {
              new import_obsidian5.Notice("Cannot complete task: daemon is offline.");
            } else {
              new import_obsidian5.Notice(`Error: ${e instanceof Error ? e.message : "Unknown error"}`);
            }
          }
        }
      });
    }
    const contentEl = taskEl.createEl("div", { cls: "aio-task-content" });
    const titleEl = contentEl.createEl("div", { cls: "aio-task-title", text: task.title });
    titleEl.addEventListener("click", () => {
      const file = this.app.vault.getAbstractFileByPath(task.path);
      if (file) {
        this.app.workspace.getLeaf(false).openFile(file);
      }
    });
    const metaEl = contentEl.createEl("div", { cls: "aio-task-meta" });
    metaEl.createEl("span", {
      cls: `aio-status-badge aio-status-${task.status}`,
      text: STATUS_FOLDERS[task.status]
    });
    if (task.due) {
      const dueDate = new Date(task.due);
      const today = /* @__PURE__ */ new Date();
      today.setHours(0, 0, 0, 0);
      const isOverdue = dueDate < today;
      metaEl.createEl("span", {
        cls: `aio-due-date ${isOverdue ? "aio-overdue" : ""}`,
        text: task.due
      });
    }
    if (task.project) {
      const projectName = task.project.replace(/^\[\[/, "").replace(/\]\]$/, "");
      metaEl.createEl("span", { cls: "aio-project", text: projectName });
    }
    if (task.tags.length > 0) {
      for (const tag of task.tags.slice(0, 3)) {
        metaEl.createEl("span", { cls: "aio-tag", text: `#${tag}` });
      }
    }
    const actionsEl = taskEl.createEl("div", { cls: "aio-task-actions" });
    if (task.status !== "next" && task.status !== "completed") {
      const startBtn = actionsEl.createEl("button", { cls: "aio-action-btn", attr: { "aria-label": "Start" } });
      (0, import_obsidian5.setIcon)(startBtn, "play");
      if (isReadOnly) {
        startBtn.addClass("aio-disabled");
        startBtn.setAttribute("title", "Daemon offline - cannot change status");
      } else {
        startBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          try {
            await this.plugin.taskService.changeStatus(task.id, "next");
            await this.refresh();
          } catch (err) {
            if (err instanceof DaemonOfflineError) {
              new import_obsidian5.Notice("Cannot start task: daemon is offline.");
            } else {
              new import_obsidian5.Notice(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
            }
          }
        });
      }
    }
    if (task.status !== "someday" && task.status !== "completed") {
      const deferBtn = actionsEl.createEl("button", { cls: "aio-action-btn", attr: { "aria-label": "Defer" } });
      (0, import_obsidian5.setIcon)(deferBtn, "clock");
      if (isReadOnly) {
        deferBtn.addClass("aio-disabled");
        deferBtn.setAttribute("title", "Daemon offline - cannot change status");
      } else {
        deferBtn.addEventListener("click", async (e) => {
          e.stopPropagation();
          try {
            await this.plugin.taskService.changeStatus(task.id, "someday");
            await this.refresh();
          } catch (err) {
            if (err instanceof DaemonOfflineError) {
              new import_obsidian5.Notice("Cannot defer task: daemon is offline.");
            } else {
              new import_obsidian5.Notice(`Error: ${err instanceof Error ? err.message : "Unknown error"}`);
            }
          }
        });
      }
    }
    const editBtn = actionsEl.createEl("button", { cls: "aio-action-btn", attr: { "aria-label": "Edit" } });
    (0, import_obsidian5.setIcon)(editBtn, "pencil");
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.plugin.openTaskEditModal(task);
    });
  }
};

// src/views/InboxView.ts
var import_obsidian6 = require("obsidian");
var INBOX_VIEW_TYPE = "aio-inbox";
var InboxView = class extends import_obsidian6.ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.inboxTasks = [];
    this.currentIndex = 0;
    this.skippedCount = 0;
    this.plugin = plugin;
  }
  getViewType() {
    return INBOX_VIEW_TYPE;
  }
  getDisplayText() {
    return "AIO Inbox";
  }
  getIcon() {
    return "inbox";
  }
  async onOpen() {
    await this.refresh();
  }
  async onClose() {
  }
  async refresh() {
    const container = this.containerEl.children[1];
    container.empty();
    this.skippedCount = 0;
    const isReadOnly = this.plugin.isReadOnly;
    container.createEl("div", { cls: "aio-inbox-container" }, async (el) => {
      if (isReadOnly) {
        el.createEl("div", {
          cls: "aio-readonly-banner",
          text: 'Read-only: daemon offline. Run "aio daemon start" to process inbox.'
        });
      }
      el.createEl("div", { cls: "aio-inbox-header" }, (header) => {
        header.createEl("h4", { text: "Process Inbox", cls: "aio-inbox-title" });
      });
      try {
        this.inboxTasks = await this.plugin.taskService.listTasks("inbox");
        if (this.inboxTasks.length === 0) {
          this.renderInboxZero(el);
        } else {
          this.renderCurrentTask(el, isReadOnly);
        }
      } catch (e) {
        el.createEl("div", { cls: "aio-error", text: `Error loading inbox: ${e}` });
      }
    });
  }
  renderInboxZero(container) {
    container.createEl("div", { cls: "aio-inbox-zero" }, (el) => {
      el.createEl("div", { cls: "aio-inbox-zero-icon", text: "\u{1F389}" });
      el.createEl("h3", { text: "Inbox Zero!" });
      el.createEl("p", { text: "All tasks have been processed. Great job!" });
      const addBtn = el.createEl("button", { cls: "mod-cta", text: "Add new task" });
      addBtn.addEventListener("click", () => {
        this.plugin.openQuickAddModal();
      });
    });
  }
  renderCurrentTask(container, isReadOnly = false) {
    const task = this.inboxTasks[this.currentIndex];
    container.createEl("div", { cls: "aio-inbox-progress" }, (progress) => {
      progress.createEl("span", {
        text: `${this.currentIndex + 1} of ${this.inboxTasks.length}`
      });
      const bar = progress.createEl("div", { cls: "aio-progress-bar" });
      bar.createEl("div", {
        cls: "aio-progress-fill",
        attr: { style: `width: ${(this.currentIndex + 1) / this.inboxTasks.length * 100}%` }
      });
    });
    container.createEl("div", { cls: "aio-inbox-card" }, (card) => {
      const titleEl = card.createEl("h3", { cls: "aio-inbox-task-title", text: task.title });
      titleEl.addEventListener("click", () => {
        const file = this.app.vault.getAbstractFileByPath(task.path);
        if (file) {
          this.app.workspace.getLeaf(false).openFile(file);
        }
      });
      card.createEl("div", { cls: "aio-inbox-task-meta" }, (meta) => {
        if (task.due) {
          meta.createEl("span", { cls: "aio-due-date", text: `Due: ${task.due}` });
        }
        if (task.project) {
          const projectName = task.project.replace(/^\[\[/, "").replace(/\]\]$/, "");
          meta.createEl("span", { cls: "aio-project", text: projectName });
        }
        meta.createEl("span", { cls: "aio-task-id", text: `#${task.id}` });
      });
      if (task.content) {
        const preview = task.content.replace(/^#\s+.*$/m, "").trim().substring(0, 200);
        if (preview) {
          card.createEl("div", { cls: "aio-inbox-preview", text: preview });
        }
      }
    });
    container.createEl("div", { cls: "aio-inbox-actions" }, (actions) => {
      const startBtn = actions.createEl("button", { cls: "aio-inbox-action mod-cta" });
      startBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian6.setIcon)(span, "play"));
      startBtn.createEl("span", { text: "Start" });
      startBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Next" });
      if (isReadOnly) {
        startBtn.addClass("aio-disabled");
        startBtn.setAttribute("title", "Daemon offline - cannot process tasks");
      } else {
        startBtn.addEventListener("click", () => this.handleAction("next"));
      }
      const deferBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      deferBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian6.setIcon)(span, "clock"));
      deferBtn.createEl("span", { text: "Defer" });
      deferBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Someday" });
      if (isReadOnly) {
        deferBtn.addClass("aio-disabled");
        deferBtn.setAttribute("title", "Daemon offline - cannot process tasks");
      } else {
        deferBtn.addEventListener("click", () => this.handleAction("someday"));
      }
      const waitBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      waitBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian6.setIcon)(span, "user"));
      waitBtn.createEl("span", { text: "Wait" });
      waitBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Waiting" });
      if (isReadOnly) {
        waitBtn.addClass("aio-disabled");
        waitBtn.setAttribute("title", "Daemon offline - cannot process tasks");
      } else {
        waitBtn.addEventListener("click", () => this.handleAction("waiting"));
      }
      const scheduleBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      scheduleBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian6.setIcon)(span, "calendar"));
      scheduleBtn.createEl("span", { text: "Schedule" });
      scheduleBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Scheduled" });
      if (isReadOnly) {
        scheduleBtn.addClass("aio-disabled");
        scheduleBtn.setAttribute("title", "Daemon offline - cannot process tasks");
      } else {
        scheduleBtn.addEventListener("click", () => this.handleAction("scheduled"));
      }
      const completeBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      completeBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian6.setIcon)(span, "check"));
      completeBtn.createEl("span", { text: "Done" });
      completeBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Completed" });
      if (isReadOnly) {
        completeBtn.addClass("aio-disabled");
        completeBtn.setAttribute("title", "Daemon offline - cannot process tasks");
      } else {
        completeBtn.addEventListener("click", () => this.handleAction("completed"));
      }
    });
    container.createEl("div", { cls: "aio-inbox-skip" }, (el) => {
      const skipBtn = el.createEl("button", { cls: "aio-skip-btn", text: "Skip for now" });
      skipBtn.addEventListener("click", () => {
        this.skippedCount++;
        if (this.skippedCount >= this.inboxTasks.length) {
          this.renderReviewComplete(container);
          return;
        }
        this.currentIndex = (this.currentIndex + 1) % this.inboxTasks.length;
        this.refresh();
      });
    });
  }
  renderReviewComplete(container) {
    container.empty();
    container.createEl("div", { cls: "aio-inbox-container" }, (el) => {
      el.createEl("div", { cls: "aio-inbox-header" }, (header) => {
        header.createEl("h4", { text: "Process Inbox", cls: "aio-inbox-title" });
      });
      el.createEl("div", { cls: "aio-inbox-review-complete" }, (content) => {
        content.createEl("div", { cls: "aio-inbox-zero-icon", text: "\u{1F4CB}" });
        content.createEl("h3", { text: "Review Complete" });
        content.createEl("p", {
          text: `You've reviewed all ${this.inboxTasks.length} task${this.inboxTasks.length === 1 ? "" : "s"} in your inbox.`
        });
        const btnContainer = content.createEl("div", { cls: "aio-review-complete-actions" });
        const reviewAgainBtn = btnContainer.createEl("button", { cls: "mod-cta", text: "Review again" });
        reviewAgainBtn.addEventListener("click", () => {
          this.skippedCount = 0;
          this.currentIndex = 0;
          this.refresh();
        });
        const closeBtn = btnContainer.createEl("button", { text: "Close" });
        closeBtn.addEventListener("click", () => {
          this.leaf.detach();
        });
      });
    });
  }
  async handleAction(newStatus) {
    const task = this.inboxTasks[this.currentIndex];
    try {
      if (newStatus === "completed") {
        await this.plugin.taskService.completeTask(task.id);
      } else {
        await this.plugin.taskService.changeStatus(task.id, newStatus);
      }
      this.inboxTasks.splice(this.currentIndex, 1);
      if (this.currentIndex >= this.inboxTasks.length) {
        this.currentIndex = 0;
      }
      await this.refresh();
    } catch (e) {
      if (e instanceof DaemonOfflineError) {
        new import_obsidian6.Notice('Cannot process task: daemon is offline. Run "aio daemon start" to enable writes.');
      } else {
        console.error("Error processing task:", e);
        new import_obsidian6.Notice(`Error processing task: ${e instanceof Error ? e.message : "Unknown error"}`);
      }
    }
  }
};

// src/modals/QuickAddModal.ts
var import_obsidian7 = require("obsidian");

// src/utils/dates.ts
var InvalidDateError = class extends Error {
  constructor(message) {
    super(message);
    this.name = "InvalidDateError";
  }
};
function parseDate(dateStr) {
  if (!(dateStr == null ? void 0 : dateStr.trim())) {
    throw new InvalidDateError("Date string cannot be empty");
  }
  const today = /* @__PURE__ */ new Date();
  const lower = dateStr.toLowerCase().trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
    const parsed = /* @__PURE__ */ new Date(dateStr + "T00:00:00");
    if (isNaN(parsed.getTime())) {
      throw new InvalidDateError(`Invalid date: ${dateStr}`);
    }
    return parsed;
  }
  if (lower === "today") {
    return today;
  }
  if (lower === "tomorrow") {
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow;
  }
  if (lower === "yesterday") {
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  }
  if (lower === "next week") {
    const nextWeek = new Date(today);
    nextWeek.setDate(nextWeek.getDate() + 7);
    return nextWeek;
  }
  const inDaysMatch = lower.match(/^in (\d+) days?$/);
  if (inDaysMatch) {
    const days2 = parseInt(inDaysMatch[1], 10);
    const future = new Date(today);
    future.setDate(future.getDate() + days2);
    return future;
  }
  const inWeeksMatch = lower.match(/^in (\d+) weeks?$/);
  if (inWeeksMatch) {
    const weeks = parseInt(inWeeksMatch[1], 10);
    const future = new Date(today);
    future.setDate(future.getDate() + weeks * 7);
    return future;
  }
  const days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
  const nextDayMatch = lower.match(/^(next )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$/);
  if (nextDayMatch) {
    const targetDay = days.indexOf(nextDayMatch[2]);
    const currentDay = today.getDay();
    let daysAhead = targetDay - currentDay;
    if (daysAhead <= 0) {
      daysAhead += 7;
    }
    if (nextDayMatch[1]) {
      daysAhead += 7;
    }
    const targetDate = new Date(today);
    targetDate.setDate(targetDate.getDate() + daysAhead);
    return targetDate;
  }
  if (lower === "end of week" || lower === "eow") {
    return getEndOfWeek();
  }
  if (lower === "end of month" || lower === "eom") {
    return getEndOfMonth();
  }
  if (lower === "end of year" || lower === "eoy") {
    return getEndOfYear();
  }
  throw new InvalidDateError(`Could not parse date: ${dateStr}`);
}
function formatIsoDate(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}
function getEndOfWeek() {
  const today = /* @__PURE__ */ new Date();
  const dayOfWeek = today.getDay();
  let daysUntilFriday = 5 - dayOfWeek;
  if (daysUntilFriday <= 0) {
    daysUntilFriday += 7;
  }
  const friday = new Date(today);
  friday.setDate(today.getDate() + daysUntilFriday);
  return friday;
}
function getEndOfMonth() {
  const today = /* @__PURE__ */ new Date();
  return new Date(today.getFullYear(), today.getMonth() + 1, 0);
}
function getEndOfYear() {
  const today = /* @__PURE__ */ new Date();
  return new Date(today.getFullYear(), 11, 31);
}

// src/modals/QuickAddModal.ts
var QuickAddModal = class extends import_obsidian7.Modal {
  constructor(app, plugin, onSubmit) {
    super(app);
    this.title = "";
    this.dueDate = "";
    this.project = "";
    this.plugin = plugin;
    this.onSubmit = onSubmit;
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("aio-quick-add-modal");
    contentEl.createEl("h2", { text: "Quick Add Task" });
    const isReadOnly = this.plugin.isReadOnly;
    if (isReadOnly) {
      contentEl.createEl("div", {
        cls: "aio-readonly-banner",
        text: 'Daemon offline - cannot create tasks. Run "aio daemon start" to enable writes.'
      });
    }
    new import_obsidian7.Setting(contentEl).setName("Title").setDesc("Task title (required)").addText((text) => {
      text.setPlaceholder("What needs to be done?").setValue(this.title).onChange((value) => {
        this.title = value;
      });
      text.inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          this.submit();
        }
      });
      setTimeout(() => text.inputEl.focus(), 10);
    });
    new import_obsidian7.Setting(contentEl).setName("Due Date").setDesc("Optional: YYYY-MM-DD or natural language (tomorrow, next friday)").addText((text) => text.setPlaceholder("tomorrow").setValue(this.dueDate).onChange((value) => {
      this.dueDate = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Project").setDesc("Optional: Link to a project").addDropdown(async (dropdown) => {
      dropdown.addOption("", "(None)");
      const projects = await this.plugin.vaultService.getProjects();
      for (const project of projects) {
        dropdown.addOption(project, project);
      }
      dropdown.setValue(this.project);
      dropdown.onChange((value) => {
        this.project = value;
      });
    });
    const buttonContainer = contentEl.createEl("div", { cls: "aio-modal-buttons" });
    const cancelBtn = buttonContainer.createEl("button", { text: "Cancel" });
    cancelBtn.addEventListener("click", () => {
      this.close();
    });
    const submitBtn = buttonContainer.createEl("button", { cls: "mod-cta", text: "Add Task" });
    if (isReadOnly) {
      submitBtn.disabled = true;
      submitBtn.addClass("aio-disabled");
    } else {
      submitBtn.addEventListener("click", () => {
        this.submit();
      });
    }
    contentEl.createEl("div", {
      cls: "aio-modal-hint",
      text: "Press Enter to save, Esc to cancel"
    });
  }
  async submit() {
    if (!this.title.trim()) {
      return;
    }
    try {
      const options = {};
      if (this.dueDate) {
        try {
          const parsed = parseDate(this.dueDate);
          options.due = formatIsoDate(parsed);
        } catch (e) {
          if (e instanceof InvalidDateError) {
            new import_obsidian7.Notice(`Invalid date: ${this.dueDate}`);
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
        new import_obsidian7.Notice('Cannot create task: daemon is offline. Run "aio daemon start" to enable writes.');
      } else {
        console.error("Error creating task:", e);
        new import_obsidian7.Notice(`Error creating task: ${e instanceof Error ? e.message : "Unknown error"}`);
      }
    }
  }
  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
};

// src/modals/TaskEditModal.ts
var import_obsidian8 = require("obsidian");
var TaskEditModal = class extends import_obsidian8.Modal {
  constructor(app, plugin, task, onSubmit) {
    var _a, _b;
    super(app);
    this.plugin = plugin;
    this.task = task;
    this.onSubmit = onSubmit;
    this.title = task.title;
    this.status = task.status;
    this.dueDate = task.due || "";
    this.project = ((_a = task.project) == null ? void 0 : _a.replace(/^\[\[Projects\//, "").replace(/\]\]$/, "")) || "";
    this.assignedTo = ((_b = task.assignedTo) == null ? void 0 : _b.replace(/^\[\[People\//, "").replace(/\]\]$/, "")) || "";
    this.waitingOn = task.waitingOn || "";
    this.timeEstimate = task.timeEstimate || "";
    this.tags = task.tags.join(", ");
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("aio-task-edit-modal");
    contentEl.createEl("h2", { text: "Edit Task" });
    const isReadOnly = this.plugin.isReadOnly;
    if (isReadOnly) {
      contentEl.createEl("div", {
        cls: "aio-readonly-banner",
        text: 'Daemon offline - cannot edit tasks. Run "aio daemon start" to enable writes.'
      });
    }
    contentEl.createEl("div", { cls: "aio-task-id-display", text: `ID: ${this.task.id}` });
    new import_obsidian8.Setting(contentEl).setName("Title").addText((text) => text.setValue(this.title).onChange((value) => {
      this.title = value;
    }));
    new import_obsidian8.Setting(contentEl).setName("Status").addDropdown((dropdown) => dropdown.addOption("inbox", "Inbox").addOption("next", "Next").addOption("waiting", "Waiting").addOption("scheduled", "Scheduled").addOption("someday", "Someday").addOption("completed", "Completed").setValue(this.status).onChange((value) => {
      this.status = value;
    }));
    new import_obsidian8.Setting(contentEl).setName("Due Date").setDesc("YYYY-MM-DD format").addText((text) => text.setPlaceholder("YYYY-MM-DD").setValue(this.dueDate).onChange((value) => {
      this.dueDate = value;
    }));
    new import_obsidian8.Setting(contentEl).setName("Project").addDropdown(async (dropdown) => {
      dropdown.addOption("", "(None)");
      const projects = await this.plugin.vaultService.getProjects();
      for (const project of projects) {
        dropdown.addOption(project, project);
      }
      dropdown.setValue(this.project);
      dropdown.onChange((value) => {
        this.project = value;
      });
    });
    new import_obsidian8.Setting(contentEl).setName("Assigned To").addDropdown(async (dropdown) => {
      dropdown.addOption("", "(None)");
      const people = await this.plugin.vaultService.getPeople();
      for (const person of people) {
        dropdown.addOption(person, person);
      }
      dropdown.setValue(this.assignedTo);
      dropdown.onChange((value) => {
        this.assignedTo = value;
      });
    });
    new import_obsidian8.Setting(contentEl).setName("Waiting On").setDesc("Person or thing you are waiting for").addText((text) => text.setValue(this.waitingOn).onChange((value) => {
      this.waitingOn = value;
    }));
    new import_obsidian8.Setting(contentEl).setName("Time Estimate").setDesc("e.g., 30m, 2h, 1d").addText((text) => text.setPlaceholder("2h").setValue(this.timeEstimate).onChange((value) => {
      this.timeEstimate = value;
    }));
    new import_obsidian8.Setting(contentEl).setName("Tags").setDesc("Comma-separated list").addText((text) => text.setPlaceholder("backend, urgent").setValue(this.tags).onChange((value) => {
      this.tags = value;
    }));
    const buttonContainer = contentEl.createEl("div", { cls: "aio-modal-buttons" });
    const cancelBtn = buttonContainer.createEl("button", { text: "Cancel" });
    cancelBtn.addEventListener("click", () => {
      this.close();
    });
    const saveBtn = buttonContainer.createEl("button", { cls: "mod-cta", text: "Save" });
    if (isReadOnly) {
      saveBtn.disabled = true;
      saveBtn.addClass("aio-disabled");
    } else {
      saveBtn.addEventListener("click", () => {
        this.save();
      });
    }
    const deleteBtn = buttonContainer.createEl("button", { cls: "mod-warning", text: "Delete" });
    if (isReadOnly) {
      deleteBtn.disabled = true;
      deleteBtn.addClass("aio-disabled");
    } else {
      deleteBtn.addEventListener("click", async () => {
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
  }
  async save() {
    if (!this.title.trim()) {
      return;
    }
    try {
      this.task.title = this.title;
      this.task.due = this.dueDate || void 0;
      this.task.project = this.project ? `[[Projects/${this.project}]]` : void 0;
      this.task.assignedTo = this.assignedTo ? `[[People/${this.assignedTo}]]` : void 0;
      this.task.waitingOn = this.waitingOn || void 0;
      this.task.timeEstimate = this.timeEstimate || void 0;
      this.task.tags = this.tags.split(",").map((t) => t.trim()).filter((t) => t.length > 0);
      this.task.content = this.task.content.replace(/^#\s+.+$/m, `# ${this.title}`);
      if (this.status !== this.task.status) {
        await this.plugin.taskService.updateTask(this.task);
        await this.plugin.taskService.changeStatus(this.task.id, this.status);
      } else {
        await this.plugin.taskService.updateTask(this.task);
      }
      this.onSubmit();
      this.close();
    } catch (e) {
      if (e instanceof DaemonOfflineError) {
        new import_obsidian8.Notice('Cannot save task: daemon is offline. Run "aio daemon start" to enable writes.');
      } else {
        console.error("Error saving task:", e);
        new import_obsidian8.Notice(`Error saving task: ${e instanceof Error ? e.message : "Unknown error"}`);
      }
    }
  }
  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
};

// src/main.ts
var HEALTH_CHECK_INTERVAL = 3e4;
var AioPlugin = class extends import_obsidian9.Plugin {
  constructor() {
    super(...arguments);
    this.statusBarItem = null;
    this.healthCheckInterval = null;
  }
  /**
   * Whether the plugin is in read-only mode.
   * Read-only when daemon mode is enabled but daemon is not connected.
   */
  get isReadOnly() {
    var _a, _b;
    return (_b = (_a = this.taskService) == null ? void 0 : _a.isReadOnly) != null ? _b : false;
  }
  async onload() {
    await this.loadSettings();
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);
    this.statusBarItem = this.addStatusBarItem();
    this.updateStatusBar(false);
    await this.checkDaemonConnection();
    this.startHealthChecks();
    await this.vaultService.ensureAioStructure();
    this.registerView(
      TASK_LIST_VIEW_TYPE,
      (leaf) => new TaskListView(leaf, this)
    );
    this.registerView(
      INBOX_VIEW_TYPE,
      (leaf) => new InboxView(leaf, this)
    );
    this.addRibbonIcon("check-square", "Open AIO Tasks", () => {
      this.activateView(TASK_LIST_VIEW_TYPE);
    });
    this.addRibbonIcon("inbox", "Open AIO Inbox", () => {
      this.activateView(INBOX_VIEW_TYPE);
    });
    this.addCommand({
      id: "aio-add-task",
      name: "Add task",
      callback: () => this.openQuickAddModal()
    });
    this.addCommand({
      id: "aio-open-tasks",
      name: "Open tasks",
      callback: () => this.activateView(TASK_LIST_VIEW_TYPE)
    });
    this.addCommand({
      id: "aio-open-inbox",
      name: "Open inbox",
      callback: () => this.activateView(INBOX_VIEW_TYPE)
    });
    this.addCommand({
      id: "aio-complete-task",
      name: "Complete current task",
      checkCallback: (checking) => {
        const task = this.getCurrentTask();
        if (task) {
          if (!checking) {
            this.taskService.completeTask(task.id).then(() => {
              this.refreshViews();
            }).catch((e) => {
              if (e instanceof DaemonOfflineError) {
                new import_obsidian9.Notice('Cannot complete task: daemon is offline. Run "aio daemon start" to enable writes.');
              } else {
                new import_obsidian9.Notice(`Error: ${e.message}`);
              }
            });
          }
          return true;
        }
        return false;
      }
    });
    this.addCommand({
      id: "aio-start-task",
      name: "Start current task (move to Next)",
      checkCallback: (checking) => {
        const task = this.getCurrentTask();
        if (task && task.status !== "next" && task.status !== "completed") {
          if (!checking) {
            this.taskService.changeStatus(task.id, "next").then(() => {
              this.refreshViews();
            }).catch((e) => {
              if (e instanceof DaemonOfflineError) {
                new import_obsidian9.Notice('Cannot start task: daemon is offline. Run "aio daemon start" to enable writes.');
              } else {
                new import_obsidian9.Notice(`Error: ${e.message}`);
              }
            });
          }
          return true;
        }
        return false;
      }
    });
    this.addCommand({
      id: "aio-defer-task",
      name: "Defer current task (move to Someday)",
      checkCallback: (checking) => {
        const task = this.getCurrentTask();
        if (task && task.status !== "someday" && task.status !== "completed") {
          if (!checking) {
            this.taskService.changeStatus(task.id, "someday").then(() => {
              this.refreshViews();
            }).catch((e) => {
              if (e instanceof DaemonOfflineError) {
                new import_obsidian9.Notice('Cannot defer task: daemon is offline. Run "aio daemon start" to enable writes.');
              } else {
                new import_obsidian9.Notice(`Error: ${e.message}`);
              }
            });
          }
          return true;
        }
        return false;
      }
    });
    this.addCommand({
      id: "aio-wait-task",
      name: "Wait on current task (move to Waiting)",
      checkCallback: (checking) => {
        const task = this.getCurrentTask();
        if (task && task.status !== "waiting" && task.status !== "completed") {
          if (!checking) {
            this.taskService.changeStatus(task.id, "waiting").then(() => {
              this.refreshViews();
            }).catch((e) => {
              if (e instanceof DaemonOfflineError) {
                new import_obsidian9.Notice('Cannot set task to waiting: daemon is offline. Run "aio daemon start" to enable writes.');
              } else {
                new import_obsidian9.Notice(`Error: ${e.message}`);
              }
            });
          }
          return true;
        }
        return false;
      }
    });
    this.addCommand({
      id: "aio-schedule-task",
      name: "Schedule current task",
      checkCallback: (checking) => {
        const task = this.getCurrentTask();
        if (task && task.status !== "scheduled" && task.status !== "completed") {
          if (!checking) {
            this.taskService.changeStatus(task.id, "scheduled").then(() => {
              this.refreshViews();
            }).catch((e) => {
              if (e instanceof DaemonOfflineError) {
                new import_obsidian9.Notice('Cannot schedule task: daemon is offline. Run "aio daemon start" to enable writes.');
              } else {
                new import_obsidian9.Notice(`Error: ${e.message}`);
              }
            });
          }
          return true;
        }
        return false;
      }
    });
    this.addSettingTab(new AioSettingTab(this.app, this));
  }
  onunload() {
    this.stopHealthChecks();
    this.app.workspace.detachLeavesOfType(TASK_LIST_VIEW_TYPE);
    this.app.workspace.detachLeavesOfType(INBOX_VIEW_TYPE);
  }
  /**
   * Check daemon connection and update status bar.
   */
  async checkDaemonConnection() {
    if (!this.settings.useDaemon) {
      this.updateStatusBar(false, "disabled");
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
  startHealthChecks() {
    if (this.healthCheckInterval) {
      return;
    }
    this.healthCheckInterval = window.setInterval(async () => {
      await this.checkDaemonConnection();
    }, HEALTH_CHECK_INTERVAL);
    this.registerInterval(this.healthCheckInterval);
  }
  /**
   * Stop periodic health checks.
   */
  stopHealthChecks() {
    if (this.healthCheckInterval) {
      window.clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
  }
  /**
   * Update the status bar with daemon connection status.
   */
  updateStatusBar(connected, mode) {
    if (!this.statusBarItem) {
      return;
    }
    if (mode === "disabled") {
      this.statusBarItem.setText("AIO: Local");
      this.statusBarItem.setAttribute("title", "Daemon mode disabled - using local files");
      this.statusBarItem.removeClass("aio-connected", "aio-disconnected");
      return;
    }
    if (connected) {
      this.statusBarItem.setText("AIO: Connected");
      this.statusBarItem.setAttribute("title", "Connected to AIO daemon");
      this.statusBarItem.addClass("aio-connected");
      this.statusBarItem.removeClass("aio-disconnected", "aio-readonly");
    } else {
      this.statusBarItem.setText("AIO: Read-only");
      this.statusBarItem.setAttribute("title", 'Daemon offline - read-only mode. Run "aio daemon start" to enable writes.');
      this.statusBarItem.addClass("aio-disconnected", "aio-readonly");
      this.statusBarItem.removeClass("aio-connected");
    }
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService.updateSettings(this.settings);
    await this.checkDaemonConnection();
  }
  /**
   * Activate a view in the right sidebar.
   */
  async activateView(viewType) {
    const { workspace } = this.app;
    let leaf = null;
    const leaves = workspace.getLeavesOfType(viewType);
    if (leaves.length > 0) {
      leaf = leaves[0];
    } else {
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
  openQuickAddModal() {
    new QuickAddModal(this.app, this, () => {
      this.refreshViews();
    }).open();
  }
  /**
   * Open the Task Edit modal.
   */
  openTaskEditModal(task) {
    new TaskEditModal(this.app, this, task, () => {
      this.refreshViews();
    }).open();
  }
  /**
   * Get the current task from the active file.
   * Uses Obsidian's metadata cache for synchronous access.
   */
  getCurrentTask() {
    const file = this.app.workspace.getActiveFile();
    if (!file)
      return null;
    if (!file.path.includes(`${this.settings.aioFolderPath}/Tasks`)) {
      return null;
    }
    const cache = this.app.metadataCache.getFileCache(file);
    if (!(cache == null ? void 0 : cache.frontmatter)) {
      return null;
    }
    const fm = cache.frontmatter;
    if (fm.type !== "task") {
      return null;
    }
    let title = fm.title || "";
    if (!title && cache.headings && cache.headings.length > 0) {
      title = cache.headings[0].heading;
    }
    if (!title) {
      title = file.basename;
    }
    return {
      id: fm.id || "",
      type: "task",
      status: fm.status || "inbox",
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
      created: fm.created || (/* @__PURE__ */ new Date()).toISOString(),
      updated: fm.updated || (/* @__PURE__ */ new Date()).toISOString(),
      completed: fm.completed,
      content: "",
      // Not needed for command palette checks
      path: file.path
    };
  }
  /**
   * Refresh all open AIO views.
   */
  refreshViews() {
    for (const leaf of this.app.workspace.getLeavesOfType(TASK_LIST_VIEW_TYPE)) {
      const view = leaf.view;
      view.refresh();
    }
    for (const leaf of this.app.workspace.getLeavesOfType(INBOX_VIEW_TYPE)) {
      const view = leaf.view;
      view.refresh();
    }
  }
};
