import streamlit as st
import time

st.title("LexMind-Omni Dummy App")

tab1, tab2, tab3, tab4 = st.tabs(["首頁", "知識餵養", "分頁3", "分頁4"])

with tab1:
    st.write("這是首頁")
    
    # Mechanism 8: Combinatorial explosion prevention
    st.checkbox("特徵 A (check_lawyer)", key="check_lawyer")
    st.checkbox("特徵 B (check_judge)", key="check_judge")
    st.checkbox("特徵 C", key="check_c")
    st.checkbox("特徵 D", key="check_d")
    
    if st.button("啟動一鍵批次研讀"):
        st.success("研讀啟動中...")
        
    # Mechanism 3: Crash detection
    if st.button("模擬系統崩潰"):
        st.error("Traceback (most recent call last):\n  File 'app.py', line 10, in <module>\nIndexError: list index out of range")
        raise IndexError("Crash simulation")

with tab2:
    st.write("這是知識餵養")
    
    # Mechanism 9: Hidden Element Exploration
    with st.expander("進階設定 (Hidden Elements)"):
        st.text_input("隱藏的輸入框", key="hidden_input")
        st.button("隱藏的按鈕", key="hidden_btn")
        
    # Mechanism 12: High-Fidelity Synthetic Events
    st.text_area("請輸入查詢", key="query_input")
    
    # Mechanism 13: Async Spinner Synchronization
    if st.button("提交查詢"):
        with st.spinner("AI 推論中..."):
            time.sleep(2)
        st.markdown("**【解答】** 這是您的模擬查詢結果。勝訴！")

with tab3:
    st.write("這是分頁3")

with tab4:
    st.write("這是分頁4")
