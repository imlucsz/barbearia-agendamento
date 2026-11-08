import test from "node:test";
import assert from "node:assert/strict";
import { bookingNavigation } from "../assets/js/product-navigation.mjs";

test("booking progress only links to completed steps with their required context", () => {
  const steps = bookingNavigation("confirm", "service_id=2&barbeiro_id=9&date_time=2026-11-09&token=private&redirect=https://example.com");
  assert.deepEqual(steps.map(s => s.href), ["client-services.html", "client-profissional.html?service_id=2", "client-date.html?service_id=2&barbeiro_id=9", null]);
  assert.equal(steps.filter(s => s.current).length, 1);
  assert.equal(steps[3].current, true);
});

test("rescheduling never offers changing service or professional and retains appointment ID", () => {
  const steps = bookingNavigation("confirm", "service_id=2&barbeiro_id=9&appointment_id=7");
  assert.deepEqual(steps.map(s => s.href), [null, null, "client-date.html?service_id=2&barbeiro_id=9&appointment_id=7", null]);
  assert.ok(bookingNavigation("date", "service_id=2&barbeiro_id=9&appointment_id=7").every(s => !s.href));
});

test("missing context does not create broken links; values cannot inject another destination", () => {
  assert.deepEqual(bookingNavigation("confirm", "").map(s => s.href), ["client-services.html", null, null, null]);
  const link = bookingNavigation("date", "service_id=%22%3E%3Cscript%3E&redirect=//evil.test")[1].href;
  assert.equal(link, "client-profissional.html?service_id=%22%3E%3Cscript%3E");
  assert.ok(bookingNavigation("services", "").every(s => !s.href));
});
