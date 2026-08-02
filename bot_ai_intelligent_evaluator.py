import json
import os
import time
import re
import urllib.request
import urllib.error
import yaml
import google.generativeai as genai

DUMP_FILE = r"C:\LocalAI_Workstation\crawler_dump_real.json"
CHECKPOINT_FILE = r"C:\LocalAI_Workstation\ai_eval_checkpoint.json"
REPORT_FILE = r"C:\LocalAI_Workstation\ultimate_600_ai_report.md"
KEYS_YAML = r"C:\LocalAI_Workstation\config\keys.yaml"

# 死 key 第一次發現時就写回 yaml，下次不再嘗試
PERMANENTLY_DEAD_CODES = {400, 401, 403}


def _is_key_alive(val: str) -> bool:
    """發一個最輕量的 /v1beta/models?key= 請求驗證金鑰是否有效。
    HTTP 200 或 429 表示金鑰有效；HTTP 400/401/403 表示金鑰永久失效。
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={val}"
    try:
        req = urllib.request.Request(url)
        urllib.request.urlopen(req, timeout=8)
        return True  # 200 OK
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return True  # 配額耗盡但金鑰有效
        if e.code in PERMANENTLY_DEAD_CODES:
            return False  # 400/401/403 永久失效
        return True  # 其他錯誤視為有效（不要因網路問題誤殺金鑰）
    except Exception:
        return True  # 網路超時等未知錯誤，視為有效


def _mark_dead_in_yaml(val: str):
    """將 keys.yaml 中對應 key 的 active 設為 false。"""
    try:
        with open(KEYS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for item in data.get("keys", []):
            if isinstance(item, dict) and item.get("value") == val and item.get("active", True):
                item["active"] = False
                old_notes = item.get("notes", "")
                if "停權" not in old_notes:
                    item["notes"] = (old_notes + " | 🔴 停權/無效 (401) - Evaluator 驗證自動標記").strip(" |")
                break
        with open(KEYS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    except Exception as e:
        print(f"⚠️ 回寫 keys.yaml 失敗: {e}")


def load_api_keys():
    """讀取 keys.yaml，回傳通過即時輕量驗證的 active 金鑰字串 list"""
    try:
        with open(KEYS_YAML, "r", encoding="utf-8-sig") as f:
            data = yaml.safe_load(f)
        raw = data.get("keys", [])
        result = []
        dead_count = 0
        for item in raw:
            if isinstance(item, dict):
                if not item.get("active", True):
                    continue  # 跳過已知失效
                val = item.get("value", "")
                if not val:
                    continue
                if not _is_key_alive(val):
                    print(f"❌ 金鑰 {val[:20]}... 驗證失敗 (400/401/403)，自動標記 inactive")
                    _mark_dead_in_yaml(val)
                    dead_count += 1
                    continue
                result.append(val)
            elif isinstance(item, str):
                val = item.strip()
                if val and _is_key_alive(val):
                    result.append(val)
        if dead_count > 0:
            print(f"🛁 自動清理了 {dead_count} 把永久失效金鑰並对應標記 keys.yaml active=false")
        return [k for k in result if k]
    except Exception as e:
        print(f"⚠️ 無法讀取 keys.yaml: {e}")
        return []

def get_ai_evaluation(model, state_id, dom_text, crash_detected):
    # 若爬蟲層已標記崩潰，直接判定 fail 不浪費 API
    if crash_detected:
        return {"passed": False, "reason": "爬蟲層已標記崩潰"}

    # 由 state_id 解析分頁與操作名稱
    parts = state_id.split("_", 1)
    tab_name = parts[0] if parts else state_id
    action_name = parts[1] if len(parts) > 1 else "Unknown"

    prompt = f"""
    你現在是一位嚴格的台灣法律系統架構驗收員。
    這是一個名叫 LexMind 的專業法律實務 AI 系統的畫面文字。
    
    【测試編號】：{state_id}
    【分頁】：{tab_name}
    【操作】：{action_name}
    【畫面文字擷取】：
    {dom_text[:1500]}
    
    請依據以下架構標準驗收：
    1. 如果畫面出現 Traceback, Exception 等系統崩潰字眼，一律判定 failed。
    2. 如果在「實務辯護諮詢」中進行輸入，畫面必須產出含有法律推理的文字（如法條、爭點、實務見解）。
    3. 沒有意義的亂碼或不完整的 HTML DOM 結構判定為 failed。
    
    請以 JSON 格式回傳，格式：
    {{"passed": true 或 false, "reason": "你的判斷理由(簡潥10個字內)"}}
    """
    resp = model.generate_content(prompt)
    raw_text = resp.text
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {"passed": False, "reason": "AI 解析失敗"}

def run_ai_evaluator():
    print("🚀 [啟動] 真．AI 智能裁判引擎 (Adversarial LLM Evaluator)")
    
    if not os.path.exists(DUMP_FILE):
        print("❌ 找不到 crawler_dump.json，請等待爬蟲完成 600 狀態。")
        return
        
    with open(DUMP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    evaluated = {}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            evaluated = json.load(f)
            
    keys = load_api_keys()
    key_idx = 0
    if keys:
        genai.configure(api_key=keys[key_idx])
    else:
        print("⚠️ 警告：沒有找到 API Keys，但我們仍嘗試依賴環境變數運行。")
        
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    total = len(data)
    current = len(evaluated)
    print(f"📦 總計 {total} 個截圖狀態，已完成 {current} 頁 OCR 與智能審查。")
    print("⏳ 開始分階段上傳與驗證...")
    
    for state in data:
        s_id = str(state["state_id"])
        if s_id in evaluated:
            continue

        print(f"➡️ 正在上傳狀態 {s_id} 進行 AI 智能審查...")
        # 每個 state 最多重試 len(keys) 次（換一把金鑰就重試，不跳過）
        success = False
        for attempt in range(max(1, len(keys))):
            try:
                result = get_ai_evaluation(model, state["state_id"], state.get("dom_text", ""), state.get("crash_detected", False))
                evaluated[s_id] = {
                    "tab": state["state_id"].split("_")[0],
                    "action": "_".join(state["state_id"].split("_")[1:]),
                    "passed": result["passed"],
                    "reason": result["reason"]
                }
                # 每成功一個就存檔 (Checkpoint 防斷線)
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    json.dump(evaluated, f, ensure_ascii=False, indent=2)
                time.sleep(2)  # 避免 Rate Limit (429)
                success = True
                break
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "exhausted" in err or "quota" in err:
                    print(f"💥 觸發 API Quota 限制！(目前已完成 {len(evaluated)}/{total})")
                    key_idx += 1
                    if key_idx < len(keys):
                        print(f"🔄 自動輪替至下一把金鑰 (Key {key_idx+1})，重試同一 state...")
                        genai.configure(api_key=keys[key_idx])
                        model = genai.GenerativeModel("gemini-2.5-flash")
                        time.sleep(5)
                        # 繼續 for attempt 迴圈，重試當前 state
                    else:
                        print("🚨 所有金鑰均耗盡！儲存進度後退出。")
                        break
                else:
                    print(f"⚠️ 發生未知錯誤: {e}")
                    break
        if not success and key_idx >= len(keys):
            break  # 金鑰全耗盡，結束整個迴圈
                
    # 產出最終報表
    report = [
        "# 全域 600 狀態 真・AI 智能正確性驗收報告",
        "",
        f"**總狀態數**: {total} | **目前完成審查**: {len(evaluated)}",
        "",
        "| 截圖編號 | 分頁與操作 | 智能審核結果 | 裁判理由 |",
        "|---|---|---|---|"
    ]
    
    for s_id, res in evaluated.items():
        status_icon = "🟢 100% 吻合設計架構" if res["passed"] else "🔴 架構邏輯失效"
        report.append(f"| {s_id} | {res['tab']} - {res['action']} | {status_icon} | {res['reason']} |")
        
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"\n🎉 本階段智能驗收結束！報表已更新至 {REPORT_FILE}")
    if len(evaluated) < total:
        print(f"⚠️ 尚有 {total - len(evaluated)} 頁未驗證，請等待 Quota 恢復後重新執行。")

if __name__ == "__main__":
    run_ai_evaluator()
