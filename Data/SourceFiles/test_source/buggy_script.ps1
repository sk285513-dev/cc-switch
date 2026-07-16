# 步驟 1: 檢查脚本的安全性
# 確保脚本允許正確的外部脚本執行
Set-ExecutionPolicy RemoteSignedScript executing -Scope Win32

# 步驟 2: 限制文件系統的訪問權限
Set-FileAttributes -Path [path_to_your_script] Hidden