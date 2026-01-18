import time
from typing import List, Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


app = FastAPI(title="API Traffic Logger")


# -------------------------------
# Global State (Prototype-level)
# -------------------------------

api_logs: List[dict] = []
monitored_api: Optional[str] = None


# -------------------------------
# Middleware: API Traffic Logger
# -------------------------------

class APITrafficLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        duration = round(time.time() - start_time, 4)

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_seconds": duration,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent")
        }

        api_logs.append(log_entry)
        return response


app.add_middleware(APITrafficLoggerMiddleware)


# -------------------------------
# UI Dashboard
# -------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Traffic Logger</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            input { padding: 8px; width: 400px; }
            button { padding: 8px 16px; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h2>API Traffic Monitoring Dashboard</h2>

        <form method="post" action="/set-api">
            <label><b>Target API URI</b></label><br><br>
            <input type="text" name="api_uri" placeholder="https://api.example.com" required>
            <br><br>
            <button type="submit">Start Monitoring</button>
        </form>

        <br><hr><br>

        <form method="get" action="/generate-pdf">
            <button type="submit">Generate PDF Report</button>
        </form>
    </body>
    </html>
    """


# -------------------------------
# Set Target API (Metadata Only)
# -------------------------------

@app.post("/set-api")
async def set_api(api_uri: str = Form(...)):
    global monitored_api
    monitored_api = api_uri
    return JSONResponse(
        content={
            "message": "API monitoring started",
            "monitored_api": monitored_api
        }
    )


# -------------------------------
# PDF Report Generator
# -------------------------------

@app.get("/generate-pdf")
async def generate_pdf():
    file_path = "report.pdf"

    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("API Traffic Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    if monitored_api:
        elements.append(
            Paragraph(f"<b>Monitored API:</b> {monitored_api}", styles["Normal"])
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
                f"Path: {log['path']} | "
                f"Status: {log['status_code']} | "
                f"Latency: {log['latency_seconds']}s | "
                f"Client IP: {log['client_ip']}"
            )
            elements.append(Paragraph(text, styles["Normal"]))
            elements.append(Spacer(1, 6))

    doc.build(elements)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename="report.pdf"
    )


# -------------------------------
# Sample Endpoints (for testing)
# -------------------------------

@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
