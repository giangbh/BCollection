from abc import ABC, abstractmethod
from typing import Dict, Any
from ..api.schemas import EvaluateRequest, ControlResult, GuardrailDecision

class BaseControl(ABC):
    def __init__(self, control_id: str, name: str):
        self.control_id = control_id
        self.name = name

    @abstractmethod
    def evaluate(self, request: EvaluateRequest, policy: Dict[str, Any], context: Dict[str, Any]) -> ControlResult:
        pass
