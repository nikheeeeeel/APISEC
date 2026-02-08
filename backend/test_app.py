from fastapi import FastAPI

app = FastAPI()

@app.get("/api/test")
async def test_endpoint(param1: str = "default"):
    """Test endpoint for Arjun discovery"""
    return {"message": "Test endpoint", "param1": param1}

@app.get("/health")
async def health():
    return {"status": "ok"}
