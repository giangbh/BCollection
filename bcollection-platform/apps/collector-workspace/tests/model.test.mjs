import test from "node:test";
import assert from "node:assert/strict";
import { nextAction, money, stale, dateTime } from "../src/workspace/model.ts";
import { request, ApiError } from "../src/workspace/api.ts";

const now = Date.parse("2026-09-07T10:00:00Z");
const workspace = () => ({
  case: { lifecycle: "OPEN", contact_hold_reason: null },
  case_scope: {
    exposures: [
      {
        balance_verified: 1,
        conflict: false,
        source_as_of: new Date(now).toISOString(),
      },
    ],
  },
  contact_schedules: [],
});
test("no fabricated zero for unknown monetary values", () => {
  assert.equal(money(null), "Chưa có dữ liệu");
  assert.equal(money(undefined), "Chưa có dữ liệu");
  assert.equal(money(0), "0 đ");
});
test("closed and held cases take precedence over contact", () => {
  const w = workspace();
  assert.equal(nextAction(w, now), "CHECK_CONTACT");
  w.case.contact_hold_reason = "PAYMENT_RECONCILIATION";
  assert.equal(nextAction(w, now), "RECONCILE");
  w.case.lifecycle = "CLOSED";
  assert.equal(nextAction(w, now), "VIEW_RESOLUTION");
});
test("balance expires with wall clock, not only on reload", () => {
  const w = workspace();
  assert.equal(nextAction(w, now + 900001), "BALANCE_CHECK");
  assert.equal(stale(w.case_scope, now), false);
  w.case_scope.exposures[0].conflict = true;
  assert.equal(nextAction(w, now), "BALANCE_CHECK");
});
test("future schedule defers contact and due schedule still requires checks", () => {
  const w = workspace();
  w.contact_schedules = [
    { status: "PLANNED", scheduled_at: new Date(now + 60000).toISOString() },
  ];
  assert.equal(nextAction(w, now), "WAIT_SCHEDULE");
  assert.equal(nextAction(w, now + 60001), "CHECK_CONTACT");
});
test("missing, future and unverified snapshots cannot authorize contact", () => {
  const w = workspace();
  w.case_scope.exposures[0].source_as_of = new Date(now + 60000).toISOString();
  assert.equal(nextAction(w, now), "BALANCE_CHECK");
  w.case_scope.exposures = [];
  assert.equal(nextAction(w, now), "BALANCE_CHECK");
});
test("legacy timezone is not silently treated as verified", () => {
  assert.match(dateTime("2026-09-07T18:00:00"), /chưa xác minh/);
  assert.match(dateTime("2026-09-07T11:00:00Z"), /18:00/);
});
test("API preserves status for version conflict and rejects invalid JSON", async () => {
  const original = global.fetch;
  try {
    global.fetch = async () =>
      new Response(JSON.stringify({ detail: "stale" }), { status: 409 });
    await assert.rejects(
      request("/test"),
      (e) => e instanceof ApiError && e.status === 409,
    );
    global.fetch = async () =>
      new Response("<html>error</html>", { status: 502 });
    await assert.rejects(request("/test"), /không hợp lệ/);
  } finally {
    global.fetch = original;
  }
});
