import json, glob, os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

manifests = list(Path('A:/manifests').glob('task_*.json'))
manifests = [m for m in manifests if '_chunks' not in m.name]

stats = Counter()
stage_count = Counter()
stt_progress = []
tasks_by_status = defaultdict(list)
source_miss = 0

for mf in manifests:
    try:
        m = json.loads(mf.read_text(encoding='utf-8'))
        tid = m.get('task_id', '')
        if 'mock_' in tid:
            continue
        status = m.get('status', '?')
        steps = m.get('steps', {})
        src = m.get('source_path') or m.get('video_path') or m.get('source_name') or ''
        name = Path(src).stem[:30] if src else '(no source)'
        if not src:
            source_miss += 1

        stats[status] += 1
        tasks_by_status[status].append((tid, name, steps, src))

        # STT chunk progress
        cm = str(mf).replace('.json', '_chunks.json')
        if os.path.exists(cm):
            try:
                chunks = json.loads(open(cm, encoding='utf-8').read())
                done = sum(1 for c in chunks if c.get('status') == 'completed')
                total = len(chunks)
                if total > 0 and done > 0:
                    stt_progress.append((tid[-8:], done, total, name[:25]))
            except Exception:
                pass
    except Exception as e:
        stats['parse_error'] += 1

print('=== 任務狀態總覽 ===')
total_all = sum(stats.values())
for s, c in sorted(stats.items(), key=lambda x: -x[1]):
    pct = c / total_all * 100
    print(f'  {s:15s}: {c:4d} 個  ({pct:5.1f}%)')
print(f'  {"TOTAL":15s}: {total_all:4d} 個')
print(f'  (source 欄位缺失: {source_miss} 個)')

print()
print('=== STT 有進度的任務（Top 15）===')
for tid, done, total, name in sorted(stt_progress, key=lambda x: -x[1]/max(x[2], 1))[:15]:
    pct = done / total * 100
    bar = '█' * int(pct / 10) + '░' * (10 - int(pct / 10))
    print(f'  [{bar}] {pct:5.1f}%  {done:3d}/{total:3d}  {name}')

print()
print('=== chunked 任務 steps 分布 ===')
chunked = tasks_by_status.get('chunked', [])
step_combos = Counter()
for tid, name, steps, src in chunked:
    key = 'pre=%s chunk=%s stt=%s' % (
        steps.get('preprocess', '-'),
        steps.get('chunk_planner', '-'),
        steps.get('stt', '-')
    )
    step_combos[key] += 1
for combo, cnt in step_combos.most_common(5):
    print(f'  {cnt:4d}x  {combo}')

print()
print('=== failed 任務：哪個 step 失敗 ===')
failed = tasks_by_status.get('failed', [])
fail_step = Counter()
for tid, name, steps, src in failed:
    which = [k for k, v in steps.items() if v == 'failed']
    key = ','.join(which) if which else 'no_failed_step_marked'
    fail_step[key] += 1
for combo, cnt in fail_step.most_common(8):
    print(f'  {cnt:4d}x  failed_step={combo}')

print()
print('=== queued 任務：有無 source path ===')
queued = tasks_by_status.get('queued', [])
no_src = sum(1 for tid, name, steps, src in queued if not src)
has_src = len(queued) - no_src
print(f'  有 source: {has_src}  無 source: {no_src}')
if no_src > 0:
    print('  範例（無 source 的 queued 任務）:')
    for tid, name, steps, src in queued:
        if not src:
            print(f'    {tid}  steps={steps}')
            break
