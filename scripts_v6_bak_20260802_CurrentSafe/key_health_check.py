"""
key_health_check.py
────────────────────────────────────────────────────────────────
定期對每一把 Gemini API 金鑰發送最輕量的 GenerateContent 請求，
主動偵測 401 Unauthorized / 403 Forbidden（金鑰失效），
不用等 STT 任務失敗才發現。

使用方式：
  python scripts/key_health_check.py            # 檢查 + 列報告
  python scripts/key_health_check.py --remove   # 自動移除失效金鑰
  python scripts/key_health_check.py --quiet    # 只印失效金鑰

排程（每天凌晨 3 點自動執行）：
  schtasks /Create /SC DAILY /TN "GeminiKeyCheck" /TR "python C:\\LocalAI_Workstation\\scripts\\key_health_check.py --remove" /ST 03:00
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ── 設定 ────────────────────────────────────────────────────────
KEYS_YAML   = os.path.join(os.path.dirname(__file__), "..", "config", "keys.yaml")
ALERT_LOG   = "A:/logs/key_health_alerts.jsonl"
REPORT_DIR  = "A:/logs/dead_key_reports"   # 失效金鑰完整報告存放目錄
# 最輕量：只用 gemini-2.0-flash，輸出最多 1 個 token
CHECK_MODEL = "gemini-2.0-flash"
CHECK_BODY  = json.dumps({
    "contents": [{"parts": [{"text": "Hi"}]}],
    "generationConfig": {"maxOutputTokens": 1}
}).encode()
TIMEOUT_SEC = 12
MAX_WORKERS = 20   # 並發測試數（不消耗 quota，只測認證）

# HTTP 狀態碼分類
DEAD_CODES  = {401, 403}   # 金鑰本身失效（Unauthorized / Forbidden）
ALIVE_CODES = {200, 429}   # 200=正常；429=配額用完但金鑰有效

# ── 載入 YAML（不依賴 PyYAML，自行解析簡單格式）──────────────────
_is_keys_encrypted = False

def load_keys_yaml(path: str):
    global _is_keys_encrypted
    try:
        import yaml
        import os, sys
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_text = f.read()
            
        if raw_text.strip().startswith("gAAAAA"):
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from utils.vault import Vault
                raw_text = Vault.decrypt_data(raw_text.strip())
                _is_keys_encrypted = True
            except Exception as e:
                print(f"[Vault] 解密金鑰失敗: {e}")
                
        return yaml.safe_load(raw_text)
    except ImportError:
        # fallback: 純文字解析 value: 欄位
        keys = []
        name = None
        with open(path, "r", encoding="utf-8-sig") as f:
            raw_text = f.read()
            if raw_text.strip().startswith("gAAAAA"):
                try:
                    from utils.vault import Vault
                    raw_text = Vault.decrypt_data(raw_text.strip())
                    _is_keys_encrypted = True
                except: pass
            for line in raw_text.splitlines():
                line = line.rstrip()
                if line.strip().startswith("- name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.strip().startswith("value:") and name:
                    value = line.split(":", 1)[1].strip()
                    keys.append({"name": name, "value": value})
                    name = None
        return {"keys": keys}


def save_keys_yaml(path: str, data: dict):
    global _is_keys_encrypted
    try:
        import yaml
        out_yaml = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        if _is_keys_encrypted:
            try:
                import sys, os
                script_dir = os.path.dirname(os.path.abspath(__file__))
                parent_dir = os.path.abspath(os.path.join(script_dir, '..'))
                if parent_dir not in sys.path:
                    sys.path.insert(0, parent_dir)
                from utils.vault import Vault
                out_yaml = Vault.encrypt_data(out_yaml)
            except Exception as e:
                print(f"[Vault] 加密金鑰回寫失敗: {e}")
                
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(out_yaml)
    except ImportError:
        # fallback: 逐行手動寫
        out_lines = ["keys:\n"]
        for item in data.get("keys", []):
            out_lines.append(f"- name: {item.get('name', 'key')}\n")
            out_lines.append(f"  value: {item.get('value', '')}\n")
            out_lines.append(f"  active: {str(item.get('active', True)).lower()}\n")
            if "notes" in item:
                out_lines.append(f"  notes: {item['notes']}\n")
        out_text = "".join(out_lines)
        if _is_keys_encrypted:
            try:
                from utils.vault import Vault
                out_text = Vault.encrypt_data(out_text)
            except: pass
        with open(path, "w", encoding="utf-8-sig") as f:
            f.write(out_text)


# ── 單一金鑰測試 ─────────────────────────────────────────────────
def check_key(item: dict) -> dict:
    """
    發送最輕量的 GenerateContent 請求，回傳結果 dict：
      status  : "ok" | "dead" | "quota" | "error"
      code    : HTTP 狀態碼（或 None）
      latency : 回應時間（秒）
      reason  : 說明文字
    """
    name  = item.get("name", "?")
    value = item.get("value", "")
    url   = (f"https://generativelanguage.googleapis.com/v1beta/models/"
             f"{CHECK_MODEL}:generateContent?key={value}")

    t0 = time.monotonic()
    try:
        req = urllib.request.Request(
            url,
            data=CHECK_BODY,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
            latency = time.monotonic() - t0
            code = resp.getcode()
            return {"name": name, "key_prefix": value[:16],
                    "status": "ok", "code": code,
                    "latency": latency, "reason": "OK"}

    except urllib.error.HTTPError as e:
        latency = time.monotonic() - t0
        code = e.code
        if code in DEAD_CODES:
            status = "dead"
            reason = f"HTTP {code} {'Unauthorized' if code==401 else 'Forbidden'} — 金鑰失效"
        elif code == 429:
            status = "quota"
            reason = "HTTP 429 — 配額用完但金鑰有效"
        else:
            status = "error"
            reason = f"HTTP {code}"
        return {"name": name, "key_prefix": value[:16],
                "status": status, "code": code,
                "latency": latency, "reason": reason}

    except Exception as ex:
        latency = time.monotonic() - t0
        return {"name": name, "key_prefix": value[:16],
                "status": "error", "code": None,
                "latency": latency, "reason": str(ex)[:80]}


# ── 主程式 ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Gemini API 金鑰健康檢查")
    parser.add_argument("--remove", action="store_true",
                        help="自動移除失效金鑰（401/403）")
    parser.add_argument("--quiet",  action="store_true",
                        help="只列印失效金鑰，略過正常金鑰")
    parser.add_argument("--model",  default=CHECK_MODEL,
                        help=f"測試用模型（預設: {CHECK_MODEL}）")
    args = parser.parse_args()

    keys_path = os.path.abspath(KEYS_YAML)
    if not os.path.exists(keys_path):
        print(f"[ERROR] keys.yaml 不存在: {keys_path}")
        sys.exit(1)

    data = load_keys_yaml(keys_path)
    keys = data.get("keys", [])
    if not keys:
        print("[ERROR] keys.yaml 內沒有金鑰")
        sys.exit(1)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'═'*60}")
    print(f"  Gemini API 金鑰健康檢查  —  {ts}")
    print(f"  模型: {args.model}  |  並發: {MAX_WORKERS}  |  共 {len(keys)} 把金鑰")
    print(f"{'═'*60}\n")

    results  = []
    ok_list  = []
    dead_list= []
    quota_list=[]
    err_list = []

    # 並發測試
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_map = {pool.submit(check_key, item): item for item in keys}
        done = 0
        for future in as_completed(future_map):
            done += 1
            r = future.result()
            results.append(r)

            # 即時印出失效金鑰
            if r["status"] == "dead":
                # 保存完整 key value 供後續報告
                r["full_value"] = future_map[future].get("value", "")
                dead_list.append(r)
                print(f"  ❌ [{r['name']:10}]  {r['key_prefix']}...  {r['reason']}")
            elif r["status"] == "quota":
                quota_list.append(r)
                if not args.quiet:
                    print(f"  ⚠️  [{r['name']:10}]  {r['key_prefix']}...  配額用完（金鑰有效）")
            elif r["status"] == "ok":
                ok_list.append(r)
                if not args.quiet:
                    print(f"  ✅ [{r['name']:10}]  {r['key_prefix']}...  OK  ({r['latency']:.1f}s)")
            else:
                err_list.append(r)
                print(f"  ⚠️  [{r['name']:10}]  {r['key_prefix']}...  {r['reason']}")

            # 進度
            print(f"\r  進度: {done}/{len(keys)}", end="", flush=True)

    print(f"\r{' '*30}\r")   # 清除進度列

    # ── 摘要報告 ────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  ✅ 正常 (200)    : {len(ok_list):>3} 把")
    print(f"  ⚠️  配額用完(429) : {len(quota_list):>3} 把  （金鑰有效，明日恢復）")
    print(f"  ❌ 失效 (401/403): {len(dead_list):>3} 把  ← 需補充替換")
    print(f"  🔸 其他錯誤     : {len(err_list):>3} 把")
    alive = len(ok_list) + len(quota_list)
    print(f"{'─'*60}")
    print(f"  有效金鑰合計    : {alive} 把")
    print(f"  每日 API 上限   : {alive * 1500:,} 次  ({alive} × 1500 RPD)")
    print(f"{'─'*60}\n")

    # ── 失效金鑰完整報告（移除前先存檔 + 印到螢幕）────────────────
    report_path = None
    if dead_list:
        # 1. 印到終端，顯示完整金鑰值供人工確認
        print(f"\n{'━'*60}")
        print(f"  ⚠️  以下 {len(dead_list)} 把金鑰已失效，請重新申請後補入 keys.yaml：")
        print(f"{'━'*60}")
        for r in dead_list:
            full = r.get("full_value", r["key_prefix"] + "...")
            print(f"  [{r['name']}]")
            print(f"    {full}")
        print(f"{'━'*60}\n")

        # 2. 寫入帶時戳的報告檔案（完整金鑰值）
        try:
            os.makedirs(REPORT_DIR, exist_ok=True)
            report_path = os.path.join(
                REPORT_DIR,
                "dead_keys_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
            )
            with open(report_path, "w", encoding="utf-8-sig") as rf:
                rf.write(f"# Gemini 失效金鑰報告 — {ts}\n")
                rf.write(f"# 請登入對應帳號至 https://aistudio.google.com 重新申請金鑰\n")
                rf.write(f"# 共 {len(dead_list)} 把失效，{alive} 把有效\n\n")
                for r in dead_list:
                    full = r.get("full_value", r["key_prefix"] + "...")
                    rf.write(f"[{r['name']}]  HTTP {r['code']}  {r['reason']}\n")
                    rf.write(f"{full}\n\n")
            print(f"  📄 完整報告已存至: {report_path}")
            print(f"     （請憑此報告到 AI Studio 補申請新金鑰）\n")
        except Exception as ex:
            print(f"  [WARN] 無法寫入報告檔: {ex}")

        # 3. 寫入告警 JSONL（機器可讀）
        try:
            os.makedirs(os.path.dirname(ALERT_LOG), exist_ok=True)
            with open(ALERT_LOG, "a", encoding="utf-8-sig") as af:
                af.write(json.dumps({
                    "ts": ts,
                    "dead_keys": [
                        {"name": r["name"], "code": r["code"],
                         "key_prefix": r["key_prefix"]}
                        for r in dead_list
                    ],
                    "dead_count": len(dead_list),
                    "alive_count": alive,
                    "report_file": report_path,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ── 自動移除失效金鑰（報告已存，此時才移除）────────────────────
    if args.remove and dead_list:
        dead_names = {r["name"] for r in dead_list}
        before = len(data["keys"])
        data["keys"] = [k for k in data["keys"] if k["name"] not in dead_names]
        after = len(data["keys"])
        save_keys_yaml(keys_path, data)
        print(f"  🗑️  已從 keys.yaml 移除 {before - after} 把失效金鑰")
        print(f"  📋 剩餘有效金鑰: {after} 把")
        if report_path:
            print(f"  📄 補申請清單: {report_path}\n")
    elif dead_list:
        print(f"  ℹ️  金鑰尚未移除（加 --remove 參數才會自動刪除）\n")

    # 有失效金鑰時以非零 exit code 退出，方便 scheduler 偵測
    sys.exit(1 if dead_list else 0)


if __name__ == "__main__":
    main()
