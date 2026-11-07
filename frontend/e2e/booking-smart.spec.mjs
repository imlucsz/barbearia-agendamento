import { test } from "@playwright/test";
import verifyBooking from "./booking-smart-browser.mjs";

test("individual calendar, suggestions, races and text safety", async ({ page }) => {
  test.setTimeout(90_000);
  await verifyBooking(page);
});
