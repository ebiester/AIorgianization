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
var import_obsidian8 = require("obsidian");

// src/types.ts
var DEFAULT_SETTINGS = {
  aioFolderPath: "AIO",
  defaultStatus: "inbox",
  dateFormat: "YYYY-MM-DD"
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
var import_obsidian = require("obsidian");
var AioSettingTab = class extends import_obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "AIorgianization Settings" });
    new import_obsidian.Setting(containerEl).setName("AIO Folder Path").setDesc("Path to the AIO folder relative to vault root").addText((text) => text.setPlaceholder("AIO").setValue(this.plugin.settings.aioFolderPath).onChange(async (value) => {
      this.plugin.settings.aioFolderPath = value || "AIO";
      await this.plugin.saveSettings();
    }));
    new import_obsidian.Setting(containerEl).setName("Default Status").setDesc("Default status for new tasks").addDropdown((dropdown) => dropdown.addOption("inbox", "Inbox").addOption("next", "Next").addOption("scheduled", "Scheduled").addOption("someday", "Someday").setValue(this.plugin.settings.defaultStatus).onChange(async (value) => {
      this.plugin.settings.defaultStatus = value;
      await this.plugin.saveSettings();
    }));
    new import_obsidian.Setting(containerEl).setName("Date Format").setDesc("Format for displaying dates").addText((text) => text.setPlaceholder("YYYY-MM-DD").setValue(this.plugin.settings.dateFormat).onChange(async (value) => {
      this.plugin.settings.dateFormat = value || "YYYY-MM-DD";
      await this.plugin.saveSettings();
    }));
  }
};

// src/services/VaultService.ts
var import_obsidian2 = require("obsidian");
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
    return (0, import_obsidian2.normalizePath)(`${this.getAioPath()}/Tasks`);
  }
  /**
   * Get the folder path for a specific task status.
   */
  getStatusPath(status) {
    const folder = STATUS_FOLDERS[status];
    return (0, import_obsidian2.normalizePath)(`${this.getTasksPath()}/${folder}`);
  }
  /**
   * Get the completed tasks folder path for a specific year/month.
   */
  getCompletedPath(year, month) {
    const monthStr = month.toString().padStart(2, "0");
    return (0, import_obsidian2.normalizePath)(`${this.getTasksPath()}/Completed/${year}/${monthStr}`);
  }
  /**
   * Get the Projects folder path.
   */
  getProjectsPath() {
    return (0, import_obsidian2.normalizePath)(`${this.getAioPath()}/Projects`);
  }
  /**
   * Get the People folder path.
   */
  getPeoplePath() {
    return (0, import_obsidian2.normalizePath)(`${this.getAioPath()}/People`);
  }
  /**
   * Get the Dashboard folder path.
   */
  getDashboardPath() {
    return (0, import_obsidian2.normalizePath)(`${this.getAioPath()}/Dashboard`);
  }
  /**
   * Get the Archive folder path.
   */
  getArchivePath() {
    return (0, import_obsidian2.normalizePath)(`${this.getAioPath()}/Archive`);
  }
  /**
   * Ensure a folder exists, creating it if necessary.
   */
  async ensureFolderExists(path) {
    const normalizedPath = (0, import_obsidian2.normalizePath)(path);
    const folder = this.app.vault.getAbstractFileByPath(normalizedPath);
    if (!folder) {
      await this.app.vault.createFolder(normalizedPath);
    } else if (!(folder instanceof import_obsidian2.TFolder)) {
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
        await this.ensureFolderExists((0, import_obsidian2.normalizePath)(`${this.getTasksPath()}/Completed`));
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
    if (!(folder instanceof import_obsidian2.TFolder)) {
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
    if (!(folder instanceof import_obsidian2.TFolder)) {
      return [];
    }
    return folder.children.filter((f) => f.name.endsWith(".md")).map((f) => f.name.replace(".md", ""));
  }
};

// src/services/TaskService.ts
var import_obsidian3 = require("obsidian");
var TaskService = class {
  constructor(app, settings) {
    this.app = app;
    this.settings = settings;
    this.vaultService = new VaultService(app, settings);
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
    const tasks = [];
    const tasksPath = this.vaultService.getTasksPath();
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
    if (!(folder instanceof import_obsidian3.TFolder)) {
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
      if (child instanceof import_obsidian3.TFile && child.extension === "md") {
        files.push(child);
      } else if (child instanceof import_obsidian3.TFolder) {
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
      jiraKey: frontmatter.jiraKey,
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
    const tasks = await this.listTasks();
    return tasks.find((t) => t.id.toUpperCase() === id.toUpperCase()) || null;
  }
  /**
   * Create a new task.
   */
  async createTask(title, options = {}) {
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
    task.path = (0, import_obsidian3.normalizePath)(`${folderPath}/${filename}`);
    const content = this.serializeTask(task);
    await this.app.vault.create(task.path, content);
    return task;
  }
  /**
   * Update an existing task.
   */
  async updateTask(task) {
    task.updated = (/* @__PURE__ */ new Date()).toISOString();
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(task.path);
    if (!(file instanceof import_obsidian3.TFile)) {
      throw new Error(`Task file not found: ${task.path}`);
    }
    await this.app.vault.modify(file, content);
  }
  /**
   * Mark a task as completed.
   */
  async completeTask(id) {
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
    task.path = (0, import_obsidian3.normalizePath)(`${completedPath}/${filename}`);
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof import_obsidian3.TFile)) {
      throw new Error(`Task file not found: ${oldPath}`);
    }
    await this.app.vault.modify(file, content);
    await this.app.fileManager.renameFile(file, task.path);
  }
  /**
   * Change a task's status.
   */
  async changeStatus(id, newStatus) {
    const task = await this.getTask(id);
    if (!task) {
      throw new Error(`Task not found: ${id}`);
    }
    if (newStatus === "completed") {
      return this.completeTask(id);
    }
    const oldStatus = task.status;
    task.status = newStatus;
    task.updated = (/* @__PURE__ */ new Date()).toISOString();
    const newFolderPath = this.vaultService.getStatusPath(newStatus);
    await this.vaultService.ensureFolderExists(newFolderPath);
    const oldPath = task.path;
    const filename = oldPath.split("/").pop() || "";
    task.path = (0, import_obsidian3.normalizePath)(`${newFolderPath}/${filename}`);
    const content = this.serializeTask(task);
    const file = this.app.vault.getAbstractFileByPath(oldPath);
    if (!(file instanceof import_obsidian3.TFile)) {
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
    if (task.jiraKey)
      frontmatter.jiraKey = task.jiraKey;
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
};

// src/views/TaskListView.ts
var import_obsidian4 = require("obsidian");
var TASK_LIST_VIEW_TYPE = "aio-task-list";
var TaskListView = class extends import_obsidian4.ItemView {
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
    container.createEl("div", { cls: "aio-task-list-container" }, (el) => {
      el.createEl("div", { cls: "aio-task-list-header" }, (header) => {
        header.createEl("h4", { text: "Tasks", cls: "aio-task-list-title" });
        const addBtn = header.createEl("button", { cls: "aio-add-btn", attr: { "aria-label": "Add task" } });
        (0, import_obsidian4.setIcon)(addBtn, "plus");
        addBtn.addEventListener("click", () => {
          this.plugin.openQuickAddModal();
        });
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
    const checkbox = taskEl.createEl("input", {
      cls: "aio-task-checkbox",
      attr: { type: "checkbox" }
    });
    checkbox.checked = task.status === "completed";
    checkbox.addEventListener("change", async () => {
      if (checkbox.checked) {
        await this.plugin.taskService.completeTask(task.id);
        await this.refresh();
      }
    });
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
      (0, import_obsidian4.setIcon)(startBtn, "play");
      startBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await this.plugin.taskService.changeStatus(task.id, "next");
        await this.refresh();
      });
    }
    if (task.status !== "someday" && task.status !== "completed") {
      const deferBtn = actionsEl.createEl("button", { cls: "aio-action-btn", attr: { "aria-label": "Defer" } });
      (0, import_obsidian4.setIcon)(deferBtn, "clock");
      deferBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await this.plugin.taskService.changeStatus(task.id, "someday");
        await this.refresh();
      });
    }
    const editBtn = actionsEl.createEl("button", { cls: "aio-action-btn", attr: { "aria-label": "Edit" } });
    (0, import_obsidian4.setIcon)(editBtn, "pencil");
    editBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.plugin.openTaskEditModal(task);
    });
  }
};

// src/views/InboxView.ts
var import_obsidian5 = require("obsidian");
var INBOX_VIEW_TYPE = "aio-inbox";
var InboxView = class extends import_obsidian5.ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.inboxTasks = [];
    this.currentIndex = 0;
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
    container.createEl("div", { cls: "aio-inbox-container" }, async (el) => {
      el.createEl("div", { cls: "aio-inbox-header" }, (header) => {
        header.createEl("h4", { text: "Process Inbox", cls: "aio-inbox-title" });
      });
      try {
        this.inboxTasks = await this.plugin.taskService.listTasks("inbox");
        if (this.inboxTasks.length === 0) {
          this.renderInboxZero(el);
        } else {
          this.renderCurrentTask(el);
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
  renderCurrentTask(container) {
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
      startBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian5.setIcon)(span, "play"));
      startBtn.createEl("span", { text: "Start" });
      startBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Next" });
      startBtn.addEventListener("click", () => this.handleAction("next"));
      const deferBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      deferBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian5.setIcon)(span, "clock"));
      deferBtn.createEl("span", { text: "Defer" });
      deferBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Someday" });
      deferBtn.addEventListener("click", () => this.handleAction("someday"));
      const waitBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      waitBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian5.setIcon)(span, "user"));
      waitBtn.createEl("span", { text: "Wait" });
      waitBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Waiting" });
      waitBtn.addEventListener("click", () => this.handleAction("waiting"));
      const scheduleBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      scheduleBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian5.setIcon)(span, "calendar"));
      scheduleBtn.createEl("span", { text: "Schedule" });
      scheduleBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Scheduled" });
      scheduleBtn.addEventListener("click", () => this.handleAction("scheduled"));
      const completeBtn = actions.createEl("button", { cls: "aio-inbox-action" });
      completeBtn.createEl("span", { cls: "aio-action-icon" }, (span) => (0, import_obsidian5.setIcon)(span, "check"));
      completeBtn.createEl("span", { text: "Done" });
      completeBtn.createEl("span", { cls: "aio-action-hint", text: "\u2192 Completed" });
      completeBtn.addEventListener("click", () => this.handleAction("completed"));
    });
    container.createEl("div", { cls: "aio-inbox-skip" }, (el) => {
      const skipBtn = el.createEl("button", { cls: "aio-skip-btn", text: "Skip for now" });
      skipBtn.addEventListener("click", () => {
        this.currentIndex = (this.currentIndex + 1) % this.inboxTasks.length;
        this.refresh();
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
      console.error("Error processing task:", e);
    }
  }
};

// src/modals/QuickAddModal.ts
var import_obsidian6 = require("obsidian");
var QuickAddModal = class extends import_obsidian6.Modal {
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
    new import_obsidian6.Setting(contentEl).setName("Title").setDesc("Task title (required)").addText((text) => {
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
    new import_obsidian6.Setting(contentEl).setName("Due Date").setDesc("Optional: YYYY-MM-DD or natural language (tomorrow, next friday)").addText((text) => text.setPlaceholder("tomorrow").setValue(this.dueDate).onChange((value) => {
      this.dueDate = value;
    }));
    new import_obsidian6.Setting(contentEl).setName("Project").setDesc("Optional: Link to a project").addDropdown(async (dropdown) => {
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
    submitBtn.addEventListener("click", () => {
      this.submit();
    });
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
        const parsed = this.parseDate(this.dueDate);
        if (parsed) {
          options.due = parsed;
        }
      }
      if (this.project) {
        options.project = `[[Projects/${this.project}]]`;
      }
      await this.plugin.taskService.createTask(this.title, options);
      this.onSubmit();
      this.close();
    } catch (e) {
      console.error("Error creating task:", e);
    }
  }
  /**
   * Simple natural language date parser.
   */
  parseDate(input) {
    const today = /* @__PURE__ */ new Date();
    const lowerInput = input.toLowerCase().trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(input)) {
      return input;
    }
    if (lowerInput === "today") {
      return today.toISOString().split("T")[0];
    }
    if (lowerInput === "tomorrow") {
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      return tomorrow.toISOString().split("T")[0];
    }
    if (lowerInput === "next week") {
      const nextWeek = new Date(today);
      nextWeek.setDate(nextWeek.getDate() + 7);
      return nextWeek.toISOString().split("T")[0];
    }
    const inDaysMatch = lowerInput.match(/^in (\d+) days?$/);
    if (inDaysMatch) {
      const days2 = parseInt(inDaysMatch[1], 10);
      const future = new Date(today);
      future.setDate(future.getDate() + days2);
      return future.toISOString().split("T")[0];
    }
    const days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
    const nextDayMatch = lowerInput.match(/^(next )?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$/);
    if (nextDayMatch) {
      const targetDay = days.indexOf(nextDayMatch[2]);
      const currentDay = today.getDay();
      let daysAhead = targetDay - currentDay;
      if (daysAhead <= 0 || nextDayMatch[1]) {
        daysAhead += 7;
      }
      const targetDate = new Date(today);
      targetDate.setDate(targetDate.getDate() + daysAhead);
      return targetDate.toISOString().split("T")[0];
    }
    if (lowerInput === "end of week" || lowerInput === "eow") {
      const currentDay = today.getDay();
      let daysUntilFriday = 5 - currentDay;
      if (daysUntilFriday <= 0) {
        daysUntilFriday += 7;
      }
      const friday = new Date(today);
      friday.setDate(friday.getDate() + daysUntilFriday);
      return friday.toISOString().split("T")[0];
    }
    if (lowerInput === "end of month" || lowerInput === "eom") {
      const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return endOfMonth.toISOString().split("T")[0];
    }
    return null;
  }
  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
};

// src/modals/TaskEditModal.ts
var import_obsidian7 = require("obsidian");
var TaskEditModal = class extends import_obsidian7.Modal {
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
    contentEl.createEl("div", { cls: "aio-task-id-display", text: `ID: ${this.task.id}` });
    new import_obsidian7.Setting(contentEl).setName("Title").addText((text) => text.setValue(this.title).onChange((value) => {
      this.title = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Status").addDropdown((dropdown) => dropdown.addOption("inbox", "Inbox").addOption("next", "Next").addOption("waiting", "Waiting").addOption("scheduled", "Scheduled").addOption("someday", "Someday").addOption("completed", "Completed").setValue(this.status).onChange((value) => {
      this.status = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Due Date").setDesc("YYYY-MM-DD format").addText((text) => text.setPlaceholder("YYYY-MM-DD").setValue(this.dueDate).onChange((value) => {
      this.dueDate = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Project").addDropdown(async (dropdown) => {
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
    new import_obsidian7.Setting(contentEl).setName("Assigned To").addDropdown(async (dropdown) => {
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
    new import_obsidian7.Setting(contentEl).setName("Waiting On").setDesc("Person or thing you are waiting for").addText((text) => text.setValue(this.waitingOn).onChange((value) => {
      this.waitingOn = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Time Estimate").setDesc("e.g., 30m, 2h, 1d").addText((text) => text.setPlaceholder("2h").setValue(this.timeEstimate).onChange((value) => {
      this.timeEstimate = value;
    }));
    new import_obsidian7.Setting(contentEl).setName("Tags").setDesc("Comma-separated list").addText((text) => text.setPlaceholder("backend, urgent").setValue(this.tags).onChange((value) => {
      this.tags = value;
    }));
    const buttonContainer = contentEl.createEl("div", { cls: "aio-modal-buttons" });
    const cancelBtn = buttonContainer.createEl("button", { text: "Cancel" });
    cancelBtn.addEventListener("click", () => {
      this.close();
    });
    const saveBtn = buttonContainer.createEl("button", { cls: "mod-cta", text: "Save" });
    saveBtn.addEventListener("click", () => {
      this.save();
    });
    const deleteBtn = buttonContainer.createEl("button", { cls: "mod-warning", text: "Delete" });
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
      console.error("Error saving task:", e);
    }
  }
  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
};

// src/main.ts
var AioPlugin = class extends import_obsidian8.Plugin {
  async onload() {
    await this.loadSettings();
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);
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
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
    this.vaultService = new VaultService(this.app, this.settings);
    this.taskService = new TaskService(this.app, this.settings);
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
   */
  getCurrentTask() {
    const file = this.app.workspace.getActiveFile();
    if (!file)
      return null;
    if (!file.path.includes(`${this.settings.aioFolderPath}/Tasks`)) {
      return null;
    }
    return null;
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
