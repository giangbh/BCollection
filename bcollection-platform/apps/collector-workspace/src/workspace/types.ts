export interface Runtime {
  mode: string;
  simulation: boolean;
  integration_read_only: boolean;
  production_ready: boolean;
}
export interface CaseRecord {
  case_id: string;
  loan_id: string;
  debtor_cif: string;
  full_name: string;
  phone_e164: string;
  product_code: string;
  dpd: number;
  overdue_amount: number;
  total_balance: number;
  status: string;
  lifecycle: string;
  stage: string;
  resolution: string | null;
  contact_hold_reason: string | null;
  case_version: number;
  data_origin: string;
  created_at?: string;
}
export interface Exposure {
  loan_id: string;
  case_id: string;
  case_ids: string[];
  overdue_vnd: number | null;
  principal_vnd: number | null;
  interest_vnd: number | null;
  dpd: number | null;
  balance_verified: number;
  source_version: number;
  source_as_of: string | null;
  conflict: boolean;
  obligation_status: string;
}
export interface Scope {
  exposures: Exposure[];
  overdue_vnd: number | null;
  total_vnd: number | null;
  max_dpd: number | null;
  verified_count: number;
  conflict_count: number;
  oldest_as_of: string | null;
  newest_as_of: string | null;
  coverage: string;
  complete_core_portfolio: boolean;
}
export interface Ptp {
  ptp_id: string;
  loan_id: string;
  amount_vnd: number;
  paid_vnd: number;
  on_time_vnd: number;
  due_at: string;
  created_at: string;
  status: string;
  observed_through: string | null;
}
export interface Payment {
  event_id: string;
  loan_id: string;
  ptp_id: string | null;
  amount_vnd: number;
  occurred_at: string;
  kind: string;
  reverses_event_id: string | null;
}
export interface Schedule {
  schedule_id: string;
  scheduled_at: string;
  channel: string;
  reason: string;
  status: string;
  created_at: string;
}
export interface Feedback {
  feedback_id: string;
  decision: string;
  reason: string;
  created_at: string;
  recommendation_json: string;
  case_version: number;
}
export interface Interaction {
  interaction_id: string;
  created_at: string;
  collector_name: string;
  outcome: string;
  notes: string | null;
  data_origin: string;
}
export interface Transition {
  transition_id: string;
  recorded_at: string;
  reason: string;
  case_version: number;
}
export type ActionKind =
  | "VIEW_RESOLUTION"
  | "RECONCILE"
  | "BALANCE_CHECK"
  | "WAIT_SCHEDULE"
  | "CHECK_CONTACT";
export interface Recommendation {
  recommendation_id: string;
  kind: ActionKind;
  basis: string;
  case_version: number;
  schedule_at: string | null;
  contact_hold_reason: string | null;
}
export interface Workspace {
  integration_state?: {
    streams: { kind: string; stream_id: string; cursor: number; complete_through: string | null; applied_through: string | null; last_error: string | null }[];
    pending_payments: { event_id: string; stream_id: string; state: string; error: string | null }[];
    pending_ews?: { event_id: string; state: string; error: string | null }[];
    ews_decisions: { signal_id: string; signal_version: number; policy_version: string; decision: string; reason: string; case_id: string | null; evaluated_at: string }[];
    delivery: { pending: number; delivered: number; events: { event_id: string; case_version: number; state: string; attempts: number; last_error: string | null; receipt_id: string | null }[] };
  };
  source_data?: {
    profile: SourceResource<unknown>;
    loans: SourceResource<SourceLoan>;
    history: SourceResource<unknown>;
    collateral: SourceResource<SourceCollateral>;
    directory: SourceResource<SourceStaff>;
  };
  case: CaseRecord;
  read_at: string;
  assigned_collector: string | null;
  case_scope: Scope;
  customer_scope: Scope;
  next_action: Recommendation;
  ptps: Ptp[];
  payment_ledger: Payment[];
  contact_schedules: Schedule[];
  decision_feedback: Feedback[];
  case_interactions: Interaction[];
  case_transition_log: Transition[];
  ews: { status: string; signals: EwsSignal[] };
  customer_profile?: CustomerProfile | null;
  customer_cases?: CustomerCase[];
  case_notes?: CaseNote[];
  dpd_history?: { case: DpdHistory; customer: DpdHistory };
  policy_handoffs?: PolicyHandoff[];
  outcome_feedback?: {
    status: string;
    causal_attribution: boolean;
    links: OutcomeLink[];
  };
  capabilities?: Record<string, string>;
}
export interface SourceResource<T> {
  status: string;
  last_attempt_at: string | null;
  received_at: string | null;
  snapshot: {
    source_system: string;
    source_version: number;
    as_of: string;
    data_origin: string;
    coverage: string;
    items: T[];
  } | null;
}
export interface SourceLoan {
  loan_id: string;
  product_code: string;
  outstanding_principal: number;
  outstanding_interest: number;
  overdue_amount: number;
  dpd: number;
  repayment_schedule: { due_at: string; amount_vnd: number }[];
}
export interface SourceCollateral {
  collateral_id: string;
  loan_ids: string[];
  description: string;
  valuation_vnd: number;
  valued_at: string;
  legal_status: string;
}
export interface SourceStaff {
  user_id: string;
  display_name: string;
  org_unit: string;
}
export interface CommandResult {
  case_id: string;
  case_version: number;
  replayed: boolean;
  committed: boolean;
}
export interface GuardrailResult {
  is_allowed: boolean;
  blocking_reason?: string;
  policy_version?: string;
  evaluated_at?: string;
  guardrail_token?: string;
}
export interface Persona {
  simulation: boolean;
  behavioral_summary?: {
    historical_on_time_ratio: number | null;
    ptp_kept_rate: number | null;
    ptp_mature_count: number;
    missing_features: string[];
  };
  recommended_playbook?: unknown;
}
export interface CustomerProfile {
  debtor_cif: string;
  party_type: "INDIVIDUAL" | "ORGANIZATION";
  legal_name: string;
  tax_id: string | null;
  industry: string | null;
  region: string | null;
  rm_name: string | null;
  source: string;
  source_as_of: string;
  data_origin: string;
}
export interface CustomerCase {
  case_id: string;
  lifecycle: string;
  stage: string;
  resolution: string | null;
  created_at: string;
  case_version: number;
}
export interface CaseNote {
  note_id: string;
  case_id: string;
  debtor_cif: string;
  body: string;
  author: string;
  created_at: string;
  data_origin: string;
}
export interface DpdHistory {
  status: string;
  definition: string;
  points: {
    month: string;
    max_dpd: number | null;
    average_dpd: number | null;
    observed_loans: number;
    scope_loans: number;
    oldest_as_of: string | null;
    newest_as_of: string | null;
  }[];
}
export interface EwsSignal {
  signal_id: string;
  debtor_cif: string;
  title: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  verification: string;
  source: string;
  occurred_at: string;
  data_origin: string;
}
export interface PolicyHandoff {
  handoff_id: string;
  case_id: string;
  signal_id: string;
  policy_version: string;
  decision: string;
  reason: string;
  occurred_at: string;
  data_origin: string;
}
export interface OutcomeLink {
  interaction_id: string;
  feedback_id: string;
  ptp_id: string | null;
  outcome: string;
  created_at: string;
  ptp_status: string | null;
  amount_vnd: number | null;
  paid_vnd: number | null;
  on_time_vnd: number | null;
  observed_through: string | null;
  payments: Pick<
    Payment,
    "event_id" | "kind" | "amount_vnd" | "reverses_event_id" | "occurred_at"
  >[];
}
export const sections = {
  work: "Tổng quan",
  customer: "Thông tin khách hàng",
  loans: "Nghĩa vụ tín dụng",
  treatment: "Case & xử lý",
  ptp: "PTP & thanh toán",
  interactions: "Lịch sử tương tác",
  evidence: "EWS & rủi ro",
  collateral: "Tài sản bảo đảm",
  documents: "Tài liệu",
} as const;
export type Section = keyof typeof sections;
