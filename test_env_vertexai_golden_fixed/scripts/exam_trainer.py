import os
import requests
import chromadb
from pathlib import Path

class ExamTrainer:
    def __init__(self, db_path=None):
        from scripts.agent_core_pro import LocalLegalAgent
        # 透過 LocalLegalAgent 單例連線，確保與主對話庫同源且避免 Windows SQLite 死結
        self.agent = LocalLegalAgent(db_path=db_path)
        self.intel_coll = self.agent.intel_coll
        self.llm_url = 'http://localhost:11434/api/chat'
        self.embed_url = 'http://localhost:11434/api/embeddings'

    def _get_embedding(self, text):
        return self.agent._get_embedding(text)

    def call_ai(self, prompt, role="expert"):
        payload = {
            "model": "deepseek-r1:7b",
            "messages": [
                {"role": "system", "content": f"你是一位台灣現役最頂尖的{role}。"},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.2}
        }
        try:
            res = requests.post(self.llm_url, json=payload, timeout=90)
            return res.json()['message']['content']
        except Exception as e:
            return f"Error: {e}"

    def train_single_exam(self, question, model_answer, question_name="未命名題庫"):
        print(f"📝 項目【{question_name}】：正在調用 RWS 檢索關聯法理中...")
        
        # 1. 執行 RAG 混合檢索，取得考生作答背景
        evidence = self.agent.search_hybrid(question, category_hint="國考")
        context_str = "\n".join([f"[{i+1}] {e['text']} (RWS 綜效得分: {e['score']})" for i, e in enumerate(evidence)])
        
        print(f"📝 項目【{question_name}】：正在模擬考場依據 RAG 檢索擬答中...")
        exam_prompt = (
            "請針對以下題目，以嚴密的台灣司法官答題三段論法擬寫高分擬答。\n"
            "答題時應特別參考並涵攝以下經由 RWS 系統篩選、與本題高度相關的法規、裁判或先前錯題反思筆記：\n\n"
            f"{context_str}\n\n"
            f"【題目】：\n{question}"
        )
        ai_solution = self.call_ai(exam_prompt, role="司法官考生")
        
        print("🧐 正在提交給嚴苛的閱卷教授進行高分對照與差額檢討...")
        reflection_prompt = (
            f"請比對以下【考生自擬回答】與【學術界高分參考範本】，"
            f"找出考生忽略 of 法律爭點、過時或錯誤引用的條文、大法官釋字或憲判字，並指出推理盲點。\n\n"
            f"【考試題目】：\n{question}\n\n"
            f"【考生自擬回答】：\n{ai_solution}\n\n"
            f"【高分參考範本】：\n{model_answer}\n\n"
            "請給出：\n"
            "1. 答題漏洞缺陷（簡要）：\n"
            "2. 司法官高分必備爭點筆記（供長期儲存演化使用）："
        )
        critique = self.call_ai(reflection_prompt, role="閱卷處法學教授")
        
        # 將教授指出的精良邏輯與錯題本納入智商庫
        lesson_text = (
            f"【司法官歷屆考題深度反思：{question_name}】\n"
            f"原始題目：{question[:100]}...\n"
            f"教授批改盲點與修正筆記：\n{critique}"
        )
        
        vec = self._get_embedding(lesson_text)
        if vec:
            self.intel_coll.add(
                ids=[f"exam_lesson_{question_name}_{os.urandom(3).hex()}"],
                embeddings=[vec],
                documents=[lesson_text],
                metadatas=[{"source": question_name, "type": "exam_lesson"}]
            )
            print("✅ 檢討經驗已成功固化在 legal_intelligence_vault (智商庫)！AI 已完成一輪智力演進。")
            
        return ai_solution, critique, evidence

    def run_all_exams(self, folder_path):
        folder = Path(folder_path)
        if not folder.exists():
            return
        
        q_files = sorted(list(folder.glob("question_*.txt")))
        for q_file in q_files:
            a_file = Path(str(q_file).replace("question_", "answer_"))
            if a_file.exists():
                with open(q_file, 'r', encoding='utf-8', errors='ignore') as f: q_text = f.read()
                with open(a_file, 'r', encoding='utf-8', errors='ignore') as f: a_text = f.read()
                self.train_single_exam(q_text, a_text, question_name=q_file.stem)