import streamlit as st
import sys
import os
import requests
import json
import traceback
import base64

# 把 src\legal_rag 加入 path 以便匯入
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
legal_rag_dir = os.path.join(project_root, "src", "legal_rag")
if legal_rag_dir not in sys.path:
    sys.path.append(legal_rag_dir)

# 嘗試匯入 Hybrid Search
try:
    from hybrid_search import LegalHybridSearchSystem
except ImportError as e:
    st.error(f"無法匯入 LegalHybridSearchSystem: {e}\n請確認您是否在 C:\\LocalAI_Workstation 下執行。")
    st.stop()

# --- 頁面設定 ---
st.set_page_config(page_title="LexMind-Omni RAG 法律顧問", page_icon="⚖️", layout="wide")
st.title("⚖️ LexMind-Omni RAG 法律顧問")
st.caption("基於 530 堂實務課程講義與 Qdrant 向量檢索的對話系統")

# --- 狀態管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "search_system" not in st.session_state:
    with st.spinner("正在初始化 Qdrant 向量檢索系統..."):
        st.session_state.search_system = LegalHybridSearchSystem()
if "last_context" not in st.session_state:
    st.session_state.last_context = []

# --- 側邊欄：設定與檢索透明化 ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("Gemini API Key", type="password", help="請輸入您的 Google Gemini API Key")
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            st.success("已從環境變數讀取 API Key！")
        else:
            st.warning("請輸入 API Key 以啟用問答功能。")
            
    st.divider()
    st.header("📚 檢索透明化 (RAG Context)")
    st.caption("這裡是機器人剛剛去資料庫翻找出來的參考講義片段：")
    
    if st.session_state.last_context:
        for idx, hit in enumerate(st.session_state.last_context, start=1):
            with st.expander(f"來源 {idx}: {hit['payload'].get('title', '未知課程')}", expanded=(idx==1)):
                st.write(f"**RRF 分數:** {hit.get('rrf_score', 0):.4f}")
                st.write(hit['payload'].get('text', ''))
    else:
        st.info("目前還沒有檢索結果。請在右側開始提問！")
        
    st.divider()
    st.header("👁️ 分析影像 (視覺理解)")
    st.caption("上傳紙本講義、黑板圖表或存證信函的照片，讓機器人為您解析。")
    uploaded_image = st.file_uploader("上傳圖像", type=["png", "jpg", "jpeg"])
    
    base64_image = None
    mime_type = None
    if uploaded_image is not None:
        st.image(uploaded_image, caption="準備解析的圖片", use_container_width=True)
        bytes_data = uploaded_image.getvalue()
        base64_image = base64.b64encode(bytes_data).decode("utf-8")
        mime_type = uploaded_image.type

# --- Gemini API 呼叫 ---
def chat_with_gemini(api_key, query, context_hits, base64_image=None, mime_type=None):
    # 組合 RAG Context
    context_text = "【參考資料】\n"
    for i, hit in enumerate(context_hits, 1):
        context_text += f"來源 {i} ({hit['payload'].get('title', '')}):\n{hit['payload'].get('text', '')}\n\n"
        
    augmented_prompt = f"{context_text}\n\n使用者提問：{query}\n\n請根據上方【參考資料】的內容，以專業的台灣法律實務顧問口吻，使用繁體中文詳盡回答使用者的提問。若參考資料不足以回答，請誠實說明。若資料中有法條或最高法院決議，請明確引用。特別注意：如果使用者的提問涉及特定土地、不動產、地段爭議或具體地標，請務必利用 Google Search 查核其地理資訊，並在回答中附上可點擊的 Google Maps 搜尋連結（例如：[在地圖上查看](https://www.google.com/maps/search/?api=1&query=關鍵字)），以提供具體的地理背景。"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # 組合歷史紀錄
    contents = []
    # 為了節省 Token，我們只把 augmented_prompt 放在最後一則，歷史紀錄保留原本的對話即可
    for msg in st.session_state.messages[:-1]: # exclude the latest user message which we just added
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
    # 加入最新的 augmented_prompt
    latest_parts = [{"text": augmented_prompt}]
    
    # 若有上傳圖片，加入多模態 payload
    if base64_image and mime_type:
        latest_parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": base64_image
            }
        })
        
    contents.append({"role": "user", "parts": latest_parts})
    
    payload = {
        "contents": contents,
        "tools": [{"googleSearch": {}}]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        res_data = response.json()
        return res_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ 呼叫 Gemini API 發生錯誤：{e}\n\n{traceback.format_exc()}"

# --- 主畫面：對話介面 ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("例如：幫我查一下土地法老師對這條法規的見解是什麼？"):
    # 顯示使用者輸入
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if not api_key:
        with st.chat_message("assistant"):
            st.error("請先在左側欄位輸入 Gemini API Key！")
    else:
        # 執行 Hybrid Search
        with st.chat_message("assistant"):
            status_container = st.empty()
            status_container.info("🔍 正在全域知識庫中檢索相關講義...")
            
            try:
                # 取得檢索結果
                hits = st.session_state.search_system.execute_hybrid_query(prompt)
                st.session_state.last_context = hits
                
                status_container.info("🧠 檢索完成，正在呼叫 Gemini 分析資料與思考解答...")
                
                # 呼叫 Gemini
                response_text = chat_with_gemini(api_key, prompt, hits, base64_image, mime_type)
                
                status_container.empty() # 清除狀態提示
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # 觸發重新渲染左側欄
                st.rerun()
                
            except Exception as e:
                status_container.error(f"檢索或生成過程中發生錯誤：{e}")
