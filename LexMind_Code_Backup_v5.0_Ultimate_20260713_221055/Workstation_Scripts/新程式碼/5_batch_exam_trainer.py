# C:/LocalAI_Workstation/scripts/batch_exam_trainer.py
# -*- coding: utf-8 -*-
import json
import time
from scripts.exam_trainer import ExamTrainer

def run_batch_exam_training(json_file_path="C:/LocalAI_Workstation/exams.json"):
    trainer = ExamTrainer()
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
    except Exception as e:
        print(f"❌ 讀取題庫檔案失敗: {e}")
        return
        
    print(f"   成功載入 {len(exam_data)} 題考題，準備開始自動匯入與訓練...")
    for idx, item in enumerate(exam_data):
        q_name = item.get("question_name", f"未命名題庫_{idx+1}")
        question = item.get("question", "")
        model_answer = item.get("model_answer", "")
        
        if not question or not model_answer: 
            continue
            
        print(f"\n⏳ 正在處理 ({idx+1}/{len(exam_data)}): {q_name}")
        trainer.train_single_exam(question=question, model_answer=model_answer, question_name=q_name)
        time.sleep(2) # 緩衝時間，避免連續呼叫 API 造成 GPU 記憶體 (OOM) 溢出
        
    print("\n   所有題庫已批次匯入並完成反思，經驗已全數寫入智商庫！")

if __name__ == '__main__':
    run_batch_exam_training()
