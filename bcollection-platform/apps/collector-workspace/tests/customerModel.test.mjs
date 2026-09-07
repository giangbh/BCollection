import { test } from "node:test";
import assert from "node:assert/strict";
import {
  debtComposition,
  normalizedSearch,
} from "../src/workspace/customerModel.ts";

const scope = {
  total_vnd: 10000,
  overdue_vnd: 200,
  exposures: [{}],
  verified_count: 1,
  conflict_count: 0,
};
test("debt decomposition is additive, not a loan-status classification", () => {
  assert.deepEqual(debtComposition(scope), {
    total: 10000,
    overdue: 200,
    remainder: 9800,
    overduePercent: 2,
  });
});
test("no donut for missing, unverified, conflicting or impossible totals", () => {
  for (const change of [
    { total_vnd: null },
    { overdue_vnd: null },
    { verified_count: 0 },
    { conflict_count: 1 },
    { overdue_vnd: 10001 },
    { total_vnd: -1 },
    { total_vnd: 1.5 },
    { exposures: [] },
  ])
    assert.equal(debtComposition({ ...scope, ...change }), null);
});
test("zero is not missing and never produces NaN", () => {
  assert.equal(
    debtComposition({ ...scope, total_vnd: 0, overdue_vnd: 0 }).overduePercent,
    0,
  );
});
test("Vietnamese accent folding supports customer lookup", () => {
  assert.equal(normalizedSearch("  Công ty ĐẠI PHÁT  "), "cong ty dai phat");
});
