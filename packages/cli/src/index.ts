#!/usr/bin/env node

import { Command } from 'commander';
import { addCommand, quickAddCommand } from './commands/add.js';
import { listCommand, lsCommand, lCommand } from './commands/list.js';
import {
  doneCommand,
  startCommand,
  deferCommand,
  waitCommand,
  activateCommand,
} from './commands/done.js';

const program = new Command();

program
  .name('aio')
  .description('AIorgianization - Personal task and deadline management')
  .version('0.1.0');

// Task commands
program.addCommand(addCommand);
program.addCommand(quickAddCommand);
program.addCommand(listCommand);
program.addCommand(lsCommand);
program.addCommand(lCommand);
program.addCommand(doneCommand);
program.addCommand(startCommand);
program.addCommand(deferCommand);
program.addCommand(waitCommand);
program.addCommand(activateCommand);

// Parse and run
program.parse();
