import os
import shutil
import datetime
from cryptography.fernet import Fernet

class LegalDBBackupManager:
    def __init__(self, db_path=None, backup_dir=None, retention_days=14):
        base_dir = Path(__file__).resolve().parent.parent
        if db_path is None:
            db_path = str(base_dir / "RAGFlow_Datasets")
        if backup_dir is None:
            backup_dir = str(base_dir / "secure_backups")
            
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.retention_days = retention_days
        self.key_path = str(base_dir / "secret.key")
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def _get_or_create_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, "rb") as key_file:
                return key_file.read()
        key = Fernet.generate_key()
        with open(self.key_path, "wb") as key_file:
            key_file.write(key)
        return key

    def run_backup_and_encrypt(self):
        if not os.path.exists(self.db_path):
            print("❌ 備份失敗：找不到本機資料庫目錄")
            return None
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_zip_prefix = os.path.join(self.backup_dir, f"temp_{timestamp}")
        final_file_path = os.path.join(self.backup_dir, f"legal_db_backup_{timestamp}.enc")

        # 打包目錄
        shutil.make_archive(temp_zip_prefix, 'zip', self.db_path)
        zip_file = f"{temp_zip_prefix}.zip"

        # 加密
        key = self._get_or_create_key()
        fernet = Fernet(key)
        try:
            with open(zip_file, "rb") as f_in:
                raw_data = f_in.read()
            encrypted_data = fernet.encrypt(raw_data)
            
            with open(final_file_path, "wb") as f_out:
                f_out.write(encrypted_data)
                
            print(f"🔒 本地資料庫已成功軍規級加密備份至：{final_file_path}")
        finally:
            if os.path.exists(zip_file):
                os.remove(zip_file)
                
        self._clean_old_backups()
        return final_file_path

    def _clean_old_backups(self):
        now = datetime.datetime.now()
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("legal_db_backup_") and filename.endswith(".enc"):
                full_path = os.path.join(self.backup_dir, filename)
                ctime = datetime.datetime.fromtimestamp(os.path.getctime(full_path))
                if (now - ctime).days > self.retention_days:
                    os.remove(full_path)
                    print(f"🧹 清理已逾期 14 天舊備份：{filename}")