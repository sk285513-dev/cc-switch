import sys, json, os
sys.path.insert(0, 'scripts')

# 合成測試資料（模擬 Whisper 原始 vs Gemini 精校）
raw = "好大家好那今天又是我們投地登記的第一堂課那個我們今天要講的是嗯消滅實效的問題然後地政治的角色"
clean = "好，大家好。今天是我們土地登記的第一堂課，我們今天要講的是消滅時效的問題，以及地政士的角色。"
chunks_data = [
    {"transcript": raw, "cleaned": clean},
    {"transcript": "那個各論部分格論我們要看", "cleaned": "各論部分，我們要看。"},
]

from markdown_formatter import save_distillation_pair
save_distillation_pair(
    'test_task_001',
    '[test_course]_lesson1.mp4',
    'civil_law',
    raw, clean, chunks_data
)

out = 'A:/distillation_data/legal_distillation_pairs.jsonl'
lines = open(out, encoding='utf-8').readlines()
print("Training pairs written:", len(lines))
for i, line in enumerate(lines):
    d = json.loads(line)
    print(f"\n--- Pair {i+1} [{d['granularity']}] ---")
    print("CoT:", d['cot'])
    print("Input len:", len(d['input']))
    print("Output len:", len(d['output']))
