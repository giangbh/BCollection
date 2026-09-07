"""
Legacy Cluster Runner
Khởi chạy đồng thời API Gateway (8090) và 6 Microservices (8091 - 8096).
Hỗ trợ quản lý vòng đời (graceful shutdown) và giám sát trạng thái cụm dịch vụ.
"""

import threading
import time
import uvicorn
from typing import List

from .core_server import app as core_app
from .los_server import app as los_app
from .cic_server import app as cic_app
from .cti_server import app as cti_app
from .speech_server import app as speech_app
from .messaging_server import app as messaging_app
from .gateway import app as gateway_app

SERVERS_CONFIG = [
    ("Core Banking ESB", core_app, 8091),
    ("LOS Origination", los_app, 8092),
    ("CIC Gateway", cic_app, 8093),
    ("CTI Telephony", cti_app, 8094),
    ("Speech AI & NLP", speech_app, 8095),
    ("Messaging Gateway", messaging_app, 8096),
    ("Legacy API Gateway", gateway_app, 8090),
]


def run_server(name: str, app_instance, port: int, servers_list: List[uvicorn.Server]):
    config = uvicorn.Config(
        app=app_instance,
        host="127.0.0.1",
        port=port,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    servers_list.append(server)
    server.run()


def run_all():
    print("=" * 70)
    print(" KHỞI CHẠY CỤM LEGACY BANKING MICROSERVICES & API GATEWAY")
    print("=" * 70)
    print(" [GATEWAY]       http://127.0.0.1:8090  (Swagger: http://127.0.0.1:8090/docs)")
    print(" [Core Banking]  http://127.0.0.1:8091  (Swagger: http://127.0.0.1:8091/docs)")
    print(" [LOS Loan]      http://127.0.0.1:8092  (Swagger: http://127.0.0.1:8092/docs)")
    print(" [CIC Gateway]   http://127.0.0.1:8093  (Swagger: http://127.0.0.1:8093/docs)")
    print(" [CTI Telephony] http://127.0.0.1:8094  (Swagger: http://127.0.0.1:8094/docs)")
    print(" [Speech AI]     http://127.0.0.1:8095  (Swagger: http://127.0.0.1:8095/docs)")
    print(" [Messaging]     http://127.0.0.1:8096  (Swagger: http://127.0.0.1:8096/docs)")
    print("=" * 70)

    servers = []
    threads = []

    for name, app_instance, port in SERVERS_CONFIG:
        t = threading.Thread(target=run_server, args=(name, app_instance, port, servers), daemon=True)
        t.start()
        threads.append(t)

    # Giữ luồng chính chạy
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nĐang dừng toàn bộ cụm Legacy Services...")
        for s in servers:
            s.should_exit = True
        for t in threads:
            t.join(timeout=2)
        print("Đã dừng thành công.")


if __name__ == "__main__":
    run_all()
