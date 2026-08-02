# C:/LocalAI_Workstation/scripts/case_manager.py
# -*- coding: utf-8 -*-
import json
import os

CASES_FILE = "C:/LocalAI_Workstation/cases_data.json"

def load_cases():
    """載入本地個案檔案，若無則生成預設模擬測試資料"""
    if not os.path.exists(CASES_FILE):
        initial_data = {
            "CASE-2026-001": {
                "title": "林ＯＯ違反證券交易法案",
                "current_stage": "一審準備程序",
                "stakeholders": ["林ＯＯ", "陳ＯＯ"],
                "dialog_history": [
                    {"role": "user", "text": "請幫我分析起訴書要點"},
                    {"role": "agent", "text": "起訴書核心指指控在於涉嫌內線交易，建議爭執非內部人身分。"}
                ],
                "documents_and_evidence": [
                    {"id": "doc_1", "name": "檢察官起訴書電子檔.pdf", "comment": "已詳閱"},
                    {"id": "doc_2", "name": "銀行帳戶交易明細表 (證物一)", "comment": "缺乏直接故意證明力"}
                ],
                "precedents": [
                    {"id": "p_1", "name": "最高法院 108 年度台上字第 432 號刑事判決", "comment": "非常契合本案時點爭點"}
                ],
                "claims": [
                    {"id": "c_1", "name": "被告非屬證交法第157之1條所規範之內部人", "comment": "主攻防線"},
                    {"id": "c_2", "name": "交易行為早於重大消息成立之前", "comment": "備位主張"}
                ]
            }
        }
        save_cases(initial_data)
        return initial_data
    
    try:
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARNING] Failed to load cases: {e}")
        return {}

def save_cases(data):
    """使用者點評時，瞬間將所有反饋與對話寫入本地 JSON 持久化"""
    try:
        with open(CASES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[ERROR] Failed to save cases: {e}")
