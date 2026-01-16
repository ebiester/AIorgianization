import { Command } from 'commander';
import { taskService, TaskStatus } from '@aio/core';
import { printTaskList, printError } from '../utils/output.js';

export const listCommand = new Command('list')
  .description('List tasks')
  .argument('[filter]', 'Filter: inbox, next, waiting, someday, today, week, overdue, all')
  .option('-p, --project <project>', 'Filter by project')
  .option('-c, --context <context>', 'Filter by context')
  .option('-T, --team <team>', 'Filter by team')
  .option('--completed', 'Include completed tasks')
  .action(async (filter, options) => {
    try {
      let tasks;
      let title;

      switch (filter) {
        case 'inbox':
          tasks = await taskService.listInbox();
          title = 'Inbox';
          break;

        case 'next':
        case 'actions':
          tasks = await taskService.listNextActions();
          title = 'Next Actions';
          break;

        case 'waiting':
          tasks = await taskService.listWaitingFor();
          title = 'Waiting For';
          break;

        case 'someday':
        case 'maybe':
          tasks = await taskService.listSomedayMaybe();
          title = 'Someday/Maybe';
          break;

        case 'today':
          tasks = await taskService.listToday();
          title = 'Due Today';
          break;

        case 'overdue':
          tasks = await taskService.listOverdue();
          title = 'Overdue';
          break;

        case 'all':
          tasks = await taskService.list({ includeCompleted: options.completed });
          title = 'All Tasks';
          break;

        default:
          // Default: show next actions + inbox
          const inbox = await taskService.listInbox();
          const nextActions = await taskService.listNextActions();
          const inProgress = await taskService.list({ status: TaskStatus.IN_PROGRESS });

          if (inProgress.length > 0) {
            printTaskList(inProgress, 'In Progress');
          }
          if (nextActions.length > 0) {
            printTaskList(nextActions, 'Next Actions');
          }
          if (inbox.length > 0) {
            printTaskList(inbox, 'Inbox');
          }

          if (inProgress.length === 0 && nextActions.length === 0 && inbox.length === 0) {
            console.log('\n  No active tasks. Use `aio add` to create one.\n');
          }
          return;
      }

      printTaskList(tasks, title);
    } catch (error) {
      printError(`Failed to list tasks: ${error}`);
      process.exit(1);
    }
  });

// Shorthand aliases
export const lsCommand = new Command('ls')
  .description('List tasks (alias for list)')
  .argument('[filter]', 'Filter')
  .action(async (filter) => {
    await listCommand.parseAsync(['list', filter ?? ''], { from: 'user' });
  });

export const lCommand = new Command('l')
  .description('List tasks (alias for list)')
  .argument('[filter]', 'Filter')
  .action(async (filter) => {
    await listCommand.parseAsync(['list', filter ?? ''], { from: 'user' });
  });
