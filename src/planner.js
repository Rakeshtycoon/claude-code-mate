import { randomUUID } from 'node:crypto';

const PLAN_VERSION = 1;

export function createPlan() {
  const now = new Date().toISOString();
  return {
    version: PLAN_VERSION,
    medications: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function addMedication(plan, {
  name,
  dosage,
  frequency,
  times = [],
  startDate,
  endDate = null,
} = {}) {
  if (typeof name !== 'string' || name.trim() === '') {
    throw new Error('Medication name is required.');
  }
  const medication = {
    id: randomUUID(),
    name: name.trim(),
    dosage: typeof dosage === 'string' ? dosage.trim() : '',
    frequency: typeof frequency === 'string' && frequency.trim() !== '' ? frequency.trim() : 'daily',
    times: Array.isArray(times) ? times : [],
    startDate: typeof startDate === 'string' && startDate !== '' ? startDate : todayStr(),
    endDate: typeof endDate === 'string' && endDate !== '' ? endDate : null,
  };
  plan.medications.push(medication);
  plan.updatedAt = new Date().toISOString();
  return medication;
}

export function removeMedication(plan, id) {
  const index = plan.medications.findIndex((m) => m.id === id);
  if (index === -1) return false;
  plan.medications.splice(index, 1);
  plan.updatedAt = new Date().toISOString();
  return true;
}

export function medicationsForDate(plan, dateStr) {
  const date = dateStr ?? todayStr();
  return plan.medications.filter((m) => {
    if (m.startDate && date < m.startDate) return false;
    if (m.endDate && date > m.endDate) return false;
    return true;
  });
}

export function validatePlan(plan) {
  if (plan === null || typeof plan !== 'object' || Array.isArray(plan)) {
    return ['Plan must be an object.'];
  }
  if (!Array.isArray(plan.medications)) {
    return ['Plan must have a medications array.'];
  }
  const errors = [];
  plan.medications.forEach((m, i) => {
    if (m === null || typeof m !== 'object' || Array.isArray(m)) {
      errors.push(`Medication #${i} is not an object.`);
      return;
    }
    if (!m.id) errors.push(`Medication #${i} is missing an id.`);
    if (!m.name) errors.push(`Medication #${i} is missing a name.`);
  });
  return errors;
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
