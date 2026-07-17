import os
import sys
import yaml
from dotenv import load_dotenv
from google import genai

class LegalReranker:
    def __init__(self, config_path=None):
        if not config_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.yaml")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        # Load dotenv from potential paths
        potential_dotenv_paths = [
            os.path.join(os.path.dirname(config_path), ".env"),
            os.path.join(os.path.dirname(config_path), "..", ".env"),
            os.path.join(os.path.dirname(config_path), "..", "..", ".env"),
            os.path.join(os.getcwd(), ".env"),
            "c:\\Users\\temp\\antigravity\\LexMind-Omni-法律實務-AI-工作站\\.env"
        ]
        for path in potential_dotenv_paths:
            if os.path.exists(path):
                load_dotenv(path)
                
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            keys_str = os.environ.get("GEMINI_API_KEYS")
            if keys_str:
                keys = [k.strip() for k in keys_str.split(",") if k.strip()]
                if keys:
                    api_key = keys[0]
                    
        self.client = None
        if api_key:
            self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"

    def compute_local_overlap_score(self, query: str, text: str) -> float:
        """
        Fallback keyword overlap similarity score (normalized)
        """
        q_chars = set(query)
        t_chars = set(text)
        if not q_chars:
            return 0.0
        intersection = q_chars.intersection(t_chars)
        return len(intersection) / len(q_chars)

    def rerank_hits(self, query: str, hits: list, limit: int = 3) -> list:
        """
        Rerank a list of Qdrant search hits
        """
        if not hits:
            return []
            
        print(f"[Reranker] Reranking {len(hits)} candidates for query: '{query}'...")
        
        reranked_hits = []
        for hit in hits:
            text = hit["payload"].get("text", "")
            title = hit["payload"].get("title", "")
            
            # Use Gemini for semantic relevance scoring if client is available
            score = 0.0
            if self.client:
                prompt = f"""請評估以下法律文獻片段與查詢問題的相關性，並給出一個 0.0 到 10.0 之間的分數（分數越高表示越相關，能直接解答或提供關鍵法源者給予 8.0 以上的高分）。
                
查詢問題：{query}
法律文獻：【{title}】{text}

請僅輸出一個浮點數，如「8.5」，不要有任何其他解釋。
"""
                try:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt
                    )
                    # Parse float score from output
                    raw_score = response.text.strip()
                    score = float(raw_score)
                except Exception as e:
                    # Fallback to local keyword overlap
                    score = self.compute_local_overlap_score(query, text) * 10.0
            else:
                score = self.compute_local_overlap_score(query, text) * 10.0
                
            hit_copy = dict(hit)
            hit_copy["rerank_score"] = score
            reranked_hits.append(hit_copy)
            
        # Sort by rerank score descending
        reranked_hits.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked_hits[:limit]
