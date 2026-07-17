Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = "請選擇法律教材與大數據人工分類資料夾 (選取後網頁將直接掃描導入，免網頁上傳警告)"
$f.ShowNewFolderButton = $false
$result = $f.ShowDialog()
if ($result -eq "OK") {
    Write-Output $f.SelectedPath
} else {
    Write-Output "CANCELLED"
}
