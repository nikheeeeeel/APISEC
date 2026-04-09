"""
Demo HTTP surface for runtime_validator OpenAPI fixtures.

Served from the same process as the main API so runtime checks can use
base_url http://127.0.0.1:8000 (or the host the backend listens on).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["integration-demo"])


# --- Northwind catalog (schema 1 — all pass) ---


@router.get("/northwind/catalog/v1/health")
async def rtv_s1_status() -> Dict[str, Any]:
    return {"ok": True, "service": "northwind-catalog"}


@router.get("/northwind/catalog/v1/products")
async def rtv_s1_widgets() -> Dict[str, Any]:
    return {"items": [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]}


@router.get("/northwind/catalog/v1/products/{productId}")
async def rtv_s1_widget(productId: int) -> Dict[str, Any]:
    return {"id": productId, "name": f"w-{productId}"}


@router.post("/northwind/catalog/v1/promotions")
async def rtv_s1_messages_post(
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    title = payload.get("title", "sample")
    priority = int(payload.get("priority", 1))
    return {"id": 1, "title": title, "priority": priority}


@router.put("/northwind/catalog/v1/promotions/{promotionId}")
async def rtv_s1_messages_put(
    promotionId: int,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    return {"id": promotionId, "title": payload.get("title", "sample")}


@router.patch("/northwind/catalog/v1/feature-flags")
async def rtv_s1_flags_patch(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    return {
        "darkMode": bool(payload.get("darkMode", True)),
        "beta": bool(payload.get("beta", True)),
    }


@router.get("/northwind/catalog/v1/sales-summary")
async def rtv_s1_summary() -> Dict[str, Any]:
    return {"totals": {"count": 42, "rate": 0.25}}


@router.post("/northwind/catalog/v1/products/bulk-resolve")
async def rtv_s1_batch(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    ids: List[int] = []
    raw = payload.get("ids")
    if isinstance(raw, list):
        ids = [int(x) for x in raw if x is not None]
    if not ids:
        ids = [1]
    return {"processed": len(ids), "ids": ids}


# --- Fabrikam partner hub (schema 2 — all pass) ---


@router.get("/fabrikam/partners/v1/heartbeat")
async def rtv_s2_ping() -> Dict[str, Any]:
    return {
        "pong": True,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


@router.get("/fabrikam/partners/v1/directory/search")
async def rtv_s2_search(q: str = Query(...)) -> Dict[str, Any]:
    return {"query": q, "hits": len(q) if q else 0}


@router.get("/fabrikam/partners/v1/programs/{programCode}")
async def rtv_s2_tag(programCode: str) -> Dict[str, Any]:
    return {"slug": programCode, "count": max(1, len(programCode))}


@router.post("/fabrikam/partners/v1/invitations")
async def rtv_s2_invite(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    email = payload.get("email", "test@example.com")
    return {"email": email, "sent": True}


@router.put("/fabrikam/partners/v1/settings/ui")
async def rtv_s2_preferences_put(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    theme = payload.get("theme", "sample")
    density = payload.get("density", "sample")
    return {"theme": theme, "density": density}


@router.patch("/fabrikam/partners/v1/settings/ui")
async def rtv_s2_preferences_patch(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    return {"theme": payload.get("theme", "sample")}


@router.get("/fabrikam/partners/v1/usage/monthly-series")
async def rtv_s2_stats() -> Dict[str, Any]:
    return {
        "series": [
            {"day": "2023-01-01", "value": 1.0},
            {"day": "2023-01-02", "value": 2.5},
        ]
    }


@router.delete("/fabrikam/partners/v1/session")
async def rtv_s2_session_delete() -> Dict[str, Any]:
    return {"ended": True}


# --- Adventure Works warehouse (schema 3 — six pass, two intentional failures) ---


@router.get("/adventureworks/warehouse/v1/status")
async def rtv_s3_health() -> Dict[str, Any]:
    return {"up": True}


@router.get("/adventureworks/warehouse/v1/stock-lots")
async def rtv_s3_items() -> Dict[str, Any]:
    return {"rows": [{"sku": "A-1", "qty": 3}, {"sku": "B-2", "qty": 1}]}


@router.get("/adventureworks/warehouse/v1/stock-lots/{sku}")
async def rtv_s3_item(sku: str) -> Dict[str, Any]:
    return {"sku": sku, "qty": 7}


@router.post("/adventureworks/warehouse/v1/bin-notes")
async def rtv_s3_notes_post(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    body = payload.get("body", "sample")
    return {"id": 1, "body": body}


@router.put("/adventureworks/warehouse/v1/bin-notes/{noteId}")
async def rtv_s3_notes_put(
    noteId: int,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    return {"id": noteId, "body": payload.get("body", "sample")}


@router.get("/adventureworks/warehouse/v1/site-config")
async def rtv_s3_meta() -> Dict[str, Any]:
    return {"version": "1.0.0", "flags": {"readOnly": False}}


@router.get("/adventureworks/warehouse/v1/replication/sync-status")
async def rtv_s3_misbehave_status() -> JSONResponse:
    # Spec documents 200 only — force status mismatch.
    return JSONResponse(status_code=503, content={"ok": False, "reason": "demo"})


@router.get("/adventureworks/warehouse/v1/replication/lag-summary")
async def rtv_s3_misbehave_schema() -> Dict[str, Any]:
    # 200 but types disagree with spec (integer vs string, string vs integer).
    return {"score": "not-an-integer", "label": 404}
