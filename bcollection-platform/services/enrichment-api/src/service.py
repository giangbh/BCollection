from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
import math


class EnrichmentFact(BaseModel):
    fact_id: str
    debtor_cif: str
    case_id: str
    fact_type: str  # ALT_PHONE, CURRENT_ADDRESS, CONTACT_WINDOW, PREFERRED_CHANNEL, EMPLOYMENT, SALARY_CYCLE, ROOT_CAUSE, NEGOTIATION_LEVER
    payload: Dict[str, Any]
    source_type: str = "DEBTOR_DECLARED"  # DEBTOR_DECLARED, STAFF_FIELD_VERIFIED, STAFF_INFERRED
    collected_by: str
    collected_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 3.0  # 1.0 đến 5.0
    half_life_days: int = 180
    state: str = "PUBLISHED"  # DRAFT, VALIDATING, PUBLISHED, SUPERSEDED, DISPUTED


class ManualEnrichmentService:
    HALF_LIFE_MAP = {
        "ALT_PHONE": 120,
        "CONTACT_WINDOW": 120,
        "PREFERRED_CHANNEL": 120,
        "CURRENT_ADDRESS": 270,
        "EMPLOYMENT": 270,
        "SALARY_CYCLE": 270,
        "ROOT_CAUSE": 180,
        "NEGOTIATION_LEVER": 180,
        "VULNERABILITY": 365
    }

    PROHIBITED_WORDS = [
        "ĐE DỌA", "BÔI NHỌ", "BÊU TÊN", "ĐÒI NỢ THUÊ", "QUẤY RỐI", "XÃ HỘI ĐEN",
        "CON CÁI", "TRƯỜNG HỌC", "TÔN GIÁO", "CHÍNH TRỊ", "BỆNH TẬT CHI TIẾT"
    ]

    def __init__(self):
        self._facts: List[EnrichmentFact] = []

    def validate_content(self, payload: Dict[str, Any]) -> bool:
        """Kiểm duyệt nội dung: Chặn từ ngữ đe dọa, xúc phạm hoặc đời tư nhạy cảm"""
        text_content = " ".join([str(v) for v in payload.values()]).upper()
        for word in self.PROHIBITED_WORDS:
            if word in text_content:
                return False
        return True

    def calculate_effective_confidence(self, fact: EnrichmentFact, as_of: Optional[datetime] = None) -> float:
        """
        Tính toán suy giảm độ tin cậy theo thời gian:
        effective_confidence = initial_confidence * 0.5^(age_days / half_life)
        """
        as_of_time = as_of or datetime.now()
        age_days = (as_of_time - fact.collected_at).total_seconds() / 86400.0
        if age_days < 0:
            age_days = 0.0
        
        decay_factor = math.pow(0.5, age_days / fact.half_life_days)
        return round(fact.confidence * decay_factor, 2)

    def add_fact(self, debtor_cif: str, case_id: str, fact_type: str, payload: Dict[str, Any], collected_by: str, initial_confidence: float = 4.0) -> EnrichmentFact:
        if not self.validate_content(payload):
            raise ValueError(f"Nội dung chứa từ ngữ bị cấm hoặc vi phạm quy chuẩn tuân thủ.")

        half_life = self.HALF_LIFE_MAP.get(fact_type, 180)
        
        # Đánh dấu SUPERSEDED cho fact cũ cùng loại
        for f in self._facts:
            if f.debtor_cif == debtor_cif and f.fact_type == fact_type and f.state == "PUBLISHED":
                f.state = "SUPERSEDED"

        new_fact = EnrichmentFact(
            fact_id=f"EF-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self._facts)+1}",
            debtor_cif=debtor_cif,
            case_id=case_id,
            fact_type=fact_type,
            payload=payload,
            collected_by=collected_by,
            confidence=initial_confidence,
            half_life_days=half_life,
            state="PUBLISHED"
        )
        self._facts.append(new_fact)
        return new_fact

    def get_active_facts(self, debtor_cif: str) -> List[Dict[str, Any]]:
        active_list = []
        for f in self._facts:
            if f.debtor_cif == debtor_cif and f.state == "PUBLISHED":
                eff_conf = self.calculate_effective_confidence(f)
                if eff_conf >= 1.5:  # Chỉ giữ lại các fact còn đủ tin cậy
                    active_list.append({
                        "fact_id": f.fact_id,
                        "fact_type": f.fact_type,
                        "payload": f.payload,
                        "collected_by": f.collected_by,
                        "collected_at": f.collected_at.isoformat(),
                        "effective_confidence": eff_conf
                    })
        return active_list
