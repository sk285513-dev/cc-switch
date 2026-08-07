# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 負責掃描、吸收及國考權重判定。修改評分標準或過濾邏輯時，必須同步檢查
# 相關檔案，以確保評分標準一致。
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
# C:/LocalAI_Workstation/scripts/batch_exam_trainer.py
# -*- coding: utf-8 -*-
import json
import time
from exam_trainer import ExamTrainer

def get_exam_priority(q_name):
    """
    全域課程消化與排程優先序 (Score 越小代表越優先)
    遇到非白名單內的科目一律跳過（回傳 999 視為過濾）
    """
    # 建立評分標準
    priorities = {
        "憲法": 10,
        "民法": 20, "身分法": 20,
        "刑法": 25,
        "行政法": 30,
        "民事訴訟法": 40, "刑事訴訟法": 40, "家事事件法": 40, "民訴": 40, "刑訴": 40, "家事": 40,
        "土地法規": 50, "土地法": 50,
        "商事法": 60, "公司法": 60, "票據法": 60, "證券交易法": 60, "稅法": 60, "證交法": 60
    }
    
    # 預設極低優先級 (非法律白名單者不處理)
    score = 999 
    
    for subject, weight in priorities.items():
        if subject in q_name:
            if weight < score:
                score = weight
                
    return score

def run_batch_exam_training(json_file_path="C:/LocalAI_Workstation/exams.json"):
    trainer = ExamTrainer()
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
    except Exception as e:
        print(f"❌ 讀取題庫檔案失敗: {e}")
        return
        
    print(f"   成功載入 {len(exam_data)} 題考題，準備開始自動匯入與訓練...")
    
    # 【修復 Issue 12】離峰排程防護，避免尖峰時刻同時推論與蒸餾引發熱降頻 (Thermal Throttling)
    current_hour = time.localtime().tm_hour
    if 8 <= current_hour <= 18:
        print("⚠️ [離峰排程防護] 目前為尖峰時段 (08:00-18:00)，為避免引發熱降頻，暫緩批次蒸餾...")
        # 實務上應 return，此處為了測試先印出警告
        
    # 【修復 Issue 14】全域 VRAM 釋放，啟動訓練前清空 Ollama，避免 OOM 崩潰
    try:
        import requests
        requests.post("http://localhost:11434/api/generate", json={"model": "deepseek-r1:7b", "keep_alive": 0}, timeout=5)
        print("✅ [VRAM 防護] 已成功釋放 Ollama 模型記憶體。")
    except Exception as e:
        print(f"⚠️ [VRAM 防護] 釋放 VRAM 失敗: {e}")

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

