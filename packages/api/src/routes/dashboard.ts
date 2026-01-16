import { Router } from 'express';
import { taskService, TaskStatus } from '@aio/core';

const router = Router();

// GET /api/dashboard/summary - Task counts by status
router.get('/summary', async (req, res) => {
  try {
    const [inbox, nextActions, inProgress, waitingFor, somedayMaybe, allTasks] = await Promise.all([
      taskService.listInbox(),
      taskService.listNextActions(),
      taskService.list({ status: TaskStatus.IN_PROGRESS }),
      taskService.listWaitingFor(),
      taskService.listSomedayMaybe(),
      taskService.list({ includeCompleted: false }),
    ]);

    // Calculate overdue
    const now = new Date();
    const overdue = allTasks.filter(
      (t) => t.dueDate && new Date(t.dueDate) < now
    );

    // Calculate due today
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    const startOfDay = new Date();
    startOfDay.setHours(0, 0, 0, 0);
    const dueToday = allTasks.filter(
      (t) => t.dueDate && new Date(t.dueDate) >= startOfDay && new Date(t.dueDate) <= today
    );

    res.json({
      inbox: inbox.length,
      nextActions: nextActions.length,
      inProgress: inProgress.length,
      waitingFor: waitingFor.length,
      somedayMaybe: somedayMaybe.length,
      overdue: overdue.length,
      dueToday: dueToday.length,
      total: allTasks.length,
    });
  } catch (error) {
    res.status(500).json({ error: 'Failed to get summary' });
  }
});

// GET /api/dashboard/today - Today's focus
router.get('/today', async (req, res) => {
  try {
    const [inProgress, overdue, dueToday] = await Promise.all([
      taskService.list({ status: TaskStatus.IN_PROGRESS }),
      taskService.listOverdue(),
      taskService.listToday(),
    ]);

    // Combine and dedupe
    const taskMap = new Map();
    [...inProgress, ...overdue, ...dueToday].forEach((t) => taskMap.set(t.id, t));

    const tasks = Array.from(taskMap.values()).sort((a, b) => {
      // Sort by: priority, then due date
      const priorityOrder = { P1: 0, P2: 1, P3: 2, P4: 3 };
      const aPri = a.priority ? priorityOrder[a.priority as keyof typeof priorityOrder] ?? 4 : 4;
      const bPri = b.priority ? priorityOrder[b.priority as keyof typeof priorityOrder] ?? 4 : 4;
      if (aPri !== bPri) return aPri - bPri;

      if (a.dueDate && b.dueDate) {
        return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
      }
      return a.dueDate ? -1 : 1;
    });

    res.json(tasks);
  } catch (error) {
    res.status(500).json({ error: 'Failed to get today tasks' });
  }
});

export { router as dashboardRoutes };
