# LexMind 官方診斷與測試腳本庫 (Diagnostic & Testing Toolkit)

**【驗收官最高守則：嚴禁角色扮演或憑空瞎掰測試結果！所有除錯與測試，必須無條件優先使用本清單內的官方腳本，禁止重新造輪子！】**

當需要驗證系統狀態、修復 Bug 或是進行單元測試時，請務必直接尋找並執行以下位於 `scripts_v6/` 或根目錄的專用腳本：

## 1. 核心通道與防撞測試 (通道暢通度驗證)
- **`C:\LocalAI_Workstation\test_vertex_adc.py`**：獨立測試 Vertex AI 企業通道與 ADC 憑證是否順暢。**當遇到 LLM 回應超時或憑證報錯時，第一時間跑這個。**
- **`C:\LocalAI_Workstation\scripts_v6\test_duplicate.py`**：壓力測試腳本，用來模擬並驗證 `inflight_guard` (防撞車鎖) 機制是否正常運作。

## 2. 系統清理與健康檢查 (殭屍任務與殘檔清理)
- **`C:\LocalAI_Workstation\scripts_v6\verify_workflow_health.py`**：工作流健康檢查器，掃描並列出是否有卡死的殭屍任務。
- **`C:\LocalAI_Workstation\scripts_v6\clean_half_processed.py` / `clean_half_processed_safe.py`**：安全清理卡在一半、殘缺不全的半成品暫存檔，釋放系統卡死的狀態。

## 3. I/O 錯誤與模組熱修復補丁 (緊急外科手術)
遇到 `pythonw` 導致的 `10106 I/O Error` 或特定模組崩潰時，優先執行現有修補補丁：
- **`C:\LocalAI_Workstation\scripts_v6\patch_fix3_surgical.py`**：外科手術式修補腳本（專門精準修改 `run_workflow.py` 的標準輸出）。
- **`C:\LocalAI_Workstation\scripts_v6\patch_fix2b_reconfigure_safe.py`**：安全設定標準輸出的腳本（強制寫入 UTF-8 以避免報錯）。
- **`C:\LocalAI_Workstation\scripts_v6\patch_markdown.py` / `restore_markdown.py`**：針對 `markdown_formatter.py` 進行熱修復與備份還原。

**💡 給未來 AI 的自我警惕：**
若使用者要求測試，請直接以 `python [腳本名稱]` 執行上述對應工具，並將真實的終端機輸出回報給使用者。絕對不准用「我已經幫您在腦海中跑過了」等敷衍話術！

## 4. 歷史測試指令與環境配置標準 (Testing Methodologies)
前人 AI 留下來的除錯經驗與指令下達標準，所有後續測試皆須依循此配置：

- **啟動背景測試的最佳實踐 (取代會當機的 pythonw)**：
  使用 PowerShell 的 `Start-Process` 並強制重新導向 I/O，以防 `10106` 崩潰：
  ```powershell
  Start-Process python -ArgumentList "scripts_v6\run_workflow.py" -RedirectStandardOutput A:\logs_v6\run_workflow_stdout.log -RedirectStandardError A:\logs_v6\run_workflow_stderr.log -WindowStyle Hidden
  ```
- **測試前的環境變數注入**：
  在進行任何單元測試或指令碼執行前，必須先在 PowerShell 終端機宣告以下環境變數，以確保編碼與路徑正確：
  ```powershell
  $env:LEXMIND_ENV="v6_canary"
  $env:PYTHONUTF8="1"
  $env:PYTHONIOENCODING="utf-8"
  $env:LEXMIND_WORKDIR="C:\LocalAI_Workstation"
  ```
- **清空殭屍進程 (Nuclear Option)**：
  在重新測試前，務必先砍乾淨所有殘留的 Python 進程，避免 Port 佔用或鎖死：
  ```powershell
  taskkill /F /IM python.exe /T 2>&1 | Out-Null
  taskkill /F /IM pythonw.exe /T 2>&1 | Out-Null
  ```
- **即時監控日誌**：
  測試啟動後，不應瞎猜，必須即時監聽日誌輸出：
  ```powershell
  Get-Content A:\logs_v6\workflow.log -Tail 30 -Wait -Encoding UTF8
  ```

## 5. 專家進階除錯技巧 (Advanced Debugging Techniques)
來自 Perplexity / Anthropic 專家的除錯精華，用於深度排錯與狀態重置：

- **驗證程式碼完整性 (SHA256)**：
  在除錯前，使用雜湊值確認檔案是否被其他 AI 偷偷竄改：
  ```powershell
  Get-FileHash scripts_v6\*.py -Algorithm SHA256
  ```
- **強制修復 UTF-8 BOM 編碼 (防禦 CP950 崩潰)**：
  若 Python 檔案缺少 BOM 導致編碼炸彈，可用此 PowerShell 腳本強制補齊：
  ```powershell
  cd C:\LocalAI_Workstation\scripts_v6
  foreach ($f in "run_workflow.py","stt_runner.py") {
      $b = [System.IO.File]::ReadAllBytes("$PWD\$f")
      if (-not ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)) {
          [System.IO.File]::WriteAllBytes("$PWD\$f", [byte[]](0xEF,0xBB,0xBF) + $b)
      }
  }
  ```
- **手動重置任務狀態 (Replay Task)**：
  為了重複測試特定工作流階段，可以直接用 PowerShell 修改 Manifest JSON 狀態：
  ```powershell
  $id = "task_xxx"
  $m = Get-Content "A:\manifests_v6\$id.json" -Raw -Encoding UTF8 | ConvertFrom-Json
  $m.status = "transcribed"
  $m | ConvertTo-Json -Depth 10 | Set-Content "A:\manifests_v6\$id.json" -Encoding UTF8
  ```
- **工作流單次擊發測試 (One-Shot 模式)**：
  不要讓 workflow 進入無限迴圈，使用 `--one-shot` 跑一次就停，方便檢查 Log：
  ```powershell
  python scripts_v6\run_workflow.py --one-shot
  ```
- **精準篩選特定任務的 Log 軌跡**：
  使用 `Select-String` 從龐大的日誌中抽出特定任務 ID 的執行紀錄：
  ```powershell
  Select-String -Path A:\logs_v6\workflow.log -Pattern "task_xxx" | Select-Object -Last 15
  ```
- **精準獵殺特定 Python 進程 (Graceful Kill)**：
  若只想砍掉特定的 workflow 腳本而非全殺 (避免影響其他任務)，可使用 WMI 查詢 `CommandLine`：
  ```powershell
  Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run_workflow.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  ```
- **監控 Python 進程 CPU 使用率**：
  若懷疑某階段 (如 Formatter) 陷入無限迴圈或資源暴衝，可隨時檢查：
  ```powershell
  Get-Process | Where-Object { $_.ProcessName -eq "python" } | Select-Object Id, CPU
  ```
- **強制跳過/完結特定任務階段 (Skip Stage)**：
  如果某個非致命階段不斷報錯卡住管線，可手動修改 JSON 強制過關：
  ```powershell
  $p = "A:\manifests_v6\task_xxx.json"
  $m = Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json
  $m.status = "completed"
  $m.steps.formatter = "completed"
  $m | ConvertTo-Json -Depth 10 | Set-Content $p -Encoding UTF8
  ```

### 5.3 進階病灶診斷與管線修復操作 (前輩 AI 實戰除錯工作流)

以下操作與邏輯完全繼承自過往成功除錯的 AI 專家。未來任何接手的 AI 必須「完全照著這個邏輯查」，嚴禁自行發明新指令或跳過步驟。

#### 工作流 1：任務狀態驗屍與空殼隔離 (Autopsy & Quarantine)
**情境**：系統中出現一直報錯的 `unknown_task` 或卡在 `needs_review` 無法推進的幽靈任務。
**AI 的邏輯與操作**：
1. **找出哪些任務卡在 needs_review**：
   ```powershell
   Get-ChildItem A:\manifests_v6\task_*.json | Where-Object { $_.Name -notlike "*_chunks.json" } | ForEach-Object {
       $m = Get-Content $_.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
       if ($m.status -eq "needs_review") { $_.Name }
   }
   ```
2. **驗屍 (印出關鍵欄位判斷可否搶救)**：
   ```powershell
   $(foreach ($f in "task_xxx", "task_yyy") {
       $m = Get-Content "A:\manifests_v6\$f.json" -Raw -Encoding UTF8 | ConvertFrom-Json
       [PSCustomObject]@{
           File       = $f
           TaskId     = $m.task_id
           Source     = $m.source_name
           SourcePath = $m.source_path
           HasSteps   = [bool]$m.steps
       }
   }) | Format-Table -AutoSize -Wrap
   ```
   *前輩的判讀規則*：「有 source_path、只缺 task_id/source_name → 可修復。全空殼或無路徑 → 不可救，隔離不刪除（保留證據）。」
3. **將不可救的殘骸打入隔離區**：
   ```powershell
   New-Item -ItemType Directory -Force A:\manifests_v6\_quarantine | Out-Null
   Move-Item A:\manifests_v6\task_empty*.json A:\manifests_v6\_quarantine\
   ```

#### 工作流 2：「裝死還是真死？」三步活體檢驗法
**情境**：管線在 STT_Runner 或 Formatter 停滯超過 10 分鐘，不確定是否死鎖。
**AI 的邏輯與操作**：不要急著砍進程，先用指令確認底層是否還在工作。
```powershell
# 1. 蒸餾是否還在產出（隔一兩分鐘跑兩次，數字有增加 = 活著在磨）
Get-ChildItem A:\distillation_dataset\*_distill.json | Measure-Object | Select-Object Count

# 2. 主日誌的最新動靜（formatter 內部訊息、蒸餾完成訊息都在這）
Get-Content A:\logs_v6\workflow.log -Tail 10

# 3. GPU 有沒有在忙（Whisper 蒸餾吃 GPU）
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv
```
*前輩的判讀規則*：「數量在增加或 GPU 在忙 → 一切正常，Whisper 本來就是慢活。workflow.log 有訊息 → 活著只是慢跑。若三條全部靜止達 15 分鐘，才判定為卡死，執行 Graceful Kill。」

#### 工作流 3：Graceful Kill 與單次擊發 (One-Shot) 重啟
**情境**：確定卡死，需要安全重啟特定工作流。
**AI 的邏輯與操作**：
1. **精準獵殺**：
   ```powershell
   Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*run_workflow.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
2. **單次擊發重啟 (排除無限迴圈干擾)**：
   ```powershell
   cd C:\LocalAI_Workstation
   python scripts_v6\run_workflow.py --one-shot
   ```

#### 工作流 4：特定任務局部狀態重置 (Replay Task)
**情境**：某幾個任務因為已知原因 (如 429 錯誤) 失敗，只需要讓它們退回上一步重試。
**AI 的邏輯與操作**：
```powershell
cd A:\manifests_v6
foreach ($id in "task_xxx", "task_yyy") {
    $m = Get-Content "$id.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($m.status -eq "failed") {
        $m.status = "transcribed"
        $m | ConvertTo-Json -Depth 10 | Set-Content "$id.json" -Encoding UTF8
        Write-Host "[RESET] $id -> transcribed (merge 待重跑)"
    }
}
```

#### 工作流 5：收官確認 (六任務狀態表與成品清單)
**情境**：任務重跑結束，需要一次性確認所有重點任務的最終完成度。
**AI 的邏輯與操作**：
```powershell
# 1. 重點任務最終狀態表
$(foreach ($id in "task_A", "task_B") {
    $m = Get-Content "A:\manifests_v6\$id.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    [PSCustomObject]@{ Task=$id; Status=$m.status; STT=$m.steps.stt; Merge=$m.steps.merge; Fmt=$m.steps.formatter }
}) | Format-Table -AutoSize

# 2. 成品清單檢查
Get-ChildItem A:\processed_md\*.md | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name, LastWriteTime
```


