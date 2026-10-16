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
from app.services import normalize
load_dotenv()

CONFIG = {
    "oai_endpoint": os.getenv("AZURE_OAI_ENDPOINT", "").rstrip("/"),
    "oai_key": os.getenv("AZURE_OAI_KEY"),
    "oai_deployment": os.getenv("AZURE_OAI_DEPLOYMENT"),
    "embedding_deployment": os.getenv("AZURE_OAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"),
    "search_endpoint": os.getenv("AZURE_SEARCH_ENDPOINT"),
    "search_key": os.getenv("AZURE_SEARCH_KEY"),
    "search_index": os.getenv("AZURE_SEARCH_INDEX"),
}

client = AzureOpenAI(
    azure_endpoint=CONFIG["oai_endpoint"],
    api_key=CONFIG["oai_key"],
    api_version="2024-05-01-preview",
)

SYSTEM_PROMPT = (
    "Eres un asistente virtual util y preciso.\n\n"
    "Tienes acceso a dos herramientas:\n"
    "1. buscar_documentos_internos: para preguntas relacionadas con la base de conocimiento "
    "interna de la empresa (documentos propios, ej. temas tecnicos como Quarkus).\n"
    "2. buscar_conocimiento_general: para preguntas de cultura general que NO estan en los "
    "documentos internos (ej. definiciones basicas, historia, ciencia).\n\n"
    "REGLAS:\n"
    "- Decide cual herramienta usar segun el tema de la pregunta. Si no estas seguro, "
    "intenta primero con buscar_documentos_internos.\n"
    "- Si el usuario solo saluda o hace conversacion casual, responde de forma natural "
    "sin usar ninguna herramienta.\n"
    "- Para buscar_documentos_internos: basate UNICAMENTE en la informacion devuelta por "
    "esta herramienta. NUNCA uses tu conocimiento propio como respaldo para temas de la "
    "empresa (precios, politicas, datos especificos de los documentos), incluso si crees "
    "saber la respuesta. Si esta herramienta no encuentra informacion relevante, dilo "
    "claramente y no inventes datos del negocio.\n"
    "- Para buscar_conocimiento_general: si la herramienta falla o no encuentra nada, SI "
    "puedes responder con tu propio conocimiento general, siempre que sea informacion "
    "estable y de bajo riesgo (definiciones, historia, ciencia basica). Indica brevemente "
    "que la respuesta viene de tu conocimiento general y no de una fuente verificada en "
    "vivo.\n"
    "- Responde siempre en español, de forma clara y concisa.\n"
    "- No menciones explicitamente que usaste una 'herramienta' o 'funcion'; responde con "
    "naturalidad."
)









# ---------------------------------------------------------------------------
# Confirmacion humana (S/N) antes de ejecutar ciertas tools.
# Util para tools que consultan fuentes externas (ej. Wikipedia) y donde
# quieres que el usuario apruebe explicitamente la consulta.
# ---------------------------------------------------------------------------

# Nombres de las tools (ver TOOLS_DEFINITION) que requieren confirmacion S/N
# antes de ejecutarse. Agrega "buscar_documentos_internos" aqui tambien si
# quieres que la RAG interna pida confirmacion.
TOOLS_REQUIRING_CONFIRMATION = {"buscar_conocimiento_general"}




# session_id -> {messages, tool_calls, herramientas_pendientes,
#                pregunta_original, pregunta_confirmacion}
# Tambien en memoria; igual que SESSIONS, no sobrevive un reinicio ni escala
# a multiples instancias sin moverlo a Redis/DB.
PENDING_CONFIRMATIONS: Dict[str, dict] = {}


# Historial en memoria por sesion. Para produccion, reemplazar por Redis/DB.
SESSIONS: Dict[str, List[dict]] = {}

app = FastAPI(title="Agent Chat API (RAG + Wikipedia)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modelos Pydantic
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# HERRAMIENTA 1: Busqueda en la base de conocimiento interna (RAG)
# ---------------------------------------------------------------------------
def get_embedding(text: str) -> List[float]:
    response = client.embeddings.create(model=CONFIG["embedding_deployment"], input=text)
    return response.data[0].embedding


def buscar_documentos_internos(query: str, top: int = 5) -> dict:
    query_vector = get_embedding(query)

    url = f"{CONFIG['search_endpoint'].rstrip('/')}/indexes/{CONFIG['search_index']}/docs/search?api-version=2023-11-01"
    headers = {"Content-Type": "application/json", "api-key": CONFIG["search_key"]}
    body = {
        "search": query,
        "vectorQueries": [
            {"kind": "vector", "vector": query_vector, "fields": "text_vector", "k": top}
        ],
        "select": "chunk,title,chunk_id",
        "top": top,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("value", [])

    if not results:
        return {"encontrado": False, "contenido": "No se encontro informacion relevante en los documentos internos."}

    parts = []
    titles = set()
    for i, r in enumerate(results, start=1):
        title = r.get("title", "Sin titulo")
        chunk = r.get("chunk", "")
        parts.append(f"[Fuente {i} - {title}]\n{chunk}")
        titles.add(title)

    return {"encontrado": True, "contenido": "\n\n".join(parts), "fuentes": list(titles)}


# ---------------------------------------------------------------------------
# HERRAMIENTA 2: Conocimiento general (Wikipedia)
# ---------------------------------------------------------------------------
def buscar_conocimiento_general(query: str) -> dict:
    headers = {"User-Agent": "ProyectoDojoRAG/1.0 (proyecto de aprendizaje)"}
    try:
        search_url = "https://es.wikipedia.org/w/api.php"
        search_params = {
            "action": "opensearch",
            "search": query,
            "limit": 1,
            "namespace": 0,
            "format": "json",
        }
        r1 = requests.get(search_url, params=search_params, headers=headers, timeout=10)
        r1.raise_for_status()
        data = r1.json()
        titles = data[1]

        if not titles:
            return {"encontrado": False, "contenido": "No se encontro informacion en Wikipedia sobre este tema."}

        title = titles[0]

        summary_url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
        r2 = requests.get(summary_url, headers=headers, timeout=10)
        r2.raise_for_status()
        summary_data = r2.json()

        extract = summary_data.get("extract", "")
        page_url = summary_data.get("content_urls", {}).get("desktop", {}).get("page", "")

        return {
            "encontrado": True,
            "contenido": extract,
            "fuente": page_url or f"https://es.wikipedia.org/wiki/{title}",
        }

    except Exception as ex:
        return {"encontrado": False, "contenido": f"Error al consultar Wikipedia: {ex}"}


# ---------------------------------------------------------------------------
# Definicion de tools para function calling
# ---------------------------------------------------------------------------
TOOLS_DEFINITION = [
    {
        "type": "function",
        "function": {
            "name": "buscar_documentos_internos",
            "description": (
                "Busca informacion en la base de conocimiento interna de la empresa "
                "(documentos propios, PDFs cargados, ej. articulos tecnicos sobre Quarkus). "
                "Usa esta funcion cuando la pregunta sea sobre temas especificos de la empresa "
                "o de los documentos internos ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de busqueda, reformulada de forma clara y autocontenida.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_conocimiento_general",
            "description": (
                "Busca informacion general en Wikipedia. Usa esta funcion para preguntas de "
                "cultura general, definiciones basicas, o cualquier tema que NO este relacionado "
                "con los documentos internos de la empresa (ej. '¿que es una casa?', "
                "'¿quien fue Einstein?', '¿que es la fotosintesis?')."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "El tema o pregunta a buscar en Wikipedia.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def ejecutar_tool(nombre_tool: str, argumentos: dict) -> str:
    """Ejecuta la funcion Python correspondiente segun lo que decida el modelo."""
    if nombre_tool == "buscar_documentos_internos":
        resultado = buscar_documentos_internos(argumentos["query"])
    elif nombre_tool == "buscar_conocimiento_general":
        resultado = buscar_conocimiento_general(argumentos["query"])
    else:
        resultado = {"error": f"Tool desconocida: {nombre_tool}"}

    return json.dumps(resultado, ensure_ascii=False)



# ---------------------------------------------------------------------------
# CAMBIO 2: helper nuevo (ponlo justo antes del endpoint /chat).
# Reemplaza a ChatResponse(...): arma un ChatMessage a partir de los mismos datos.
# ---------------------------------------------------------------------------
def _respuesta(
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


# ---------------------------------------------------------------------------
# CAMBIO 3: el endpoint. Misma estructura que el original; solo cambian:
#   - ruta y response_model
#   - req.question -> req.content, req.session_id -> req.conversation_id
#   - modelo y temperatura salen del request
#   - ChatResponse(...) -> _respuesta(...)
# ---------------------------------------------------------------------------




if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)