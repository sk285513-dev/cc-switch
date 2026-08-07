import sys
import os
import getpass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.utils.key_manager import KeyManager
except Exception as e:
    try:
        from utils.key_manager import KeyManager
    except Exception as e2:
        print(f"載入模組失敗: {e2}")
        input("按 Enter 鍵離開...")
        sys.exit(1)

print("==================================================")
print(" LexMind-Omni 絕對安全金鑰匯入工具 (CLI 軌道 B)")
print("==================================================")
print("【安全保證】本工具運行於您本機 Session，金鑰將被 DPAPI 加密，絕不明碼存檔。")
print("【隱私防護】輸入時畫面『不會顯示任何字元』，不會留存在終端機歷史紀錄中。")
print("")
key = getpass.getpass("請貼上您的 Google API Key (貼上後請按 Enter): ")

if not key.strip():
    print("未輸入金鑰，操作取消。")
else:
    try:
        result = KeyManager.add_keys_from_cli(key.strip())
        if result.get('status') == 'success':
            if result.get('added', 0) > 0:
                print(f"\n✅ 成功！金鑰已完成本地加密並匯入安全庫。(新增 {result.get('added')} 把金鑰)")
            else:
                print("\n⚠️ 金鑰已存在於安全庫中，未重複新增。")
        else:
            print(f"\n❌ 寫入失敗: {result.get('message', '未知錯誤')}")
    except Exception as e:
        print(f"\n❌ 寫入失敗: {e}")

print("")
input("按 Enter 鍵關閉視窗...")
