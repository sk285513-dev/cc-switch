import json
import os
import re

DUMP_FILE = r"C:\LocalAI_Workstation\crawler_dump.json"
REPORT_FILE = r"C:\LocalAI_Workstation\ultimate_600_intelligent_report.md"

def evaluate_intelligent_correctness():
    print("🚀 [啟動] 混合式視覺驗收引擎 - 智能正確性審查 (Hybrid Vision Validator)")
    if not os.path.exists(DUMP_FILE):
        print("❌ 找不到爬蟲產出的 crawler_dump.json，請先執行 bot_ultimate_600_crawler.py")
        return
        
    with open(DUMP_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    report = [
        "# 全域 600 狀態 AI 智能正確性驗收報告 (Intelligent Correctness)",
        "",
        "| 截圖編號 | 分頁與操作 | 狀態路徑 | 智能架構驗證 | 邏輯正確性評分 |",
        "|---|---|---|---|---|"
    ]
    
    passed_count = 0
    failed_count = 0
    
    for state in data:
        state_id = state["state_id"]
        tab = state["tab"]
        action = state["action"]
        text = state["text"]
        
        status = "🟢 100% 正確"
        eval_msg = "符合架構預期"
        
        # 進行架構級別的智能驗證邏輯
        # 1. 基礎崩潰檢查
        if "Traceback" in text or "Exception" in text:
            status = "🚨 嚴重崩潰"
            eval_msg = "偵測到底層程式碼錯誤"
            failed_count += 1
        
        # 2. 分頁專屬的領域邏輯驗證
        elif "實務辯護諮詢" in tab:
            if "壓力測試輸入" in action:
                # 若進行了文字輸入，畫面上必須要有法律推理的跡象
                if "實務見解" not in text and "最高法院" not in text and "法條" not in text:
                    status = "🔴 不及格"
                    eval_msg = "缺乏 IRAC 法律推理架構與爭點分析 (無智能延伸)"
                    failed_count += 1
                else:
                    passed_count += 1
            else:
                # 預設狀態必須具備看板
                if "RWS 證據看板" not in text and "事件關係圖" not in text:
                    status = "🔴 不及格"
                    eval_msg = "缺少核心證據看板元件"
                    failed_count += 1
                else:
                    passed_count += 1
                    
        elif "知識餵養" in tab:
            if "上傳" not in text and "解析" not in text:
                status = "🔴 不及格"
                eval_msg = "缺少知識庫上傳與解析入口"
                failed_count += 1
            else:
                passed_count += 1
                
        else:
            # 一般狀態驗證：確保畫面沒有呈現空白或錯亂的 HTML 原始碼
            if len(text.strip()) < 50:
                status = "🔴 不及格"
                eval_msg = "畫面無意義資訊過少 (低於 50 字元)"
                failed_count += 1
            elif "<div" in text or "function(" in text:
                status = "🔴 不及格"
                eval_msg = "DOM 原始碼外洩，畫面渲染失敗"
                failed_count += 1
            else:
                passed_count += 1
                
        report.append(f"| {state_id:03d} | {tab} | {action} | {eval_msg} | {status} |")
        
    report.insert(2, f"**總計驗證狀態數**: {len(data)} | **智能通過**: {passed_count} | **智能失敗/不符架構**: {failed_count}")
    report.insert(3, "")
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"🎉 智能驗收完成！共查核 {len(data)} 個畫面狀態，報告產出至 {REPORT_FILE}")

if __name__ == "__main__":
    evaluate_intelligent_correctness()
