from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional,List

class _Base(BaseModel):
    # Permite construir con nombres snake_case (conversation_id=...) y
    # serializar con alias camelCase (conversationId) hacia el frontend.
    model_config = ConfigDict(populate_by_name=True)

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
    conversation_id: Optional[str] = Field(None, alias="conversationId")
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

class ChatRequest(_Base):
    conversation_id: Optional[str] = Field(None, alias="conversationId")
    content: str
    model_id: Optional[str] = Field(None, alias="modelId")
    temperature: float = Field(0.5)
    reasoning_depth: str = Field("standard", alias="reasoningDepth")
    stream: bool = True
    attached_docs: Optional[List[str]] = Field(None, alias="attachedDocs")
    
class RepositoryDocItem(_Base):
    id: str
    title: str
    category: str
    size: str
    updated_at: str= Field(..., alias="updatedAt")
    chunks: int
    embedding_model: str = Field(...,alias="embeddingModel")
    description: str
    
class RagCitation(_Base):
  id: str
  title: str
  page: Optional[int]=None
  snippet: Optional[str]=None
  confidence: Optional[int]=None
  category: Optional[str]=None
  chunk_id: Optional[str]=Field(None,alias="chunkId")
  cosine_similarity: Optional[int]=Field(None,alias="cosineSimilarity")
  tokens_count: Optional[int]=Field(0,alias="tokensCount")
  embedding_model: str=Field(...,alias="embeddingModel")
  total_document_pages: Optional[int]=Field(None,alias="totalDocumentPages")

