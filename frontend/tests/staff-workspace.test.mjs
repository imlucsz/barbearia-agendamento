import test from 'node:test';
import assert from 'node:assert/strict';
import { staffDestination, staffAreas } from '../assets/js/staff-workspace.mjs';
test('admin hashes preserve every existing section and reject unknown/external destinations', () => {
  for (const area of staffAreas) for (const section of area.sections) assert.equal(staffDestination('#' + section, 'admin'), section);
  for (const hash of ['#missing', '//evil.test', '#<script>']) assert.equal(staffDestination(hash, 'admin'), 'agenda');
});
test('barber and unknown roles cannot navigate to management through a hash', () => {
  for (const role of ['barbeiro', 'cliente', null]) for (const area of staffAreas) for (const section of area.sections) assert.equal(staffDestination('#' + section, role), 'agenda');
});
