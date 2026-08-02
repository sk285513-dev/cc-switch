import sys
sys.path.insert(0, "C:\\LocalAI_Workstation")
import time
from streamlit.testing.v1 import AppTest

# 我們這裡撰寫一個小型的假 Streamlit App，用來測試 find_deep_anomalies
# 但由於我們想直接測試 system_ui_tester.py 中的邏輯，我們可以匯入它或複製部分邏輯來跑
import streamlit as st

def main():
    st.title("Test App for TC-0.2")
    st.error("這是一個頂層的 Error，應該會被抓到。")
    
    with st.expander("深層容器"):
        st.warning("這是一個位於 Expander 內的 Warning，尚未實作設定頁面！")
        
    t1, t2 = st.tabs(["T1", "T2"])
    with t1:
        st.success("一切正常")
    with t2:
        st.markdown("這裡發生了 Traceback 錯誤！")

if __name__ == "__main__":
    main()
