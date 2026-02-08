from pydantic import BaseModel
from typing import Optional

class CanonicalParameter(BaseModel):
    name: str
    in_: str  # query, path, header
    type_: str  # string, integer, etc.
    required: bool = False
    description: Optional[str] = None
    example: Optional[str] = None
