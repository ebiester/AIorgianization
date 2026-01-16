import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from '../schema/index.js';
import { homedir } from 'os';
import { join } from 'path';
import { mkdirSync, existsSync } from 'fs';

const AIO_DIR = join(homedir(), '.aio');
const DB_FILE = 'aio.db';

export function getDbPath(): string {
  return join(AIO_DIR, DB_FILE);
}

export function ensureDbDir(): void {
  if (!existsSync(AIO_DIR)) {
    mkdirSync(AIO_DIR, { recursive: true });
  }
}

let dbInstance: ReturnType<typeof createDb> | null = null;

function createDb() {
  ensureDbDir();
  const sqlite = new Database(getDbPath());
  sqlite.pragma('journal_mode = WAL');
  return drizzle(sqlite, { schema });
}

export function getDb() {
  if (!dbInstance) {
    dbInstance = createDb();
  }
  return dbInstance;
}

export type Db = ReturnType<typeof getDb>;
