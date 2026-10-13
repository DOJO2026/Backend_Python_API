from pydantic import BaseModel,Field
from typing import Optional,List

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta del usuario")
    session_id: Optional[str] = Field(None, description="ID de sesion. Si no se envia, se crea una nueva")


class HistoryTurn(BaseModel):
    role: str
    content: str
    

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    fuentes: List[str]
    herramientas_usadas: List[str]
    blocked: bool = False
    requiere_confirmacion: bool = False
