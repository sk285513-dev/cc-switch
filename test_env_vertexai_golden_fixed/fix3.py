import sys

path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

bad_start = -1
bad_end = -1
for i, line in enumerate(lines):
    if 'let selectedGpu = 0;' in line:
        chunk = ''.join(lines[i:i+40])
        if 'history.push({ role: ' in chunk:
            bad_start = i
            for j in range(i, i+40):
                if 'history.push({ role: ' in lines[j]:
                    bad_end = j
                    break
            break

if bad_start != -1 and bad_end != -1:
    print('Found bad block from ' + str(bad_start) + ' to ' + str(bad_end) + '. Deleting it.')
    del lines[bad_start:bad_end]
else:
    print('Bad block not found')

# Fix the good block
good_found = False
for i, line in enumerate(lines):
    if 'let selectedGpu = 0;' in line:
        chunk = ''.join(lines[i:i+30])
        if 'await gpuOrchestrator.acquireSlot(filePath);' in chunk:
            if 'activeIngestProgresses.set' not in chunk:
                # Needs replacement!
                print('Replacing good block...')
                # We will manually replace the exact old chunk
                old_chunk_end = i
                for j in range(i, i+30):
                    if 'return;' in lines[j] and 'res.status(500).json' in lines[j-2]:
                        old_chunk_end = j + 1
                        break
                
                # Create the new chunk
                new_chunk = '''    let selectedGpu = 0;
    const progressId = parse_;
    try {
      if (timedOut) {
        console.log("[MULTIMODAL GPU ENGINE] Request already timed out before GPU selection, aborting.");
        return;
      }
      
      activeIngestProgresses.set(progressId, {
        filename: path.basename(filePath),
        totalChunks: 100,
        processedChunks: 0,
        status: "queued",
        message: "已加入佇列，等待系統釋放記憶體與顯卡資源...",
        timestamp: Date.now()
      });

      // 使用專門的 GPU Parallel Orchestration Agent 排隊索取 Slot
      selectedGpu = await gpuOrchestrator.acquireSlot(filePath);
      if (timedOut) {
        console.log("[MULTIMODAL GPU ENGINE] Request already timed out during GPU slot acquisition, releasing slot.");
        gpuOrchestrator.releaseSlot(selectedGpu);
        activeIngestProgresses.delete(progressId);
        return;
      }
    } catch (e: any) {
      console.error([MULTIMODAL GPU ENGINE] Failed to acquire GPU slot: );
      activeIngestProgresses.delete(progressId);
      if (!res.headersSent && !timedOut) {
        res.status(500).json({ error: GPU 資源調度失敗:  });
      }
      return;
    }\n'''
                
                lines[i:old_chunk_end] = [new_chunk]
                print('Replaced good block!')
            else:
                print('Good block already has set() logic.')
            break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
