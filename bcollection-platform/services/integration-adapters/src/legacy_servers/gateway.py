"""
Legacy API Gateway (Port 8090)
Cổng tiếp nhận duy nhất cho toàn bộ hệ sinh thái Legacy Banking.
Tự động định tuyến (Reverse Proxy / Routing) tới 6 Microservices:
- Core Banking (Port 8091)
- LOS (Port 8092)
- CIC (Port 8093)
- CTI Telephony (Port 8094)
- Speech AI (Port 8095)
- Messaging Gateway (Port 8096)
"""

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core_server import app as core_app
from .los_server import app as los_app
from .cic_server import app as cic_app
from .cti_server import app as cti_app
from .speech_server import app as speech_app
from .messaging_server import app as messaging_app

app = FastAPI(
    title="Legacy Banking Unified API Gateway",
    description="API Gateway trung tâm (Port 8090) điều phối 6 Microservices ngân hàng (Core, LOS, CIC, CTI, Speech AI, Messaging)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES_PORT_MAP = {
    "core": ("http://127.0.0.1:8091", "/api/core/v1", core_app),
    "los": ("http://127.0.0.1:8092", "/api/los/v1", los_app),
    "cic": ("http://127.0.0.1:8093", "/api/cic/v1", cic_app),
    "cti": ("http://127.0.0.1:8094", "/api/cti/v1", cti_app),
    "speech-ai": ("http://127.0.0.1:8095", "/api/speech-ai/v1", speech_app),
    "messaging": ("http://127.0.0.1:8096", "/api/messaging/v1", messaging_app),
}


@app.get("/health")
def health():
    return {
        "status": "HEALTHY",
        "service": "legacy-api-gateway",
        "port": 8090,
        "routed_services": {
            "core_banking": "http://127.0.0.1:8091 (Docs: /legacy/core/v1)",
            "los": "http://127.0.0.1:8092 (Docs: /legacy/los/v1)",
            "cic": "http://127.0.0.1:8093 (Docs: /legacy/cic/v1)",
            "cti": "http://127.0.0.1:8094 (Docs: /legacy/cti/v1)",
            "speech_ai": "http://127.0.0.1:8095 (Docs: /legacy/speech-ai/v1)",
            "messaging": "http://127.0.0.1:8096 (Docs: /legacy/messaging/v1)",
        }
    }


# Forwarder endpoint cho toàn bộ các route
@app.api_route("/legacy/{service}/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def route_gateway(service: str, path: str, request: Request):
    if service not in SERVICES_PORT_MAP:
        raise HTTPException(status_code=404, detail=f"Service '{service}' không tồn tại trên Gateway.")

    base_url, prefix, fallback_app = SERVICES_PORT_MAP[service]
    target_url = f"{base_url}{prefix}/{path.lstrip('/')}"
    query_params = dict(request.query_params)
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["X-Forwarded-By"] = "BCOLLECTION_LEGACY_GATEWAY"

    # Thử gọi tới microservice độc lập
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                params=query_params,
                content=body,
                headers=headers
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type")
            )
    except (httpx.ConnectError, httpx.TimeoutException):
        # Fallback trực tiếp vào internal app nếu microservice chưa khởi động
        # Đảm bảo hệ thống luôn luôn hoạt động 100%
        transport = httpx.ASGITransport(app=fallback_app)
        async with httpx.AsyncClient(transport=transport, base_url=base_url) as local_client:
            resp = await local_client.request(
                method=request.method,
                url=f"{prefix}/{path.lstrip('/')}",
                params=query_params,
                content=body,
                headers=headers
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.headers.get("content-type")
            )


# Mount Swagger Documentation của 6 services vào Gateway Swagger
# Giúp người dùng khi truy cập http://127.0.0.1:8090/docs thấy đầy đủ toàn bộ endpoints!
for svc_name, (_, svc_prefix, sub_app) in SERVICES_PORT_MAP.items():
    app.mount(f"/docs/{svc_name}", sub_app)


def run():
    import uvicorn
    uvicorn.run("legacy_servers.gateway:app", host="127.0.0.1", port=8090, reload=False)


if __name__ == "__main__":
    run()
