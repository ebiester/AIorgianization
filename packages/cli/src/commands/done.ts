import { Command } from 'commander';
import { taskService } from '@aio/core';
import { printSuccess, printError, printInfo } from '../utils/output.js';

async function findTask(idOrQuery: string) {
  // First try exact ID match
  let task = await taskService.getById(idOrQuery);
  if (task) return task;

  // Try partial ID match (last 6 characters)
  const allTasks = await taskService.list({ includeCompleted: false });
  task = allTasks.find((t) => t.id.endsWith(idOrQuery));
  if (task) return task;

  // Try title match
  task = allTasks.find((t) => t.title.toLowerCase().includes(idOrQuery.toLowerCase()));
  return task;
}

export const doneCommand = new Command('done')
  .description('Mark a task as completed')
  .argument('<task>', 'Task ID or title fragment')
  .action(async (taskQuery) => {
    try {
      const task = await findTask(taskQuery);
      if (!task) {
        printError(`Task not found: "${taskQuery}"`);
        process.exit(1);
      }

      const completed = await taskService.complete(task.id);
      if (completed) {
        printSuccess(`Completed: ${completed.title}`);
      }
    } catch (error) {
      printError(`Failed to complete task: ${error}`);
      process.exit(1);
    }
  });

export const startCommand = new Command('start')
  .description('Start working on a task')
  .argument('<task>', 'Task ID or title fragment')
  .action(async (taskQuery) => {
    try {
      const task = await findTask(taskQuery);
      if (!task) {
        printError(`Task not found: "${taskQuery}"`);
        process.exit(1);
      }

      const updated = await taskService.start(task.id);
      if (updated) {
        printSuccess(`Started: ${updated.title}`);
      }
    } catch (error) {
      printError(`Failed to start task: ${error}`);
      process.exit(1);
    }
  });

export const deferCommand = new Command('defer')
  .description('Defer a task to someday/maybe')
  .argument('<task>', 'Task ID or title fragment')
  .action(async (taskQuery) => {
    try {
      const task = await findTask(taskQuery);
      if (!task) {
        printError(`Task not found: "${taskQuery}"`);
        process.exit(1);
      }

      const updated = await taskService.defer(task.id);
      if (updated) {
        printSuccess(`Deferred: ${updated.title}`);
        printInfo('Moved to Someday/Maybe');
      }
    } catch (error) {
      printError(`Failed to defer task: ${error}`);
      process.exit(1);
    }
  });

export const waitCommand = new Command('wait')
  .description('Move task to waiting-for')
  .argument('<task>', 'Task ID or title fragment')
  .argument('[person]', 'Person you are waiting on')
  .action(async (taskQuery, person) => {
    try {
      const task = await findTask(taskQuery);
      if (!task) {
        printError(`Task not found: "${taskQuery}"`);
        process.exit(1);
      }

      const updated = await taskService.moveToWaiting(task.id, person);
      if (updated) {
        printSuccess(`Waiting: ${updated.title}`);
        if (person) {
          printInfo(`Waiting on: ${person}`);
        }
      }
    } catch (error) {
      printError(`Failed to update task: ${error}`);
      process.exit(1);
    }
  });

export const activateCommand = new Command('activate')
  .description('Move task to next actions')
  .argument('<task>', 'Task ID or title fragment')
  .action(async (taskQuery) => {
    try {
      const task = await findTask(taskQuery);
      if (!task) {
        printError(`Task not found: "${taskQuery}"`);
        process.exit(1);
      }

      const updated = await taskService.activate(task.id);
      if (updated) {
        printSuccess(`Activated: ${updated.title}`);
        printInfo('Moved to Next Actions');
      }
    } catch (error) {
      printError(`Failed to activate task: ${error}`);
      process.exit(1);
    }
  });
