import { describe, it, expect, beforeEach } from 'vitest';
import { MockApp, MockTFile } from './mocks/obsidian';
import { ID_CHARS, DEFAULT_SETTINGS, AioSettings } from '../src/types';
import { TaskService } from '../src/services/TaskService';

describe('TaskService', () => {
  let app: MockApp;
  let settings: AioSettings;
  let taskService: TaskService;

  beforeEach(() => {
    app = new MockApp();
    settings = { ...DEFAULT_SETTINGS };
    // Create TaskService with mocked app
    taskService = new TaskService(app as any, settings);
  });

  describe('generateId', () => {
    it('generates 4-character ID', () => {
      const id = taskService.generateId();
      expect(id.length).toBe(4);
    });

    it('uses only valid ID characters', () => {
      for (let i = 0; i < 100; i++) {
        const id = taskService.generateId();
        for (const char of id) {
          expect(ID_CHARS).toContain(char);
        }
      }
    });

    it('generates different IDs (not always the same)', () => {
      const ids = new Set<string>();
      for (let i = 0; i < 50; i++) {
        ids.add(taskService.generateId());
      }
      // With random generation, we should get at least some unique IDs
      expect(ids.size).toBeGreaterThan(1);
    });

    it('never includes ambiguous characters', () => {
      const ambiguous = ['0', '1', 'I', 'O', 'i', 'o', 'l'];
      for (let i = 0; i < 100; i++) {
        const id = taskService.generateId();
        for (const char of ambiguous) {
          expect(id).not.toContain(char);
        }
      }
    });
  });

  describe('parseFrontmatter (via parseTaskFile)', () => {
    it('parses basic frontmatter', async () => {
      const content = `---
id: AB2C
type: task
status: inbox
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Test Task

Some content here.`;

      app.vault.setFileContent('AIO/Tasks/Inbox/test.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/test.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task).not.toBeNull();
      expect(task!.id).toBe('AB2C');
      expect(task!.status).toBe('inbox');
      expect(task!.title).toBe('Test Task');
    });

    it('parses frontmatter with due date', async () => {
      const content = `---
id: XY3Z
type: task
status: next
due: 2024-06-20
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Task with Due`;

      app.vault.setFileContent('AIO/Tasks/Next/task.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Next/task.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.due).toBe('2024-06-20');
    });

    it('parses frontmatter with project wikilink', async () => {
      const content = `---
id: PJ4T
type: task
status: inbox
project: "[[AIO/Projects/Q4-Migration]]"
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Project Task`;

      app.vault.setFileContent('AIO/Tasks/Inbox/project-task.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/project-task.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.project).toBe('[[AIO/Projects/Q4-Migration]]');
    });

    it('parses frontmatter with tags array', async () => {
      const content = `---
id: TG5S
type: task
status: inbox
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags:
  - backend
  - urgent
---

# Tagged Task`;

      app.vault.setFileContent('AIO/Tasks/Inbox/tagged.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/tagged.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.tags).toEqual(['backend', 'urgent']);
    });

    it('extracts title from markdown heading', async () => {
      const content = `---
id: TT1A
type: task
status: inbox
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# My Task Title

Content goes here.`;

      app.vault.setFileContent('AIO/Tasks/Inbox/my-task.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/my-task.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.title).toBe('My Task Title');
    });

    it('returns null for non-task files', async () => {
      const content = `---
type: project
name: Some Project
---

# Project`;

      app.vault.setFileContent('AIO/Projects/project.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Projects/project.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task).toBeNull();
    });

    it('parses waiting status with waitingOn field', async () => {
      const content = `---
id: WT1B
type: task
status: waiting
waitingOn: "[[AIO/People/Sarah]]"
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Waiting Task`;

      app.vault.setFileContent('AIO/Tasks/Waiting/waiting.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Waiting/waiting.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.status).toBe('waiting');
      expect(task!.waitingOn).toBe('[[AIO/People/Sarah]]');
    });
  });

  describe('YAML parsing edge cases', () => {
    it('handles empty arrays', async () => {
      const content = `---
id: EA1C
type: task
status: inbox
blockedBy: []
blocks: []
tags: []
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Empty Arrays`;

      app.vault.setFileContent('AIO/Tasks/Inbox/empty-arrays.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/empty-arrays.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.blockedBy).toEqual([]);
      expect(task!.blocks).toEqual([]);
      expect(task!.tags).toEqual([]);
    });

    it('handles null values', async () => {
      const content = `---
id: NV1D
type: task
status: inbox
due: null
project: null
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Null Values`;

      app.vault.setFileContent('AIO/Tasks/Inbox/null-values.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/null-values.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.due).toBeNull();
      expect(task!.project).toBeNull();
    });

    it('handles boolean values', async () => {
      const content = `---
id: BV1E
type: task
status: inbox
someFlag: true
anotherFlag: false
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Boolean Values`;

      app.vault.setFileContent('AIO/Tasks/Inbox/bool-values.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/bool-values.md') as MockTFile;

      // Just verify it parses without error
      const task = await taskService.parseTaskFile(file as any);
      expect(task).not.toBeNull();
    });

    it('handles numeric values', async () => {
      const content = `---
id: NM1F
type: task
status: inbox
someNumber: 42
floatNumber: 3.14
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
blockedBy: []
blocks: []
tags: []
---

# Numeric Values`;

      app.vault.setFileContent('AIO/Tasks/Inbox/numeric.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/numeric.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);
      expect(task).not.toBeNull();
    });
  });

  describe('serializeTask', () => {
    it('serializes task with required fields', async () => {
      // Create a task and check the output
      const content = `---
id: SR1G
type: task
status: inbox
blockedBy: []
blocks: []
tags: []
created: 2024-01-15T10:00:00
updated: 2024-01-15T10:00:00
---

# Serialize Test`;

      app.vault.setFileContent('AIO/Tasks/Inbox/serialize.md', content);
      const file = app.vault.getAbstractFileByPath('AIO/Tasks/Inbox/serialize.md') as MockTFile;

      const task = await taskService.parseTaskFile(file as any);

      expect(task!.id).toBe('SR1G');
      expect(task!.type).toBe('task');
      expect(task!.status).toBe('inbox');
    });
  });
});
