import test from "node:test";
import assert from "node:assert/strict";
import { bookingDateBounds, isBookableDate, isBookableDateTime } from "../assets/js/booking-date.mjs";

const now = new Date("2026-11-04T15:00:00-03:00");
test("rejects incomplete years, impossible dates and outside window", () => {
  for (const value of ["", "2026-11-", "2026-1-11", "2026-11-11extra", "0002-11-11", "0202-11-11", "0020-11-11", "2026-02-30", "2026-11-31", "2026-11-19", "2026-11-03"]) assert.equal(isBookableDate(value, now), false, value);
});

test("calendar month rollover, leap years and bounds use Sao Paulo", () => {
  assert.equal(isBookableDate("2028-02-29", new Date("2028-02-20T12:00:00Z")), true);
  assert.equal(isBookableDate("2027-02-29", new Date("2027-02-20T12:00:00Z")), false);
  assert.deepEqual(bookingDateBounds(new Date("2026-11-01T01:00:00Z")), { min: "2026-10-31", max: "2026-11-14" });
});

test("slot window includes exact now and now plus 14 days, not rest of final day", () => {
  assert.equal(isBookableDateTime("2026-11-04T15:00:00", now), true);
  assert.equal(isBookableDateTime("2026-11-18T15:00:00", now), true);
  assert.equal(isBookableDateTime("2026-11-18T18:00:00Z", now), true);
  for (const value of ["2026-11-04T14:59:59", "2026-11-18T15:00:01", "2026-11-11T24:00:00", "2026-02-30T12:00:00", "0002-11-11T12:00:00", "invalid"]) assert.equal(isBookableDateTime(value, now), false, value);
});
test("accepts valid dates through day 14 including month and year rollover", () => {
  for (const value of ["2026-11-04", "2026-11-18"]) assert.equal(isBookableDate(value, now), true, value);
  const yearRollover = new Date("2026-12-20T12:00:00-03:00");
  for (const value of ["2026-12-20", "2027-01-03"]) assert.equal(isBookableDate(value, yearRollover), true, value);
  assert.equal(isBookableDate("2027-01-04", yearRollover), false);
});
test("uses Sao Paulo calendar day regardless of instant timezone", () => {
  assert.equal(isBookableDate("2026-11-04", new Date("2026-11-05T01:00:00Z")), true);
});
