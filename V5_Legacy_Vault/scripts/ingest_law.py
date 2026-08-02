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

def analyze_law_meta(filename):
    level = 5
    if '憲法' in filename: level = 1
    elif any(n in filename for n in ['法', '律', '條例', '通則']): level = 2
    elif any(n in filename for n in ['規程', '規則', '細則', '辦法', '綱要', '標準', '準則']): level = 3
    elif any(n in filename for n in ['要點', '規定', '須知', '注意事項', '原則', '基準']): level = 4
    
    category = '通用'
    if any(n in filename for n in ['民法', '民事', '商事', '財產', '合約', '債權']): category = '民事'
    elif any(n in filename for n in ['刑法', '刑事', '懲治', '犯罪', '偵查']): category = '刑事'
    elif any(n in filename for n in ['行政', '處分', '訴願', '公務']): category = '行政'
    elif any(n in filename for n in ['家事', '婚姻', '離婚', '監護', '遺產']): category = '家事'
    elif any(n in filename for n in ['憲法', '基本權']): category = '公法/憲法'
    return level, category

def split_text_with_overlap(text, chunk_size=800, overlap=100):
    '''使用重疊分塊法，防止法律條文在中間被切斷導致語義丟失'''
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap) # 每次前進，保留 overlap 個字的重複
    return chunks

def read_file_with_encoding(file_path):
    encodings = ['utf-8', 'big5', 'cp950', 'gbk']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except: continue
    return None

def run_law_ingest():
    print('\n<<< [LAW RAG INGEST] 啟動【高保真/透明化】導入... >>>')
    db_path = 'C:/LocalAI_Workstation/RAGFlow_Datasets'
    source_dir = r'E:\法律\台灣法規庫'
    
    client = chromadb.PersistentClient(path=db_path)
    try: client.delete_collection(name='legal_docs')
    except: pass
    collection = client.get_or_create_collection(name='legal_docs')

    extensions = ('.txt', '.md', '.csv', '.html', '.htm')
    files = [f for f in Path(source_dir).rglob('*') if f.suffix.lower() in extensions]

    print(f'📂 發現 {len(files)} 個文件，開始分析...')

    total_chunks = 0
    for file_path in files:
        content = read_file_with_encoding(file_path)
        if not content: 
            print(f'⚠️ 無法讀取 (編碼錯誤): {file_path.name}')
            continue
        
        # 【關鍵更新】印出實際讀到的字數，方便檢查是否被截斷
        total_chars = len(content)
        level, category = analyze_law_meta(file_path.name)
        chunks = split_text_with_overlap(content)
        
        print(f'📦 {file_path.name} | 字數: {total_chars:6d} | 分塊: {len(chunks):3d} | 位階: {level} | 類別: {category}')

        for idx, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)
            if embedding:
                collection.add(
                    ids=[f"{str(file_path)}_{idx}"],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{'source': str(file_path), 'level': level, 'category': category, 'chunk': idx}]
                )
                total_chunks += 1

    print(f'\n✅ [SUCCESS] 導入完成！總共生成 {total_chunks} 個重疊分塊。')

if __name__ == '__main__':
    run_law_ingest()