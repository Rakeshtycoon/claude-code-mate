import { readFile, writeFile, mkdir, readdir, stat, rm } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import path from 'node:path';

const DEFAULT_DATA_DIR = path.join(process.cwd(), 'data');

export class PlanStore {
  constructor(dataDir = DEFAULT_DATA_DIR, { maxBackups = 20 } = {}) {
    this.dataDir = dataDir;
    this.backupDir = path.join(dataDir, 'backups');
    this.planFile = path.join(dataDir, 'plan.json');
    this.maxBackups = maxBackups;
  }

  async init() {
    await mkdir(this.backupDir, { recursive: true });
  }

  exists() {
    return existsSync(this.planFile);
  }

  async load() {
    if (!existsSync(this.planFile)) return null;
    return JSON.parse(await readFile(this.planFile, 'utf8'));
  }

  async save(plan) {
    await this.init();
    if (existsSync(this.planFile)) {
      await this.backup();
    }
    await writeFile(this.planFile, JSON.stringify(plan, null, 2), 'utf8');
    return this.planFile;
  }

  async backup() {
    if (!existsSync(this.planFile)) {
      throw new Error('No plan data to back up.');
    }
    await this.init();
    const raw = await readFile(this.planFile, 'utf8');
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const dest = path.join(this.backupDir, `plan-${stamp}-${randomUUID().slice(0, 8)}.json`);
    await writeFile(dest, raw, 'utf8');
    await this.#prune();
    return dest;
  }

  async listBackups() {
    if (!existsSync(this.backupDir)) return [];
    const entries = [];
    for (const file of await readdir(this.backupDir)) {
      if (!file.startsWith('plan-') || !file.endsWith('.json')) continue;
      const full = path.join(this.backupDir, file);
      const info = await stat(full);
      entries.push({ name: file, path: full, mtime: info.mtime, size: info.size });
    }
    entries.sort((a, b) => b.mtime - a.mtime);
    return entries;
  }

  async #prune() {
    const backups = await this.listBackups();
    for (const old of backups.slice(this.maxBackups)) {
      await rm(old.path, { force: true });
    }
  }
}
