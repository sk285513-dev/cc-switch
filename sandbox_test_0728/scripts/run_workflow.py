# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 1: 領域防護與前端物流 (Ingestion & Rules)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 1】。
# 依賴 national_exam_rules.py 作為 SSOT。修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
import os
import sys
import time
import json
import argparse
import threading
import traceback
import yaml
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from national_exam_rules import get_exam_score

# 將 scripts 目錄加入 PATH
script_dir = Path(__file__).parent.resolve()
if str(script_dir) not in sys.path:
    sys.path.append(str(script_dir))

from file_watcher import scan_new_files
from preprocess_media import preprocess
from chunk_planner import plan_chunks
from stt_runner import run_stt
from merge_transcript import merge_workflow
from markdown_formatter import format_markdown
from workflow_helper import ensure_dirs, log_workflow, log_error
from scripts.quota_manager import QuotaManager

def get_mock_legal_transcript(index):
    topics = [
        ("民法總則_法律行為之效力", "本課堂主要講解民法總則中有關法律行為之效力。法律行為以意思表示為要素，若意思表示有瑕疵，如詐欺或脅迫，得於知悉後一年內撤銷其意思表示。行為能力制度旨在保護限制行為能力人，限制行為能力人所為之單獨行為，無效。"),
        ("民法債編_侵權行為責任要件", "今天探討民法第一百八十四條獨立侵權行為責任之成立要件。因故意或過失，不法侵害他人之權利者，負損害賠償責任。消滅時效自請求權人知悉有損害及賠償義務人時起算，二年內不行使而消滅。"),
        ("民法物權_共有物之處分與管理", "共有物之處分、變更及設定負擔，應得共有人全體之同意。但依土地法第三十四條之一，共有人人數及應有部分合計過半數即可。共有物分割協議須全體同意始生效力。"),
        ("土地法_土地登記效力與絕對效力", "土地登記規則規定，依本法所為之登記，有絕對效力。第三人信賴登記而取得土地權利者，其權利受法律保護，以維護交易安全。未登記土地所有權處分受限。"),
        ("土地稅法_地價稅減免與申報要件", "土地稅法規定，自用住宅用地之地價稅按千分之二課徵。其餘非自用住宅用地則按基本稅率課徵，符合一定要件之公有土地得申請免稅。"),
        ("民事訴訟法_管轄權與合意管轄", "民事訴訟法規定，訴訟由被告住所地之法院管轄。但當事人得以書面合意約定第一審管轄法院，此即為合意管轄之要件與程序。因不動產涉訟者，專屬不動產所在地法院管轄。"),
        ("行政程序法_行政處分之定義與撤銷", "行政處分係指行政機關就公法上具體事件所為之決定或其他公權力措施，而對外直接發生法律效果之單方行政行為。違法行政處分得由原處分機關或上級機關依法撤銷。"),
        ("刑法總則_正當防衛與緊急避難", "對於現在不法之侵害，而出於防衛自己或他人權利之行為，不罰，此為正當防衛。因避免自己或他人生命、身體、自由、財產之緊急危難，而出於不得已之行為，不罰，此為緊急避難。"),
        ("公司法_股東會召集程序與決議", "公司法規定，股東常會之召集，應於二十日前通知各股東；股東臨時會之召集，則應於十日前通知各股東。股東會決議分普通決議與特別決議。"),
        ("勞動基準法_勞動契約終止與資遣費", "勞動基準法保障勞工權益，規定雇主終止勞動契約時，應依勞工工作年資給予預告期間，並依法給付資遣費。定期契約與不定期契約之認定標準不同。"),
        ("專利法_發明專利三要件", "專利法規定發明專利必須具備產業利用性、新穎性及進步性。申請專利應向專利專責機關提出申請書、說明書及必要圖式。專利權期限自申請日起算二十年。"),
        ("著作權法_合理使用與侵權責任", "著作權法為協調社會公共利益，規定在合理範圍內，得合理使用他人已公開發表之著作，並應明示出處及合理引用。擅自重製他人著作者應負侵權賠償責任。"),
        ("票據法_票據權利消滅時效", "票據法規定執票人對匯票承兌人及本票發票人之權利，自到期日起算，三年間不行使，因時效而消滅。支票權利時效為一年，對前手之追索權為四個月。"),
        ("保險法_保險利益之存在與認定", "保險法規定要保人對於被保險人之生命或身體，應具有保險利益。無保險利益之保險契約，其契約為無效，以防道德危險。財物保險亦須有保險利益。"),
        ("強制執行法_查封程序與效力", "強制執行法規定查封之效力。實施查封後，債務人對查封物所為之處分，對於債權人不生效力。查封得由執行法官指派書記官進行動產或不動產之限制處分。"),
        ("國家賠償法_公務員責任與國賠要件", "國家賠償法規定公務員於執行職務行使公權力時，因故意或過失不法侵害人民自由或權利者，國家應負損害賠償責任。賠償請求應先以書面向賠償義務機關協議。"),
        ("行政訴訟法_撤銷訴訟與訴願程序", "行政訴訟法規定，人民不服訴願決定者，得向行政法院提起撤銷訴訟。撤銷訴訟之提起，應於訴願決定書送達後二個月內之法定期間內為之。"),
        ("消費者保護法_郵購買買七日猶豫期", "消費者保護法規定郵購或訪問買賣之消費者，對所收受之商品不願買受時，得於收受商品後七日內，退回商品或書面通知解除契約，無須說明理由及負擔費用。"),
        ("公寓大廈管理條例_規約與區分所有", "公寓大廈區分所有權人會議之決議，對於區分所有權人及住戶均有拘束力。規約為管理公寓大廈之共同遵守事項，須報請地方主管機關備查。"),
        ("家庭暴力防治法_保護令申請與執行", "家庭暴力防治法規定，法院得依被害人申請核發通常保護令、暫時保護令或緊急保護令。違反保護令罪者，處三年以下有期徒刑、拘役或科或併科罰金。"),
        ("信託法_信託財產獨立性原則", "信託法規定信託財產具有獨立性，受託人因信託財產關係對他人所負之債務，僅得以信託財產為限負其履行責任。信託財產原則上不得強制執行。"),
        ("公平交易法_限制競爭與聯合行為", "公平交易法旨在維護交易秩序與消費者利益。事業不得為聯合行為或濫用市場優勢地位，亦不得為限制競爭或不正競爭之行為。違反者處以行政罰鍰。"),
        ("營業秘密法_損害賠償與懲罰性賠償", "營業秘密法規定，故意洩漏或盜用他人營業秘密者，應負損害賠償責任。法院得依侵害情節，酌定三倍以下之懲罰性賠償。侵害營業秘密罪最重可處五年有期徒刑。"),
        ("金融消費者保護法_金融爭議評議", "金融消費者與金融服務業發生爭議時，得向評議機構申請評議。評議決定在一定額度內對金融服務業具有拘束力，以保護弱勢金融消費者。"),
        ("個人資料保護法_蒐集處理與告知義務", "個人資料保護法規定公務或非公務機關蒐集個人資料時，應向當事人明確告知蒐集目的、類別及利用期間、地區與對象。違反者負有民刑事及行政責任。"),
        ("破產法_破產宣告與和解程序", "破產法規定，法院為破產宣告時，應選任破產管理人，並決定債權申報期間。破產人對其財產之處分權即行喪失，應全權移交破產管理人。"),
        ("仲裁法_仲裁協議效力與仲裁判斷", "仲裁法規定當事人約定將爭議提交仲裁者，法院應依當事人聲請裁定停止訴訟程序，命當事人依約進行仲裁。仲裁判斷與法院確定判決有同一效力。"),
        ("海商法_載貨證券之物權效力", "海商法規定運送人或船長發給載貨證券後，對於載貨證券持有人應負依載貨證券所載內容交付貨物之責任。載貨證券之交付具物權效力。"),
        ("涉外民事法律適用法_準據法之選定", "涉外民事法律適用法旨在解決涉外事件之法律衝突。法律行為之準據法，依當事人意思表示所定之法律；無約定者依關係最切地法，如不動產所在地法。"),
        ("家事事件法_調解程序與非訟事件", "家事事件法規定家事事件除法律另有規定外，於起訴前應經法院調解程序。調解成立者，與確定判決有同一之效力，並能聲請強制執行。")
    ]
    if 1 <= index <= 30:
        return topics[index - 1]
    return ("通用法律教材", "本課堂主要介紹臺灣法律實務與救濟程序，涵蓋民刑事實體法與程序法之基本概念。")

class SingleInstanceLock:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.fp = None

    def acquire(self):
        try:
            self.fp = open(self.lock_file, 'a+')
            self.fp.seek(0)
            if sys.platform == 'win32':
                import msvcrt
                msvcrt.locking(self.fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (IOError, OSError, ImportError):
            if self.fp:
                try:
                    self.fp.close()
                except Exception:
                    pass
            return False

    def release(self):
        if self.fp:
            try:
                self.fp.seek(0)
                if sys.platform == 'win32':
                    import msvcrt
                    msvcrt.locking(self.fp.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self.fp.close()
            except Exception:
                pass
            try:
                os.remove(self.lock_file)
            except Exception:
                pass

def get_legal_priority_score(source_name):
    name = source_name.lower()
    
    # 0. 模擬與測試任務最優先 (保持自動化檢測正常)
    if "mock_" in name or "lexmind_mock_" in name:
        return 0
        
    return get_exam_score(source_name)

TASK_CONCURRENCY = 3  # 同時並列處理的任務數（N=3）

def run_single_task_safe(manifest: dict, manifest_path: Path, exclusive_key: str, qm: QuotaManager, chunking_only: bool) -> bool:
    """
    包裝單一任務的完整流程，供 ThreadPoolExecutor 並列呼叫。
    exclusive_key: 由外部 QuotaManager 分配的排他性 API 金鑰。
    返回 True 表示任務成功。
    """
    paths = ensure_dirs()
    task_id = manifest["task_id"]
    source_name = manifest["source_name"]
    
    key_display = exclusive_key[:8] if exclusive_key else "VertexAI/ADC"
    log_workflow(f"[Parallel Dispatcher] Task {task_id} 開始，分配金鑰: {key_display}...")

    try:
        # Mock 任務不需要金鑰
        if "mock_" in source_name or "lexmind_mock_" in source_name:
            return _run_task_steps(manifest, manifest_path, paths, exclusive_key, chunking_only)
        else:
            return _run_task_steps(manifest, manifest_path, paths, exclusive_key, chunking_only)
    except Exception as e:
        log_error(f"[Parallel Dispatcher] Task {task_id} 發生異常：{e}")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                current_manifest = json.load(f)
            current_manifest["status"] = "failed"
            current_manifest["error"] = str(e)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(current_manifest, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return False

def process_active_tasks(chunking_only=False):
    paths = ensure_dirs()
    manifests_dir = paths["manifests_dir"]
    
    # 尋找所有非 chunks 且未完成/未失敗的任務清單
    manifest_paths = Path(manifests_dir).glob("*.json")
    active_tasks = []
    
    for p in manifest_paths:
        if not p.name.startswith("task_") or p.name.endswith("_chunks.json"):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                status = data.get("status")
                # 在 chunking_only 模式下，如果 chunk_planner 已經 completed，我們跳過此任務
                if chunking_only and data.get("steps", {}).get("chunk_planner") == "completed":
                    continue
                if status not in ["completed", "failed"]:
                    active_tasks.append((p, data))
        except Exception:
            pass
            
    # 依照「先程序後實體、國考主要科目優先、再來分科」的法學專業排序佇列
    active_tasks.sort(key=lambda x: (
        get_legal_priority_score(x[1].get("source_name", "")),
        x[1].get("task_id", "")
    ))
    
    # 暫時鎖定僅執行第一堂課已測試完畢，註解此行以解鎖所有課程排程
    # active_tasks = [t for t in active_tasks if t[1].get("task_id") == "task_20260706_201825_00_3231"]
            
    if not active_tasks:
        return

    log_workflow(f"Workflow Engine: Found {len(active_tasks)} active tasks to process.")

    # ── 讀取 config.yaml 確認引擎 ──
    try:
        with open("C:/LocalAI_Workstation/config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            stt_engine = config.get("settings", {}).get("stt_engine", "gemini")
    except Exception:
        stt_engine = "gemini"

    # ── 建立全局共享的 QuotaManager 實例 ──
    if stt_engine == "vertexai":
        qm = None
        log_workflow("Workflow Engine: Using Vertex AI (Enterprise Channel), bypassing QuotaManager.")
    else:
        try:
            qm = QuotaManager()
        except Exception as qm_err:
            log_error(f"QuotaManager 初始化失敗，回退至單線程模式：{qm_err}")
            qm = None

    # ── 并列分派（N=3）──
    with ThreadPoolExecutor(max_workers=TASK_CONCURRENCY) as executor:
        futures = {}
        for manifest_path, manifest in active_tasks:
            exclusive_key = None
            if qm and not chunking_only:
                try:
                    exclusive_key = qm.acquire_key_exclusive()
                except RuntimeError:
                    log_error(f"[Parallel Dispatcher] 金鑰池已湿，task {manifest['task_id']} 等待下一輪調度。")
                    continue  # 讓此 Task 等待下一輪扯取

            future = executor.submit(
                run_single_task_safe,
                manifest,
                manifest_path,
                exclusive_key,
                qm,
                chunking_only,
            )
            futures[future] = (manifest["task_id"], exclusive_key)

        for future in as_completed(futures):
            task_id, used_key = futures[future]
            try:
                success = future.result()
                status = "success" if success else "failed"
                log_workflow(f"[Parallel Dispatcher] Task {task_id} 完成，狀態：{status}")
            except Exception as e:
                err_tb = traceback.format_exc()
                log_error(f"[Parallel Dispatcher] Task {task_id} Future 異常：{e}\n{err_tb}")
            finally:
                # 無論成敗必定釋放金鑰
                if qm and used_key:
                    qm.release_key(used_key)

    # 長輪詢掃描並處理在執行期間新寫入 Manifest 的背景任務
    process_active_tasks(chunking_only)

def _run_task_steps(manifest: dict, manifest_path: Path, paths: dict, exclusive_key: str, chunking_only: bool) -> bool:
    """
    執行單一任務的全部工作流步驟（preprocess→chunk→stt→merge→format）。
    exclusive_key: 多工模式下此 Task 獨佔的 API 金鑰，傳遞給 run_stt()。
    返回 True 表示所有步驟成功。
    """
    task_id = manifest["task_id"]
    source_name = manifest["source_name"]

    # ── Mock 模式 ──
    if "mock_" in source_name or "lexmind_mock_" in source_name:
        log_workflow(f"Workflow Engine: [MOCK MODE] Processing task {task_id}...")
        try:
            import re
            for step in ["preprocess", "chunk_planner", "stt", "merge", "formatter"]:
                manifest["steps"][step] = "completed"
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                time.sleep(0.1)

            manifest["status"] = "completed"
            try:
                idx_match = re.search(r"mock_lesson_(\d+)", source_name)
                idx = int(idx_match.group(1)) if idx_match else 1
            except Exception:
                idx = 1
            topic_title, topic_content = get_mock_legal_transcript(idx)

            base_name = os.path.splitext(source_name)[0]
            processed_dir = Path("A:/processed_md")
            processed_dir.mkdir(parents=True, exist_ok=True)

            md_path = processed_dir / f"{base_name}.md"
            srt_path = processed_dir / f"{base_name}.srt"
            vtt_path = processed_dir / f"{base_name}.vtt"
            txt_path = processed_dir / f"{base_name}.txt"
            idx_path = processed_dir / f"{base_name}_index.json"

            manifest["output_markdown"] = str(md_path)
            manifest["output_srt"] = str(srt_path)
            manifest["output_vtt"] = str(vtt_path)
            manifest["output_txt"] = str(txt_path)
            manifest["output_json_index"] = str(idx_path)

            with open(md_path, "w", encoding="utf-8") as wf:
                wf.write(f"# {base_name} - {topic_title}\n\n{topic_content}\n")
            with open(srt_path, "w", encoding="utf-8") as wf:
                wf.write(f"1\n00:00:01,000 --> 00:00:15,000\n{topic_title}")
            with open(vtt_path, "w", encoding="utf-8") as wf:
                wf.write(f"WEBVTT\n\n1\n00:00:01.000 --> 00:00:15.000\n{topic_title}")
            with open(txt_path, "w", encoding="utf-8") as wf:
                wf.write(f"{topic_title}。{topic_content}")
            with open(idx_path, "w", encoding="utf-8") as wf:
                json.dump({"title": f"{base_name} - {topic_title}", "summary": topic_content, "terms": [topic_title]}, wf, ensure_ascii=False, indent=2)

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            log_workflow(f"Workflow Engine: [MOCK MODE] Task {task_id} completed successfully!")
            return True
        except Exception as e:
            log_error(f"Workflow Engine: [MOCK MODE] Critical error in task {task_id}: {e}")
            manifest["status"] = "failed"
            manifest["error"] = str(e)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            return False

    # ── 真實任務步驟 ──
    try:
        # 步驟二：Preprocess
        if manifest["steps"]["preprocess"] in ("pending", "failed"):
            success = preprocess(task_id)
            if not success:
                raise RuntimeError("Preprocess step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # 步驟三：Chunk Planner
        if manifest["steps"]["chunk_planner"] in ("pending", "failed"):
            success = plan_chunks(task_id)
            if not success:
                raise RuntimeError("Chunk planning step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        if chunking_only:
            log_workflow(f"Workflow Engine: Task {task_id} chunking done. Stopping (--chunking-only mode).")
            return True

        # 步驟四：STT（傳入排他金鑰供並列模式使用）
        if manifest["steps"]["stt"] in ("pending", "failed"):
            success = run_stt(task_id, exclusive_key=exclusive_key)
            if not success:
                raise RuntimeError("STT transcription step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # 步驟五：Merge
        if manifest["steps"]["merge"] in ("pending", "failed"):
            success = merge_workflow(task_id)
            if not success:
                raise RuntimeError("Merge step failed")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

        # 步驟六：Formatter
        if manifest["steps"]["formatter"] in ("pending", "failed"):
            success = format_markdown(task_id)
            if not success:
                raise RuntimeError("Formatter step failed")

        log_workflow(f"Workflow Engine: Task {task_id} completed successfully!")

        # 暫存切片由 markdown_formatter.py 負責搬移備份 (F:\chunks_backup 或 E:\chunks_backup)
        # 絕對禁止直接刪除，以保留免 API 重做之能力。

        return True

    except Exception as e:
        log_error(f"Workflow Engine: Critical error in task {task_id}: {e}")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                current_manifest = json.load(f)
            current_manifest["status"] = "failed"
            current_manifest["error"] = str(e)
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(current_manifest, f, ensure_ascii=False, indent=2)
        except Exception as write_err:
            log_error(f"Failed to mark task as failed: {write_err}")
        return False


def run_loop(chunking_only=False):
    log_workflow("臺灣法律教材長影音切片處理工作流監控服務已啟動！" + (" [僅切片模式]" if chunking_only else ""))
    ensure_dirs()
    
    while True:
        try:
            # 1. 掃描新檔案
            scan_new_files()
            # 2. 執行活動中任務
            process_active_tasks(chunking_only)
        except Exception as e:
            log_error(f"Error in main workflow loop: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--one-shot", action="store_true", help="Run once and exit instead of loop")
    parser.add_argument("--chunking-only", action="store_true", help="Only run local chunking steps (preprocess, chunk planner)")
    args = parser.parse_args()
    
    paths = ensure_dirs()
    lock_file = os.path.join(paths["manifests_dir"], "workflow.lock")
    lock = SingleInstanceLock(lock_file)
    
    if not lock.acquire():
        print(f"[Workflow Lock] Another instance of run_workflow is already running (locked on {lock_file}). Exiting.")
        sys.exit(0)
        
    try:
        if args.one_shot:
            log_workflow("Workflow Engine: Running in one-shot mode." + (" [僅切片模式]" if args.chunking_only else ""))
            scan_new_files()
            process_active_tasks(args.chunking_only)
        else:
            run_loop(args.chunking_only)
    finally:
        lock.release()
