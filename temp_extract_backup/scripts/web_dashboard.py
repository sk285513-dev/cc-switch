"""
LexMind-Omni Web 進度儀表板
============================
背景靜默跑 HTTP server，開瀏覽器 http://localhost:7788 查看。
不佔任何終端機/PowerShell 視窗。
"""
import json, glob, os, time, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

MANIFESTS_DIR = Path("A:/manifests")
LOG_PATH      = Path("A:/logs/workflow.log")
PROCESSED_DIR = Path("A:/processed_md")
PORT = 7788
REFRESH_SEC = 30

# ── 資料收集 ──────────────────────────────────────────────
def load_stats():
    stats = {"completed": [], "in_progress": [], "pending": 0,
             "total": 0, "log_tail": [], "updated": ""}
    try:
        for mf in glob.glob(str(MANIFESTS_DIR / "task_*.json")):
            if "_chunks" in mf:
                continue
            try:
                m = json.loads(Path(mf).read_text(encoding="utf-8"))
                tid  = m.get("task_id", "")
                src  = m.get("source_name", "")
                name = Path(src).stem if src else tid[-8:]
                st   = m.get("status", "")
                if "mock_" in tid:
                    continue
                stats["total"] += 1
                chunks = m.get("chunks", {})
                done   = sum(1 for c in chunks.values() if c.get("status") == "completed")
                total  = len(chunks)

                if st == "completed":
                    mtime = Path(mf).stat().st_mtime
                    stats["completed"].append({
                        "name": name[:55], "time": datetime.fromtimestamp(mtime).strftime("%m-%d %H:%M")
                    })
                elif st in ("stt_in_progress", "merged", "formatter_pending"):
                    label = "🔄 Merge" if st == "merged" else f"🎙️ STT {done}/{total}"
                    stats["in_progress"].append({"name": name[:55], "stage": label, "done": done, "total": total})
                else:
                    stats["pending"] += 1
            except Exception:
                pass

        stats["completed"].sort(key=lambda x: x["time"], reverse=True)
        stats["in_progress"] = stats["in_progress"][:10]

        if LOG_PATH.exists():
            lines = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
            stats["log_tail"] = [l for l in lines if "[INFO]" in l or "[ERROR]" in l][-12:]

        stats["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        stats["error"] = str(e)
    return stats

# ── HTML 模板 ─────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="{refresh}">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LexMind-Omni 進度儀表板</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; color: #e6edf3; font-family: 'Segoe UI', sans-serif; padding: 20px; }}
  h1 {{ font-size: 1.4em; color: #58a6ff; margin-bottom: 4px; }}
  .sub {{ color: #8b949e; font-size: .85em; margin-bottom: 20px; }}
  .cards {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 20px; min-width: 140px; }}
  .card .num {{ font-size: 2.2em; font-weight: 700; }}
  .card .lbl {{ color: #8b949e; font-size: .8em; margin-top: 2px; }}
  .card.green .num {{ color: #3fb950; }}
  .card.blue  .num {{ color: #58a6ff; }}
  .card.gray  .num {{ color: #8b949e; }}
  section {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }}
  section h2 {{ font-size: .9em; padding: 10px 16px; background: #21262d; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .85em; }}
  th {{ padding: 8px 12px; text-align: left; color: #8b949e; border-bottom: 1px solid #30363d; font-weight: 500; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #21262d; }}
  tr:last-child td {{ border-bottom: none; }}
  .bar-wrap {{ background: #21262d; border-radius: 4px; height: 6px; width: 120px; display: inline-block; vertical-align: middle; }}
  .bar {{ background: #58a6ff; height: 6px; border-radius: 4px; }}
  .log {{ font-family: monospace; font-size: .78em; padding: 12px 16px; max-height: 200px; overflow-y: auto; }}
  .log div {{ padding: 2px 0; color: #8b949e; }}
  .log div.err {{ color: #f85149; }}
  .tag {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: .75em; }}
  .tag.done {{ background: #1a3a2a; color: #3fb950; }}
  .tag.run  {{ background: #1a2a3a; color: #58a6ff; }}
  .refresh {{ color: #8b949e; font-size: .75em; margin-top: 12px; }}
</style>
</head>
<body>
<h1>⚖️ LexMind-Omni 法律轉譯進度儀表板</h1>
<div class="sub">更新時間：{updated} ｜ 每 {refresh} 秒自動刷新</div>

<div class="cards">
  <div class="card green"><div class="num">{n_completed}</div><div class="lbl">✅ 已完成</div></div>
  <div class="card blue"><div class="num">{n_inprog}</div><div class="lbl">🔄 進行中</div></div>
  <div class="card gray"><div class="num">{n_pending}</div><div class="lbl">⏳ 待處理</div></div>
  <div class="card gray"><div class="num">{n_total}</div><div class="lbl">📚 總計</div></div>
</div>

<section>
  <h2>🔄 進行中任務</h2>
  <table>
    <tr><th>階段</th><th>課程</th><th>進度</th></tr>
    {rows_inprog}
  </table>
</section>

<section>
  <h2>✅ 已完成（最近 10 堂）</h2>
  <table>
    <tr><th>完成時間</th><th>課程</th></tr>
    {rows_done}
  </table>
</section>

<section>
  <h2>📋 系統日誌（最新 12 行）</h2>
  <div class="log">{log_lines}</div>
</section>

<div class="refresh">⟳ 瀏覽器將在 {refresh} 秒後自動刷新 ｜ <a href="/" style="color:#58a6ff">立即刷新</a></div>
</body></html>"""

def build_html(stats):
    rows_ip = ""
    for t in stats.get("in_progress", []):
        pct = int(t["done"] / t["total"] * 100) if t["total"] else 0
        bar = f'<div class="bar-wrap"><div class="bar" style="width:{pct}%"></div></div> {t["done"]}/{t["total"]}'
        rows_ip += f'<tr><td><span class="tag run">{t["stage"]}</span></td><td>{t["name"]}</td><td>{bar}</td></tr>'
    if not rows_ip:
        rows_ip = '<tr><td colspan="3" style="color:#8b949e;padding:16px">無進行中任務</td></tr>'

    rows_done = ""
    for c in stats.get("completed", [])[:10]:
        rows_done += f'<tr><td style="color:#8b949e">{c["time"]}</td><td>{c["name"]}</td></tr>'
    if not rows_done:
        rows_done = '<tr><td colspan="2" style="color:#8b949e;padding:16px">尚無完成記錄</td></tr>'

    log_html = ""
    for l in stats.get("log_tail", []):
        cls = "err" if "[ERROR]" in l else ""
        safe = l.replace("&","&amp;").replace("<","&lt;")
        log_html += f'<div class="{cls}">{safe}</div>'

    return HTML_TEMPLATE.format(
        refresh=REFRESH_SEC,
        updated=stats.get("updated",""),
        n_completed=len(stats.get("completed",[])),
        n_inprog=len(stats.get("in_progress",[])),
        n_pending=stats.get("pending",0),
        n_total=stats.get("total",0),
        rows_inprog=rows_ip,
        rows_done=rows_done,
        log_lines=log_html or "<div>無日誌</div>",
    )

# ── HTTP Server ───────────────────────────────────────────
class DashHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            stats = load_stats()
            html  = build_html(stats).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(html))
            self.end_headers()
            self.wfile.write(html)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())

    def log_message(self, *a):
        pass  # 靜默，不印 access log

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), DashHandler)
    print(f"LexMind-Omni 儀表板：http://localhost:{PORT}")
    server.serve_forever()
