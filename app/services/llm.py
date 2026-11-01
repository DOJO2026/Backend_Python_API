from typing import List
from openai import AzureOpenAI
from app.core.config import settings
from app.services.tools import TOOLS_DEFINITION

client = AzureOpenAI(
    azure_endpoint=settings.oai_endpoint,
    api_key=settings.azure_oai_key,
    api_version="2024-05-01-preview",
)

def get_embedding(text: str) -> List[float]:
    """Convierte texto en 'coordenadas' con ada-002."""
    response = client.embeddings.create(
        model=settings.azure_oai_embedding_deployment, input=text
    )
    return response.data[0].embedding


def get_chat(model: str, temperature: float, messages: List[dict]):
    """Pide la respuesta a gpt-4.1-mini. Devuelve (texto, uso de tokens)."""
    response = client.chat.completions.create(
        model=model, temperature=temperature, max_tokens=1000, messages=messages
    )
    return response.choices[0].message.content, response.usage


def get_chat_with_tools(model: str, temperature: float, messages: List[dict]):
    """Pide la respuesta a gpt-4.1-mini. Devuelve (texto, uso de tokens)."""
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=1000,
        messages=messages,
        tools=TOOLS_DEFINITION,
        tool_choice="auto",
    )
    return response.choices[0].message.content, response.usage