# import asyncio
# from sqlalchemy import text
# from app.db.session import build_engine

# async def main():
#     engine = build_engine()
#     async with engine.connect() as conn:
#         for t in ("CONVERSATION", "MESSAGE", "TOKEN_USAGE"):
#             n = (await conn.execute(text(f"SELECT COUNT(*) FROM dbo.{t}"))).scalar()
#             print(t, "->", n, "filas")
#     await engine.dispose()

# asyncio.run(main())


import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Tus credenciales directas solo para esta prueba rápida
SQL_SERVER = "servidorsql.database.windows.net"
SQL_DATABASE = "mibbdd"
SQL_USER = "azureuser"
SQL_PASSWORD = "Australia.3000"

# Construir la URL de conexión asíncrona para SQL Server con aioodbc
DATABASE_URL = (
    f"mssql+aioodbc://{SQL_USER}:{SQL_PASSWORD}@{SQL_SERVER}:1433/{SQL_DATABASE}"
    f"?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
)

async def main():
    # Crear el motor directamente sin tocar Pydantic
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.connect() as conn:
        for t in ("CONVERSATION", "MESSAGE", "TOKEN_USAGE"):
            n = (await conn.execute(text(f"SELECT COUNT(*) FROM dbo.{t}"))).scalar()
            print(f"Tabla {t} -> {n} filas")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())