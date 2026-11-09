import os
import pyodbc
from app.core.config import settings


def get_db_connection():
    conn_str = (
        f"mssql+aioodbc://{settings.azure_sql_user}:{settings.azure_sql_password}@{settings.azure_sql_server}:1433/{settings.azure_sql_database}"
        f"?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
    )

    if not conn_str:
        raise ValueError(
            "No se encontró la cadena de conexión de Azure SQL en las variables de entorno.")
    return pyodbc.connect(conn_str)

