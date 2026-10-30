from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings


def build_engine() -> AsyncEngine:
    s = get_settings()
    pwd = s.sql_password.replace("}", "}}")  # escape de llaves en cadenas ODBC
    odbc = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{s.sql_server},1433;Database={s.sql_database};"
        f"Uid={s.sql_user};Pwd={{{pwd}}};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )
    url = URL.create("mssql+aioodbc", query={"odbc_connect": odbc})
    # Connection Timeout=60 y pool_pre_ping cubren el arranque en frío de la
    # oferta serverless (la BD se pausa sola y la primera conexión tarda).
    return create_async_engine(
        url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800
    )
