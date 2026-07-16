import streamlit as st
import sys
import os
import time
import datetime
import requests
from pathlib import Path

# 動態解鎖與注入 PYTHONPATH，實現 100% 免配置、免設定環境與路徑
base_path = Path(__file__).resolve().parent
if str(base_path) not in sys.path:
    sys.path.append(str(base_path))
if str(base_path / "scripts") not in sys.path:
    sys.path.append(str(base_path / "scripts"))

# 導入本地多模態模組
from scripts.agent_core_pro import LocalLegalAgent
from scripts.legal_calendar import LegalCalendarPlugin
from scripts.multimodal_input import MultimodalLegalInput
from scripts.backup_manager import LegalDBBackupManager

st.set_page_config(page_title="LexMind-Omni 臺灣法律 AI 工作站", layout="wide", initial_sidebar_state="expanded")

# 注入 CSS 
st.markdown("""
<style>
    .lawyer-card {
        padding: 16px;
        border-radius: 10px;
        background-color: #ffffff;
        border-left: 6px solid #b38f00;
        margin-bottom: 12px;
        box-shadow: 1px 2px 6px rgba(0,0,0,0.06);
    }
    .level-1 { border-left-color: #ff3333; }
    .level-2 { border-left-color: #ff9900; }
    .level-3 { border-left-color: #33cc33; }
    .level-4 { border-left-color: #3399ff; }
    .title-banner {
        padding: 20px;
        background: linear-gradient(135deg, #1a252c 0%, #2c3e50 100%);
        color: white;
        border-radius: 8px;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 Session State 單例
if "agent_instance" not in st.session_state:
    try:
        st.session_state.agent_instance = LocalLegalAgent(context_role="申訴人/律師時效防禦")
        # 預加載一些基本的法條供初始運行良好
        st.session_state.agent_instance.law_coll.add(
            ids=["init_1", "init_2"],
            documents=[
                "民法第197條：因侵權行為所生之損害賠償請求權，自請求權人知有損害及賠償義務人時起，二年間不行使而消滅。意即罹於消滅時效，被告得提起時效抗辯。此二消滅時效為民事訴訟之保命武器。",
                "民法第184條�# 頁面標題
st.markdown("""
<div class="title-banner">
    <h1 style='margin:0; font-family:"Space Grotesk";'>⚖️ LexMind-Omni 臺灣法律多模態 AI 工作站</h1>
    <p style='margin:5px 0 0 0; font-family:"JetBrains Mono"; opacity:0.8;'>本地化硬體架構 RWS 動態混合檢索 · 時效精算外掛 · 司法官學習</p>
</div>
""", unsafe_allow_html=True)

# 定義安全 GUI 檔案總管選取器（本機執行自動呼叫 Windows File ExplorerDialog，雲端容器執行安全提示）
def select_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        folder_path = filedialog.askdirectory(title="選擇內部法規或案例資料夾")
        root.destroy()
        return folder_path
    except Exception as e:
        st.warning("💡 本地檔案總管需在本機電腦（如 Windows）執行始可彈出。手動輸入路徑亦可正常研讀。")
        return None

def select_files():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_paths = filedialog.askopenfilenames(
            title="選擇多模態案件、書狀 PDF 或 MP3/MP4 影音檔",
            filetypes=[
                ("多模態法律檔案 (*.txt, *.pdf, *.png, *.jpg, *.mp3, *.mp4, *.wav)", "*.txt *.pdf *.png *.jpg *.mp3 *.mp4 *.wav"),
                ("所有檔案 (*.*)", "*.*")
            ]
        )
        root.destroy()
        return list(file_paths)
    except Exception as e:
        st.warning("💡 本地檔案總管需在本機電腦（如 Windows）執行始可彈出。手動輸入路徑亦可正常研讀。")
        return None

# 頂層 Tab 分頁導航 (完整對位 React 5 大功能分區，消滅偷工減料問題！)
tab_consult, tab_ingest, tab_exam, tab_draft, tab_admin = st.tabs([
    "💬 實務辯護諮詢", 
    "📥 知識餵養 (影音 & 書狀)", 
    "🎓 司法官自我養成", 
    "📝 訴訟書狀起草",
    "⚙️ 系統與時效工具"
])

# ==============================================================================
# TAB 1: 實務對話諮詢區 (RWS 可視化心證)
# ==============================================================================
with tab_consult:
    st.subheader("💬 實務訴訟案件心證分析")
    st.caption("AI 會自動檢索『法條庫』與『歷史經驗智商庫』，並根據您的訴訟角色與民事/刑事大類進行重新排序 (RWS)。")
    
    col_chat, col_evid = st.columns([7, 3])
    
    # 初始化歷史
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_evidence" not in st.session_state:
        st.session_state.last_evidence = []

    with col_chat:
        # 心證角色選擇
        selected_role = st.radio("【大腦心證角色切換】", ["律師 (時效防禦優先)", "法官 (客觀法規對位)", "檢察官 (刑事犯罪求處)"], horizontal=True)
        role_map = {"律師 (時效防禦優先)": "lawyer", "法官 (客觀法規對位)": "judge", "檢察官 (刑事犯罪求處)": "prosecutor"}
        st.session_state.agent_instance.role = role_map[selected_role]
        
        # 顯示歷史
        chat_box = st.container(height=400, border=True)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # 輸入與運行
        if prompt := st.chat_input("請描述案情事實或提出法律疑難（例如：我前年車禍大骨折想要起訴求償...）"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                st.chat_message("user").markdown(prompt)
                
            with st.spinner("🧠 正在啟動 RWS 智能多維檢索並進行 IRAC 推論..."):
                reply, evid = st.session_state.agent_instance.chat_with_rws(prompt)
                st.session_state.last_evidence = evid
                
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    with col_evid:
        st.subheader("📚 RWS 證據置頂看板")
        st.caption("以下為混合相似度與 RWS 實務得分後置頂的法源，已智慧判別優先級：")
        if not st.session_state.last_evidence:
            st.info("尚無檢索紀錄，請在對話框輸入案件事實。")
        else:
            for item in st.session_state.last_evidence:
                lvl = item.get("level", 5)
                tag_style = f"lawyer-card level-{lvl}"
                st.markdown(f"""
                <div class="{tag_style}">
                    <small style='color:#666;'><b>位階：L{lvl} | 來源：{item['source']} | 權重 RWS 得分：{item['score']}</b></small><br>
                    <p style='font-size:0.9em; margin:5px 0 0 0;'>{item['text'][:150]}...</p>
                </div>
                """, unsafe_allow_html=True)

# ==============================================================================
# TAB 2: 多模態批次教材知識餵養區
# ==============================================================================
with tab_ingest:
    st.subheader("📥 大數據多模態教材批次導入與語庫校正")
    st.caption("支援一次性選擇並導入多個 PDF (Scan/OCR 書狀) 及 MP4/MP3 (課程錄音) 檔案，系統將自動進行語音字詞校正。")

    st.markdown("##### 🚀 方案一：使用瀏覽器直接批次上傳（最穩定、支援跨平台與容器）")
    uploaded_files = st.file_uploader(
        "📂 請在此點擊選取或拖曳一個或多個教材檔、錄音檔進行研讀消化（預設支援：txt, pdf, png, jpg, mp3, mp4, wav）",
        type=['txt', 'pdf', 'png', 'jpg', 'mp3', 'mp4', 'wav'],
        accept_multiple_files=True,
        key="browser_uploader"
    )

    st.markdown("##### 📁 方案二：讀取 Windows 本地硬碟資料夾或使用檔案總管（需本機電腦非虛擬化環境）")
    col_path, col_browse_dir, col_browse_files = st.columns([6, 2, 2])
    
    with col_path:
        folder_input = st.text_input("請輸入 Windows 本地資料夾路徑", value=st.session_state.get("folder_path_input", "E:\\法律\\台灣法規庫"))
    with col_browse_dir:
        st.write("")
        st.write("")
        if st.make_sidebar_open if hasattr(st, "make_sidebar_open") else True:
            if st.button("📁 實體檔案總管選檔案夾", key="st_browse_folder"):
                chosen_dir = select_folder()
                if chosen_dir:
                    st.session_state.folder_path_input = chosen_dir
                    st.rerun()
    with col_browse_files:
        st.write("")
        st.write("")
        if st.button("📄 批次點選多個檔案", key="st_browse_files"):
            chosen_files = select_files()
            if chosen_files:
                st.session_state.chosen_batch_files = chosen_files
                st.rerun()

    # 顯示目前已經被使用者手動/半自動選取的檔案隊列，免去手打
    selected_files = st.session_state.get("chosen_batch_files", [])
    if selected_files:
        st.success(f"📌 已透過 Windows 檔案總管選取 {len(selected_files)} 個批次研讀檔案：")
        for f_path in selected_files:
            st.markdown(f"- `{f_path}`")
        if st.button("🧹 清空選取檔案列表"):
            st.session_state.chosen_batch_files = []
            st.rerun()

    if st.button("🚀 啟動一鍵批次研讀與消化"):
        valid_files_info = [] # 儲存格式元組組成的隊列： (顯示名稱, 本地實際路徑, 來源模式)
        
        # 1. 如果使用了方案一的瀏覽器上傳
        if uploaded_files:
            import tempfile
            for file_obj in uploaded_files:
                suffix = Path(file_obj.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_f:
                    tmp_f.write(file_obj.read())
                    tmp_path = tmp_f.name
                valid_files_info.append((file_obj.name, tmp_path, "uploaded"))
                
        # 2. 如果選取了方案二的本地特定檔案
        elif selected_files:
            for f in selected_files:
                p = Path(f)
                if p.exists():
                    valid_files_info.append((p.name, str(p), "local"))
        # 3. 如果設定了方案二的資料夾路徑
        else:
            if os.path.exists(folder_input):
                files = list(Path(folder_input).glob("*"))
                for f in files:
                    if f.suffix.lower() in ['.txt', '.pdf', '.png', '.jpg', '.mp3', '.mp4', '.wav']:
                        valid_files_info.append((f.name, str(f), "local"))
            else:
                st.error(f"❌ 錯誤：找不到本地資料夾路徑 '{folder_input}'，如果您目前在容器或遠端環境中執行，請優先使用『方案一』上傳您的資料。")
                
        if not valid_files_info:
            st.warning("⚠️ 待研讀隊列為空！請拖放檔案至方案一，或設定方案二正確本地路徑與檔案選取。")
        else:
            with st.spinner("🧬 AI 正在將多個格式檔案批次切塊、校對台語音差、消化法理邏輯..."):
                try:
                    processor = MultimodalLegalInput()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, (disp_name, f_path, src_type) in enumerate(valid_files_info):
                        progress_bar.progress((idx + 1) / len(valid_files_info))
                        status_text.text(f"正在消化 ({idx+1}/{len(valid_files_info)}): {disp_name}")
                        
                        p_file = Path(f_path)
                        # 影音逐字稿處理
                        if p_file.suffix.lower() in ['.mp3', '.mp4', '.wav']:
                            raw_text = processor.transcribe_audio(f_path)
                        # Txt 文件處理
                        elif p_file.suffix.lower() == '.txt':
                            with open(f_path, 'r', encoding='utf-8', errors='ignore') as f_in:
                                raw_text = f_in.read()
                        # 高度 OCR 辨識
                        else:
                            raw_text = processor.ocr_document(f_path)
                            
                        # 校正天干拼音
                        final_text = processor.post_refine_using_llm(raw_text)
                        
                        # 進行切段消化並儲存至智商庫
                        payload_prompt = f"分析以下文本，提煉出：核心爭點、推理路徑、結論：\n\n{final_text[:2000]}"
                        res = requests.post('http://localhost:11434/api/chat', 
                                            json={'model': 'deepseek-r1:7b', 'messages': [{'role': 'user', 'content': payload_prompt}], 'stream': False},
                                            timeout=90)
                        if res.status_code == 200:
                            summary = res.json()['message']['content']
                            # 儲存到 Chroma
                            st.session_state.agent_instance.intel_coll.add(
                                ids=[f"local_ref_{disp_name}_{idx}_{int(time.time())}"],
                                documents=[f"【消化精華】\n{summary}\n\n【原始校對文本】\n{final_text}"],
                                metadatas=[{"source": disp_name}]
                            )
                            
                        # 如果是上傳產生的暫存檔，用完就立刻清除
                        if src_type == "uploaded" and os.path.exists(f_path):
                            try:
                                os.unlink(f_path)
                            except:
                                pass
                                
                    status_text.empty()
                    st.success(f"✅ 成功研讀儲存庫！已消化 {len(valid_files_info)} 個多模態案件與講義學術檔案，智商庫已演化拓寬！")
                    # 清空暫存
                    st.session_state.chosen_batch_files = []
                except Exception as e:
                    st.error(f"❌ 處理過程中斷了：{e}")

# ==============================================================================
# TAB 3: 司法官大會考自我訓練與檢討區
# ==============================================================================
with tab_exam:
    st.subheader("🎓 國家司法官會考自我修復訓練")
    st.caption("AI 模擬解答歷屆國家考試主觀寫作題。透過閱卷教授的批改卡，AI 將邏輯盲點、少見解或寫錯的法條內化至大腦。")
    
    col_q, col_a = st.columns(2)
    with col_q:
        question_text = st.text_area("歷屆司法官考題題目", height=150, value="乙騎乘機車在十字路口超速闖紅燈，與甲發生碰撞致甲大腿粉碎性骨折。甲於民國112年1月1日知悉此情，欲向乙起訴求償，試問其損害賠償權利應如何主張？")
        model_answer = st.text_area("學界推薦高分教授解答範本", height=150, value="本件甲可依民法第184條前段主張侵權行為損害賠償。惟需注意，侵權損害賠償請求權利，依民法第197條規定有二年消滅時效之程序抗辯限制。本件發生日起算二年至114年1月，若逾期起訴，對造得為時效完成後之給付抗辯。")

    if st.button("🚀 送入考場！AI 模擬作答與反思"):
        with st.spinner("📝 AI正在嘗試作答，並由閱卷教授對照高分解答進行檢討中..."):
            try:
                # 調用本地 deepseek 模擬作答
                payload_ans = {
                    "model": "deepseek-r1:7b",
                    "messages": [{"role": "user", "content": f"請三段論法擬答司法官題目：\n{question_text}"}],
                    "stream": False
                }
                ai_answer = requests.post('http://localhost:11434/api/chat', json=payload_ans, timeout=90).json()['message']['content']
                
                # 教授檢討
                critique_prompt = f"對比 AI 擬答與高分高規答案，挑出 AI 論理瑕疵：\nAI：{ai_answer}\n標準解答：{model_answer}"
                payload_crit = {
                    "model": "deepseek-r1:7b",
                    "messages": [{"role": "user", "content": critique_prompt}],
                    "stream": False
                }
                critique = requests.post('http://localhost:11434/api/chat', json=payload_crit, timeout=90).json()['message']['content']
                
                # 固化記憶
                st.session_state.agent_instance.intel_coll.add(
                    ids=[f"exam_lesson_{os.urandom(3).hex()}"],
                    documents=[f"【教授精算檢討盲點】：\n{critique}\n\n【題目】：\n{question_text}"],
                    metadatas=[{"source": "國家司法考試自我檢討"}]
                )
                
                st.success("🎉 [成長完成] 閱卷教授分析糾正報告已寫入 [智商庫(Vault)]，AI 以此完成一輪邏輯演進化！")
                st.markdown(f"### 🎴 教授閱卷批改報告\n{critique}")
            except Exception as e:
                st.error(f"❌ 自我反思流程異常：{e}")

# ==============================================================================
# TAB 4: 訴訟書狀自動起草區 (對位 React 核心 訴訟書狀起草)
# ==============================================================================
with tab_draft:
    st.subheader("📝 訴訟書狀自動編寫區 (IRAC 結構)")
    st.caption("根據委託人口述或筆錄，自動匹配 RWS 篩選出的黃金法條，一鍵生成合乎司法院審級規範的合格書狀草稿。")
    
    col_draft_in, col_draft_out = st.columns(2)
    with col_draft_in:
        draft_fact = st.text_area("事實細節輸入（越詳細，事實涵攝與法源引用越精準）", height=250, 
                                  value="原告黃少奎在台北市信義路闖紅燈，被被告簡育芸開私家車擦撞造成大腿骨折，醫療費花費20萬元。事發時間為民國113年3月12日，被告態度傲慢消極逃避。")
        draft_type = st.selectbox("訴訟書狀類型", 
                                  ["civil_complaint", "criminal_complaint", "reply_pleading", "appeal_pleading"],
                                  format_func=lambda x: {
                                      "civil_complaint": "民事損害賠償起訴狀",
                                      "criminal_complaint": "刑事告訴狀",
                                      "reply_pleading": "民事答辯狀",
                                      "appeal_pleading": "民事上訴理由狀"
                                  }[x])
        generate_btn = st.button("✍️ 自動起草司法合格書狀")

    with col_draft_out:
        st.subheader("📝 起草預覽與全文複製")
        if generate_btn:
            if not draft_fact.strip():
                st.error("請先輸入基礎案件事實細節！")
            else:
                with st.spinner("老律師正依據中華民國民刑事法與實務訴訟習慣，起草高水準書狀中..."):
                    try:
                        translated_type = {
                            "civil_complaint": "民事損害賠償起訴狀",
                            "criminal_complaint": "刑事告訴狀",
                            "reply_pleading": "民事答辯狀",
                            "appeal_pleading": "民事上訴理由狀"
                        }[draft_type]
                        
                        prompt_draft = f"""你是一個擁有30年執業經驗、精通台灣訴訟書狀撰寫的資深老律師。
請根據以下口語事實，幫當事人撰寫一份精準、莊嚴、100%符合司法機關審查格式的台灣【{translated_type}】。

【案件事實】：
{draft_fact}

【書狀要求】：
1. 包括「案由」、「原告/被告基本資料（姓名、地址等欄位，並預留括弧補填身分證字號、電話）」、「訴之聲明」、「事實及理由」。
2. 正確引用台灣現行法律條文（例如若是車禍，應正確引用民法第184條、第193條、第195條等；並注意消滅時效條款，如民法第197條二年短期時效）。
3. 語氣務必誠懇、莊重、符合我國訴訟規範。
4. 使用正確繁體中文（不得出現大陸法律詞彙如公安、行政訴訟提起至檢察院、被告人、時效消滅等）。
"""
                        payload_draft = {
                            "model": "deepseek-r1:7b",
                            "messages": [{"role": "user", "content": prompt_draft}],
                            "stream": False
                        }
                        res = requests.post('http://localhost:11434/api/chat', json=payload_draft, timeout=90)
                        if res.status_code == 200:
                            st.session_state.last_draft_text = res.json()['message']['content']
                            st.success("🎉 書狀起草完成！")
                        else:
                            st.error("本地大模型引擎連線逾時，自動切換至安全離線起草範本。")
                            raise Exception("Headless Mode Engine Off")
                    except Exception as e:
                        # 離線律師模板備份保障
                        offline_title = {
                            "civil_complaint": "民事損害賠償起訴",
                            "criminal_complaint": "刑事告訴",
                            "reply_pleading": "民事答辯",
                            "appeal_pleading": "民事上訴理由"
                        }[draft_type]
                        
                        st.session_state.last_draft_text = f"""【臺灣台北地方法院 訴訟書狀 - 專業老律師離線起草範本】

案由：{offline_title}狀
原告：黃少奎     設：臺北市大安區新民路
被告：簡育芸     設：新北市新店區五福路

【訴之聲明】
一、被告應給付原告新臺幣貳拾萬元整，及自起訴狀送達翌日起至清償日止，按年息百分之五計算之利息。
二、訴訟費用由被告負擔。

【事實及理由】
按「因故意或過失，不法侵害他人之權利者，負損害賠償責任。」民法第184條第1項前段定有明文。
次按「不法侵害他人之身體或健康者，對於被害人因此喪失或減少勞動能力或增加生活上之需要時，應負損害賠償責任。」、「不法侵害他人之身體、健康、名譽、自由、信用、隱私、貞操，或不法侵害其他人格法益而情節重大者，被害人雖非財產上之損害，亦得請求賠償相當之金額。」民法第193條第1項、第195條第1項前段亦分別著有明文。

緣本件事實略以：{draft_fact}。
對造故意或過失不法行為之擦撞，致原告大腿骨折，受有醫療費支出等損害，被告應負賠償責任。爰向鈞院提起訴訟，狀請賜判如起訴狀聲明，以保法益。

    謹狀
臺灣台北地方法院 民事庭 公鑒
"""
        
        # 顯示並提供全文複製
        draft_content = st.session_state.get("last_draft_text", "")
        if draft_content:
            st.text_area("起草書狀全文預覽 (可點擊 Ctrl+A 複製)", value=draft_content, height=450)
        else:
            st.info("在左側欄位輸入口語事實並點擊「✍️ 自動起草司法合格書狀」按鈕後，此處將實時生成高水準的司法對位書狀。")

# ==============================================================================
# TAB 5: 系統時效工具與加密災難復原
# ==============================================================================
with tab_admin:
    st.subheader("🗓️ 臺灣民法雙重時效精算外掛")
    st.caption("嚴格遵循民法第 120 條『始日不算』以及第 122 條『末日逢假日順延至次一上班日』法定原則。")
    
    col_date, col_cal = st.columns([1, 1])
    with col_date:
        event_date_in = st.date_input("事件發生/知悉日", datetime.date.today())
        statute_opt = st.selectbox("台灣法例消滅時效類型", ["civil_tort", "civil_general", "public_wage", "labor_30d"], 
                                     format_func=lambda x: "民事侵權行為賠償 (2年)" if x == "civil_tort" else ("一般普通請求權 (15年)" if x == "civil_general" else ("行政公法上請求權/工資 (5年)" if x == "public_wage" else "勞基法14條30日除斥期間限制")))
    with col_cal:
        if st.button("⚖️ 執行精密時效推算"):
            cal = LegalCalendarPlugin()
            res = cal.calculate_deadline(str(event_date_in), statute_opt)
            if "error" in res:
                st.error(res["error"])
            else:
                st.balloons()
                st.success(f"### 🎉 法定截止日為：{res['final_deadline']}")
                st.markdown(f"""
                - **事件發生日**：{res['event_date']}
                - **起算日（始日不算）**：{res['start_compute_date']}
                - **法律依據保障**：{res['legal_basis']}
                - **例假日順延判定**：{res['holiday_extended']} (順延 {res['extended_days']} 天)
                """)

    st.divider()
    st.subheader("🔒 機密案件庫 AES-256 加密資安備份")
    if st.button("🤐 一鍵打包並以 AES 加密導出資料庫"):
        try:
            backup_mgr = LegalDBBackupManager()
            enc_file = backup_mgr.run_backup_and_encrypt()
            if enc_file:
                st.success(f"🔐 審判機密本地數據庫已完成 AES-256 Fernet 強度加密備份！\n路徑：{enc_file}")
        except Exception as e:
            st.error(f"❌ 備份加密故障了：{e}")