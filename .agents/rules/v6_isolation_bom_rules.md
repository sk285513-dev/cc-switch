# V6.1 獨立版架構與 UTF-8 BOM 防護鐵律 (V6_Isolation_and_BOM_Rules)

> [!CAUTION]
> **血淚教訓與核心痛點 (2026-08-07)**
> 這兩天專案經歷了災難性的循環，所有 AI 必須將此銘記在心：
> 1. **Git 還原會洗掉 BOM**：Windows 的 Git 在 checkout 或 reset 時，預設會把 PowerShell 續命用的 UTF-8 BOM 給洗掉，導致中文字元亂碼、雙擊閃退。
> 2. **AI 的 Launch_Isolated 幻覺**：過去 AI 自作聰明發明的 `Launch_Isolated.py` 與 `pythonw.exe` 是引發視窗消失與死鎖的錯誤幻覺！系統真正的架構是「獨立的 `python.exe` 原版架構（搭配 Start-Process powershell）」。

## 核心禁忌與最高指導原則

1. **一鍵啟動腳本必須維持「獨立的 python.exe 原版架構」**
   - 我們的系統一鍵啟動腳本必須維持「獨立的 `python.exe` 原版架構（搭配 `Start-Process powershell`）」，這才是解決 10106 死鎖的正確方式。
   - 過去 AI 自作聰明發明的 `Launch_Isolated.py` 與 `pythonw.exe` 是錯誤幻覺，會引發視窗消失與死鎖。
   - **絕對禁止**未來任何 Agent 再次使用 `Launch_Isolated.py` 或 `pythonw.exe`！

2. **嚴禁破壞 UTF-8 BOM 編碼**
   - Windows PowerShell 5.1 需要 UTF-8 BOM 才能正確解析包含中文字元的腳本，否則會引發嚴重亂碼與進程崩潰。
   - 為避免 Git 剝除 Windows 必要的 UTF-8 BOM 導致亂碼，未來在執行任何 git 復原或寫入操作前，都必須嚴格遵守 `README_DEVEL.md` 警告。
   - **嚴禁**使用會破壞 BOM 的方式寫入腳本。

---
*此規則由使用者透過深度學習機制 (/learn) 永久寫入系統。所有 Agent 必須無條件遵守。*
