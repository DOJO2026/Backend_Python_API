from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    #azure openai/foundry
    azure_oai_endpoint:str
    azure_oai_key:str
    azure_oai_deployment:str
    azure_oai_embedding_deployment:str
    #azure opensearch
    azure_search_endpoint:str
    azure_search_key:str
    azure_search_index:str
    #azure sql
    azure_sql_server:str
    azure_sql_database:str
    azure_sql_user:str
    azure_sql_password:str
    #azure blob storage
    azure_storage_connection_string:str
    azure_storage_container:str
    #ubicacion de los archivos de palabras bloqueadas
    blocked_words_file: Path = BASE_DIR / "blocked_words.txt"
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    
    @property
    def oai_endpoint(self) -> str:
        return self.azure_oai_endpoint.rstrip("/")
    
    @property
    def search_endpoint(self)->str:
        return self.azure_search_endpoint.rstrip("/")
    
settings = Settings()