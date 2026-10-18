from openai import AzureOpenAI
from app.core.config import settings

client = AzureOpenAI(
    azure_endpoint=settings.oai_endpoint,
    api_key=settings.azure_oai_key,
    api_version="2024-05-01-preview",
)
