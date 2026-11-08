import test from "node:test";
import assert from "node:assert/strict";
import { nextAvailableDays, latestRequest } from "../assets/js/booking-calendar.mjs";

test("suggestions include only future days with real slots, capped at three", () => {
  const days = [
    { date: "2030-01-08", slots: [] },
    ...[9, 10, 11, 12].map(n => ({ date: `2030-01-${n.toString().padStart(2, "0")}`, slots: [{}] })),
  ];
  assert.deepEqual(nextAvailableDays(days, "2030-01-08").map(d => d.date),
    ["2030-01-09", "2030-01-10", "2030-01-11"]);
  assert.deepEqual(nextAvailableDays(days, "2030-01-12"), []);
});

test("a late response cannot overwrite a newer professional/service/date or an invalidation", async () => {
  const run = latestRequest();
  let finish;
  const old = run(() => new Promise(resolve => { finish = resolve; }));
  const fresh = await run(async () => "fresh");
  finish("old");
  assert.deepEqual(await old, { current: false, value: "old" });
  assert.deepEqual(fresh, { current: true, value: "fresh" });
  const pending = run(() => new Promise(resolve => { finish = resolve; }));
  run.invalidate();
  finish("invalid");
  assert.equal((await pending).current, false);
});

test("a stale failure cannot replace the newest successful calendar", async () => {
  const run = latestRequest();
  let reject;
  const old = run(() => new Promise((resolve, fail) => { reject = fail; }));
  assert.equal((await run(async () => "new calendar")).current, true);
  reject(new Error("old failure"));
  const result = await old;
  assert.equal(result.current, false);
  assert.equal(result.error.message, "old failure");
});
