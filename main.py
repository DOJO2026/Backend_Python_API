import json
import os
import uuid
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
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
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Pregunta del usuario")
    session_id: Optional[str] = Field(None, description="ID de sesion. Si no se envia, se crea una nueva")


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    fuentes: List[str]
    herramientas_usadas: List[str]


class HistoryTurn(BaseModel):
    role: str
    content: str


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
                "o de los documentos internos."
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
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    history = SESSIONS.setdefault(session_id, [])

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": req.question})

        # Primera llamada: el modelo decide si necesita usar una herramienta
        response = client.chat.completions.create(
            model=CONFIG["oai_deployment"],
            temperature=0.3,
            max_tokens=1000,
            messages=messages,
            tools=TOOLS_DEFINITION,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        fuentes_usadas: List[str] = []
        herramientas_usadas: List[str] = []

        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                nombre_tool = tool_call.function.name
                argumentos = json.loads(tool_call.function.arguments)
                herramientas_usadas.append(nombre_tool)

                resultado_json = ejecutar_tool(nombre_tool, argumentos)
                resultado_dict = json.loads(resultado_json)

                if "fuentes" in resultado_dict:
                    fuentes_usadas.extend(resultado_dict["fuentes"])
                elif "fuente" in resultado_dict:
                    fuentes_usadas.append(resultado_dict["fuente"])

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": resultado_json,
                    }
                )

            # Segunda llamada: el modelo genera la respuesta final con los resultados
            final_response = client.chat.completions.create(
                model=CONFIG["oai_deployment"],
                temperature=0.5,
                max_tokens=1000,
                messages=messages,
            )
            answer = final_response.choices[0].message.content
        else:
            answer = response_message.content

        # Guardar el turno en el historial de la sesion
        history.append({"role": "user", "content": req.question})
        history.append({"role": "assistant", "content": answer})

        return ChatResponse(
            session_id=session_id,
            answer=answer,
            fuentes=list(set(fuentes_usadas)),
            herramientas_usadas=herramientas_usadas,
        )

    except requests.HTTPError as ex:
        raise HTTPException(status_code=502, detail=f"Error en una herramienta externa: {ex}")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@app.get("/sessions/{session_id}/history", response_model=List[HistoryTurn])
def get_history(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return SESSIONS[session_id]


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    del SESSIONS[session_id]
    return {"status": "eliminada", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
