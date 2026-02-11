from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class TestRequest(BaseModel):
    username: str
    email: str
    age: int = None

@app.post("/api/secure")
async def secure_endpoint(data: TestRequest):
    """Test endpoint that validates parameters"""
    errors = {}
    
    if not data.username:
        errors["username"] = "username parameter is required"
    elif len(data.username) < 3:
        errors["username"] = "username must be at least 3 characters"
    
    if not data.email:
        errors["email"] = "email parameter is missing"
    elif "@" not in data.email:
        errors["email"] = "email parameter is invalid"
    
    if data.age is not None and data.age < 18:
        errors["age"] = "age parameter must be at least 18"
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail=errors
        )
    
    return {"message": "Success", "data": data}

@app.get("/api/secure")
async def secure_get_endpoint(username: str = None, email: str = None):
    """GET endpoint that validates parameters"""
    errors = {}
    
    if not username:
        errors["username"] = "username parameter is required"
    
    if not email:
        errors["email"] = "email parameter is missing"
    elif "@" not in email:
        errors["email"] = "email parameter is invalid"
    
    if errors:
        raise HTTPException(
            status_code=400,
            detail=errors
        )
    
    return {"message": "Success", "username": username, "email": email}

@app.get("/health")
async def health():
    return {"status": "ok"}
