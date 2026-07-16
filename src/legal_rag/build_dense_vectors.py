import os
import sys
import yaml
from dotenv import load_dotenv
from google import genai

class DenseVectorBuilder:
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
            raise Exception("GEMINI_API_KEY not found in environment variables!")
            
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-embedding-2"

    def get_embedding(self, text: str) -> list:
        """
        Generate dense embedding for a single text string
        """
        if not text or not text.strip():
            # Return zero vector if empty
            return [0.0] * self.config['vectors']['dense']['size']
            
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"[Dense Vector Error] Failed to generate embedding: {e}")
            raise e

    def get_embeddings_batch(self, texts: list) -> list:
        """
        Generate dense embeddings for a batch of text strings
        """
        if not texts:
            return []
            
        cleaned_texts = [t if (t and t.strip()) else "empty" for t in texts]
        
        try:
            response = self.client.models.embed_content(
                model=self.model,
                contents=cleaned_texts
            )
            return [emb.values for emb in response.embeddings]
        except Exception as e:
            print(f"[Dense Vector Error] Failed to generate batch embeddings: {e}")
            # Fallback to individual generation if batch fails
            results = []
            for t in texts:
                results.append(self.get_embedding(t))
            return results

if __name__ == "__main__":
    builder = DenseVectorBuilder()
    test_text = "測試民法侵權行為與消滅時效之 Embedding 產生。"
    vector = builder.get_embedding(test_text)
    print(f"Success! Generated dense vector of size {len(vector)}")
    print(f"Preview (first 5 elements): {vector[:5]}")
