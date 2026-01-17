from fastapi import FastAPI, Request

app = FastAPI(title="API Traffic Observer")

@app.middleware("http")
async def traffic_logger(request: Request, call_next):
    response = await call_next(request)

    print({
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code
    })

    return response

@app.get("/health")
def health():
    return {"status": "ok"}
