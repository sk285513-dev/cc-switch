import os
import re

out_file = r'C:\LocalAI_Workstation\prompt_for_coder.txt'
prompt_text = '''请不要只给建议，也不要只给 diff。请直接审查并修复我的 LexMind V6 工作流代码，最后输出“可直接覆盖原文件”的完整代码。

我会按顺序上传这些完整原始文件：
1. run_workflow.py
2. workflow_helper.py
3. manifest_manager.py
4. stt_runner.py
5. merge_transcript.py
6. markdown_formatter.py
7. config.yaml

【你的工作目标】
修复工作流的并发调度、配置读取、manifest 状态写入竞争、失败恢复与 retry 行为；必须保持现有模块接口和文件名可用，不能为了重构而破坏现有 PowerShell 启动器、watchdog、数据库、chunks 或 manifest 格式。

【已确认的系统事实】
- run_workflow.py 负责扫描、调度 preprocess、chunk planner、STT、merge、formatter。
- stt_runner.py 负责按 chunk 并发执行 STT，并写 task 的 chunks manifest。
- merge_transcript.py 负责合并转录，必要时有 raw fallback / degraded 模式。
- manifest_manager.py 已经有 ManifestManager、文件锁、线程锁、atomic replace、Windows PermissionError retry。
- workflow_helper.py 负责 load_config、get_resolved_paths、ensure_dirs、日志、API key 状态。
- manifest 主状态流应为：
  queued → chunked → transcribed → merged → completed
- 每个 manifest 还有 steps，例如：
  preprocess / chunk_planner / stt / merge / formatter
- 系统可能使用 Gemini AI Studio 或 Vertex AI。
- Windows 环境；必须考虑文件被 Defender、索引服务或其他 Python process 短暂占用的情况。
- 不能输出任何密钥、token、service-account JSON 内容或敏感环境变量。

【必须检查并修复的项目】

1) 配置读取必须统一
- 所有 stt_engine、merge_engine、vertex_ai_project、vertex_ai_location、credential 等设置，必须统一从同一个配置层读取。
- 目前疑似有的文件使用 config.get("settings", {}).get(...)，另一些却直接 config.get(...)。
- 请以现有 config.yaml 的真实结构为准，建立安全兼容读取方式。
- 不要因为读取层级不一致，误把 Vertex AI 当成 Gemini，或错误初始化 QuotaManager。

2) Manifest 写入必须消除竞争条件
- 所有 task manifest 的“读取 → 修改 → 写入”必须经由 ManifestManager 或 update_manifest 完成。
- 不允许 run_workflow.py、stt_runner.py、merge_transcript.py 对同一个 task manifest 使用无锁的：
  open(...) → json.load(...) → 修改 → atomic_json_dump(...)
- 必须避免以下覆盖问题：
  - STT 刚把任务恢复为 status="chunked"、steps["stt"]="pending"，workflow 又把旧内存中的 manifest 写成 failed；
  - merge 写入 merged 状态时，被 workflow 用旧数据覆盖；
  - formatter 完成时覆盖 merge 的 paths 或 degraded 信息。
- chunks manifest 如果会被多个线程或进程修改，也要使用同等安全的锁和原子写入策略。

3) 调度必须严格分相位，不能混用并发额度
- queued 任务只能进入 preprocess/chunk planner 调度，使用 PREPROCESS_CONCURRENCY。
- chunked 任务才进入 STT/merge/formatter 调度，使用 STT_CONCURRENCY 或 adaptive concurrency。
- 在同一轮 batch 中，不允许 queued 任务因为 chunked 任务存在或因为进入 STT 时段，就跟着使用 STT 高并发一起执行。
- 每轮调度只选择一种任务类别：
  a. 若有 chunked，优先只处理 chunked；
  b. 否则处理 queued；
  c. 已 completed / failed / needs_review 的任务不能重新进入 active batch，除非代码已有明确且安全的恢复机制。
- 保留现有优先级排序逻辑，但移除或替代任何硬编码 task ID 黑名单。若确有暂停任务需求，应使用 manifest 状态，例如 hold 或 needs_review，或清楚的配置项，不能静默跳过某一个固定任务 ID。

4) 失败、retry 与状态恢复
- STT 任一 chunk 最终失败时，任务必须可靠回到：
  status="chunked"
  steps["stt"]="pending"
  且失败 chunk 可安全重试。
- workflow 的异常处理在写 failed 前，必须重新在锁内读取当前 manifest：
  - 如果当前状态已经是 chunked，且 stt 是 pending，则不得覆盖为 failed；
  - 如果 merge 已写成 merged 或 formatter 已写成 completed，也不得用旧异常覆盖；
  - 记录 error 时不能删除现有 paths、steps、degraded_reason、merge_mode、needs_review 等字段。
- merge 的 Vertex timeout / raw fallback 行为必须保留：
  - raw fallback 成功时，应安全写入 steps["merge"]="completed"、status="merged"、输出 paths；
  - 保留 degraded_reason、merge_mode、retry_count、needs_review；
  - 不得让 workflow 再把已降级但可继续 formatter 的任务打回 failed。
- 对 429、503、UNAVAILABLE、deadline exceeded 保留合理的 backoff/retry；不要制造无限循环或 busy loop。

5) API key 与 Vertex 行为
- Gemini 模式：保留 key pool / QuotaManager 的排他 key 语义，确保 acquire 后必定 finally release。
- Vertex AI 模式：不得错误申请 Gemini key；应使用 ADC / service account 的既有逻辑。
- 如果 STT 与 merge 都是 Vertex AI，调度器不得因为默认值或错误配置而错误启用 QuotaManager。
- 不要打印完整 key、token 或 credential path；日志只能显示脱敏信息。

6) 保持兼容
- 保留现有公开函数名和调用约定，尤其是：
  run_stt(task_id, exclusive_key=None)
  merge_workflow(task_id)
  format_markdown(task_id)
  preprocess(task_id)
  plan_chunks(task_id)
  process_active_tasks(...)
  run_loop(...)
- 保留 CLI：
  --one-shot
  --chunking-only
- 保留 SingleInstanceLock 或提供等价的跨平台单实例保护。
- 不要引入新的第三方依赖，除非现有 requirements 明确已有。
- 不要把系统改成 async，也不要重写整个架构；请做最小但完整的可靠性修复。

【输出格式，必须严格遵守】
第一部分：用不超过 20 条要点列出你实际发现的问题与修复理由。

第二部分：按文件分别输出完整可覆盖代码，格式必须如下：

===== FILE: run_workflow.py =====
`python
完整文件内容
`

===== FILE: workflow_helper.py =====
`python
完整文件内容
`

依此类推。

第三部分：给出 Windows PowerShell 验证命令，必须包括：
1. Python 语法检查；
2. one-shot chunking-only 测试；
3. one-shot 完整流程测试；
4. workflow.log 和 chunkerrors.log 的 tail 命令；
5. 检查 manifest 状态与 steps 的命令；
6. 检查是否有多个 workflow Python 进程的命令。

以下是所有完整文件的原始内容：'''

files_to_read = [
    r'C:\LocalAI_Workstation\scripts_v6\run_workflow.py',
    r'C:\LocalAI_Workstation\scripts_v6\workflow_helper.py',
    r'C:\LocalAI_Workstation\scripts_v6\manifest_manager.py',
    r'C:\LocalAI_Workstation\scripts_v6\stt_runner.py',
    r'C:\LocalAI_Workstation\scripts_v6\merge_transcript.py',
    r'C:\LocalAI_Workstation\scripts_v6\markdown_formatter.py',
    r'C:\LocalAI_Workstation\config.yaml'
]

with open(out_file, 'w', encoding='utf-8-sig') as out:
    out.write(prompt_text + '\n\n')
    
    for fpath in files_to_read:
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8-sig', errors='ignore') as fp:
                content = fp.read()
            
            # Mask API keys and credentials
            content = re.sub(r'(api_key\s*[:=]\s*[\"\'\\]+)[A-Za-z0-9_\-]+([\"\'\\]+)', r'\1[REDACTED]\2', content, flags=re.IGNORECASE)
            content = re.sub(r'(token\s*[:=]\s*[\"\'\\]+)[A-Za-z0-9_\-]+([\"\'\\]+)', r'\1[REDACTED]\2', content, flags=re.IGNORECASE)
            content = re.sub(r'([A-Za-z0-9_\-]{30,})', r'[REDACTED]', content)
            # specially for config yaml
            content = re.sub(r'(keys:\s*\n(\s*- .+\n)*)', r'keys: [REDACTED]\n', content)
            content = re.sub(r'(credentials:\s*.+)', r'credentials: [REDACTED]', content)
            
            out.write(f'===== FILE: {os.path.basename(fpath)} =====\n')
            if fpath.endswith('.py'):
                out.write('`python\n')
            elif fpath.endswith('.yaml'):
                out.write('`yaml\n')
            else:
                out.write('`\n')
                
            out.write(content)
            
            if not content.endswith('\n'):
                out.write('\n')
            out.write('`\n\n')

print(f'Successfully generated {out_file}')
