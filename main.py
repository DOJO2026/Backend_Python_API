import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI
from datetime import datetime, timezone
from app.schemas.chat import ChatMessage, ChatRequest, MessageSource,HistoryTurn

app = FastAPI(title="Agent Chat API (RAG + Wikipedia)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



# def _respuesta(
#     conv_id: str,
#     answer: str,
#     model: str,
#     fuentes: Optional[List[str]] = None,
#     herramientas: Optional[List[str]] = None,
#     blocked: bool = False,
#     confirmacion: bool = False,
# ) -> ChatMessage:
#     fuentes_unicas = list(dict.fromkeys(fuentes or []))  # sin duplicados, conserva orden
#     return ChatMessage(
#         id=str(uuid.uuid4()),
#         conversation_id=conv_id,
#         role="assistant",
#         content=answer,
#         timestamp=datetime.now(timezone.utc).isoformat(),
#         sources=[
#             MessageSource(title=f, url=f if f.startswith("http") else None)
#             for f in fuentes_unicas
#         ] or None,
#         status="complete",
#         model_used=model,
#         interactive_type="tool_confirmation" if confirmacion else None,
#         blocked=blocked,
#         tools_used=herramientas or None,
#     )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)