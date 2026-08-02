import re
import sys

def main():
    file_path = r"C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\app.py"
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Add import html
    if "import html" not in content:
        content = re.sub(r"import json\n", "import json\nimport html\n", content, count=1)

    # 2. Escape HTML
    content = content.replace(
        "<b>{role_label}：</b>{msg['content']}</div>\", unsafe_allow_html=True)",
        "<b>{role_label}：</b>{html.escape(msg.get('content', ''))}</div>\", unsafe_allow_html=True)"
    )
    content = content.replace(
        "<b>使用者：</b>{text}</div>\", unsafe_allow_html=True)",
        "<b>使用者：</b>{html.escape(text)}</div>\", unsafe_allow_html=True)"
    )
    content = content.replace(
        "<b>AI 建議：</b>{text}</div>\", unsafe_allow_html=True)",
        "<b>AI 建議：</b>{html.escape(text)}</div>\", unsafe_allow_html=True)"
    )
    content = content.replace(
        "<div class='thought-bubble'>{thought_content}</div>\", unsafe_allow_html=True)",
        "<div class='thought-bubble'>{html.escape(thought_content)}</div>\", unsafe_allow_html=True)"
    )
    content = content.replace(
        "<pre class='terminal-box'>{disp_content}</pre>\", unsafe_allow_html=True)",
        "<pre class='terminal-box'>{html.escape(disp_content)}</pre>\", unsafe_allow_html=True)"
    )

    # 3. Form null checks (Tab 7 top feedback)
    old_top_feedback = """            if submitted:
                score_type = "like" if "👍" in rating else "dislike"
                SubjectIQManager.add_feedback(selected_sub, score_type, comment_input)"""
    new_top_feedback = """            if submitted:
                if selected_sub is not None and rating is not None:
                    score_type = "like" if "👍" in rating else "dislike"
                    SubjectIQManager.add_feedback(selected_sub, score_type, comment_input)
                else:
                    st.warning("請確保科別與評價已正確選取。")"""
    content = content.replace(old_top_feedback, new_top_feedback)

    # Form null checks (Tab 7 chat feedback)
    old_chat_feedback = """                        if submit_resp_agt:
                            SubjectIQManager.add_feedback("編碼助手調校", "like" if "👍" in rating_resp_agt else "dislike", f"【編碼評判】{comment_resp_agt}")"""
    new_chat_feedback = """                        if submit_resp_agt:
                            if rating_resp_agt is not None:
                                SubjectIQManager.add_feedback("編碼助手調校", "like" if "👍" in rating_resp_agt else "dislike", f"【編碼評判】{comment_resp_agt}")
                            else:
                                st.warning("請選取生成品質評判。")"""
    content = content.replace(old_chat_feedback, new_chat_feedback)

    # 4. JSON Decode Error protection
    old_json = """                with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            steps.append(json.loads(line))
            except Exception as e:
                st.warning(f"載入運行軌跡時出錯：{e}")"""
    new_json = """                with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                steps.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                st.warning(f"載入運行軌跡時出錯：{e}")"""
    content = content.replace(old_json, new_json)
    
    # 5. Connection flood protection for Button (Tab 7 heart beat)
    # We need to inject a session state variable
    old_button = """        if st.button("🔌 執行智商庫連線心跳診斷", key="btn_agent_diag", use_container_width=True):"""
    new_button = """        if "diag_running" not in st.session_state:
            st.session_state.diag_running = False
            
        if st.button("🔌 執行智商庫連線心跳診斷", key="btn_agent_diag", use_container_width=True, disabled=st.session_state.diag_running):
            st.session_state.diag_running = True
            st.rerun()
            
        if st.session_state.diag_running:"""
        
    old_button_end = """                    except Exception as ex:
                        st.error(f"❌ 診斷失敗：無法與本地推理服務建立連線。原因：{ex}")"""
    new_button_end = """                    except Exception as ex:
                        st.error(f"❌ 診斷失敗：無法與本地推理服務建立連線。原因：{ex}")
                    finally:
                        st.session_state.diag_running = False
                        st.rerun()"""
                        
    content = content.replace(old_button, new_button)
    content = content.replace(old_button_end, new_button_end)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Patch applied successfully.")

if __name__ == "__main__":
    main()
