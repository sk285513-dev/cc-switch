import sys, re

path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the bad insert around line 1875
bad_insert = '''    let selectedGpu = 0;
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

      // ϥαM GPU Parallel Orchestration Agent ƶ Slot
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
        res.status(500).json({ error: GPU Ƶ{իץ:  });
      }
      return;
    }'''

if bad_insert in content:
    content = content.replace(bad_insert, '')
    print('Removed bad insertion.')

old_code = '''    let selectedGpu = 0;
    try {
      if (timedOut) {
        console.log("[MULTIMODAL GPU ENGINE] Request already timed out before GPU selection, aborting.");
        return;
      }
      // 使用專屬 GPU Parallel Orchestration Agent 取得 Slot
      selectedGpu = await gpuOrchestrator.acquireSlot(filePath);
      if (timedOut) {
        console.log("[MULTIMODAL GPU ENGINE] Request already timed out during GPU slot acquisition, releasing slot.");
        gpuOrchestrator.releaseSlot(selectedGpu);
        return;
      }
    } catch (e: any) {
      console.error([MULTIMODAL GPU ENGINE] Failed to acquire GPU slot: );
      if (!res.headersSent && !timedOut) {
        res.status(500).json({ error: GPU 資源調度失敗:  });
      }
      return;
    }'''

new_code = '''    let selectedGpu = 0;
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

      // 使用專屬 GPU Parallel Orchestration Agent 取得 Slot
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
    }'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print('Updated target code successfully.')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

