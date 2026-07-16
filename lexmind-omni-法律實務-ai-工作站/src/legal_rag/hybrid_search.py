import os
import sys
import yaml
import re
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Import local modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)
from build_dense_vectors import DenseVectorBuilder
from build_sparse_vectors import SparseVectorBuilder
from rerank import LegalReranker

# RRF Constants
RRF_K = 60

class LegalHybridSearchSystem:
    def __init__(self, config_path=None):
        if not config_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.yaml")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        local_path = self.config['qdrant'].get('local_path')
        host = self.config['qdrant'].get('host', 'localhost')
        port = self.config['qdrant'].get('port', 6333)
        
        if local_path:
            self.client = QdrantClient(path=local_path)
        else:
            self.client = QdrantClient(host=host, port=port)
            
        # Init builders
        self.dense_builder = DenseVectorBuilder(config_path)
        self.sparse_builder = SparseVectorBuilder(config_path)
        self.reranker = LegalReranker(config_path)

    def classify_query(self, query: str) -> dict:
        """
        Step 1: Query Classification
        Analyze query for keywords to route to the correct collection and extract metadata filters.
        """
        classification = {
            "target_collection": self.config['collections']['laws'],
            "filters": {},
            "keywords": []
        }
        
        query_lower = query.lower()
        
        # Route logic
        if any(w in query_lower for w in ["判決", "判例", "最高法院", "裁定", "會議決議", "字第", "刑事訴訟", "民事訴訟"]):
            classification["target_collection"] = self.config['collections']['cases']
        elif any(w in query_lower for w in ["課程", "講義", "教授", "授課", "筆記", "逐字稿", "教材"]):
            classification["target_collection"] = self.config['collections']['course_notes']
        elif any(w in query_lower for w in ["題目", "考題", "國考", "選擇題", "申論題", "答案"]):
            classification["target_collection"] = self.config['collections']['exam_bank']
        else:
            classification["target_collection"] = self.config['collections']['laws']
            
        # Law filters extraction
        law_matches = re_match_law(query)
        if law_matches:
            # Clean up key match
            classification["filters"]["law_name"] = law_matches[0][0]
            classification["filters"]["article_no"] = law_matches[0][1]
                
        print(f"[Query Classifier] Query: '{query}' -> Target Collection: '{classification['target_collection']}'")
        if classification["filters"]:
            print(f"[Query Classifier] Extracted Filters: {classification['filters']}")
            
        return classification

    def build_filters(self, filters_dict: dict) -> models.Filter:
        """
        Step 2: Build Qdrant Metadata Filter
        """
        must_conditions = []
        for key, val in filters_dict.items():
            must_conditions.append(
                models.FieldCondition(
                    key=key,
                    match=models.MatchValue(value=val)
                )
            )
            
        if must_conditions:
            return models.Filter(must=must_conditions)
        return None

    def sparse_search(self, query: str, collection_name: str, filters: models.Filter, limit: int = 10) -> list:
        """
        Step 3: Sparse Retrieval (BM25)
        """
        print(f"[Sparse Search] Executing BM25/Sparse query for '{query}' on collection '{collection_name}'...")
        
        # Compute sparse vector
        sparse_vec_data = self.sparse_builder.get_sparse_vector(query)
        sparse_vector = models.SparseVector(
            indices=sparse_vec_data["indices"],
            values=sparse_vec_data["values"]
        )
        
        results_obj = self.client.query_points(
            collection_name=collection_name,
            query=models.SparseVector(
                indices=sparse_vec_data["indices"],
                values=sparse_vec_data["values"]
            ),
            using=self.config['vectors']['sparse']['name'],
            query_filter=filters,
            limit=limit
        )
        results = results_obj.points
        
        hits = []
        for r in results:
            hits.append({
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload
            })
        return hits

    def dense_search(self, query: str, collection_name: str, filters: models.Filter, limit: int = 10) -> list:
        """
        Step 4: Dense Retrieval (Gemini Embeddings)
        """
        print(f"[Dense Search] Executing Embedding query for '{query}' on collection '{collection_name}'...")
        
        # Compute dense vector
        dense_vector = self.dense_builder.get_embedding(query)
        
        results_obj = self.client.query_points(
            collection_name=collection_name,
            query=dense_vector,
            query_filter=filters,
            limit=limit
        )
        results = results_obj.points
        
        hits = []
        for r in results:
            hits.append({
                "id": str(r.id),
                "score": r.score,
                "payload": r.payload
            })
        return hits

    def rrf_fusion(self, dense_hits: list, sparse_hits: list, limit: int = 5) -> list:
        """
        Step 5: Reciprocal Rank Fusion (RRF)
        """
        print(f"[RRF Fusion] Merging Dense and Sparse hits using K={RRF_K}...")
        scores = {}
        payloads = {}
        
        # Process Dense ranks
        for rank, hit in enumerate(dense_hits, start=1):
            hit_id = hit["id"]
            scores[hit_id] = scores.get(hit_id, 0.0) + (1.0 / (RRF_K + rank))
            payloads[hit_id] = hit["payload"]
            
        # Process Sparse ranks
        for rank, hit in enumerate(sparse_hits, start=1):
            hit_id = hit["id"]
            scores[hit_id] = scores.get(hit_id, 0.0) + (1.0 / (RRF_K + rank))
            payloads[hit_id] = hit["payload"]
            
        # Sort by fusion score
        fused = []
        for hit_id, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            fused.append({
                "id": hit_id,
                "rrf_score": rrf_score,
                "payload": payloads[hit_id]
            })
            
        return fused[:limit]

    def execute_hybrid_query(self, query: str) -> list:
        """
        Run the complete retrieval pipeline
        """
        print(f"\n===== START HYBRID RETRIEVAL PIPELINE =====")
        # 1. Query classification
        classification = self.classify_query(query)
        col_name = classification["target_collection"]
        
        # 2. Metadata filtering
        filters = self.build_filters(classification["filters"])
        
        # 3. Sparse search
        sparse_hits = self.sparse_search(query, col_name, filters)
        
        # 4. Dense search
        dense_hits = self.dense_search(query, col_name, filters)
        
        # 5. RRF Fusion
        fused_hits = self.rrf_fusion(dense_hits, sparse_hits)
        
        # 6. Rerank
        final_results = self.reranker.rerank_hits(query, fused_hits)
        
        print(f"===== HYBRID RETRIEVAL COMPLETED (Top {len(final_results)} hits) =====")
        for idx, hit in enumerate(final_results, start=1):
            print(f" {idx}. [{hit['payload']['title']}] RRF_Score={hit['rrf_score']:.4f} | Rerank_Score={hit.get('rerank_score', 0):.4f}")
            print(f"    文獻內文: {hit['payload']['text']}")
            
        return final_results

def re_match_law(query: str):
    # Match pattern: e.g. 民法第197條, 行政程序法第131條, 民法第126條
    pattern = r"((?:民法|刑法|行政程序法|勞基法)第[一二三四五六七八九十百零\d]+條)"
    matches = re.findall(pattern, query)
    res = []
    for m in matches:
        split_match = re.split(r"第", m)
        if len(split_match) == 2:
            res.append((split_match[0], "第" + split_match[1]))
    return res

def main():
    search_system = LegalHybridSearchSystem()
    
    # 5 Legal Test Cases
    test_cases = [
        "侵權行為損害賠償請求權之消滅時效，民法第197條短期與長期時效如何計算？",
        "人民對國家之公法上請求權，消滅時效是五年還是十年？行政程序法第131條如何規定？",
        "借名登記關係終止後，委託人請求返還登記物之權利基礎為何？是否有消滅時效限制？",
        "無權占有他人土地，請求相當於租金之不當得利，其消滅時效是適用民法第126條之五年短期時效嗎？",
        "雇主違反勞動基準法不依期給付工資，工資債權之消滅時效與處罰規定為何？"
    ]
    
    for idx, case in enumerate(test_cases, start=1):
        print(f"\n\n==========================================")
        print(f"【真實測試案例 {idx}】: {case}")
        print(f"==========================================")
        search_system.execute_hybrid_query(case)

if __name__ == "__main__":
    main()
