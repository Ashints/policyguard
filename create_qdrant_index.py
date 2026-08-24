from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType


COLLECTION_NAME = "policy_docs"


qdrant = QdrantClient(
    host="localhost",
    port=6333,
)

existing_indexes = qdrant.get_collection(
    collection_name=COLLECTION_NAME,
).payload_schema

if "article" not in existing_indexes:
    qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="article",
        field_schema=PayloadSchemaType.KEYWORD,
    )

    print(
        "Payload index created for the 'article' field."
    )
else:
    print(
        "Payload index already exists."
    )