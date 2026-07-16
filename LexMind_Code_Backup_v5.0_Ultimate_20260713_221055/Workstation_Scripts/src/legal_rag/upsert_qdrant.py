import os
import sys
import yaml
from qdrant_client import QdrantClient
from qdrant_client.http import models

def setup_qdrant_collections():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        
    local_path = config['qdrant'].get('local_path')
    host = config['qdrant'].get('host', 'localhost')
    port = config['qdrant'].get('port', 6333)
    
    # Initialize client: check if local path is specified (persistent local client)
    print(f"Connecting to Qdrant client...")
    if local_path:
        os.makedirs(local_path, exist_ok=True)
        print(f"Using persistent local storage at: {local_path}")
        client = QdrantClient(path=local_path)
    else:
        print(f"Connecting to remote Qdrant server at {host}:{port}")
        client = QdrantClient(host=host, port=port)
        
    # Collections list
    collections_to_create = [
        config['collections']['laws'],
        config['collections']['cases'],
        config['collections']['course_notes'],
        config['collections']['exam_bank']
    ]
    
    dense_size = config['vectors']['dense']['size']
    dense_distance = config['vectors']['dense']['distance']
    sparse_name = config['vectors']['sparse']['name']
    
    # Map distance name to Qdrant enum
    distance_map = {
        "Cosine": models.Distance.COSINE,
        "Euclid": models.Distance.EUCLID,
        "Dot": models.Distance.DOT
    }
    qdrant_distance = distance_map.get(dense_distance, models.Distance.COSINE)
    
    for collection in collections_to_create:
        print(f"\nCreating collection: '{collection}'...")
        
        # Recreate collection
        client.recreate_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=dense_size,
                distance=qdrant_distance
            ),
            sparse_vectors_config={
                sparse_name: models.SparseVectorParams(
                    index=models.SparseIndexParams(
                        on_disk=True
                    )
                )
            }
        )
        print(f"Collection '{collection}' created successfully.")
        
        # Set up Payload Field Indexes for fast metadata filtering
        fields_to_index = [
            ("doc_id", models.PayloadSchemaType.KEYWORD),
            ("source_type", models.PayloadSchemaType.KEYWORD),
            ("law_name", models.PayloadSchemaType.KEYWORD),
            ("article_no", models.PayloadSchemaType.KEYWORD),
            ("court_level", models.PayloadSchemaType.KEYWORD),
            ("review_status", models.PayloadSchemaType.KEYWORD)
        ]
        
        for field_name, field_type in fields_to_index:
            client.create_payload_index(
                collection_name=collection,
                field_name=field_name,
                field_schema=field_type
            )
            print(f"Created payload index on '{field_name}' in collection '{collection}'")

    print("\nAll Qdrant collections initialized and indexed successfully!")

if __name__ == "__main__":
    setup_qdrant_collections()
