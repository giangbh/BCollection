"""
B.Collection Mock Legacy Banking Gateway (Port 8090)
Điểm tiếp nhận tập trung (Unified API Gateway) điều phối sang 6 Microservices:
- Core Banking (Port 8091)
- LOS (Port 8092)
- CIC (Port 8093)
- CTI Telephony (Port 8094)
- Speech AI (Port 8095)
- Messaging Gateway (Port 8096)
"""

from legacy_servers.gateway import app
from legacy_servers.runner import run_all


def main():
    run_all()


if __name__ == "__main__":
    main()
