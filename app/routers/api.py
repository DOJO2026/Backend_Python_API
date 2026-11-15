import json
import requests
import pyodbc
from fastapi import APIRouter, FastAPI, HTTPException
from typing import List
from app.core.config import settings
from app.db.get_conversations import get_list_conversations
from app.db.get_messages import get_list_messages_by_conversation
from app.db.save_chat_transaction import save_chat_transaction
from app.schemas.chat import ChatRequest, ChatMessage, RepositoryDocItem
from app.services.response import response
from app.services.llm import get_chat_with_tools, get_chat
from app.services import prompts
from app.services.human_review import PENDING_CONFIRMATIONS, TOOLS_REQUIRING_CONFIRMATION, parse_confirmation
from app.services.guardrail import reload_guardrail, BLOCKED_PATTERNS, check_trip_wire, GUARDRAIL_MESSAGE
from app.services.tools import TOOLS_DEFINITION, ejecutar_tool
from azure.storage.blob import BlobServiceClient

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.post("/guardrail/reload")
def guardrail_reload():
    """Recarga blocked_words.txt en caliente, sin reiniciar el servidor."""
    reload_guardrail()
    return {"status": "reloaded", "patterns_loaded": len(BLOCKED_PATTERNS)}

@router.get("/api/v1/fuentes")
def get_internal_sources():
    try:
        service = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string)
        cont = service.get_container_client(settings.azure_storage_container)

        if cont:
            list_docs: List[dict] = []
            for i, blob in enumerate(cont.list_blobs(include=["metadata"]), start=1):
                id = f"src-{i}"
                file_name = blob.name
                metadata = blob.metadata or {}
                category = metadata.get("category", "General")
                file_size = blob.size
                # Formatear el tamaño en una unidad legible (MB o KB)
                file_size_formatted = f"{file_size / (1024 * 1024):.2f} MB" if file_size > 1024 * \
                    1024 else f"{file_size / 1024:.2f} KB"
                date_updated = blob.last_modified.strftime(
                    "%Y-%m-%d") if blob.last_modified else "Desconocida"
                chunks = int(metadata.get("chunks", 0))
                embedding_model = metadata.get(
                    "embeddingModel", settings.azure_oai_embedding_deployment)
                description = metadata.get(
                    "description", "Documento extraído de Blob Storage.")

                list_docs.append(RepositoryDocItem(
                    id=id,
                    title=file_name,
                    category=category,
                    size=file_size_formatted,
                    updated_at=date_updated,
                    chunks=chunks,
                    embedding_model=embedding_model,
                    description=description
                ))
            return {
                "success": True,
                "data": {
                    "totalDocuments": len(list_docs),
                    "documents": list_docs
                }
            }

        else:
            return {"success": False, "data": "Contenedor no accesible"}

    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.post("/api/v1/chat/messages", response_model=ChatMessage, response_model_by_alias=True)
def chat(req: ChatRequest):
    model = req.model_id or settings.azure_oai_deployment
    req.model_id=model
    user_message = req
    conv_id = req.conversation_id

    try:  
       # --- Guardarraíl: corre ANTES de cualquier otra cosa ---
        if check_trip_wire(user_message.content):
            PENDING_CONFIRMATIONS.pop(conv_id, None)
            assistant_message =response(conv_id=conv_id, answer=GUARDRAIL_MESSAGE, model=model, blocked=True)
            save_chat_transaction(user_message, assistant_message)
            return assistant_message

        # --- ¿Esta sesión tiene una tool esperando confirmación S/N? ---
        if conv_id in PENDING_CONFIRMATIONS:
            confirmado = parse_confirmation(req.content)
            pendiente = PENDING_CONFIRMATIONS[conv_id]

            if confirmado is None:
                assistant_message= response(
                    conv_id,
                    f"No entendí tu respuesta. {pendiente['pregunta_confirmacion']}",
                    model,
                    confirmacion=True,
                    herramientas=pendiente["herramientas_pendientes"]
                    
                )
                save_chat_transaction(user_message, assistant_message)
                return assistant_message

            PENDING_CONFIRMATIONS.pop(conv_id)
            if not confirmado:
                answer = "De acuerdo, no realicé esa búsqueda. ¿Hay algo más en lo que te pueda ayudar?"
                assistant_message = response(conv_id, answer, model)
                save_chat_transaction(user_message, assistant_message)
                return assistant_message
            
            # Confirmado -> ahora sí ejecutamos las tool_calls pendientes
            messages = pendiente["messages"]
            fuentes_usadas: List[str] = []
            herramientas_usadas: List[str] = pendiente["herramientas_pendientes"]
            for tool_call in pendiente["tool_calls"]:
                argumentos = json.loads(tool_call.function.arguments)
                resultado_json = ejecutar_tool(
                    tool_call.function.name, argumentos)
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
                
            response_message, _ = get_chat(model, req.temperature, messages)
            answer = response_message.content
            assistant_message= response(
                conv_id, answer, model,
                fuentes=fuentes_usadas, herramientas=herramientas_usadas,
            )
            save_chat_transaction(user_message, assistant_message)
            return assistant_message

        # --- Flujo normal: no hay nada pendiente para esta sesión ---
        messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
        messages.append({"role": "user", "content": req.content})
        response_message, _ = get_chat_with_tools(model, req.temperature, messages, TOOLS_DEFINITION)
        fuentes_usadas: List[str] = []
        herramientas_usadas: List[str] = []

        if response_message.tool_calls:
            nombres_tools = [
                tc.function.name for tc in response_message.tool_calls]
            # ¿Alguna de las tools requiere confirmación S/N antes de ejecutarse?
            if any(n in TOOLS_REQUIRING_CONFIRMATION for n in nombres_tools):
                # IMPORTANTE: Usamos .model_dump() para guardarlo como diccionario plano
                messages.append(
                    response_message.model_dump(exclude_unset=True))

                primer_call = response_message.tool_calls[0]
                primer_arg = json.loads(primer_call.function.arguments)
                consulta = primer_arg.get("query", req.content)
                pregunta_confirmacion = (
                    f'Para responder eso necesito consultar una fuente externa '
                    f'("{consulta}"). ¿Deseas que la consulte? Responde S/N.'
                )

                assistant_message= response(
                                    conv_id=conv_id,
                                    answer=pregunta_confirmacion,
                                    model=model,
                                    herramientas=nombres_tools,
                                    confirmacion=True,
                                )
                conv_id=save_chat_transaction(user_message, assistant_message)
                PENDING_CONFIRMATIONS[conv_id] = {
                    "messages": messages,
                    "tool_calls": response_message.tool_calls,
                    "herramientas_pendientes": nombres_tools,
                    "pregunta_original": req.content,
                    "pregunta_confirmacion": pregunta_confirmacion,
                }
                
                return assistant_message

            # docs internos
            messages.append(response_message.model_dump(exclude_unset=True))
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

            final_response, _ = get_chat(model, req.temperature, messages)
            answer = final_response.content
        else:
            answer = response_message.content
        
        assistant_message = response(
            conv_id,answer, model,
            fuentes=fuentes_usadas, herramientas=herramientas_usadas,
        )
        save_chat_transaction(user_message, assistant_message)
        return assistant_message
    except pyodbc.Error as db_ex:
        raise HTTPException(
            status_code=503, detail=f'Error en base de datos: {str(db_ex)}')
    except requests.HTTPError as ex:
        raise HTTPException(
            status_code=502, detail=f"Error en una herramienta externa: {ex}")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/api/v1/chat/conversations")
def get_conversations(archived: bool | None = None,
                       category: str | None = None,
                       title: str | None = None):
    try:
        return get_list_conversations(archived, category, title)
    except pyodbc.Error as db_ex:
        raise HTTPException(
                status_code=503, detail=f'Error en base de datos: {str(db_ex)}')
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    
@router.get("/api/v1/chat/conversations/{id}/messages")
def get_messages_by_conversation(id: str):
    try:
        return get_list_messages_by_conversation(id)
    except pyodbc.Error as db_ex:
        raise HTTPException(
                    status_code=503, detail=f'Error en base de datos: {str(db_ex)}')
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))