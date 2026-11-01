
from typing import Optional, List
import uuid
from datetime import datetime, timezone
from app.schemas.chat import ChatMessage, MessageSource


def respuesta(
    conv_id: str,
    answer: str,
    model: str,
    fuentes: Optional[List[str]] = None,
    herramientas: Optional[List[str]] = None,
    blocked: bool = False,
    confirmacion: bool = False,
) -> ChatMessage:
    fuentes_unicas = list(dict.fromkeys(fuentes or []))  # sin duplicados, conserva orden
    return ChatMessage(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        role="assistant",
        content=answer,
        timestamp=datetime.now(timezone.utc).isoformat(),
        sources=[
            MessageSource(title=f, url=f if f.startswith("http") else None)
            for f in fuentes_unicas
        ] or None,
        status="complete",
        model_used=model,
        interactive_type="tool_confirmation" if confirmacion else None,
        blocked=blocked,
        tools_used=herramientas or None,
    )
