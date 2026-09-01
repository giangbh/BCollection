import time
import hmac
import hashlib
import json
import base64
from typing import Dict, Any, Optional

SECRET_KEY = "BIDV_GUARDRAIL_ES256_INTERNAL_KEY_SECURE_TOKEN"

def generate_guardrail_token(request_id: str, loan_id: str, target_party_id: str, channel: str, ttl_seconds: int = 300) -> str:
    """
    Sinh Guardrail Token có chữ ký bảo mật và TTL ngắn (5 phút).
    """
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "req_id": request_id,
        "loan_id": loan_id,
        "party_id": target_party_id,
        "chan": channel,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": "bcollection-guardrail-l6"
    }
    
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"{message}.{sig_b64}"


def verify_guardrail_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Xác thực chữ ký và thời hạn hiệu lực của Guardrail Token.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        message = f"{header_b64}.{payload_b64}"
        
        expected_sig = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")
        
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode()
        payload = json.loads(payload_json)
        
        now = int(time.time())
        if payload.get("exp", 0) < now:
            return None  # Token expired
        
        return payload
    except Exception:
        return None
