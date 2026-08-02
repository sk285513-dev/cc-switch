# C:/LocalAI_Workstation/scripts/batch_exam_trainer.py
# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 依賴 national_exam_rules.py 作為 SSOT。修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
# -*- coding: utf-8 -*-
import json
import time
from scripts.exam_trainer import ExamTrainer
from national_exam_rules import get_exam_score

def get_exam_priority(q_name):
    """
    全域課程消化與排程優先序 (Score 越小代表越優先)
    遇到非白名單內的科目一律跳過（回傳 999 視為過濾）
    """
    return get_exam_score(q_name)

def run_batch_exam_training(json_file_path="C:/LocalAI_Workstation/exams.json"):
    trainer = ExamTrainer()
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
    except Exception as e:
        print(f"❌ 讀取題庫檔案失敗: {e}")
        return
        
    print(f"   成功載入 {len(exam_data)} 題考題，準備開始自動匯入與訓練...")
    
    # 進行國考科目權重排序與過濾
    valid_exams = []
    for item in exam_data:
        q_name = item.get("question_name", "")
        score = get_exam_priority(q_name)
        if score < 999: # 僅保留白名單內的專業科目
            valid_exams.append((score, item))
            
    # 依據 score 排序 (越小越優先)
    valid_exams.sort(key=lambda x: x[0])
    
    print(f"   經過國考核心過濾，共保留 {len(valid_exams)} 題專業考題準備進行訓練。")
    
    for idx, (score, item) in enumerate(valid_exams):
        q_name = item.get("question_name", f"未命名題庫_{idx+1}")
        question = item.get("question", "")
        model_answer = item.get("model_answer", "")
        
        if not question or not model_answer: 
            continue
            
        print(f"\n⏳ 正在處理 ({idx+1}/{len(valid_exams)}) [優先級 {score}]: {q_name}")
        trainer.train_single_exam(question=question, model_answer=model_answer, question_name=q_name)
        time.sleep(2) # 緩衝時間，避免連續呼叫 API 造成 GPU 記憶體 (OOM) 溢出
        
    print("\n   所有題庫已批次匯入並完成反思，經驗已全數寫入智商庫！")

if __name__ == '__main__':
    run_batch_exam_training()
