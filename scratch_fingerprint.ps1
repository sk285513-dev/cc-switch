 = @(
    "LexMind_一鍵正式啟動.ps1",
    "LexMind_一鍵完全關閉系統.ps1",
    ".streamlit\config.toml",
    "scripts_v6\run_workflow.py",
    "app_v6.py",
    "Launch_Isolated.vbs",
    "kpi_runner.ps1",
    "scripts_v6\progress_dashboard.py",
    "scripts_v6\auto_gui_debugger.py"
)

 = ""File","Path","SHA256"
"

foreach ( in ) {
     = Join-Path "C:\LocalAI_Workstation" 
    if (Test-Path ) {
         = (Get-FileHash  -Algorithm SHA256).Hash
         = [System.IO.Path]::GetFileName()
         += ""","",""
"
    } else {
        Write-Host "Missing file: "
    }
}

 | Out-File -FilePath C:\LocalAI_Workstation\v6.1_script_fingerprints.csv -Encoding utf8
Write-Host "Generated v6.1_script_fingerprints.csv"
