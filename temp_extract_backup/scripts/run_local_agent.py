# -*- coding: utf-8 -*-
import sys
import os
from colorama import init, Fore, Style

# 確保編碼正確
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

init(autoreset=True)

from agent_core_pro import LocalLegalAgent

def print_banner():
    print(Fore.CYAN + Style.BRIGHT + "="*60)
    print(Fore.CYAN + Style.BRIGHT + " LexMind-Omni Local RAG Agent (Powered by Ollama)")
    print(Fore.CYAN + Style.BRIGHT + "="*60)
    print(Fore.YELLOW + "使用模型: deepseek-r1:7b | 嵌入模型: nomic-embed-text")
    print("這是一個完全離線運行的法律諮詢機器人。輸入 'quit' 離開。\n")

def main():
    print_banner()
    
    print(Fore.GREEN + "[系統] 正在載入 ChromaDB 向量庫與 Ollama 引擎...")
    try:
        agent = LocalLegalAgent(context_role="lawyer")
        print(Fore.GREEN + "[系統] 載入成功！請開始提問。\n")
    except Exception as e:
        print(Fore.RED + f"[錯誤] 載入失敗: {e}")
        print(Fore.YELLOW + "請確保 Ollama 正在運行，並且擁有 nomic-embed-text 模型。")
        sys.exit(1)

    while True:
        try:
            user_input = input(Fore.WHITE + Style.BRIGHT + "\n[您]: ")
            if user_input.strip().lower() in ['quit', 'exit', 'q']:
                print(Fore.CYAN + "感謝使用，再見！")
                break
                
            if not user_input.strip():
                continue

            print(Fore.MAGENTA + "\n[Ollama RAG Agent] 思考中...")
            
            # 使用 agent_core_pro.py 的標準接口
            reply, evidence, mermaid = agent.chat_with_rws(user_input)
            
            print(Fore.CYAN + "\n[回答]:\n" + "-"*40)
            print(reply)
            print("-" * 40)
            
            if evidence:
                print(Fore.YELLOW + "\n[參考法條/判例 (RWS 排序)]:")
                for i, ev in enumerate(evidence, 1):
                    score = ev.get('score', 0)
                    src = ev.get('source', '未知')
                    print(f" {i}. [{src}] 權重: {score:.2f}")
            
        except KeyboardInterrupt:
            print(Fore.CYAN + "\n感謝使用，再見！")
            break
        except Exception as e:
            print(Fore.RED + f"\n[執行錯誤]: {e}")

if __name__ == "__main__":
    main()
