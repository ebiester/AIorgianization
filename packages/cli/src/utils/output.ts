import chalk from 'chalk';
import Table from 'cli-table3';
import type { Task } from '@aio/core';
import { formatDate } from './date-parser.js';

export function printSuccess(message: string): void {
  console.log(chalk.green('✓'), message);
}

export function printError(message: string): void {
  console.error(chalk.red('✗'), message);
}

export function printWarning(message: string): void {
  console.log(chalk.yellow('!'), message);
}

export function printInfo(message: string): void {
  console.log(chalk.blue('i'), message);
}

function getPriorityColor(priority: string | null): (text: string) => string {
  switch (priority) {
    case 'P1':
      return chalk.red;
    case 'P2':
      return chalk.yellow;
    case 'P3':
      return chalk.blue;
    case 'P4':
      return chalk.gray;
    default:
      return (t: string) => t;
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'inbox':
      return '📥';
    case 'next_action':
      return '→';
    case 'in_progress':
      return '▶';
    case 'waiting_for':
      return '⏳';
    case 'scheduled':
      return '📅';
    case 'someday_maybe':
      return '💭';
    case 'completed':
      return '✓';
    case 'archived':
      return '📦';
    default:
      return '○';
  }
}

function getDueDateColor(dueDate: Date | null): (text: string) => string {
  if (!dueDate) return (t: string) => t;

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dateOnly = new Date(dueDate.getFullYear(), dueDate.getMonth(), dueDate.getDate());

  if (dateOnly < today) {
    return chalk.red; // Overdue
  }
  if (dateOnly.getTime() === today.getTime()) {
    return chalk.yellow; // Today
  }
  return (t: string) => t;
}

export function printTaskList(tasks: Task[], title?: string): void {
  if (title) {
    console.log(chalk.bold(`\n${title}`));
    console.log(chalk.gray('─'.repeat(50)));
  }

  if (tasks.length === 0) {
    console.log(chalk.gray('  No tasks found'));
    return;
  }

  const table = new Table({
    head: ['', 'ID', 'Task', 'Due', 'Pri'],
    colWidths: [3, 10, 40, 12, 4],
    style: { head: ['cyan'] },
    chars: {
      top: '', 'top-mid': '', 'top-left': '', 'top-right': '',
      bottom: '', 'bottom-mid': '', 'bottom-left': '', 'bottom-right': '',
      left: '', 'left-mid': '', mid: '', 'mid-mid': '',
      right: '', 'right-mid': '', middle: ' ',
    },
  });

  for (const task of tasks) {
    const icon = getStatusIcon(task.status);
    const shortId = task.id.slice(-6);
    const priorityColor = getPriorityColor(task.priority);
    const dueDateColor = getDueDateColor(task.dueDate);
    const dueStr = formatDate(task.dueDate);

    table.push([
      icon,
      chalk.gray(shortId),
      task.title.length > 38 ? task.title.slice(0, 35) + '...' : task.title,
      dueDateColor(dueStr),
      task.priority ? priorityColor(task.priority) : '-',
    ]);
  }

  console.log(table.toString());
  console.log(chalk.gray(`\n  ${tasks.length} task${tasks.length === 1 ? '' : 's'}`));
}

export function printTask(task: Task): void {
  console.log();
  console.log(chalk.bold(task.title));
  console.log(chalk.gray('─'.repeat(50)));
  console.log(`  ID:       ${chalk.gray(task.id)}`);
  console.log(`  Status:   ${getStatusIcon(task.status)} ${task.status}`);
  console.log(`  Type:     ${task.taskType}`);
  if (task.priority) {
    const color = getPriorityColor(task.priority);
    console.log(`  Priority: ${color(task.priority)}`);
  }
  if (task.dueDate) {
    const color = getDueDateColor(task.dueDate);
    console.log(`  Due:      ${color(formatDate(task.dueDate))}`);
  }
  if (task.description) {
    console.log(`  Notes:    ${task.description}`);
  }
  console.log();
}
