# from pathlib import Path
# from pydantic_settings import BaseSettings,SettingsConfigDict

# BASE_DIR = Path(__file__).resolve().parent.parent.parent

# class Settings(BaseSettings):
#     azure_oai_deployment:str
#     azure_oai_endpoint:str
#     azure_oai_key:str
#     azure_oai_embedding_deployment:str="text-embedding-ada-002"
#     azure_search_endpoint:str
#     azure_search_index:str
#     azure_search_key:str
    
#     blocked_words_file: Path = BASE_DIR / "blocked_words.txt"
#     model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    
#     @property
#     def oai_endpoint(self) -> str:
#         return self.azure_oai_endpoint.rstrip("/")
    
# settings = Settings()
    
##############################################################################

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Azure SQL
    sql_server: str
    sql_database: str
    sql_user: str
    sql_password: str

    # Foundry / Azure OpenAI
    oai_endpoint: str=""
    azure_oai_key: str=""
    oai_api_version: str = "2024-10-21"
    embedding_deployment: str=""
    models: dict[str, str] = {"gpt-4o": "gpt-4o"}  # modelId del contrato -> deployment
    default_model: str = "gpt-4o"

    # Azure AI Search
    search_endpoint: str=""
    search_key: str=""
    search_index: str=""
    search_api_version: str = "2024-07-01"
    search_semantic_config: str = ""
    rag_min_reranker_score: float = 1.5  # escala 0-4; calibrar con tus consultas

    # Auth
    auth_mode: str = "demo"  # demo | entra
    entra_tenant_id: str = ""
    entra_audience: str = ""

    # Límites
    token_quota_monthly: int = 100_000
    history_max_messages: int = 30
    confirmation_ttl_minutes: int = 10
    max_tool_rounds: int = 3
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
