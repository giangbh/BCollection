from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    VOICE = "VOICE"
    SMS = "SMS"
    ZALO = "ZALO"
    EMAIL = "EMAIL"
    APP_NOTIFICATION = "APP_NOTIFICATION"
    FIELD_VISIT = "FIELD_VISIT"
    LEGAL_NOTICE = "LEGAL_NOTICE"


class GuardrailDecision(str, Enum):
    ALLOW = "ALLOW"
    ALLOW_WITH_CONDITIONS = "ALLOW_WITH_CONDITIONS"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class TargetParty(BaseModel):
    party_id: str
    party_type: str = "PERSON"  # PERSON / ORG
    full_name: Optional[str] = None
    phone_e164: Optional[str] = None
    relation_to_debtor: Optional[str] = None


class ActionIntentPayload(BaseModel):
    action_type: str  # REMINDER_MSG, CALL_ATTEMPT, RESTRUCTURE_OFFER, FIELD_VISIT
    channel: ChannelType
    proposed_time: datetime = Field(default_factory=datetime.now)
    content_template_id: Optional[str] = None
    negotiation_levers: List[str] = Field(default_factory=list)
    free_text_note: Optional[str] = None


class EvaluateRequest(BaseModel):
    request_id: str
    loan_id: str
    debtor_cif: str
    target_party: TargetParty
    intent: ActionIntentPayload
    case_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ControlResult(BaseModel):
    control_id: str  # G01..G12
    status: GuardrailDecision
    reason_code: Optional[str] = None
    message: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


class EvaluateResponse(BaseModel):
    request_id: str
    decision: GuardrailDecision
    guardrail_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    policy_version: str
    evaluated_at: datetime = Field(default_factory=datetime.now)
    blocking_reason: Optional[str] = None
    conditions: List[str] = Field(default_factory=list)
    control_trace: List[ControlResult] = Field(default_factory=list)


class CommitRequest(BaseModel):
    request_id: str
    guardrail_token: str
    executed_at: datetime = Field(default_factory=datetime.now)
    delivery_status: str  # DELIVERED, FAILED, ANSWERED, NO_ANSWER
    actual_channel: ChannelType
    cost_spent: Optional[float] = 0.0
