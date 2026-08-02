# ==========================================
# 【機制十七】作業系統層級之記憶體防禦機制實作
# 目的：強制設定 128GB 虛擬記憶體，防止 GPU/CPU 高併發時 OOM
# ==========================================
Write-Host "正在停用自動分頁檔管理..."
$cs = Get-CimInstance -ClassName Win32_ComputerSystem
$cs | Set-CimInstance -Property @{AutomaticManagedPagefile=$False}

Write-Host "設定 C 槽分頁檔為 128GB (131072 MB)..."
$pagefile = Get-CimInstance -ClassName Win32_PageFileSetting | Where-Object { $_.Name -match "^C:" }
if ($pagefile) {
    $pagefile | Set-CimInstance -Property @{InitialSize=131072; MaximumSize=131072}
} else {
    New-CimInstance -ClassName Win32_PageFileSetting -Property @{Name="C:\pagefile.sys"; InitialSize=131072; MaximumSize=131072}
}
Write-Host "設定完成！建議重新啟動電腦以套用最佳變更。"
