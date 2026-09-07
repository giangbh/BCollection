import { test, expect, type Page } from "@playwright/test";

function fixture(id = "C1") {
  const now = new Date().toISOString();
  const c = {
    case_id: id,
    loan_id: "L1",
    debtor_cif: "D1",
    full_name: id === "C1" ? "Nguyễn Minh An (E2E)" : "Khách hàng thứ hai",
    phone_e164: "+84900000000",
    product_code: "LOAN",
    dpd: 28,
    overdue_amount: 12500000,
    total_balance: 700000000,
    status: "IN_TREATMENT",
    lifecycle: "OPEN",
    stage: "EARLY_COLLECTION",
    resolution: null,
    contact_hold_reason: null,
    case_version: 0,
    data_origin: "SYNTHETIC",
  };
  const exposures = [500000000, 200000000].map((principal, i) => ({
    loan_id: `L${i + 1}`,
    case_id: id,
    case_ids: [id],
    overdue_vnd: i ? 7500000 : 5000000,
    principal_vnd: principal,
    interest_vnd: 0,
    dpd: i ? 28 : 12,
    balance_verified: 1,
    source_version: 1,
    source_as_of: now,
    conflict: false,
    obligation_status: "OVERDUE",
  }));
  const scope = {
    exposures,
    overdue_vnd: 12500000,
    total_vnd: 700000000,
    max_dpd: 28,
    verified_count: 2,
    conflict_count: 0,
    oldest_as_of: now,
    newest_as_of: now,
    coverage: "RECORDED_IN_BCOLLECTION_ONLY",
    complete_core_portfolio: false,
  };
  return {
    case: c,
    read_at: now,
    assigned_collector: null,
    case_scope: scope,
    customer_scope: {
      ...scope,
      total_vnd: 1500000000,
      verified_count: 3,
      exposures: [
        ...exposures,
        {
          ...exposures[0],
          loan_id: "L3",
          case_ids: ["C3"],
          principal_vnd: 800000000,
          overdue_vnd: 0,
          dpd: 0,
          obligation_status: "CURRENT",
        },
      ],
    },
    next_action: {
      recommendation_id: "WORKSPACE_RULES_V1",
      kind: "CHECK_CONTACT",
      basis: "CASE_STATE_RULES_NOT_AI",
      case_version: 0,
      schedule_at: null,
      contact_hold_reason: null,
    },
    ptps: [],
    payment_ledger: [],
    contact_schedules: [],
    decision_feedback: [],
    case_interactions: [],
    case_transition_log: [],
    ews: { status: "NOT_CONNECTED", signals: [] },
  };
}

async function setup(
  page: Page,
  opts: {
    readonly?: boolean;
    closed?: boolean;
    held?: boolean;
    conflict?: boolean;
    lostResponse?: boolean;
  } = {},
) {
  const w = fixture();
  if (opts.closed) {
    w.case.lifecycle = "CLOSED";
    w.next_action.kind = "VIEW_RESOLUTION";
  }
  if (opts.held) {
    Object.assign(w.case, { contact_hold_reason: "PAYMENT_RECONCILIATION" });
    w.next_action.kind = "RECONCILE";
  }
  const seen: string[] = [];
  let conflictOnce = !!opts.conflict,
    loseOnce = !!opts.lostResponse;
  const commands = new Map<string, object>();
  await page.route("**/api/**", async (route) => {
    const req = route.request(),
      path = new URL(req.url()).pathname;
    if (path === "/api/runtime")
      return route.fulfill({
        json: {
          mode: opts.readonly ? "integration" : "test",
          simulation: !opts.readonly,
          integration_read_only: !!opts.readonly,
          production_ready: false,
        },
      });
    if (path === "/api/cases")
      return route.fulfill({ json: [w.case, fixture("C2").case] });
    if (path.endsWith("/workspace"))
      return route.fulfill({ json: path.includes("/C2/") ? fixture("C2") : w });
    if (path.endsWith("/call-intent"))
      return route.fulfill({
        json: { is_allowed: false, blocking_reason: "POLICY_BLOCKED" },
      });
    if (path.includes("/commands/")) {
      const body = req.postDataJSON();
      seen.push(body.command_id);
      if (conflictOnce) {
        conflictOnce = false;
        w.case.case_version++;
        return route.fulfill({ status: 409, json: { detail: "case changed" } });
      }
      if (commands.has(body.command_id))
        return route.fulfill({
          json: { ...commands.get(body.command_id), replayed: true },
        });
      if (path.endsWith("schedule_contact")) {
        Object.assign(w, {
          contact_schedules: [
            {
              schedule_id: "S1",
              ...body.payload,
              created_at: new Date().toISOString(),
              status: "PLANNED",
            },
          ],
        });
        w.next_action.kind = "WAIT_SCHEDULE";
      }
      if (path.endsWith("decision_feedback"))
        Object.assign(w, {
          decision_feedback: [
            {
              feedback_id: "F1",
              ...body.payload,
              case_version: w.case.case_version,
              created_at: new Date().toISOString(),
            },
          ],
        });
      w.case.case_version++;
      const result = {
        case_id: "C1",
        case_version: w.case.case_version,
        committed: true,
        replayed: false,
      };
      commands.set(body.command_id, result);
      if (loseOnce) {
        loseOnce = false;
        return route.abort("failed");
      }
      return route.fulfill({ json: result });
    }
    return route.fulfill({
      status: 503,
      json: { detail: "Not connected in test" },
    });
  });
  await page.goto("/#/cases/C1/work");
  await expect(
    page.getByRole("heading", { name: "Nguyễn Minh An (E2E)" }),
  ).toBeVisible();
  return { w, seen };
}

async function fillSchedule(page: Page) {
  await page
    .getByRole("button", { name: "Lên lịch liên hệ", exact: true })
    .click();
  await page.getByLabel("Thời gian liên hệ").fill("2026-12-01T18:00");
  await page
    .getByLabel("Lý do / nội dung ghi nhận")
    .fill("Xác minh khả năng trả; đây là kế hoạch cán bộ.");
}

test("scope totals are consistent and schedule persists after reload", async ({
  page,
}) => {
  await setup(page);
  await expect(
    page.getByRole("region", { name: "Tổng hợp nghĩa vụ" }),
  ).toContainText("700.000.000 đ");
  await page.getByRole("button", { name: /Khách hàng · Đã ghi nhận/ }).click();
  await expect(
    page.getByRole("region", { name: "Tổng hợp nghĩa vụ" }),
  ).toContainText("1.500.000.000 đ");
  await expect(
    page.getByRole("cell", { name: "L3", exact: false }),
  ).toBeVisible();
  await fillSchedule(page);
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu vào hệ thống" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Điều chỉnh lịch", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Kiểm tra & gọi mô phỏng", exact: true }),
  ).toBeDisabled();
});

test("409 keeps text and needs explicit reload before another submit", async ({
  page,
}) => {
  const { seen } = await setup(page, { conflict: true });
  await fillSchedule(page);
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Hồ sơ hoặc đề xuất đã thay đổi",
  );
  await expect(page.getByLabel("Lý do / nội dung ghi nhận")).toHaveValue(
    /Xác minh/,
  );
  await expect(
    page.getByRole("button", { name: "Lưu vào hệ thống", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Lưu vào hệ thống", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Điều chỉnh lịch", exact: true }),
  ).toBeVisible();
  expect(seen[0]).not.toBe(seen[1]);
});

test("retry after a lost response reuses command ID", async ({ page }) => {
  const { seen } = await setup(page, { lostResponse: true });
  await fillSchedule(page);
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(page.getByRole("alert")).toBeVisible();
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Điều chỉnh lịch", exact: true }),
  ).toBeVisible();
  expect(seen).toHaveLength(2);
  expect(seen[0]).toBe(seen[1]);
});

for (const state of ["closed", "held", "readonly"] as const)
  test(`${state} disables contact and planning`, async ({ page }) => {
    await setup(page, { [state]: true });
    for (const button of await page
      .getByRole("button", { name: "Kiểm tra & gọi mô phỏng", exact: true })
      .all())
      await expect(button).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Lên lịch liên hệ", exact: true }),
    ).toBeDisabled();
  });

test("feedback persists without invented EWS evidence", async ({ page }) => {
  await setup(page);
  await page
    .getByRole("button", { name: "Ghi nhận quyết định", exact: true })
    .click();
  await page.getByLabel("Quyết định", { exact: true }).selectOption("DECLINE");
  await page
    .getByLabel("Lý do / nội dung ghi nhận")
    .fill("Cần rà soát nguồn dữ liệu.");
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await page.reload();
  await expect(page.getByText("Không áp dụng · v0")).toBeVisible();
  await page
    .getByRole("tab", { name: "EWS & bằng chứng", exact: true })
    .click();
  await expect(
    page.getByText("Chưa có EWS intake hoặc policy handoff đang vận hành.", {
      exact: false,
    }),
  ).toBeVisible();
});

test("late response from the previous case never replaces current data", async ({
  page,
}) => {
  await setup(page);
  await page.route("**/api/cases/C1/workspace", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 500));
    await route.fulfill({ json: fixture() });
  });
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await page.evaluate(() => {
    location.hash = "/cases/C2/work";
  });
  await expect(
    page.getByRole("heading", { name: "Khách hàng thứ hai", exact: true }),
  ).toBeVisible();
  await page.waitForTimeout(650);
  await expect(
    page.getByRole("heading", { name: "Nguyễn Minh An (E2E)", exact: true }),
  ).toHaveCount(0);
});

test("layout fits desktop and narrow screens in both themes", async ({
  page,
}) => {
  await setup(page);
  for (const width of [1440, 1024, 360]) {
    await page.setViewportSize({ width, height: 1000 });
    for (let theme = 0; theme < 2; theme++) {
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      await page
        .getByRole("button", { name: "Đổi giao diện sáng tối" })
        .click();
    }
  }
});

test('late wrapup keeps form open and cannot silently reopen a closed case', async ({ page }) => {
  await setup(page);
  await page.route('**/api/cases/C1/call-intent', route => route.fulfill({ json: { is_allowed: true, guardrail_token: 'SIMULATED-TOKEN', policy_version: 'test' } }));
  await page.route('**/api/cases/C1/call-wrapup', route => route.fulfill({ status: 409, json: { detail: 'Case closed while call was in progress' } }));
  await page.getByRole('button', { name: 'Kiểm tra & gọi mô phỏng', exact: true }).first().click();
  await expect(page.getByRole('heading', { name: 'Cuộc gọi mô phỏng đang mở', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Kết thúc & ghi nhận kết quả', exact: true }).click();
  await page.getByLabel('Lý do / nội dung ghi nhận').fill('Ghi nhận cuộc gọi đang diễn ra khi case thay đổi.');
  await page.getByRole('button', { name: 'Lưu vào hệ thống', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Case closed');
  await expect(page.getByLabel('Lý do / nội dung ghi nhận')).toHaveValue(/Ghi nhận cuộc gọi/);
  await expect(page.getByRole('button', { name: 'Lưu vào hệ thống', exact: true })).toBeDisabled();
});

test('an API error never presents the stale case as actionable', async ({ page }) => {
  await setup(page);
  await page.route('**/api/cases/C1/workspace', route => route.fulfill({ status: 503, json: { detail: 'temporarily unavailable' } }));
  await page.getByRole('button', { name: 'Tải lại dữ liệu', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('tạm khóa tác nghiệp');
  for (const button of await page.getByRole('button', { name: 'Kiểm tra & gọi mô phỏng', exact: true }).all()) await expect(button).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Lên lịch liên hệ', exact: true })).toBeDisabled();
});
