import os
import re
import json
import zlib
import math
import yaml

class SparseVectorBuilder:
    def __init__(self, config_path=None):
        if not config_path:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, "config.yaml")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
            
        local_path = self.config['qdrant'].get('local_path', "A:\\vector_db\\qdrant")
        os.makedirs(local_path, exist_ok=True)
        self.df_path = os.path.join(local_path, "bm25_df.json")
        
        # Load or initialize DF dictionary
        self.load_df()
        
        # BM25 Hyperparameters
        self.k1 = 1.5
        self.b = 0.75

    def load_df(self):
        if os.path.exists(self.df_path):
            try:
                with open(self.df_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.df = data.get("df", {})
                    self.N = data.get("N", 0)
                    self.avg_doc_len = data.get("avg_doc_len", 100.0)
            except:
                self.df = {}
                self.N = 0
                self.avg_doc_len = 100.0
        else:
            self.df = {}
            self.N = 0
            self.avg_doc_len = 100.0

    def save_df(self):
        with open(self.df_path, 'w', encoding='utf-8') as f:
            json.dump({
                "df": self.df,
                "N": self.N,
                "avg_doc_len": self.avg_doc_len
            }, f, ensure_ascii=False, indent=2)

    def tokenize(self, text: str) -> list:
        """
        Character-level and Bigram-level tokenizer for Traditional Chinese.
        Extremely robust and does not require external C-libraries.
        """
        if not text:
            return []
        
        # Clean text, keep only alphanumeric and Chinese characters
        clean_text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
        
        tokens = []
        # Unigrams
        for char in clean_text:
            tokens.append(char)
        # Bigrams
        for i in range(len(clean_text) - 1):
            tokens.append(clean_text[i:i+2])
            
        return tokens

    def update_corpus_stats(self, corpus_texts: list):
        """
        Update Document Frequency (DF), total document count (N), and average doc length
        """
        if not corpus_texts:
            return
            
        total_len = 0
        doc_count = 0
        
        for text in corpus_texts:
            tokens = self.tokenize(text)
            if not tokens:
                continue
            
            total_len += len(tokens)
            doc_count += 1
            
            # Count unique tokens in this document
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.df[token] = self.df.get(token, 0) + 1
                
        self.N += doc_count
        if self.N > 0:
            # Update running average document length
            self.avg_doc_len = ((self.avg_doc_len * (self.N - doc_count)) + total_len) / self.N
            
        self.save_df()

    def get_sparse_vector(self, text: str) -> dict:
        """
        Compute BM25 sparse vector representation
        """
        tokens = self.tokenize(text)
        if not tokens:
            return {"indices": [], "values": []}
            
        doc_len = len(tokens)
        
        # Compute term frequencies
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
            
        sparse_dict = {}
        for token, count in tf.items():
            # Calculate token ID using CRC32
            token_id = zlib.crc32(token.encode('utf-8')) & 0xffffffff
            
            # Calculate IDF
            token_df = self.df.get(token, 1)
            # Standard BM25 IDF formula
            idf = math.log(((self.N - token_df + 0.5) / (token_df + 0.5)) + 1.0)
            if idf <= 0:
                idf = 0.0001
                
            # BM25 TF weight
            numerator = count * (self.k1 + 1)
            denominator = count + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
            tf_weight = numerator / denominator
            
            weight = tf_weight * idf
            
            # Add or accumulate weight in case of CRC32 collisions
            sparse_dict[token_id] = sparse_dict.get(token_id, 0.0) + weight
            
        # Sort indices to match Qdrant's sparse vector requirement
        sorted_indices = sorted(sparse_dict.keys())
        sorted_values = [sparse_dict[idx] for idx in sorted_indices]
        
        return {
            "indices": sorted_indices,
            "values": sorted_values
        }

if __name__ == "__main__":
    builder = SparseVectorBuilder()
    
    # Train stats on small sample
    sample_corpus = [
        "民法第一百八十四條規定侵權行為之損害賠償責任。",
        "侵權行為之消滅時效為二年，民法第197條著有明文。",
        "行政程序法第一百三十一條規定公法上請求權時效。"
    ]
    builder.update_corpus_stats(sample_corpus)
    
    # Generate sparse vector
    vec = builder.get_sparse_vector("侵權行為消滅時效民法")
    print("Success! Generated sparse vector.")
    print(f"Indices: {vec['indices'][:5]}")
    print(f"Values: {vec['values'][:5]}")
