from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from .enums import CaseStatus, ExperimentArm, ChannelType, CaseStage, CaseLifecycle


class CollectionCase(BaseModel):
    case_id: str
    loan_id: str
    debtor_cif: str
    product_code: str
    segment: str = "RETAIL"
    dpd: int
    outstanding_principal: float
    outstanding_interest: float
    overdue_amount: float
    status: CaseStatus = CaseStatus.CREATED
    assigned_to: Optional[str] = None
    experiment_arm: ExperimentArm = ExperimentArm.TREATED
    opened_at: datetime = Field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    ptp_amount: Optional[float] = None
    ptp_date: Optional[datetime] = None
    cure_flag: bool = False
    recovery_amount: float = 0.0
    cost_to_collect: float = 0.0
    case_version: int = 0
    stage: CaseStage = CaseStage.EARLY_COLLECTION
    lifecycle: CaseLifecycle = CaseLifecycle.OPEN
    resolution: Optional[str] = None
    exposure_ids: List[str] = Field(default_factory=list)


class ScoreComponent(BaseModel):
    value: float
    coverage: float
    top_drivers: List[Dict[str, Any]] = Field(default_factory=list)


class DebtorPersonaSnapshot(BaseModel):
    snapshot_id: str
    persona_id: str
    debtor_cif: str
    as_of: datetime = Field(default_factory=datetime.now)
    ability_score: ScoreComponent
    willingness_score: ScoreComponent
    contactability_score: ScoreComponent
    segment_cell: str  # S1, S2, S3, S4
    dominant_root_cause: str
    applicable_levers: List[str]
    best_channel: ChannelType
    best_time_window: str
    vulnerability_flag: bool = False
    dnc_flag: bool = False
