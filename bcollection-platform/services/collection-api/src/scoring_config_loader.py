import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("bcollection.scoring_config")

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "1.0.0",
    "d1_ability": {
        "weights": {"dsr": 0.35, "inflow": 0.25, "cic": 0.25, "collateral": 0.15},
        "living_wage_policy": {
            "living_wage_min": 5500000.0,
            "high_income_cushion_min": 15000000.0
        },
        "product_dsr_thresholds": {
            "MORTGAGE": {"safe_max": 0.45, "insolvent_min": 0.70},
            "MORTGAGE_HOME": {"safe_max": 0.45, "insolvent_min": 0.70},
            "AUTO_LOAN": {"safe_max": 0.40, "insolvent_min": 0.65},
            "SME_WORKING_CAPITAL": {"safe_max": 0.40, "insolvent_min": 0.65},
            "CREDIT_CARD": {"safe_max": 0.30, "insolvent_min": 0.50},
            "UNSECURED_LOAN": {"safe_max": 0.30, "insolvent_min": 0.50},
            "DEFAULT": {"safe_max": 0.35, "insolvent_min": 0.65}
        },
        "dsr_thresholds": {"safe_max": 0.35, "insolvent_min": 0.80},
        "cic_penalty": {"penalty_per_group": 35.0},
        "collateral_thresholds": {"safe_ltv": 0.50, "max_ltv": 1.00, "unsecured_score": 30.0},
        "score_bounds": {"min": 10, "max": 98},
        "coverage": 0.88
    },
    "d2_willingness": {
        "weights": {"ptp": 0.40, "self_cure": 0.25, "priority": 0.20, "avoidance": 0.15},
        "ptp_decay": {"base_rate": 0.90, "decay_cycle_days": 35.0, "min_rate": 0.20, "max_rate": 0.95},
        "priority_scores": {"paying_other_banks": 15.0, "normal": 85.0},
        "avoidance": {"penalty_per_day": 2.0, "max_penalty": 60.0},
        "score_bounds": {"min": 15, "max": 95},
        "coverage": 0.82
    },
    "d3_contactability": {
        "weights": {"rpc": 0.40, "digital": 0.35, "recency": 0.25},
        "digital_thresholds": {
            "high_logins": 10, "high_score": 100.0,
            "medium_logins": 3, "medium_score": 70.0,
            "low_score": 30.0
        },
        "score_bounds": {"min": 20, "max": 95},
        "coverage": 0.90
    },
    "segment_matrix": {
        "ability_cutoff": 60,
        "willingness_cutoff": 50
    },
    "ml01_self_cure": {
        "base_intercept": 0.60,
        "weights": {
            "historical_on_time_ratio": 0.40,
            "days_since_salary_day": -0.05,
            "dpd": -0.03,
            "prior_cure_count": 0.15,
            "dti_ratio": -0.20,
            "casa_buffer_weight": 0.25
        },
        "tiers": {
            "high_prob": 0.80, "high_grace_days": 5,
            "med_prob": 0.45, "med_grace_days": 3
        },
        "channel_threshold": 0.70
    }
}


class ScoringConfigManager:
    """
    Quản lý cấu hình tính điểm Debtor Persona & ML01.
    Hỗ trợ Hot-Reload: Tự động phát hiện khi file scoring_config.yaml thay đổi
    và nạp lại cấu hình mới trong thời gian thực mà không cần restart server.
    """
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "config", "scoring_config.yaml")
            )
        self.config_path = config_path
        self._cached_config: Dict[str, Any] = {}
        self._last_mtime: float = 0.0
        self.reload_if_needed()

    def reload_if_needed(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.config_path):
                current_mtime = os.path.getmtime(self.config_path)
                if current_mtime != self._last_mtime:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f)
                    if isinstance(loaded, dict):
                        # Merge loaded config on top of DEFAULT_CONFIG
                        merged = DEFAULT_CONFIG.copy()
                        for k, v in loaded.items():
                            if isinstance(v, dict) and k in merged:
                                merged[k] = {**merged[k], **v}
                            else:
                                merged[k] = v
                        self._cached_config = merged
                        self._last_mtime = current_mtime
                        logger.info("ScoringConfigManager: Reloaded config from %s (v%s)", self.config_path, self._cached_config.get("version"))
            else:
                if not self._cached_config:
                    logger.warning("ScoringConfigManager: Config file %s not found. Using defaults.", self.config_path)
                    self._cached_config = DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.error("ScoringConfigManager: Error reading %s: %s. Using cached/default config.", self.config_path, e)
            if not self._cached_config:
                self._cached_config = DEFAULT_CONFIG.copy()

        return self._cached_config

    def get_config(self) -> Dict[str, Any]:
        return self.reload_if_needed()

    def get_d1_config(self) -> Dict[str, Any]:
        return self.get_config().get("d1_ability", DEFAULT_CONFIG["d1_ability"])

    def get_d2_config(self) -> Dict[str, Any]:
        return self.get_config().get("d2_willingness", DEFAULT_CONFIG["d2_willingness"])

    def get_d3_config(self) -> Dict[str, Any]:
        return self.get_config().get("d3_contactability", DEFAULT_CONFIG["d3_contactability"])

    def get_segment_matrix_config(self) -> Dict[str, Any]:
        return self.get_config().get("segment_matrix", DEFAULT_CONFIG["segment_matrix"])

    def get_ml01_config(self) -> Dict[str, Any]:
        return self.get_config().get("ml01_self_cure", DEFAULT_CONFIG["ml01_self_cure"])


# Singleton instance
_manager_instance: Optional[ScoringConfigManager] = None

def get_scoring_config_manager() -> ScoringConfigManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ScoringConfigManager()
    return _manager_instance
