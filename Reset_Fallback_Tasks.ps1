$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== 正在掃描並重置 Fallback 半成品任務 ===" -ForegroundColor Cyan

# 1. 精確匹配：使用 UTF8 編碼讀取，避免漏抓中文
$fallbackFiles = Select-String -Path A:\chunks\task_*\merged_summary.txt -Pattern "(摘要生成遇限失敗)|(無 API 金鑰跳過)" -Encoding UTF8 | Select-Object -ExpandProperty Path -Unique

$count = 0
$taskIds = @()

foreach ($file in $fallbackFiles) {
    $taskId = (Get-Item $file).Directory.Name
    $taskIds += $taskId
}

if ($taskIds.Count -eq 0) {
    Write-Host "恭喜！沒有發現需要重置的 Fallback 任務。" -ForegroundColor Green
    exit
}

# 2. 將任務清單傳給 Python 進行最安全的 JSON 寫入 (避免 PowerShell ConvertTo-Json 的 Unicode 亂碼問題)
$pyScript = @"
import json
import os
import sys

task_ids = sys.argv[1].split(',')
count = 0

for tid in task_ids:
    manifest_path = f'A:/manifests/{tid}.json'
    if not os.path.exists(manifest_path):
        continue
        
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 判斷是否為已合併或已完成狀態
        status = data.get('status', '')
        merge_step = data.get('steps', {}).get('merge', '')
        
        if status in ['completed', 'merged'] or merge_step == 'completed':
            data['status'] = 'processing'
            if 'steps' not in data:
                data['steps'] = {}
            data['steps']['merge'] = 'pending'
            data['steps']['formatter'] = 'pending'
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f'成功重置: {data.get("file_info", {}).get("course_title", tid)}')
            count += 1
    except Exception as e:
        print(f'處理 {tid} 時發生錯誤: {e}')

print(f'\n[Summary] 共計退回 {count} 堂課程至待合併佇列。')
"@

# 將陣列轉為逗號分隔字串傳遞
$taskIdsStr = $taskIds -join ','
Write-Host "開始調用 Python 安全修改 JSON 檔案..." -ForegroundColor Yellow
python -c $pyScript $taskIdsStr

Write-Host "重置完成！系統背景的 PipelineDaemon 會在數分鐘內自動發現這些任務，並派發給 AI 重新精校。" -ForegroundColor Green
