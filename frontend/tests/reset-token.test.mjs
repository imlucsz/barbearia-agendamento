import assert from "node:assert/strict";
import test from "node:test";

import { readPasswordResetToken } from "../assets/js/reset-token.mjs";

test("reads the reset token from the URL fragment", () => {
  assert.equal(
    readPasswordResetToken({ hash: "#token=fragment-token&source=email", search: "" }),
    "fragment-token",
  );
});

test("does not accept a reset token from the query string", () => {
  assert.equal(
    readPasswordResetToken({ hash: "", search: "?token=query-token" }),
    null,
  );
});
