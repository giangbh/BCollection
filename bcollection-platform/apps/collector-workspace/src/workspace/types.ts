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
  ews: { status: string; signals: unknown[] };
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
export type Section = "work" | "ptp" | "evidence";
