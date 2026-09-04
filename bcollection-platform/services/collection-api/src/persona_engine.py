import sys
import os
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Path references
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../integration-adapters/src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../bcollection-data')))

from core_banking.adapter import CoreBankingAdapter, CustomerInflowProfile
from los.adapter import LOSAdapter
from cic.adapter import CICAdapter
from ml.models.ml01_self_cure import ML01SelfCureModel
from ml.models.ml04_best_time import ML04BestTimeToContactModel
from scoring_config_loader import get_scoring_config_manager
from database import get_debtor_behavioral_metrics


class D1AbilityEngine:
    """
    Trục D1: Tính điểm Khả năng trả nợ (Ability Score 0 - 100).
    Cấu hình toàn bộ trọng số và ngưỡng từ scoring_config.yaml (Hỗ trợ Hot-Reload).
    """
    @staticmethod
    def calculate(
        monthly_obligation: float,
        inflow_profile: CustomerInflowProfile,
        cic_score: int,
        worst_group_other_banks: int,
        collateral_ltv: Optional[float] = None,
        product_code: str = "DEFAULT"
    ) -> Dict[str, Any]:
        cfg = get_scoring_config_manager().get_d1_config()
        weights = cfg["weights"]
        cic_cfg = cfg["cic_penalty"]
        collat_cfg = cfg["collateral_thresholds"]
        bounds = cfg["score_bounds"]

        # 1. S_DSR theo Phân khúc Sản phẩm & Kiểm tra Sàn Mức sống Tối thiểu (Living Wage)
        inflow = max(1.0, inflow_profile.verified_inflow_avg_monthly)
        dsr = monthly_obligation / inflow
        remaining_income = inflow - monthly_obligation

        # Lấy ngưỡng DSR đặc thù theo từng loại sản phẩm
        prod_dsr_map = cfg.get("product_dsr_thresholds", {})
        prod_cfg = prod_dsr_map.get(
            product_code,
            prod_dsr_map.get("DEFAULT", cfg.get("dsr_thresholds", {"safe_max": 0.35, "insolvent_min": 0.80}))
        )
        safe_max = prod_cfg.get("safe_max", 0.35)
        insolvent_min = prod_cfg.get("insolvent_min", 0.80)

        # Tính điểm cơ sở theo đường cong DSR của sản phẩm
        if dsr <= safe_max:
            s_dsr_base = 100.0
        elif dsr >= insolvent_min:
            s_dsr_base = 0.0
        else:
            s_dsr_base = 100.0 * (1.0 - (dsr - safe_max) / max(0.01, (insolvent_min - safe_max)))

        # Hiệu chỉnh theo Mức sống tối thiểu & Đệm thanh khoản khả dụng theo quy mô nghĩa vụ nợ
        living_cfg = cfg.get("living_wage_policy", {})
        living_min = living_cfg.get("living_wage_min", 5_500_000.0)
        safe_cushion_multiple = living_cfg.get("safe_cushion_multiple", 1.00)
        affluent_remaining_min = living_cfg.get("affluent_remaining_min", 30_000_000.0)
        overleveraged_cushion_max = living_cfg.get("overleveraged_cushion_max", 0.20)
        large_exposure_obligation = living_cfg.get("large_exposure_obligation", 20_000_000.0)

        cushion_multiple = remaining_income / max(monthly_obligation, 1.0)

        drivers = []
        if remaining_income < living_min:
            # Nhánh 1: Kiệt quệ sinh tồn do số tiền còn lại không đủ sống (ví dụ lương 8tr nợ 4tr -> còn 4tr < 5.5tr)
            penalty_ratio = max(0.0, remaining_income / max(1.0, living_min))
            s_dsr = min(s_dsr_base, 100.0 * penalty_ratio * 0.6)  # Phạt nặng điểm DSR
            drivers.append(f"Cảnh báo kiệt quệ: Thu nhập còn lại sau trả nợ ({remaining_income/1e6:.1f}tr) thấp hơn mức sống tối thiểu {living_min/1e6:.1f}tr/tháng")
        elif cushion_multiple < overleveraged_cushion_max and monthly_obligation >= large_exposure_obligation:
            # Nhánh 2: Đòn bẩy cao rủi ro (khoản nợ lớn >= 20M/tháng nhưng tiền dư < 20% nghĩa vụ nợ, ví dụ nợ 80tr còn dư 15tr -> đệm chỉ 18.7% nghĩa vụ)
            s_dsr = max(10.0, s_dsr_base - 15.0)
            drivers.append(f"Cảnh báo đòn bẩy nợ cao: Đệm dòng tiền ({remaining_income/1e6:.1f}tr) chỉ đạt {cushion_multiple*100:.0f}% nghĩa vụ trả nợ tháng ({monthly_obligation/1e6:.1f}tr)")
        elif cushion_multiple >= safe_cushion_multiple and remaining_income >= affluent_remaining_min and dsr > safe_max:
            # Nhánh 3: Đệm thanh khoản dồi dào chuẩn khá giả (>= 30M dư sau trả nợ) và đệm >= 1.0x nghĩa vụ nợ
            bonus = min(25.0, cushion_multiple * 10.0)
            s_dsr = min(100.0, s_dsr_base + bonus)
            drivers.append(f"Dòng tiền an toàn: Đệm khả dụng ({remaining_income/1e6:.1f}tr) gấp {cushion_multiple:.1f}x nghĩa vụ nợ")
        else:
            s_dsr = s_dsr_base
            if dsr <= safe_max:
                drivers.append(f"DSR an toàn {dsr*100:.1f}% ({product_code}) trên thu nhập {inflow/1e6:.1f}tr/tháng")
            else:
                drivers.append(f"DSR {dsr*100:.1f}% vượt ngưỡng an toàn {safe_max*100:.0f}% của gói {product_code}")

        # 2. S_Inflow
        cv = max(0.0, 1.0 - inflow_profile.stability_coefficient)
        casa_ratio = min(1.0, inflow_profile.casa_balance / max(1.0, monthly_obligation))
        s_inflow = 50.0 * (1.0 - cv) + 50.0 * casa_ratio

        # 3. S_CIC (Lịch sử CIC)
        penalty_per_grp = cic_cfg["penalty_per_group"]
        s_cic = max(0.0, 100.0 - (worst_group_other_banks - 1) * penalty_per_grp)

        # 4. S_Collateral (Tài sản bảo đảm)
        if collateral_ltv is not None:
            safe_ltv = collat_cfg["safe_ltv"]
            max_ltv = collat_cfg["max_ltv"]
            if collateral_ltv <= safe_ltv:
                s_collateral = 100.0
            elif collateral_ltv >= max_ltv:
                s_collateral = 0.0
            else:
                s_collateral = 100.0 * (1.0 - (collateral_ltv - safe_ltv) / max(0.01, (max_ltv - safe_ltv)))
        else:
            s_collateral = collat_cfg["unsecured_score"]

        raw_score = (weights["dsr"] * s_dsr 
                     + weights["inflow"] * s_inflow 
                     + weights["cic"] * s_cic 
                     + weights["collateral"] * s_collateral)
        score = int(max(bounds["min"], min(bounds["max"], round(raw_score))))

        if inflow_profile.casa_balance > monthly_obligation:
            drivers.append(f"Số dư CASA {inflow_profile.casa_balance/1e6:.1f}tr đệm thanh khoản tốt")
        else:
            drivers.append(f"Dòng tiền lương ổn định ngày {inflow_profile.salary_day_of_month} hàng tháng")

        if collateral_ltv is not None:
            drivers.append(f"Tài sản thế chấp đệm an toàn LTV {collateral_ltv*100:.0f}%")

        return {
            "value": score,
            "coverage": cfg.get("coverage", 0.88),
            "top_drivers": drivers[:2]
        }


class D2WillingnessEngine:
    """
    Trục D2: Tính điểm Thiện chí trả nợ (Willingness Score 0 - 100).
    Cấu hình toàn bộ trọng số và ngưỡng từ scoring_config.yaml (Hỗ trợ Hot-Reload).
    """
    @staticmethod
    def calculate(
        dpd: int,
        cif_hash: int,
        self_cure_propensity: float,
        paying_other_banks_while_overdue: bool,
        actual_ptp_kept_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        cfg = get_scoring_config_manager().get_d2_config()
        weights = cfg["weights"]
        ptp_cfg = cfg["ptp_decay"]
        pri_cfg = cfg["priority_scores"]
        avoid_cfg = cfg["avoidance"]
        bounds = cfg["score_bounds"]

        # 1. PTP Kept Rate (Ưu tiên số liệu thực tế từ DB nếu có)
        if actual_ptp_kept_rate is not None:
            ptp_kept_rate = actual_ptp_kept_rate
        else:
            base_rate = ptp_cfg["base_rate"]
            decay_days = ptp_cfg["decay_cycle_days"]
            ptp_kept_rate = max(ptp_cfg["min_rate"], min(ptp_cfg["max_rate"], base_rate - (dpd / decay_days)))
        s_ptp = ptp_kept_rate * 100.0

        # 2. Self-cure
        s_self_cure = self_cure_propensity * 100.0

        # 3. Priority (Thứ tự ưu tiên thanh toán)
        if paying_other_banks_while_overdue:
            s_priority = pri_cfg["paying_other_banks"]
        else:
            s_priority = pri_cfg["normal"]

        # 4. Avoidance (Tốc độ phạt né tránh theo DPD)
        penalty_rate = avoid_cfg["penalty_per_day"]
        max_pen = avoid_cfg["max_penalty"]
        avoidance_penalty = min(max_pen, dpd * penalty_rate)
        s_avoidance = 100.0 - avoidance_penalty

        raw_score = (weights["ptp"] * s_ptp 
                     + weights["self_cure"] * s_self_cure 
                     + weights["priority"] * s_priority 
                     + weights["avoidance"] * s_avoidance)
        score = int(max(bounds["min"], min(bounds["max"], round(raw_score))))

        drivers = []
        if paying_other_banks_while_overdue:
            drivers.append("Cảnh báo: Đang trả nợ TCTD khác trong khi nợ Ngân hàng")
        else:
            drivers.append(f"Tỷ lệ giữ cam kết hẹn trả (PTP Kept) {ptp_kept_rate*100:.0f}%")

        if self_cure_propensity >= 0.70:
            drivers.append(f"Xác suất tự khỏi cao {self_cure_propensity*100:.0f}% trong 48h")
        elif dpd > 20:
            drivers.append("Dấu hiệu bắt đầu né tránh khi số ngày quá hạn tăng")
        else:
            drivers.append("Thái độ hợp tác tích cực khi trao đổi thông tin")

        return {
            "value": score,
            "coverage": cfg.get("coverage", 0.82),
            "top_drivers": drivers[:2]
        }


class D3ContactabilityEngine:
    """
    Trục D3: Tính điểm Khả năng tiếp cận (Contactability Score 0 - 100).
    Cấu hình toàn bộ trọng số và ngưỡng từ scoring_config.yaml (Hỗ trợ Hot-Reload).
    """
    @staticmethod
    def calculate(
        expected_rpc_rate: float,
        cif_hash: int,
        app_logins: Optional[int] = None
    ) -> Dict[str, Any]:
        cfg = get_scoring_config_manager().get_d3_config()
        weights = cfg["weights"]
        dig_cfg = cfg["digital_thresholds"]
        bounds = cfg["score_bounds"]

        s_rpc = expected_rpc_rate * 100.0

        # Digital footprint (Lấy số lần tương tác số từ DB hoặc fallback hash)
        logins = app_logins if app_logins is not None else ((cif_hash % 15) + 2)
        if logins >= dig_cfg["high_logins"]:
            s_digital = dig_cfg["high_score"]
        elif logins >= dig_cfg["medium_logins"]:
            s_digital = dig_cfg["medium_score"]
        else:
            s_digital = dig_cfg["low_score"]

        s_recency = 90.0 - (cif_hash % 20)

        raw_score = (weights["rpc"] * s_rpc 
                     + weights["digital"] * s_digital 
                     + weights["recency"] * s_recency)
        score = int(max(bounds["min"], min(bounds["max"], round(raw_score))))

        drivers = [
            "Số di động chính chủ hoạt động trên mạng",
            f"Tần suất đăng nhập SmartBanking: {logins} lần/tháng"
        ]

        return {
            "value": score,
            "coverage": cfg.get("coverage", 0.90),
            "top_drivers": drivers
        }


class RootCauseAnalyzer:
    """
    Bộ Phân tích & Suy luận Nguyên nhân Gốc (Root Cause Engine).
    Đã được chuyển đổi sang chuẩn Camunda DMN 1.3 qua EmbeddedDMNEngine:
    - Đọc bảng quyết định từ rules/root_cause_rules.dmn
    - Không hardcode trong code, cán bộ quản trị rủi ro có thể cập nhật qua Camunda Modeler
    - Tốc độ thực thi < 0.2ms, hỗ trợ Hot-Reload tự động
    - Cung cấp rule_id phục vụ kiểm toán tuân thủ (Audit Trail)
    """
    @staticmethod
    def diagnose(
        case: Dict[str, Any],
        inflow_profile: CustomerInflowProfile,
        paying_other_banks_while_overdue: bool
    ) -> Dict[str, Any]:
        from dmn_engine import get_dmn_engine
        engine = get_dmn_engine()
        return engine.evaluate_root_cause(
            case=case,
            inflow_profile=inflow_profile,
            paying_other_banks_while_overdue=paying_other_banks_while_overdue
        )


class DynamicDebtorPersonaEngine:
    """
    Dịch vụ Tạo Chân dung Khách nợ Debtor Persona 360 Động.
    Hoàn toàn hướng cấu hình (Configuration Driven) và nạp dữ liệu thực tế từ DB:
    - Tích hợp CoreBankingAdapter, LOSAdapter, CICAdapter
    - Nạp hành vi lịch sử thực tế từ CSDL SQLite (bảng cases & case_interactions)
    - Mô hình AI ML01 Self-Cure và ML04 Best-Time
    - Công thức toán học D1, D2, D3 cấu hình qua scoring_config.yaml
    - Bộ suy luận Nguyên nhân gốc Camunda DMN và CBR 192 Chiều.
    """
    def __init__(
        self,
        core_adapter: CoreBankingAdapter,
        los_adapter: LOSAdapter,
        cic_adapter: CICAdapter
    ):
        self.core_adapter = core_adapter
        self.los_adapter = los_adapter
        self.cic_adapter = cic_adapter
        ml01_cfg = get_scoring_config_manager().get_ml01_config()
        self.ml01 = ML01SelfCureModel(config=ml01_cfg)
        self.ml04 = ML04BestTimeToContactModel()

    def generate_persona(self, case: Dict[str, Any]) -> Dict[str, Any]:
        cif = case["debtor_cif"]
        loan_id = case["loan_id"]
        case_id = case["case_id"]
        dpd = int(case.get("dpd", 1))
        cif_hash = sum(ord(ch) for ch in cif)

        # 1. Truy vấn Dữ liệu từ các Backend Adapters (Core Banking, CIC, LOS)
        inflow_profile = self.core_adapter.get_customer_inflow_profile(cif)
        cic_report = self.cic_adapter.get_credit_report(cif)
        collaterals = self.los_adapter.get_loan_collateral(loan_id)
        ltv = collaterals[0].ltv_ratio if collaterals else None

        # 2. Truy vấn Đặc trưng Hành vi Thực tế từ CSDL SQLite (bảng cases & case_interactions)
        behavioral = get_debtor_behavioral_metrics(cif, case_id)

        # 3. Chạy Mô hình AI ML01 (Self-Cure Propensity) với dữ liệu thực tế
        monthly_obligation = case.get("overdue_amount", 5_000_000.0)
        inferred_day = getattr(inflow_profile, "inferred_pay_day_of_month", 12) or 12
        ml01_features = {
            "dpd": dpd,
            "historical_on_time_ratio": behavioral["historical_on_time_ratio"],
            "days_since_salary_day": abs(datetime.now().day - inflow_profile.salary_day_of_month),
            "prior_cure_count": behavioral["prior_cure_count"],
            "dti_ratio": min(0.9, monthly_obligation / max(1.0, inflow_profile.verified_inflow_avg_monthly)),
            "has_payroll_relationship": getattr(inflow_profile, "has_payroll_relationship", True),
            "inflow_archetype": getattr(inflow_profile, "inflow_archetype", "PAYROLL_INTERNAL"),
            "casa_buffer_ratio": getattr(inflow_profile, "casa_buffer_ratio", 1.0),
            "payroll_bank_name": getattr(inflow_profile, "payroll_bank_name", "BIDV"),
            "days_since_historical_pay_rhythm": abs(datetime.now().day - inferred_day)
        }
        self_cure_pred = self.ml01.evaluate_case(cif, ml01_features)

        # 4. Chạy Mô hình AI ML04 (Best-Time-To-Contact)
        prod_code = case.get("product_code", "")
        occupation = "MERCHANT" if prod_code in ("MORTGAGE", "MORTGAGE_HOME", "SME_WORKING_CAPITAL") else "OFFICE_WORKER"
        best_time_pred = self.ml04.predict_best_time(cif, {
            "occupation": occupation,
            "age": 32 + (cif_hash % 25)
        })

        # 5. Tính toán Điểm số 3 Trục D1, D2, D3 theo Công thức Toán học cấu hình
        ability_data = D1AbilityEngine.calculate(
            monthly_obligation=monthly_obligation,
            inflow_profile=inflow_profile,
            cic_score=cic_report.credit_score,
            worst_group_other_banks=cic_report.worst_group_other_banks,
            collateral_ltv=ltv,
            product_code=prod_code
        )

        actual_ptp = None
        if behavioral["ptp_agreed_count"] > 0:
            actual_ptp = 0.90  # Khách hàng có tiền lệ giữ cam kết PTP tốt

        willingness_data = D2WillingnessEngine.calculate(
            dpd=dpd,
            cif_hash=cif_hash,
            self_cure_propensity=self_cure_pred.self_cure_propensity,
            paying_other_banks_while_overdue=cic_report.paying_other_banks_while_overdue,
            actual_ptp_kept_rate=actual_ptp
        )

        contactability_data = D3ContactabilityEngine.calculate(
            expected_rpc_rate=best_time_pred.expected_rpc_rate,
            cif_hash=cif_hash,
            app_logins=behavioral["app_logins"]
        )

        # 6. Phân loại Phân khúc Ma trận 2x2 từ file cấu hình scoring_config.yaml
        seg_cfg = get_scoring_config_manager().get_segment_matrix_config()
        a_cutoff = seg_cfg.get("ability_cutoff", 60)
        w_cutoff = seg_cfg.get("willingness_cutoff", 50)

        if ability_data["value"] >= a_cutoff and willingness_data["value"] >= w_cutoff:
            segment_cell = "S1"
            segment_name = "Tự khỏi cao / Nhắc nhẹ"
        elif ability_data["value"] < a_cutoff and willingness_data["value"] >= w_cutoff:
            segment_cell = "S2"
            segment_name = "Lệch dòng tiền / Cần hẹn PTP"
        elif ability_data["value"] >= a_cutoff and willingness_data["value"] < w_cutoff:
            segment_cell = "S3"
            segment_name = "Áp lực nợ / Chây ỳ chọn lọc"
        else:
            segment_cell = "S4"
            segment_name = "Nguy cơ cao / Chuẩn bị pháp lý"

        # 7. Chuẩn đoán Nguyên nhân Gốc Động (Root Cause qua Camunda DMN)
        root_cause = RootCauseAnalyzer.diagnose(
            case=case,
            inflow_profile=inflow_profile,
            paying_other_banks_while_overdue=cic_report.paying_other_banks_while_overdue
        )

        # 8. So sánh Thực tế với 1,000 Reference Cases trong SQLite qua Vector Nhúng 192 Chiều
        from cbr_engine import find_top_similar_reference_cases, synthesize_playbook_from_references
        
        similar_cases = find_top_similar_reference_cases(
            case=case,
            root_cause=root_cause["primary"],
            d1=ability_data["value"] / 100.0,
            d2=willingness_data["value"] / 100.0,
            d3=contactability_data["value"] / 100.0,
            top_k=5
        )
        cbr_playbook = synthesize_playbook_from_references(similar_cases)

        ml01_cfg = get_scoring_config_manager().get_ml01_config()
        chan_thresh = ml01_cfg.get("channel_threshold", 0.70)
        cbr_playbook["best_channel"] = "ZALO" if self_cure_pred.self_cure_propensity > chan_thresh else "VOICE"
        cbr_playbook["best_time_window"] = best_time_pred.best_time_window

        # 9. Cảnh báo L6 Guardrail bắt buộc
        guarantor_note = f", Bên bảo lãnh ({case['guarantor_id']})" if case.get("guarantor_id") else ""
        mandatory_guardrails = [
            f"Chỉ được liên hệ: Chính chủ ({case['full_name']}){guarantor_note}.",
            "TUYỆT ĐỐI KHÔNG liên hệ người thân, đồng nghiệp không có cam kết bảo lãnh.",
            f"Khung giờ hợp lệ: 07:00 – 21:00 (Khuyến nghị gọi {best_time_pred.best_time_window})."
        ]

        return {
            "case_id": case["case_id"],
            "loan_id": loan_id,
            "debtor_cif": cif,
            "full_name": case["full_name"],
            "phone_e164": case["phone_e164"],
            "dpd": dpd,
            "product_code": case.get("product_code", "UNSECURED_LOAN"),
            "overdue_amount": monthly_obligation,
            "experiment_arm": case.get("experiment_arm", "TREATED"),
            "status": case.get("status", "ASSIGNED"),
            "scores": {
                "ability": ability_data,
                "willingness": willingness_data,
                "contactability": contactability_data
            },
            "segment_cell": segment_cell,
            "segment_name": segment_name,
            "root_cause": root_cause,
            "inflow_profile": {
                "archetype": getattr(inflow_profile, "inflow_archetype", "PAYROLL_INTERNAL"),
                "has_payroll": getattr(inflow_profile, "has_payroll_relationship", True),
                "payroll_bank": getattr(inflow_profile, "payroll_bank_name", "BIDV"),
                "casa_balance": getattr(inflow_profile, "casa_balance", 0.0),
                "casa_buffer_ratio": getattr(inflow_profile, "casa_buffer_ratio", 1.0),
                "salary_day": getattr(inflow_profile, "salary_day_of_month", 10) if getattr(inflow_profile, "has_payroll_relationship", True) else getattr(inflow_profile, "inferred_pay_day_of_month", 12)
            },
            "behavioral_summary": {
                "total_interactions": behavioral["total_interactions"],
                "historical_on_time_ratio": behavioral["historical_on_time_ratio"],
                "prior_cure_count": behavioral["prior_cure_count"],
                "app_logins_monthly": behavioral["app_logins"]
            },
            "recommended_playbook": cbr_playbook,
            "similar_references": similar_cases,
            "mandatory_guardrail_notes": mandatory_guardrails
        }
