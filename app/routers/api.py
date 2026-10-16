from fastapi import APIRouter,FastAPI, HTTPException
from typing import List

router=APIRouter()

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/guardrail/reload")
def guardrail_reload():
    """Recarga blocked_words.txt en caliente, sin reiniciar el servidor."""
    reload_guardrail()
    return {"status": "reloaded", "patterns_loaded": len(BLOCKED_PATTERNS)}

@app.post("/api/v1/chat/messages", response_model=ChatMessage, response_model_by_alias=True)
def chat(req: ChatRequest):
    session_id = req.conversation_id or str(uuid.uuid4())
    history = SESSIONS.setdefault(session_id, [])
    model = req.model_id or CONFIG["oai_deployment"]

    # --- Guardarraíl: corre ANTES de cualquier otra cosa, incluida una
    # eventual confirmacion pendiente ---
    if check_trip_wire(req.content):
        PENDING_CONFIRMATIONS.pop(session_id, None)
        return _respuesta(session_id, GUARDRAIL_MESSAGE, model, blocked=True)

    try:
        # --- ¿Esta sesion tiene una tool esperando confirmacion S/N? ---
        if session_id in PENDING_CONFIRMATIONS:
            confirmado = _parse_confirmation(req.content)
            pendiente = PENDING_CONFIRMATIONS[session_id]

            if confirmado is None:
                # No entendimos la respuesta: repetimos la pregunta, sin
                # ejecutar nada y sin perder lo que estaba pendiente.
                return _respuesta(
                    session_id,
                    f"No entendí tu respuesta. {pendiente['pregunta_confirmacion']}",
                    model,
                    herramientas=pendiente["herramientas_pendientes"],
                    confirmacion=True,
                )

            PENDING_CONFIRMATIONS.pop(session_id)

            if not confirmado:
                answer = "De acuerdo, no realicé esa búsqueda. ¿Hay algo más en lo que te pueda ayudar?"
                return _respuesta(session_id, answer, model)

            # Confirmado -> ahora si ejecutamos las tool_calls que quedaron pendientes
            messages = pendiente["messages"]
            fuentes_usadas: List[str] = []
            herramientas_usadas: List[str] = pendiente["herramientas_pendientes"]

            for tool_call in pendiente["tool_calls"]:
                argumentos = json.loads(tool_call.function.arguments)
                resultado_json = ejecutar_tool(tool_call.function.name, argumentos)
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

            final_response = client.chat.completions.create(
                model=model,
                temperature=req.temperature,
                max_tokens=1000,
                messages=messages,
            )
            answer = final_response.choices[0].message.content

            history.append({"role": "user", "content": pendiente["pregunta_original"]})
            history.append({"role": "assistant", "content": answer})

            return _respuesta(
                session_id, answer, model,
                fuentes=fuentes_usadas, herramientas=herramientas_usadas,
            )

        # --- Flujo normal: no hay nada pendiente para esta sesion ---
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": req.content})

        # Primera llamada: el modelo decide si necesita usar una herramienta
        response = client.chat.completions.create(
            model=model,
            temperature=req.temperature,
            max_tokens=1000,
            messages=messages,
            tools=TOOLS_DEFINITION,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        fuentes_usadas: List[str] = []
        herramientas_usadas: List[str] = []

        if response_message.tool_calls:
            nombres_tools = [tc.function.name for tc in response_message.tool_calls]

            # ¿Alguna de las tools que el modelo quiere usar requiere
            # confirmacion S/N antes de ejecutarse?
            if any(n in TOOLS_REQUIRING_CONFIRMATION for n in nombres_tools):
                messages.append(response_message)

                primer_call = response_message.tool_calls[0]
                primer_arg = json.loads(primer_call.function.arguments)
                consulta = primer_arg.get("query", req.content)
                pregunta_confirmacion = (
                    f'Para responder eso necesito consultar una fuente externa '
                    f'("{consulta}"). ¿Deseas que la consulte? Responde S/N.'
                )

                PENDING_CONFIRMATIONS[session_id] = {
                    "messages": messages,
                    "tool_calls": response_message.tool_calls,
                    "herramientas_pendientes": nombres_tools,
                    "pregunta_original": req.content,
                    "pregunta_confirmacion": pregunta_confirmacion,
                }

                return _respuesta(
                    session_id, pregunta_confirmacion, model,
                    herramientas=nombres_tools, confirmacion=True,
                )

            # Ninguna tool pedida requiere confirmacion -> se ejecutan de
            # inmediato, igual que antes.
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

            final_response = client.chat.completions.create(
                model=model,
                temperature=req.temperature,
                max_tokens=1000,
                messages=messages,
            )
            answer = final_response.choices[0].message.content
        else:
            answer = response_message.content

        # Guardar el turno en el historial de la sesion
        history.append({"role": "user", "content": req.content})
        history.append({"role": "assistant", "content": answer})

        return _respuesta(
            session_id, answer, model,
            fuentes=fuentes_usadas, herramientas=herramientas_usadas,
        )

    except requests.HTTPError as ex:
        raise HTTPException(status_code=502, detail=f"Error en una herramienta externa: {ex}")
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))



@router.get("/sessions/{session_id}/history", response_model=List[HistoryTurn])
def get_history(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    return SESSIONS[session_id]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Sesion no encontrada")
    del SESSIONS[session_id]
    PENDING_CONFIRMATIONS.pop(session_id, None)
    return {"status": "eliminada", "session_id": session_id}