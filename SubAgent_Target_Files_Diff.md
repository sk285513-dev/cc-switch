diff --git a/scripts_v6/chunk_planner.py b/scripts_v6/chunk_planner.py
index 5c085097..19a60dc9 100644
--- a/scripts_v6/chunk_planner.py
+++ b/scripts_v6/chunk_planner.py
@@ -119,7 +119,15 @@ def plan_chunks(task_id):
     task_chunks_dir = os.path.join(chunks_dir, task_id)
     os.makedirs(task_chunks_dir, exist_ok=True)
     
-    source_stem = Path(manifest["source_name"]).stem
+    source_name = manifest.get("source_name")
+    if not source_name:
+        log_error(f"Chunk Planner: [CRITICAL] source_name is missing. Task corrupted.")
+        log_error("CRITICAL: source_name is missing. Marking task as CRITICAL_CORRUPT for isolation.")
+        manifest["status"] = "CRITICAL_CORRUPT"
+        with open(manifest_file, "w", encoding="utf-8-sig") as wf:
+            json.dump(manifest, wf, ensure_ascii=False, indent=2)
+        return False
+    source_stem = Path(source_name).stem
     # 清理檔名，避免特殊字元
     clean_stem = "".join([c if c.isalnum() or c in ('_', '-') else '_' for c in source_stem])
     
diff --git a/scripts_v6/manifest_manager.py b/scripts_v6/manifest_manager.py
index b6550338..c19ffff7 100644
--- a/scripts_v6/manifest_manager.py
+++ b/scripts_v6/manifest_manager.py
@@ -51,7 +51,7 @@ class ManifestManager:
         if not self.manifest_path.exists():
             return {}
         try:
-            with open(self.manifest_path, 'r', encoding='utf-8') as f:
+            with open(self.manifest_path, 'r', encoding='utf-8-sig') as f:
                 return json.load(f)
         except Exception as e:
             print(f"[ManifestManager] Warning: failed to read {self.manifest_path}: {e}")
diff --git a/scripts_v6/markdown_formatter.py b/scripts_v6/markdown_formatter.py
index db060076..c2d70c37 100644
--- a/scripts_v6/markdown_formatter.py
+++ b/scripts_v6/markdown_formatter.py
@@ -1,4 +1,4 @@
-﻿import json
+import json
 import os
 import sys, io
 from pathlib import Path
@@ -19,7 +19,7 @@ try:
     from quota_manager import QuotaManager
 except ImportError:
     try:
-        from scripts_v6.quota_manager import QuotaManager
+        from quota_manager import QuotaManager
     except ImportError:
         QuotaManager = None
 
@@ -401,7 +401,16 @@ def format_markdown(task_id):
             chunks = mm.read()
         
     media_info = manifest.get("media_info", {})
-    source_name = manifest["source_name"]
+    source_name = manifest.get("source_name")
+    
+    if not source_name:
+        log_error(f"Markdown Formatter: [CRITICAL] source_name is missing. Task corrupted.")
+        manifest["status"] = "CRITICAL_CORRUPT"
+        manifest["error"] = "CRITICAL_CORRUPT: source_name missing"
+        with ManifestManager(manifest_file) as mm:
+            mm.write(manifest)
+        return False
+        
     source_stem = Path(source_name).stem
     
     full_txt_path = os.path.join(task_chunks_dir, "merged_full_transcript.txt")
diff --git a/scripts_v6/merge_transcript.py b/scripts_v6/merge_transcript.py
index 4e67368d..473437d7 100644
--- a/scripts_v6/merge_transcript.py
+++ b/scripts_v6/merge_transcript.py
@@ -35,7 +35,7 @@ def log_degraded_event(task, reason, merge_mode, extra=None):
     寫入降級事件日誌，不使用 emoji，只用 ASCII。
     """
     try:
-        log_path = Path(r"A:\logs_v6\merge_degraded.log")
+        log_path = Path(r"A:\logs\merge_degraded.log")
         log_path.parent.mkdir(parents=True, exist_ok=True)
 
         payload = {
@@ -77,6 +77,11 @@ def apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_
     - 直接用原始 chunks 合併輸出
     - 保存輸出與 manifest
     """
+    if not manifest.get("task_id") or not manifest.get("source_name"):
+        from workflow_helper import log_error
+        log_error(f"Merge Agent: [GUARD] Manifest Truncation Prevented for task {task_id}")
+        return False
+
     manifest = mark_task_degraded(manifest, reason="merge_timeout", merge_mode="raw_fallback")
 
     log_degraded_event(
@@ -111,6 +116,10 @@ def apply_raw_fallback(task_id, manifest, raw_chunks, task_chunks_dir, manifest_
         })
         
         from manifest_manager import ManifestManager
+        if not manifest.get("task_id") or not manifest.get("source_name"):
+            log_error("Merge Agent: [GUARD] Manifest Truncation Prevented")
+            return False
+            
         with ManifestManager(manifest_file) as mm:
             mm.write(manifest)
     except Exception as e:
