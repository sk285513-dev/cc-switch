import os
import sys
import json
import time
import asyncio
import logging
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Proxy] %(message)s")

# Allow import of QuotaManager
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts_v6.quota_manager import QuotaManager

app = FastAPI(title="LexMind Local API Proxy")

client = None
quota_manager = None

@app.on_event("startup")
async def startup_event():
    global client, quota_manager
    client = httpx.AsyncClient(timeout=300.0)
    
    # Initialize QuotaManager to load keys via KeyManager (which calls vault.py)
    quota_manager = QuotaManager(
        keys_path="config/keys.yaml",
        policy_path="config/quota_policy.yaml",
        state_path="config/quota_state.json"
    )
    logging.info(f"Proxy Server Started. Loaded {len(quota_manager.keys)} keys from QuotaManager.")

@app.on_event("shutdown")
async def shutdown_event():
    global client
    if client:
        await client.aclose()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_all(request: Request, path: str):
    target_url = f"https://generativelanguage.googleapis.com/{path}"
    
    params = dict(request.query_params)
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)
    
    consecutive_429 = 0
    try:
        current_key = quota_manager.acquire_key()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    
    while True:
        quota_manager.throttle_key(current_key)
        headers["x-goog-api-key"] = current_key
        
        try:
            req = client.build_request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=params,
                content=body
            )
            
            # Send the request
            response = await client.send(req, stream=True)
            
            # Handle 429/403/401 Quota errors
            if response.status_code in (429, 401, 403):
                err_bytes = await response.aread()
                err_text = err_bytes.decode('utf-8', errors='ignore')
                logging.warning(f"[Proxy] Key {current_key[:8]}... returned {response.status_code}: {err_text[:100]}")
                
                class DummyAPIError(Exception):
                    def __init__(self, msg):
                        super().__init__(msg)
                
                consecutive_429 += 1
                e = DummyAPIError(err_text)
                
                # Use quota_manager's error handling.
                # To prevent blocking the async loop, run the sleep part manually if needed.
                # Since handle_error might sleep synchronously, we wrap it in a thread.
                result = await asyncio.to_thread(
                    quota_manager.handle_error, e, current_key, consecutive_429, False
                )
                
                sleep_time = result.get("sleep_time", 0)
                if sleep_time > 0:
                    logging.info(f"[Proxy] Sleeping for {sleep_time}s due to quota limits...")
                    await asyncio.sleep(sleep_time)
                
                new_key = result.get("new_key")
                if not new_key:
                    raise HTTPException(status_code=429, detail="All API keys exhausted. Cooldown in progress.")
                
                current_key = new_key
                continue # Retry with new key
            
            # Success: Stream response back
            async def stream_generator():
                async for chunk in response.aiter_raw():
                    yield chunk
                    
            return StreamingResponse(
                stream_generator(),
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ("content-encoding", "transfer-encoding")}
            )
            
        except httpx.RequestError as e:
            logging.error(f"Proxy request error: {e}")
            raise HTTPException(status_code=502, detail="Bad Gateway")

if __name__ == "__main__":
    import uvicorn
    # Make sure this is only runnable by api_proxy.py directly
    # So process name is api_proxy.py
    os.environ["PROXY_AUTH_TOKEN"] = "1"
    uvicorn.run("api_proxy:app", host="127.0.0.1", port=8081, workers=1)
