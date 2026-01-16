import { Command } from 'commander';
import { taskService, TaskStatus } from '@aio/core';
import { parseDate } from '../utils/date-parser.js';
import { printSuccess, printError, printTask } from '../utils/output.js';

export const addCommand = new Command('add')
  .description('Add a new task')
  .argument('<title>', 'Task title')
  .option('-d, --due <date>', 'Due date (natural language: tomorrow, next monday, etc.)')
  .option('-p, --project <project>', 'Project name or ID')
  .option('-P, --priority <priority>', 'Priority (P1, P2, P3, P4)')
  .option('-c, --context <context>', 'Context (@work, @home, etc.)')
  .option('-T, --team <team>', 'Team name')
  .option('-a, --assign <person>', 'Assign to person')
  .option('--time <estimate>', 'Time estimate (15m, 1h, 2h)')
  .option('--note <path>', 'Link to Obsidian note')
  .option('-s, --status <status>', 'Initial status (default: inbox)')
  .action(async (title, options) => {
    try {
      let dueDate: Date | undefined;
      if (options.due) {
        const parsed = parseDate(options.due);
        if (!parsed) {
          printError(`Could not parse date: "${options.due}"`);
          process.exit(1);
        }
        dueDate = parsed;
      }

      let timeEstimateMinutes: number | undefined;
      if (options.time) {
        const match = options.time.match(/^(\d+)(m|h)$/);
        if (match) {
          const value = parseInt(match[1], 10);
          const unit = match[2];
          timeEstimateMinutes = unit === 'h' ? value * 60 : value;
        }
      }

      const task = await taskService.create({
        title,
        dueDate,
        priority: options.priority,
        projectId: options.project,
        teamId: options.team,
        assignedToId: options.assign,
        timeEstimateMinutes,
        obsidianNotePath: options.note,
        status: options.status ?? TaskStatus.INBOX,
      });

      printSuccess(`Added task: ${task.title}`);
      printTask(task);
    } catch (error) {
      printError(`Failed to add task: ${error}`);
      process.exit(1);
    }
  });

// Shorthand alias
export const quickAddCommand = new Command('a')
  .description('Quick add a task (alias for add)')
  .argument('<title>', 'Task title')
  .option('-d, --due <date>', 'Due date')
  .option('-P, --priority <priority>', 'Priority')
  .action(async (title, options) => {
    // Delegate to add command
    await addCommand.parseAsync(['add', title, ...process.argv.slice(3)], { from: 'user' });
  });
