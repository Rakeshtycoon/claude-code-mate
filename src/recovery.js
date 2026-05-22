import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { validatePlan } from './planner.js';

export async function diagnose(store) {
  const report = {
    planFile: store.planFile,
    exists: existsSync(store.planFile),
    status: 'unknown',
    healthy: false,
    errors: [],
    backups: await store.listBackups(),
  };

  if (!report.exists) {
    report.status = 'missing';
    return report;
  }

  let data;
  try {
    data = JSON.parse(await readFile(store.planFile, 'utf8'));
  } catch (err) {
    report.status = 'corrupt';
    report.errors = [err.message];
    return report;
  }

  const errors = validatePlan(data);
  if (errors.length > 0) {
    report.status = 'invalid';
    report.errors = errors;
    return report;
  }

  report.status = 'healthy';
  report.healthy = true;
  return report;
}

export async function recover(store, { backupName } = {}) {
  const backups = await store.listBackups();
  if (backups.length === 0) {
    throw new Error('No backups available to recover from.');
  }

  let candidates = backups;
  if (backupName) {
    candidates = backups.filter((b) => b.name === backupName);
    if (candidates.length === 0) {
      throw new Error(`Backup not found: ${backupName}`);
    }
  }

  for (const backup of candidates) {
    let data;
    try {
      data = JSON.parse(await readFile(backup.path, 'utf8'));
    } catch {
      continue;
    }
    if (validatePlan(data).length > 0) continue;

    let preserved = null;
    if (existsSync(store.planFile)) {
      const stamp = new Date().toISOString().replace(/[:.]/g, '-');
      preserved = path.join(store.dataDir, `corrupt-${stamp}.json`);
      await copyFile(store.planFile, preserved);
    }
    await writeFile(store.planFile, JSON.stringify(data, null, 2), 'utf8');
    return { restoredFrom: backup.name, preserved, plan: data };
  }

  throw new Error('No valid backup could be restored.');
}
