from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    azure_oai_deployment:str
    azure_oai_endpoint:str
    azure_oai_key:str
    azure_oai_embedding_deployment:str="text-embedding-ada-002"
    azure_search_endpoint:str
    azure_search_index:str
    azure_search_key:str
    
    blocked_words_file: Path = BASE_DIR / "blocked_words.txt"
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")
    
    @property
    def oai_endpoint(self) -> str:
        return self.azure_oai_endpoint.rstrip("/")
    
settings = Settings()
    
