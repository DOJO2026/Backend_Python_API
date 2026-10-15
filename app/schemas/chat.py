from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional,List


#####################################
###ANTIGUO MODELO
# class ChatRequest(BaseModel):
#     question: str = Field(..., min_length=1, description="Pregunta del usuario")
#     session_id: Optional[str] = Field(None, description="ID de sesion. Si no se envia, se crea una nueva")

class HistoryTurn(BaseModel):
    role: str
    content: str
    
# class ChatResponse(BaseModel):
#     session_id: str
#     answer: str
#     fuentes: List[str]
#     herramientas_usadas: List[str]
#     blocked: bool = False
#     requiere_confirmacion: bool = False
#####################################


##################### NUEVO MODELO ################
#####################################
class _Base(BaseModel):
    # Permite construir con nombres snake_case (conversation_id=...) y
    # serializar con alias camelCase (conversationId) hacia el frontend.
    model_config = ConfigDict(populate_by_name=True)

#* **Ruta:** `/api/v1/chat/conversations`
#conversations.json          # Listado de conversaciones e historial
class ChatConversation(_Base):
    id: str
    title: str
    updated_at: str = Field(..., alias="updatedAt")
    date_group: Optional[Literal["Hoy", "Ayer", "Últimos 7 días", "Mes anterior"]] = Field(
        None, alias="dateGroup"
    )
    pinned: Optional[bool] = False
    archived: Optional[bool] = False
    message_count: Optional[int] = Field(0, alias="messageCount")
    category: Optional[
        Literal[
            "Legal", "Operaciones", "Ciberseguridad", "Finanzas", "General",
            "Observabilidad", "Infraestructura", "Bases de Datos",
        ]
    ] = None
    model_used: Optional[str] = Field(None, alias="modelUsed")
    cited_sources_count: Optional[int] = Field(0, alias="citedSourcesCount")
    tokens_used: Optional[int] = Field(0, alias="tokensUsed")
    positive_feedback_count: Optional[int] = Field(0, alias="positiveFeedbackCount")



#####################################
#* **Ruta:** `/api/v1/chat/conversations/:id/messages`
#messages.json               # Mensajes por conversación con estados interactivos
class MessageSource(_Base):
    title: Optional[str] = None
    url: Optional[str] = None

class ClaimDetails(_Base):
    claim_number: str = Field(..., alias="claimNumber")
    status: str
    description: Optional[str] = None
    policy_number: Optional[str] = Field(None, alias="policyNumber")
    
class ChatMessage(_Base):
    id: str
    conversation_id: str = Field(..., alias="conversationId")
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    sources: Optional[List[MessageSource]] = None
    status: Optional[Literal["sending", "thinking", "streaming", "complete", "error"]] = None
    feedback: Optional[Literal["up", "down"]] = None
    model_used: Optional[str] = Field(None, alias="modelUsed")
    interactive_type: Optional[
        Literal[
            "claim_prompt_request",
            "claim_ask_attachment",
            "claim_uploader",
            "claim_scanned_result",
            "tool_confirmation",  # NUEVO: pregunta S/N antes de ejecutar una tool
        ]
    ] = Field(None, alias="interactiveType")
    claim_details: Optional[ClaimDetails] = Field(None, alias="claimDetails")
    # NUEVOS: reemplazan a blocked y herramientas_usadas del ChatResponse viejo
    blocked: Optional[bool] = False
    tools_used: Optional[List[str]] = Field(None, alias="toolsUsed")
#####################################

#####################################
#* **Ruta:** `/api/v1/chat/messages`
#send-message-request.json   # Payload de envío de consulta (prompt)
class ChatRequest(_Base):
    conversation_id: Optional[str] = Field(None, alias="conversationId")
    content: str
    model_id: Optional[str] = Field(None, alias="modelId")
    temperature: float = Field(0.5)
    reasoning_depth: str = Field("standard", alias="reasoningDepth")
    stream: bool = True
    attached_docs: Optional[List[str]] = Field(None, alias="attachedDocs")
