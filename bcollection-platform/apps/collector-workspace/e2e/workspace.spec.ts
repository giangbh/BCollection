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
    created_at: "2026-08-15T08:00:00+07:00",
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
    demoHttp?: boolean;
    closed?: boolean;
    held?: boolean;
    conflict?: boolean;
    lostResponse?: boolean;
  } = {},
) {
  const w: any = fixture();
  w.customer_cases = [w.case, fixture("C2").case];
  w.case_notes = [];
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
          mode: opts.readonly ? "integration" : opts.demoHttp ? "demo-http" : "test",
          simulation: !opts.readonly,
          integration_read_only: !!opts.readonly,
          production_ready: false,
        },
      });
    if (path === "/api/cases")
      return route.fulfill({ json: [w.case, fixture("C2").case] });
    if (path.endsWith("/balance-check")) {
      seen.push("balance_check");
      w.case.case_version++;
      return route.fulfill({ json: { case_version: w.case.case_version, replayed: false } });
    }
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
      if (path.endsWith("add_note"))
        w.case_notes.unshift({
          note_id: body.command_id,
          case_id: "C1",
          debtor_cif: "D1",
          body: body.payload.reason,
          author: "Demo collector (unauthenticated)",
          created_at: new Date().toISOString(),
          data_origin: "SYNTHETIC",
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

test("demo-http permits only the explicit REST balance action on the workspace", async ({ page }) => {
  const { seen } = await setup(page, { demoHttp: true });
  const balance = page.getByRole("button", { name: "Kiểm tra số dư qua REST Core" });
  await expect(balance).toBeEnabled();
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toBeDisabled();
  await expect(page.getByRole("button", { name: "Lên lịch liên hệ", exact: true })).toBeDisabled();
  await balance.click();
  await expect(page.getByText("Đã lưu vào hệ thống và tải lại trạng thái.", { exact: false })).toBeVisible();
  expect(seen).toEqual(["balance_check"]);
});

test('Customer 360 sync shows source coverage, schedules and collateral without changing case scope', async ({ page }) => {
  const { w } = await setup(page, { demoHttp: true });
  const now = new Date().toISOString();
  const resource = (items: unknown[], name: string) => ({ status: 'RECORDED', last_attempt_at: now, received_at: now,
    snapshot: { source_system: name, source_version: 1, as_of: now, data_origin: 'SYNTHETIC', coverage: 'COMPLETE', items } });
  await page.route('**/api/cases/C1/sync-customer', route => {
    w.customer_profile = { debtor_cif: 'D1', party_type: 'ORGANIZATION', legal_name: 'CÔNG TY REST DEMO',
      tax_id: 'DEMO-TAX-D1', industry: 'Xây dựng demo', region: 'Hà Nội demo', rm_name: 'RM demo',
      source: 'MOCK_CRM', source_as_of: now, data_origin: 'SYNTHETIC' };
    w.source_data = {
      profile: resource([], 'MOCK_CRM'), history: resource([], 'MOCK_DWH'), directory: resource([], 'MOCK_DIRECTORY'),
      loans: resource([{ loan_id: 'L9', product_code: 'LOAN', outstanding_principal: 100000000, outstanding_interest: 0,
        overdue_amount: 0, dpd: 0, repayment_schedule: [{ due_at: '2026-12-15T09:00:00+07:00', amount_vnd: 5000000 }] }], 'MOCK_CORE'),
      collateral: resource([{ collateral_id: 'COL-REST-01', loan_ids: ['L9'], description: 'Tài sản REST demo',
        valuation_vnd: 600000000, valued_at: now, legal_status: 'PLEDGED' }], 'MOCK_LOS'),
    };
    return route.fulfill({ json: { resources: {}, financial_state_changed: false } });
  });
  await page.getByRole('button', { name: 'Đồng bộ Customer 360', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'CÔNG TY REST DEMO', exact: true })).toBeVisible();
  await page.getByText('Nguồn dữ liệu Customer 360 · Trạng thái đồng bộ', { exact: true }).click();
  await expect(page.getByText('Đầy đủ theo contract nguồn').first()).toBeVisible();
  await page.getByRole('tab', { name: 'Nghĩa vụ tín dụng', exact: true }).click();
  const row = page.getByRole('row').filter({ hasText: 'L9' });
  await expect(row).toContainText('Không');
  await expect(row).toContainText('5.000.000');
  await page.getByRole('tab', { name: 'Tài sản bảo đảm', exact: true }).click();
  await expect(page.getByRole('cell', { name: 'COL-REST-01 Tài sản REST demo', exact: true })).toBeVisible();
  await expect(page.getByText('600.000.000', { exact: false })).toBeVisible();
  expect(w.case.case_version).toBe(0);
  expect(w.case_scope.exposures.length).toBe(2);
});

test('demo event actions show cursor, policy decisions and outcome receipts', async ({ page }) => {
  const { w } = await setup(page, { demoHttp: true });
  const seen: string[] = [];
  w.integration_state = { streams: [], pending_payments: [], ews_decisions: [], delivery: { pending: 0, delivered: 0, events: [] } };
  await page.route(/\/api\/cases\/C1\/(sync-payments|sync-ews|publish-outcomes)$/, route => {
    const action = new URL(route.request().url()).pathname.split('/').pop()!;
    seen.push(action);
    const state = w.integration_state;
    if (action === 'sync-payments') state.streams = [{ kind: 'payment', stream_id: 'L1', cursor: 2,
      complete_through: new Date().toISOString(), applied_through: new Date().toISOString(), last_error: null }];
    if (action === 'sync-ews') state.ews_decisions = [{ signal_id: 'EWS-DEMO', signal_version: 1,
      policy_version: 'DEMO_HANDOFF_V1', decision: 'APPLIED', reason: 'Demo treatment review', case_id: 'C1', evaluated_at: new Date().toISOString() }];
    if (action === 'publish-outcomes') state.delivery = { pending: 0, delivered: 1, events: [
      { event_id: 'OUTCOME-1', case_version: 3, state: 'DELIVERED', attempts: 1, last_error: null, receipt_id: 'RECEIPT-1' }] };
    return route.fulfill({ json: { status: 'OK' } });
  });
  for (const name of ['Đồng bộ thanh toán', 'Đồng bộ EWS', 'Gửi outcome']) {
    await page.getByRole('button', { name, exact: true }).click();
    await expect(page.getByRole('button', { name, exact: true })).toBeEnabled();
  }
  await page.getByText('Payment / EWS / Outcome · Nhật ký tích hợp', { exact: true }).click();
  await expect(page.getByText('payment · L1', { exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'DEMO_HANDOFF_V1', exact: true })).toBeVisible();
  await expect(page.getByRole('cell', { name: 'RECEIPT-1', exact: true })).toBeVisible();
  expect(seen).toEqual(['sync-payments', 'sync-ews', 'publish-outcomes']);
  await expect(page.getByRole('button', { name: 'Lên lịch liên hệ', exact: true })).toBeDisabled();
});

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
  await page.getByRole("tab", { name: "EWS & rủi ro", exact: true }).click();
  await expect(
    page.getByText("Xem trạng thái đồng bộ EWS và quyết định policy trong nhật ký tích hợp.", {
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

test("late wrapup keeps form open and cannot silently reopen a closed case", async ({
  page,
}) => {
  await setup(page);
  await page.route("**/api/cases/C1/call-intent", (route) =>
    route.fulfill({
      json: {
        is_allowed: true,
        guardrail_token: "SIMULATED-TOKEN",
        policy_version: "test",
      },
    }),
  );
  await page.route("**/api/cases/C1/call-wrapup", (route) =>
    route.fulfill({
      status: 409,
      json: { detail: "Case closed while call was in progress" },
    }),
  );
  await page
    .getByRole("button", { name: "Kiểm tra & gọi mô phỏng", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Cuộc gọi mô phỏng đang mở",
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Kết thúc & ghi nhận kết quả", exact: true })
    .click();
  await page
    .getByLabel("Lý do / nội dung ghi nhận")
    .fill("Ghi nhận cuộc gọi đang diễn ra khi case thay đổi.");
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Case closed");
  await expect(page.getByLabel("Lý do / nội dung ghi nhận")).toHaveValue(
    /Ghi nhận cuộc gọi/,
  );
  await expect(
    page.getByRole("button", { name: "Lưu vào hệ thống", exact: true }),
  ).toBeDisabled();
});

test("an API error never presents the stale case as actionable", async ({
  page,
}) => {
  await setup(page);
  await page.route("**/api/cases/C1/workspace", (route) =>
    route.fulfill({ status: 503, json: { detail: "temporarily unavailable" } }),
  );
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("tạm khóa tác nghiệp");
  for (const button of await page
    .getByRole("button", { name: "Kiểm tra & gọi mô phỏng", exact: true })
    .all())
    await expect(button).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Lên lịch liên hệ", exact: true }),
  ).toBeDisabled();
});

test("notes persist and unsaved drafts prevent switching customer case", async ({
  page,
}) => {
  await setup(page);
  await page
    .getByLabel("Nội dung ghi chú nhanh")
    .fill("Khách hàng cung cấp thông tin cần xác minh.");
  await expect(page.getByLabel("Chọn case của khách hàng")).toBeDisabled();
  await page.evaluate(() => {
    location.hash = "/cases/C2/work";
  });
  await expect(page.getByRole("alert")).toContainText("Hoàn tất hoặc đóng");
  await page.getByRole("button", { name: "Lưu ghi chú", exact: true }).click();
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toHaveValue("");
  await page.reload();
  await expect(
    page.getByText("Khách hàng cung cấp thông tin cần xác minh.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByLabel("Chọn case của khách hàng").selectOption("C2");
  await expect(
    page.getByRole("heading", { name: "Khách hàng thứ hai" }),
  ).toBeVisible();
  await expect(
    page.getByText("Khách hàng cung cấp thông tin cần xác minh.", {
      exact: true,
    }),
  ).toHaveCount(0);
});

test("notes retain draft and retry lost response idempotently", async ({
  page,
}) => {
  const { seen } = await setup(page, { lostResponse: true });
  await page
    .getByLabel("Nội dung ghi chú nhanh")
    .fill("Giữ nguyên ghi chú khi mất mạng.");
  await page.getByRole("button", { name: "Lưu ghi chú", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toHaveValue(
    "Giữ nguyên ghi chú khi mất mạng.",
  );
  await page.getByRole("button", { name: "Lưu ghi chú", exact: true }).click();
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toHaveValue("");
  expect(seen[0]).toBe(seen[1]);
  await expect(
    page.getByText("Giữ nguyên ghi chú khi mất mạng.", { exact: true }),
  ).toHaveCount(1);
});

test("note conflict requires explicit reload and keeps original content", async ({
  page,
}) => {
  const { seen } = await setup(page, { conflict: true });
  await page
    .getByLabel("Nội dung ghi chú nhanh")
    .fill("Ghi chú chưa lưu khi case thay đổi.");
  await page.getByRole("button", { name: "Lưu ghi chú", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Hồ sơ hoặc đề xuất đã thay đổi",
  );
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toHaveValue(
    "Ghi chú chưa lưu khi case thay đổi.",
  );
  await expect(
    page.getByRole("button", { name: "Lưu ghi chú", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await page.getByRole("button", { name: "Lưu ghi chú", exact: true }).click();
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toHaveValue("");
  expect(seen[0]).not.toBe(seen[1]);
});

test("wrapup links only the explicitly selected decision and displays outcome trace", async ({
  page,
}) => {
  const { w } = await setup(page);
  w.decision_feedback = [
    {
      feedback_id: "F1",
      decision: "ACCEPT",
      reason: "Đã chọn quy tắc để áp dụng",
      case_version: 0,
      created_at: new Date().toISOString(),
    },
  ];
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await page.route("**/api/cases/C1/call-intent", (route) =>
    route.fulfill({
      json: {
        is_allowed: true,
        guardrail_token: "SIMULATED-TOKEN",
        policy_version: "test",
      },
    }),
  );
  let selected: string | null = null;
  await page.route("**/api/cases/C1/call-wrapup", (route) => {
    selected = route.request().postDataJSON().decision_feedback_id;
    w.outcome_feedback = {
      status: "LOCAL_TRACE_ONLY",
      causal_attribution: false,
      links: [
        {
          feedback_id: selected,
          interaction_id: "I1",
          outcome: "REFUSED",
          created_at: new Date().toISOString(),
          ptp_id: null,
          ptp_status: null,
          payments: [],
        },
      ],
    };
    w.case.case_version++;
    return route.fulfill({
      json: { committed: true, case_version: w.case.case_version },
    });
  });
  await page
    .getByRole("button", { name: "Kiểm tra & gọi mô phỏng", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Kết thúc & ghi nhận kết quả", exact: true })
    .click();
  await expect(
    page.getByLabel("Quyết định được áp dụng (không bắt buộc)"),
  ).toHaveValue("");
  await page
    .getByLabel("Quyết định được áp dụng (không bắt buộc)")
    .selectOption("F1");
  await page.getByLabel("Kết quả", { exact: true }).selectOption("REFUSED");
  await page
    .getByLabel("Lý do / nội dung ghi nhận")
    .fill("Chưa thống nhất phương án.");
  await page
    .getByRole("button", { name: "Lưu vào hệ thống", exact: true })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Đã lưu vào hệ thống" }),
  ).toBeVisible();
  expect(selected).toBe("F1");
  await page.getByRole("tab", { name: "Case & xử lý", exact: true }).click();
  await expect(page.getByText("Quyết định F1", { exact: true })).toBeVisible();
  await expect(page.getByText("Không có PTP", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Chấp nhận đề xuất ≠ thu hồi thành công.", { exact: false }),
  ).toBeVisible();
});

test("readonly notes and unconnected tabs never present active writes or fake scores", async ({
  page,
}) => {
  await setup(page, { readonly: true });
  await expect(page.getByLabel("Nội dung ghi chú nhanh")).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Lưu ghi chú", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText("Chưa có mô hình rủi ro", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Chưa đủ lịch sử DPD", { exact: true }),
  ).toBeVisible();
  for (const title of [
    "Thông tin khách hàng",
    "Nghĩa vụ tín dụng",
    "Case & xử lý",
    "PTP & thanh toán",
    "Lịch sử tương tác",
    "EWS & rủi ro",
    "Tài sản bảo đảm",
    "Tài liệu",
  ]) {
    await page.getByRole("tab", { name: title, exact: true }).click();
    await expect(page.getByRole("tabpanel")).toBeVisible();
  }
  await expect(
    page.getByText("Chưa kết nối nguồn dữ liệu", { exact: true }),
  ).toBeVisible();
});

test("global search opens selected case and keyboard tabs are navigable", async ({
  page,
}) => {
  await setup(page);
  await page.route("**/api/customer-search?*", (route) =>
    route.fulfill({ json: { items: [fixture("C2").case], has_more: false } }),
  );
  await page
    .getByRole("searchbox", {
      name: "Tìm khách hàng, CIF, MST, khoản vay hoặc case",
    })
    .fill("khach hang");
  await page.getByRole("button", { name: "Tìm kiếm", exact: true }).click();
  await page.getByRole("button", { name: /Khách hàng thứ hai.*C2/ }).click();
  await expect(
    page.getByRole("heading", { name: "Khách hàng thứ hai", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Tổng quan", exact: true }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("tab", { name: "Thông tin khách hàng", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.keyboard.press("End");
  await expect(
    page.getByRole("tab", { name: "Tài liệu", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
});

test("corporate profile, EWS provenance, scoped membership and charts render without invented AI", async ({
  page,
}) => {
  const { w } = await setup(page);
  w.customer_profile = {
    debtor_cif: "D1",
    legal_name: "CÔNG TY TNHH MINH PHÁT (E2E)",
    party_type: "ORGANIZATION",
    tax_id: "0101234567",
    industry: "Xây dựng",
    region: "Hà Nội",
    rm_name: "RM mô phỏng",
    source: "CRM fixture",
    source_as_of: new Date().toISOString(),
    data_origin: "SYNTHETIC",
  };
  w.ews = {
    status: "RECORDED_EVIDENCE",
    signals: [
      {
        signal_id: "EWS-001",
        debtor_cif: "D1",
        title: "Dòng tiền về giảm — dữ liệu kiểm thử",
        severity: "HIGH",
        verification: "VERIFIED",
        source: "EWS fixture",
        occurred_at: new Date().toISOString(),
        data_origin: "SYNTHETIC",
      },
      {
        signal_id: "EWS-002",
        debtor_cif: "D1",
        title: "Biến động sử dụng hạn mức — kiểm thử",
        severity: "MEDIUM",
        verification: "UNVERIFIED",
        source: "EWS fixture",
        occurred_at: new Date().toISOString(),
        data_origin: "SYNTHETIC",
      },
    ],
  };
  w.policy_handoffs = [
    {
      handoff_id: "H1",
      case_id: "C1",
      signal_id: "EWS-001",
      policy_version: "TEST-v1",
      decision: "REVIEW",
      reason: "Rà soát bằng chứng",
      occurred_at: new Date().toISOString(),
      data_origin: "SYNTHETIC",
    },
  ];
  const h = {
    status: "OBSERVED",
    definition: "LATEST_OBSERVATION_PER_LOAN_MONTH_UNWEIGHTED_CURRENT_SCOPE",
    points: Array.from({ length: 12 }, (_, i) => ({
      month: `2025-${String(i + 1).padStart(2, "0")}`,
      max_dpd: i === 3 ? null : i * 3,
      average_dpd: i === 3 ? null : i * 2,
      observed_loans: i === 3 ? 1 : 2,
      scope_loans: 2,
      oldest_as_of: "2025-09-10T00:00:00Z",
      newest_as_of: "2025-09-10T00:00:00Z",
    })),
  };
  w.dpd_history = { case: h, customer: h };
  await page
    .getByRole("button", { name: "Tải lại dữ liệu", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "CÔNG TY TNHH MINH PHÁT (E2E)" }),
  ).toBeVisible();
  await expect(
    page.getByText("Khách hàng doanh nghiệp", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("cell", { name: "Có bàn giao", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Khách hàng · Đã ghi nhận/ }).click();
  await expect(
    page.getByLabel("Không thuộc case đang chọn", { exact: true }),
  ).toHaveCount(1);
  await page.waitForTimeout(200);
  for (const width of [1440, 1920, 1024, 360]) {
    await page.setViewportSize({ width, height: width < 600 ? 900 : 1080 });
    await expect
      .poll(() =>
        page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      )
      .toBe(true);
    await page.screenshot({
      path: `test-results/customer360-${width}.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1440, height: 1080 });
  await page.getByRole("button", { name: "Đổi giao diện sáng tối" }).click();
  await page.waitForTimeout(200);
  await page.screenshot({
    path: "test-results/customer360-dark.png",
    fullPage: true,
  });
});
