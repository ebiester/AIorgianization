import { eq, and, isNull, lte, gte, desc, asc, ne, notInArray } from 'drizzle-orm';
import { ulid } from 'ulid';
import { getDb, type Db } from '../db/client.js';
import { tasks, TaskStatus, type Task, type NewTask } from '../schema/index.js';

export interface CreateTaskInput {
  title: string;
  description?: string;
  status?: string;
  taskType?: string;
  priority?: string;
  projectId?: string;
  assignedToId?: string;
  teamId?: string;
  dueDate?: Date;
  timeEstimateMinutes?: number;
  obsidianNotePath?: string;
}

export interface ListTasksOptions {
  status?: string | string[];
  projectId?: string;
  assignedToId?: string;
  teamId?: string;
  dueBefore?: Date;
  dueAfter?: Date;
  includeCompleted?: boolean;
}

export class TaskService {
  private db: Db;

  constructor(db?: Db) {
    this.db = db ?? getDb();
  }

  async create(input: CreateTaskInput): Promise<Task> {
    const now = new Date();
    const id = ulid();

    const newTask: NewTask = {
      id,
      title: input.title,
      description: input.description,
      status: input.status ?? TaskStatus.INBOX,
      taskType: input.taskType ?? 'personal',
      priority: input.priority,
      projectId: input.projectId,
      assignedToId: input.assignedToId,
      teamId: input.teamId,
      dueDate: input.dueDate,
      timeEstimateMinutes: input.timeEstimateMinutes,
      obsidianNotePath: input.obsidianNotePath,
      createdAt: now,
      updatedAt: now,
    };

    await this.db.insert(tasks).values(newTask);
    return this.getById(id) as Promise<Task>;
  }

  async getById(id: string): Promise<Task | undefined> {
    const result = await this.db.select().from(tasks).where(eq(tasks.id, id));
    return result[0];
  }

  async list(options: ListTasksOptions = {}): Promise<Task[]> {
    const conditions = [];

    if (options.status) {
      if (Array.isArray(options.status)) {
        // Handle array of statuses with OR
        const statusConditions = options.status.map((s) => eq(tasks.status, s));
        // For simplicity, we'll filter in JS if multiple statuses
      } else {
        conditions.push(eq(tasks.status, options.status));
      }
    }

    if (options.projectId) {
      conditions.push(eq(tasks.projectId, options.projectId));
    }

    if (options.assignedToId) {
      conditions.push(eq(tasks.assignedToId, options.assignedToId));
    }

    if (options.teamId) {
      conditions.push(eq(tasks.teamId, options.teamId));
    }

    if (options.dueBefore) {
      conditions.push(lte(tasks.dueDate, options.dueBefore));
    }

    if (options.dueAfter) {
      conditions.push(gte(tasks.dueDate, options.dueAfter));
    }

    if (!options.includeCompleted) {
      conditions.push(
        notInArray(tasks.status, [TaskStatus.COMPLETED, TaskStatus.ARCHIVED])
      );
    }

    let query = this.db.select().from(tasks);

    if (conditions.length > 0) {
      query = query.where(and(...conditions)) as typeof query;
    }

    const result = await query.orderBy(asc(tasks.dueDate), desc(tasks.createdAt));

    // Post-filter for array of statuses
    if (Array.isArray(options.status)) {
      return result.filter((t) => options.status!.includes(t.status));
    }

    return result;
  }

  async listInbox(): Promise<Task[]> {
    return this.list({ status: TaskStatus.INBOX });
  }

  async listNextActions(): Promise<Task[]> {
    return this.list({ status: TaskStatus.NEXT_ACTION });
  }

  async listWaitingFor(): Promise<Task[]> {
    return this.list({ status: TaskStatus.WAITING_FOR });
  }

  async listSomedayMaybe(): Promise<Task[]> {
    return this.list({ status: TaskStatus.SOMEDAY_MAYBE });
  }

  async listToday(): Promise<Task[]> {
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    return this.list({ dueBefore: today });
  }

  async listOverdue(): Promise<Task[]> {
    const now = new Date();
    const result = await this.list({ dueBefore: now });
    return result.filter(
      (t) => t.status !== TaskStatus.COMPLETED && t.status !== TaskStatus.ARCHIVED
    );
  }

  async update(id: string, updates: Partial<CreateTaskInput>): Promise<Task | undefined> {
    const task = await this.getById(id);
    if (!task) return undefined;

    await this.db
      .update(tasks)
      .set({
        ...updates,
        updatedAt: new Date(),
      })
      .where(eq(tasks.id, id));

    return this.getById(id);
  }

  async complete(id: string): Promise<Task | undefined> {
    const task = await this.getById(id);
    if (!task) return undefined;

    const now = new Date();
    await this.db
      .update(tasks)
      .set({
        status: TaskStatus.COMPLETED,
        completedAt: now,
        updatedAt: now,
      })
      .where(eq(tasks.id, id));

    return this.getById(id);
  }

  async defer(id: string): Promise<Task | undefined> {
    return this.update(id, { status: TaskStatus.SOMEDAY_MAYBE });
  }

  async moveToWaiting(id: string, assignedToId?: string): Promise<Task | undefined> {
    const updates: Partial<CreateTaskInput> = { status: TaskStatus.WAITING_FOR };
    if (assignedToId) {
      updates.assignedToId = assignedToId;
    }
    return this.update(id, updates);
  }

  async start(id: string): Promise<Task | undefined> {
    return this.update(id, { status: TaskStatus.IN_PROGRESS });
  }

  async activate(id: string): Promise<Task | undefined> {
    return this.update(id, { status: TaskStatus.NEXT_ACTION });
  }

  async delete(id: string): Promise<boolean> {
    const result = await this.db.delete(tasks).where(eq(tasks.id, id));
    return true;
  }
}

export const taskService = new TaskService();
