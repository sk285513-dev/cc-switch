import json
import os
import json
import shutil
from pathlib import Path

def restore_0kb_srt_tasks():
    processed_md_dir = Path(r"A:\processed_md")
    chunks_backup_dir = Path(r"F:\chunks_backup")
    chunks_active_dir = Path(r"A:\chunks")
    manifests_dir = Path(r"A:\manifests")
    
    empty_srts = list(processed_md_dir.glob("*.srt"))
    empty_srts = [f for f in empty_srts if f.stat().st_size == 0]
    
    print(f"找到 {len(empty_srts)} 個 0.0KB 異常 SRT 檔案。")
    
    restored_count = 0
    for srt_file in empty_srts:
        task_id = srt_file.stem
        print(f"\n處理任務: {task_id}")
        
        # 1. 將原始切片從備份區搬回活動區
        backup_task_dir = chunks_backup_dir / task_id
        active_task_dir = chunks_active_dir / task_id
        
        if backup_task_dir.exists():
            print(f"  - 正在從備份區搬回切片: {backup_task_dir} -> {active_task_dir}")
            if active_task_dir.exists():
                shutil.rmtree(active_task_dir)
            shutil.move(str(backup_task_dir), str(active_task_dir))
        elif active_task_dir.exists():
            print(f"  - 切片已經在活動區: {active_task_dir}")
        else:
            print(f"  - 警告: 找不到切片目錄 ({task_id})")
            continue
            
        # 2. 重置主 Manifest
        manifest_file = manifests_dir / f"{task_id}.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8-sig") as f:
                    manifest = json.load(f)
                
                manifest["status"] = "chunked"
                manifest["steps"]["stt"] = "pending"
                if "merge" in manifest["steps"]: del manifest["steps"]["merge"]
                if "formatter" in manifest["steps"]: del manifest["steps"]["formatter"]
                if "paths" in manifest: del manifest["paths"]
                
                with open(manifest_file, "w", encoding="utf-8-sig") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                print("  - 主 Manifest 已重置為 chunked。")
            except Exception as e:
                print(f"  - 重置主 Manifest 失敗: {e}")
                
        # 3. 重置切片清單
        chunks_manifest_file = manifests_dir / f"{task_id}_chunks.json"
        if chunks_manifest_file.exists():
            try:
                with open(chunks_manifest_file, "r", encoding="utf-8-sig") as f:
                    chunks = json.load(f)
                
                reset_chunks = 0
                for chunk in chunks:
                    chunk["status"] = "pending"
                    chunk["text"] = ""
                    reset_chunks += 1
                    
                with open(chunks_manifest_file, "w", encoding="utf-8-sig") as f:
                    json.dump(chunks, f, ensure_ascii=False, indent=2)
                print(f"  - 已重置 {reset_chunks} 個切片的狀態為 pending。")
            except Exception as e:
                print(f"  - 重置切片清單失敗: {e}")
                
        # 4. 清理異常產物
        srt_file.unlink(missing_ok=True)
        md_file = processed_md_dir / f"{task_id}.md"
        vtt_file = processed_md_dir / f"{task_id}.vtt"
        txt_file = processed_md_dir / f"{task_id}.txt"
        
        for f in [md_file, vtt_file, txt_file]:
            if f.exists():
                f.unlink()
        print("  - 異常的最終產物 (.srt, .md, .vtt, .txt) 已刪除。")
        
        restored_count += 1
        
    print(f"\n成功還原了 {restored_count} 堂課，它們現在已經回到 A:\\chunks 等待重新轉錄。")

if __name__ == "__main__":
    restore_0kb_srt_tasks()

