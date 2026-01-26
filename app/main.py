import time
from typing import List, Optional

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import (
    HTMLResponse,
    FileResponse,
    JSONResponse,
    Response
)
from starlette.middleware.base import BaseHTTPMiddleware

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


app = FastAPI(title="API Proxy Traffic Monitor")

# --------------------------------
# Global State (Prototype-level)
# --------------------------------

api_logs: List[dict] = []
monitored_api: Optional[str] = None


# --------------------------------
# UI Dashboard
# --------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Proxy Monitor</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            input { padding: 8px; width: 420px; }
            button { padding: 8px 16px; margin-top: 10px; }
            code { background: #eee; padding: 4px; }
        </style>
    </head>
    <body>
        <h2>API Proxy Traffic Monitoring</h2>

        <form method="post" action="/set-api">
            <label><b>Target API Base URI</b></label><br><br>
            <input type="text" name="api_uri" placeholder="https://httpbin.org" required>
            <br><br>
            <button type="submit">Start Monitoring</button>
        </form>

        <br><hr><br>

        <p><b>Proxy Usage Example:</b></p>
        <code>http://localhost:8000/proxy/get</code>

        <br><br>

        <form method="get" action="/generate-pdf">
            <button type="submit">Generate PDF Report</button>
        </form>
    </body>
    </html>
    """


# --------------------------------
# Set Target API
# --------------------------------

@app.post("/set-api")
async def set_api(api_uri: str = Form(...)):
    global monitored_api
    monitored_api = api_uri.rstrip("/")
    api_logs.clear()

    return JSONResponse(
        content={
            "message": "Proxy monitoring started",
            "monitored_api": monitored_api
        }
    )


# --------------------------------
# PROXY ROUTE (CORE FEATURE)
# --------------------------------

@app.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_request(path: str, request: Request):
    if not monitored_api:
        return JSONResponse(
            status_code=400,
            content={"error": "No target API set"}
        )

    target_url = f"{monitored_api}/{path}"

    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()
    start_time = time.time()

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            params=request.query_params
        )

    latency = round(time.time() - start_time, 4)

    # Log traffic
    api_logs.append({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": request.method,
        "target_url": target_url,
        "status_code": response.status_code,
        "latency_seconds": latency,
        "request_size": len(body),
        "response_size": len(response.content)
    })

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers)
    )


# --------------------------------
# PDF Report Generator
# --------------------------------

@app.get("/generate-pdf")
async def generate_pdf():
    file_path = "api_traffic_report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("API Proxy Traffic Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    if monitored_api:
        elements.append(
            Paragraph(f"<b>Target API:</b> {monitored_api}", styles["Normal"])
        )
        elements.append(Spacer(1, 12))

    if not api_logs:
        elements.append(Paragraph("No traffic recorded.", styles["Normal"]))
    else:
        for idx, log in enumerate(api_logs, start=1):
            text = (
                f"<b>{idx}.</b> "
                f"Time: {log['timestamp']} | "
                f"Method: {log['method']} | "
                f"URL: {log['target_url']} | "
                f"Status: {log['status_code']} | "
                f"Latency: {log['latency_seconds']}s | "
                f"Req Size: {log['request_size']}B | "
                f"Resp Size: {log['response_size']}B"
            )
            elements.append(Paragraph(text, styles["Normal"]))
            elements.append(Spacer(1, 6))

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename="api_traffic_report.pdf"
    )
