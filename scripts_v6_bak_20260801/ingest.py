import os
import requests
from pathlib import Path
import chromadb

def get_embedding(text, model='nomic-embed-text:latest'):
    url = 'http://localhost:11434/api/embeddings'
    payload = {'model': model, 'prompt': text}
    try:
        response = requests.post(url, json=payload, timeout=60)
        return response.json()['embedding']
    except Exception as e:
        print(f'❌ Embedding 失敗: {e}')
        return None

def run_ingest():
    print('\n<<< [RAG INGEST] 開始導入知識庫 >>>')
    db_path = 'C:/LocalAI_Workstation/RAGFlow_Datasets'
    source_dir = 'C:/LocalAI_Workstation/Data/SourceFiles/test_source'
    
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name='legal_docs')

    # 掃描所有 ps1, py, txt 文件
    files = list(Path(source_dir).rglob('*.[ps1|py|txt]'))
    if not files:
        # 如果沒找到，嘗試直接掃描所有文件
        files = list(Path(source_dir).glob('*'))

    print(f'📂 發現 {len(files)} 個目標文件，開始向量化...')

    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                if not content.strip(): continue
                
                print(f'📦 正在處理: {file_path.name}...')
                embedding = get_embedding(content)
                
                if embedding:
                    collection.add(
                        ids=[str(file_path)],
                        embeddings=[embedding],
                        documents=[content],
                        metadatas=[{'source': str(file_path)}]
                    )
        except Exception as e:
            print(f'⚠️ 處理 {file_path.name} 時出錯: {e}')

    print('\n✅ [SUCCESS] 所有數據已成功存入 ChromaDB!')

if __name__ == '__main__':
    run_ingest()