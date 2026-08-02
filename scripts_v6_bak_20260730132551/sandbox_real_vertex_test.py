import os
import wave
import json
import base64
from google import genai
from google.genai import types
from google.cloud import storage
import logging

logging.basicConfig(level=logging.INFO)

def create_dummy_wav(path):
    with wave.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        # Write 1 second of silence
        f.writeframes(b'\x00\x00' * 16000)
    return path

def run_tests():
    project_id = "project-bbb51788-254b-4ec3-ad7"
    
    logging.info(f"Using Vertex AI Project: {project_id}")
    
    # 1. Create dummy wav
    wav_path = "C:\\LocalAI_Workstation\\scripts_v6\\dummy_test.wav"
    create_dummy_wav(wav_path)
    
    # Init Vertex AI client
    client = genai.Client(vertexai=True, project=project_id, location="us-central1")
    model_name = "gemini-2.5-flash"
    
    prompt = "This is a 1-second silent audio file for a system test. Please reply with 'AUDIO_RECEIVED'."
    
    print("\n===========================================")
    print("[TEST 1] Testing Base64 InlineData Route")
    print("===========================================")
    try:
        with open(wav_path, "rb") as f:
            audio_data = f.read()
        audio_part = types.Part.from_bytes(data=audio_data, mime_type="audio/wav")
        
        response = client.models.generate_content(
            model=model_name,
            contents=[audio_part, prompt],
        )
        print(f"[SUCCESS] Base64 Response: {response.text.strip()}")
    except Exception as e:
        print(f"[FAILED] Base64 Test Failed: {e}")

    print("\n===========================================")
    print("[TEST 2] Testing GCS (gs://) Route")
    print("===========================================")
    try:
        storage_client = storage.Client(project=project_id)
        bucket_name = f"lexmind-temp-{project_id}"
        bucket = storage_client.bucket(bucket_name)
        
        # Check if bucket exists, create if not
        if not bucket.exists():
            print(f"Bucket {bucket_name} does not exist! Creating it...")
            bucket.create(location="us-central1")
            print(f"Bucket {bucket_name} created successfully.")
            
        blob_name = "test_dual_route_dummy.wav"
        blob = bucket.blob(blob_name)
        
        print(f"Uploading to gs://{bucket_name}/{blob_name} ...")
        blob.upload_from_filename(wav_path)
        
        audio_part = types.Part.from_uri(file_uri=f"gs://{bucket_name}/{blob_name}", mime_type="audio/wav")
        
        print("Calling Vertex AI ...")
        response = client.models.generate_content(
            model=model_name,
            contents=[audio_part, prompt],
        )
        print(f"[SUCCESS] GCS Response: {response.text.strip()}")
        
        # Clean up
        blob.delete()
        print("[CLEANUP] Cleaned up GCS blob.")
            
    except Exception as e:
        print(f"[FAILED] GCS Test Failed: {e}")

    # Clean up local file
    if os.path.exists(wav_path):
        os.remove(wav_path)

if __name__ == "__main__":
    run_tests()
