import hashlib
import time
from typing import Dict, Any

class VietQRService:
    """
    Sinh mã VietQR động chuẩn Napas247 và link thanh toán Tokenized rút gọn.
    BANK BIN: 970418.
    """
    BANK_BIN = "970418"
    BASE_PAYMENT_PORTAL_URL = "https://bank.vn/c"

    def generate_payment_link(self, loan_id: str, debtor_cif: str, amount: float) -> Dict[str, Any]:
        """
        Sinh tokenized short link và chuỗi payload VietQR.
        """
        # Sinh token an toàn 8 ký tự
        raw_seed = f"{loan_id}:{debtor_cif}:{amount}:{time.time()}".encode('utf-8')
        token = hashlib.md5(raw_seed).hexdigest()[:8].upper()
        
        short_url = f"{self.BASE_PAYMENT_PORTAL_URL}/{token}"
        transfer_desc = f"TT DUP {loan_id}"

        # Chuỗi Napas247 Quick Pay Format
        qr_payload = f"00020101021238540010A00000072701240006{self.BANK_BIN}0110{loan_id[:10]}530370454{int(amount):02d}5802VN62{len(transfer_desc):02d}{transfer_desc}6304"

        return {
            "token": token,
            "short_url": short_url,
            "loan_id": loan_id,
            "debtor_cif": debtor_cif,
            "amount": amount,
            "bank_bin": self.BANK_BIN,
            "bank_name": "VIETNAM_BANK",
            "account_no": loan_id,
            "transfer_content": transfer_desc,
            "qr_payload": qr_payload,
            "expires_in_hours": 72
        }
