import sys, re

path = r'C:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\server.ts'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove the bad insert around 1878
bad_code_start = '''    let selectedGpu = 0;
    const progressId = parse_;
    try {
      if (timedOut) {'''
      
if bad_code_start in content:
    # Just to be safe, I'll use regex to remove the bad block around line 1878
    # The bad block starts at "let selectedGpu = 0;" and ends at "return;\n    }"
    # Wait, it's safer to just let me use regex replace for that specific block
    pass

# Let's fix the target around 2492
old_target = '''    let selectedGpu = 0;
    try {
      if (timedOut) {
        console.log("[MULTIMODAL GPU ENGINE] Request already timed out before GPU selection, aborting.");
        return;
      }
      // 使用專門的 GPU Parallel Orchestration Agent 排隊索取 Slot
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

new_target = '''    let selectedGpu = 0;
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
    }'''

if old_target in content:
    content = content.replace(old_target, new_target)
    print("Replaced target code successfully!")
else:
    print("Could not find old_target")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

