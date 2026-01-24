/**
 * Mock implementations of Obsidian API classes for testing.
 * These mocks allow testing TaskService and VaultService without Obsidian.
 */

/**
 * Mock TFile representing a markdown file.
 */
export class MockTFile {
  path: string;
  name: string;
  basename: string;
  extension: string;
  parent: MockTFolder | null = null;

  constructor(path: string, parent?: MockTFolder) {
    this.path = path;
    this.name = path.split('/').pop() || '';
    this.extension = this.name.includes('.') ? this.name.split('.').pop() || '' : '';
    this.basename = this.name.replace(/\.[^.]+$/, '');
    this.parent = parent || null;
  }
}

/**
 * Mock TFolder representing a folder.
 */
export class MockTFolder {
  path: string;
  name: string;
  children: (MockTFile | MockTFolder)[] = [];
  parent: MockTFolder | null = null;

  constructor(path: string, parent?: MockTFolder) {
    this.path = path;
    this.name = path.split('/').pop() || '';
    this.parent = parent || null;
  }

  addChild(child: MockTFile | MockTFolder): void {
    child.parent = this;
    this.children.push(child);
  }
}

/**
 * Mock Vault for file operations.
 */
export class MockVault {
  private files: Map<string, string> = new Map();
  private folders: Map<string, MockTFolder> = new Map();
  private root: MockTFolder;

  constructor() {
    this.root = new MockTFolder('');
    this.folders.set('', this.root);
  }

  /**
   * Read file contents.
   */
  async read(file: MockTFile): Promise<string> {
    return this.files.get(file.path) || '';
  }

  /**
   * Modify file contents.
   */
  async modify(file: MockTFile, content: string): Promise<void> {
    if (!this.files.has(file.path)) {
      throw new Error(`File not found: ${file.path}`);
    }
    this.files.set(file.path, content);
  }

  /**
   * Create a new file.
   */
  async create(path: string, content: string): Promise<MockTFile> {
    const normalizedPath = this.normalizePath(path);
    if (this.files.has(normalizedPath)) {
      throw new Error(`File already exists: ${normalizedPath}`);
    }

    // Ensure parent folder exists
    const parentPath = normalizedPath.split('/').slice(0, -1).join('/');
    if (parentPath && !this.folders.has(parentPath)) {
      await this.createFolder(parentPath);
    }

    this.files.set(normalizedPath, content);
    const parent = this.folders.get(parentPath) || this.root;
    const file = new MockTFile(normalizedPath, parent);
    parent.addChild(file);
    return file;
  }

  /**
   * Create a new folder.
   */
  async createFolder(path: string): Promise<void> {
    const normalizedPath = this.normalizePath(path);
    if (this.folders.has(normalizedPath)) {
      return; // Folder already exists
    }

    // Create parent folders recursively
    const parts = normalizedPath.split('/');
    let currentPath = '';
    let parent = this.root;

    for (const part of parts) {
      const newPath = currentPath ? `${currentPath}/${part}` : part;
      if (!this.folders.has(newPath)) {
        const folder = new MockTFolder(newPath, parent);
        this.folders.set(newPath, folder);
        parent.addChild(folder);
      }
      parent = this.folders.get(newPath)!;
      currentPath = newPath;
    }
  }

  /**
   * Get a file or folder by path.
   */
  getAbstractFileByPath(path: string): MockTFile | MockTFolder | null {
    const normalizedPath = this.normalizePath(path);

    // Check folders first
    if (this.folders.has(normalizedPath)) {
      return this.folders.get(normalizedPath)!;
    }

    // Check files
    if (this.files.has(normalizedPath)) {
      // Find the parent folder and return the file
      const parentPath = normalizedPath.split('/').slice(0, -1).join('/');
      const parent = this.folders.get(parentPath);
      if (parent) {
        const file = parent.children.find(
          (c): c is MockTFile => c instanceof MockTFile && c.path === normalizedPath
        );
        if (file) return file;
      }
      // Create a file object for the path
      return new MockTFile(normalizedPath);
    }

    return null;
  }

  /**
   * Delete a file.
   */
  async delete(file: MockTFile): Promise<void> {
    this.files.delete(file.path);
    if (file.parent) {
      const index = file.parent.children.indexOf(file);
      if (index > -1) {
        file.parent.children.splice(index, 1);
      }
    }
  }

  /**
   * Rename/move a file.
   */
  async rename(file: MockTFile, newPath: string): Promise<void> {
    const content = this.files.get(file.path);
    if (content === undefined) {
      throw new Error(`File not found: ${file.path}`);
    }

    // Remove from old location
    this.files.delete(file.path);
    if (file.parent) {
      const index = file.parent.children.indexOf(file);
      if (index > -1) {
        file.parent.children.splice(index, 1);
      }
    }

    // Add to new location
    const normalizedPath = this.normalizePath(newPath);
    const parentPath = normalizedPath.split('/').slice(0, -1).join('/');
    if (parentPath && !this.folders.has(parentPath)) {
      await this.createFolder(parentPath);
    }

    this.files.set(normalizedPath, content);
    file.path = normalizedPath;
    file.name = normalizedPath.split('/').pop() || '';
    file.basename = file.name.replace(/\.[^.]+$/, '');

    const newParent = this.folders.get(parentPath) || this.root;
    file.parent = newParent;
    newParent.addChild(file);
  }

  /**
   * Normalize a path (remove leading/trailing slashes, collapse multiple slashes).
   */
  private normalizePath(path: string): string {
    return path
      .replace(/\\/g, '/')
      .replace(/\/+/g, '/')
      .replace(/^\/|\/$/g, '');
  }

  // Helper methods for testing

  /**
   * Set file content directly (for test setup).
   */
  setFileContent(path: string, content: string): void {
    const normalizedPath = this.normalizePath(path);
    this.files.set(normalizedPath, content);

    // Create parent folders
    const parentPath = normalizedPath.split('/').slice(0, -1).join('/');
    if (parentPath && !this.folders.has(parentPath)) {
      const parts = parentPath.split('/');
      let currentPath = '';
      let parent = this.root;
      for (const part of parts) {
        const newPath = currentPath ? `${currentPath}/${part}` : part;
        if (!this.folders.has(newPath)) {
          const folder = new MockTFolder(newPath, parent);
          this.folders.set(newPath, folder);
          parent.addChild(folder);
        }
        parent = this.folders.get(newPath)!;
        currentPath = newPath;
      }
    }

    // Create file object
    const parent = parentPath ? this.folders.get(parentPath)! : this.root;
    const existingFile = parent.children.find(
      (c): c is MockTFile => c instanceof MockTFile && c.path === normalizedPath
    );
    if (!existingFile) {
      const file = new MockTFile(normalizedPath, parent);
      parent.addChild(file);
    }
  }

  /**
   * Get all file paths (for test assertions).
   */
  getAllFilePaths(): string[] {
    return Array.from(this.files.keys());
  }

  /**
   * Get file content directly (for test assertions).
   */
  getFileContent(path: string): string | undefined {
    return this.files.get(this.normalizePath(path));
  }

  /**
   * Check if folder exists.
   */
  hasFolder(path: string): boolean {
    return this.folders.has(this.normalizePath(path));
  }
}

/**
 * Mock FileManager for file operations.
 */
export class MockFileManager {
  constructor(private vault: MockVault) {}

  async renameFile(file: MockTFile, newPath: string): Promise<void> {
    await this.vault.rename(file, newPath);
  }
}

/**
 * Mock App combining all Obsidian services.
 */
export class MockApp {
  vault: MockVault;
  fileManager: MockFileManager;

  constructor() {
    this.vault = new MockVault();
    this.fileManager = new MockFileManager(this.vault);
  }
}

/**
 * Mock normalizePath function from Obsidian API.
 */
export function normalizePath(path: string): string {
  return path
    .replace(/\\/g, '/')
    .replace(/\/+/g, '/')
    .replace(/^\/|\/$/g, '');
}
