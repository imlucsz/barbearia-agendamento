import test from 'node:test';
import assert from 'node:assert/strict';
import { summarizeDay } from '../assets/js/staff-summary.mjs';
const now = new Date('2026-11-07T15:00:00Z'); // noon in São Paulo
const rows = [{ horario: '11:00', status: 'confirmado' }, { horario: '13:00', status: 'cancelado' }, { horario: '14:00', status: 'pendente' }, { horario: '10:00', status: 'avaliado' }];
test('summary distinguishes reservations, pending completion and completed; next excludes past/cancelled', () => {
  assert.deepEqual(summarizeDay(rows, '2026-11-07', now), { total: 4, pending: 2, completed: 1, next: rows[2] });
});
test('past date never offers a next appointment, future date includes first valid reservation', () => {
  assert.equal(summarizeDay(rows, '2026-11-06', now).next, null);
  assert.equal(summarizeDay(rows, '2026-11-08', now).next, rows[0]);
  assert.equal(summarizeDay([{ horario: '--:--', status: 'confirmado' }], '2026-11-08', now).next, null);
});
test('empty agenda reports zero reservations without implying working hours or available slots', () => {
  assert.deepEqual(summarizeDay([], '2026-11-07', now), { total: 0, pending: 0, completed: 0, next: null });
});
