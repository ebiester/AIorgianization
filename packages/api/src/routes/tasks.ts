import { Router } from 'express';
import { taskService, TaskStatus } from '@aio/core';
import { z } from 'zod';
import * as chrono from 'chrono-node';

const router = Router();

// Validation schemas
const createTaskSchema = z.object({
  title: z.string().min(1),
  description: z.string().optional(),
  dueDate: z.string().optional(),
  priority: z.enum(['P1', 'P2', 'P3', 'P4']).optional(),
  status: z.string().optional(),
  projectId: z.string().optional(),
  assignedToId: z.string().optional(),
  teamId: z.string().optional(),
});

const updateTaskSchema = createTaskSchema.partial();

// GET /api/tasks - List tasks
router.get('/', async (req, res) => {
  try {
    const { status, includeCompleted } = req.query;

    const options: any = {
      includeCompleted: includeCompleted === 'true',
    };

    if (status && typeof status === 'string') {
      options.status = status;
    }

    const tasks = await taskService.list(options);
    res.json(tasks);
  } catch (error) {
    res.status(500).json({ error: 'Failed to list tasks' });
  }
});

// GET /api/tasks/:id - Get single task
router.get('/:id', async (req, res) => {
  try {
    const task = await taskService.getById(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: 'Failed to get task' });
  }
});

// POST /api/tasks - Create task
router.post('/', async (req, res) => {
  try {
    const data = createTaskSchema.parse(req.body);

    let dueDate: Date | undefined;
    if (data.dueDate) {
      dueDate = chrono.parseDate(data.dueDate) ?? undefined;
    }

    const task = await taskService.create({
      ...data,
      dueDate,
    });

    res.status(201).json(task);
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    res.status(500).json({ error: 'Failed to create task' });
  }
});

// PATCH /api/tasks/:id - Update task
router.patch('/:id', async (req, res) => {
  try {
    const data = updateTaskSchema.parse(req.body);

    let dueDate: Date | undefined;
    if (data.dueDate) {
      dueDate = chrono.parseDate(data.dueDate) ?? undefined;
    }

    const task = await taskService.update(req.params.id, {
      ...data,
      dueDate: dueDate ?? (data.dueDate === '' ? undefined : undefined),
    });

    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }

    res.json(task);
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(400).json({ error: 'Validation failed', details: error.errors });
    }
    res.status(500).json({ error: 'Failed to update task' });
  }
});

// DELETE /api/tasks/:id - Delete task
router.delete('/:id', async (req, res) => {
  try {
    await taskService.delete(req.params.id);
    res.status(204).send();
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete task' });
  }
});

// POST /api/tasks/:id/complete - Mark complete
router.post('/:id/complete', async (req, res) => {
  try {
    const task = await taskService.complete(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: 'Failed to complete task' });
  }
});

// POST /api/tasks/:id/start - Start task
router.post('/:id/start', async (req, res) => {
  try {
    const task = await taskService.start(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: 'Failed to start task' });
  }
});

// POST /api/tasks/:id/activate - Move to next actions
router.post('/:id/activate', async (req, res) => {
  try {
    const task = await taskService.activate(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: 'Failed to activate task' });
  }
});

// POST /api/tasks/:id/defer - Defer to someday
router.post('/:id/defer', async (req, res) => {
  try {
    const task = await taskService.defer(req.params.id);
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    res.json(task);
  } catch (error) {
    res.status(500).json({ error: 'Failed to defer task' });
  }
});

export { router as taskRoutes };
