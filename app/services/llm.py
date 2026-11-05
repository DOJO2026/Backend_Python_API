from typing import List
from openai import AzureOpenAI
from app.core.config import settings

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
        model=model, 
        temperature=temperature, 
        max_tokens=1000, 
        messages=messages
    )
    return response.choices[0].message, response.usage


def get_chat_with_tools(model: str, temperature: float, messages: List[dict], tools: List[dict]):
    """Pide la respuesta a gpt-4.1-mini. Devuelve (texto, uso de tokens)."""
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=1000,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    return response.choices[0].message, response.usage