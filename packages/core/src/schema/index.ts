import { sqliteTable, text, integer, primaryKey } from 'drizzle-orm/sqlite-core';

// ============ ENUMS (as const for TypeScript) ============

export const TaskStatus = {
  INBOX: 'inbox',
  NEXT_ACTION: 'next_action',
  WAITING_FOR: 'waiting_for',
  SCHEDULED: 'scheduled',
  SOMEDAY_MAYBE: 'someday_maybe',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  ARCHIVED: 'archived',
} as const;

export type TaskStatus = (typeof TaskStatus)[keyof typeof TaskStatus];

export const TaskType = {
  PERSONAL: 'personal',
  DELEGATED: 'delegated',
  TEAM: 'team',
} as const;

export type TaskType = (typeof TaskType)[keyof typeof TaskType];

export const PARACategory = {
  PROJECT: 'project',
  AREA: 'area',
  RESOURCE: 'resource',
  ARCHIVE: 'archive',
} as const;

export type PARACategory = (typeof PARACategory)[keyof typeof PARACategory];

export const Priority = {
  P1: 'P1', // Urgent + Important
  P2: 'P2', // Not Urgent + Important
  P3: 'P3', // Urgent + Not Important
  P4: 'P4', // Not Urgent + Not Important
} as const;

export type Priority = (typeof Priority)[keyof typeof Priority];

// ============ TABLES ============

export const teams = sqliteTable('teams', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  jiraProjectKey: text('jira_project_key'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const people = sqliteTable('people', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  email: text('email'),
  teamId: text('team_id').references(() => teams.id),
  jiraAccountId: text('jira_account_id'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const contexts = sqliteTable('contexts', {
  id: text('id').primaryKey(),
  name: text('name').notNull().unique(),
  description: text('description'),
  icon: text('icon'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
});

export const projects = sqliteTable('projects', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  outcome: text('outcome'),
  paraCategory: text('para_category').notNull().default('project'),
  status: text('status').notNull().default('active'),
  teamId: text('team_id').references(() => teams.id),
  parentProjectId: text('parent_project_id'),
  obsidianNotePath: text('obsidian_note_path'),
  jiraProjectKey: text('jira_project_key'),
  jiraEpicKey: text('jira_epic_key'),
  startDate: integer('start_date', { mode: 'timestamp' }),
  targetDate: integer('target_date', { mode: 'timestamp' }),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const tasks = sqliteTable('tasks', {
  id: text('id').primaryKey(),
  title: text('title').notNull(),
  description: text('description'),
  status: text('status').notNull().default('inbox'),
  taskType: text('task_type').notNull().default('personal'),
  priority: text('priority'),
  energyLevel: text('energy_level'),
  timeEstimateMinutes: integer('time_estimate_minutes'),
  projectId: text('project_id').references(() => projects.id),
  parentTaskId: text('parent_task_id'),
  assignedToId: text('assigned_to_id').references(() => people.id),
  delegatedById: text('delegated_by_id').references(() => people.id),
  teamId: text('team_id').references(() => teams.id),
  obsidianNotePath: text('obsidian_note_path'),
  obsidianBlockRef: text('obsidian_block_ref'),
  jiraIssueKey: text('jira_issue_key'),
  jiraIssueId: text('jira_issue_id'),
  jiraSyncStatus: text('jira_sync_status'),
  jiraLastSyncedAt: integer('jira_last_synced_at', { mode: 'timestamp' }),
  dueDate: integer('due_date', { mode: 'timestamp' }),
  startDate: integer('start_date', { mode: 'timestamp' }),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  recurrenceRule: text('recurrence_rule'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const taskContexts = sqliteTable(
  'task_contexts',
  {
    taskId: text('task_id')
      .references(() => tasks.id, { onDelete: 'cascade' })
      .notNull(),
    contextId: text('context_id')
      .references(() => contexts.id, { onDelete: 'cascade' })
      .notNull(),
  },
  (table) => [primaryKey({ columns: [table.taskId, table.contextId] })]
);

export const tags = sqliteTable('tags', {
  id: text('id').primaryKey(),
  name: text('name').notNull().unique(),
  color: text('color'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
});

export const taskTags = sqliteTable(
  'task_tags',
  {
    taskId: text('task_id')
      .references(() => tasks.id, { onDelete: 'cascade' })
      .notNull(),
    tagId: text('tag_id')
      .references(() => tags.id, { onDelete: 'cascade' })
      .notNull(),
  },
  (table) => [primaryKey({ columns: [table.taskId, table.tagId] })]
);

export const weeklyReviews = sqliteTable('weekly_reviews', {
  id: text('id').primaryKey(),
  weekStart: integer('week_start', { mode: 'timestamp' }).notNull(),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  notes: text('notes'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
});

export const syncLog = sqliteTable('sync_log', {
  id: text('id').primaryKey(),
  syncType: text('sync_type').notNull(),
  startedAt: integer('started_at', { mode: 'timestamp' }).notNull(),
  completedAt: integer('completed_at', { mode: 'timestamp' }),
  status: text('status').notNull(),
  itemsSynced: integer('items_synced'),
  errorMessage: text('error_message'),
});

// ============ TYPE INFERENCE ============

export type Team = typeof teams.$inferSelect;
export type NewTeam = typeof teams.$inferInsert;

export type Person = typeof people.$inferSelect;
export type NewPerson = typeof people.$inferInsert;

export type Context = typeof contexts.$inferSelect;
export type NewContext = typeof contexts.$inferInsert;

export type Project = typeof projects.$inferSelect;
export type NewProject = typeof projects.$inferInsert;

export type Task = typeof tasks.$inferSelect;
export type NewTask = typeof tasks.$inferInsert;

export type Tag = typeof tags.$inferSelect;
export type NewTag = typeof tags.$inferInsert;

export type WeeklyReview = typeof weeklyReviews.$inferSelect;
export type NewWeeklyReview = typeof weeklyReviews.$inferInsert;
