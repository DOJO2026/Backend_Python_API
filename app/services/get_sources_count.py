
from app.core.config import settings
from azure.storage.blob import BlobServiceClient

def get_sources_count():
    try:
        service = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string)
        cont = service.get_container_client(settings.azure_storage_container)

        if cont:
            return len(list(cont.list_blobs()))
        return 0
    except Exception as e:
        print(f"Error getting sources count: {e}")
        return 0
