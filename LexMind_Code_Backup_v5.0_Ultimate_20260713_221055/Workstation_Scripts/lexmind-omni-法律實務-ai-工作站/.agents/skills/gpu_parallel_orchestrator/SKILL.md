---
name: gpu-parallel-orchestrator
description: Manages load balancing, system telemetry monitoring, and dynamic concurrency scaling (increasing/decreasing parallel workloads) for dual GPUs. Use this skill when modifying, debugging, or tuning multi-GPU scheduling, dispatch queueing, or overload safety guards.
---

# GPU Parallel Orchestration Agent Skill

This skill defines the responsibilities and guidelines for the dedicated GPU Parallel Orchestration Agent. All multi-GPU load balancing, telemetry, and capacity scaling logic must be isolated within this module.

## File Locations
- **Orchestrator Implementation**: [gpuOrchestrator.ts](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/src/utils/gpuOrchestrator.ts)
- **Express Backend Router**: [server.ts](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/server.ts) (delegates dispatching and telemetry to the Orchestrator)
- **Frontend UI Integration**: [App.tsx](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/src/App.tsx) (receives telemetry and displays active state/reports)

---

## Agent Responsibilities

1. **GPU Task Dispatching**:
   - Queue up parsing tasks in a FIFO pending queue.
   - When a slot becomes available, assign the task to the optimal GPU:
     - If GPU 0 utilization is > GPU 1 utilization + 15%: select GPU 1.
     - If GPU 1 utilization is > GPU 0 utilization + 15%: select GPU 0.
     - Otherwise, select the GPU with more free VRAM.
     - Fallback to the GPU with fewer active tasks (`activeGpuLoads`).

2. **Workload Performance Management (Dynamic Scaling)**:
   - **Scale Up (Increase Parallel Workload)**: If both GPU temperatures are below `72°C` and system RAM usage is below `80%` (and there are pending items in the queue), increase `concurrencyLimit` by 1 (up to a maximum of `4`).
   - **Scale Down (Decrease Parallel Workload)**: If any GPU temperature is above `78°C` or system RAM usage is above `88%`, decrease `concurrencyLimit` by 1 (down to a minimum of `2`).
   - **Emergency Pause**: If any GPU temperature is above `80°C` or system RAM usage is above `90%`, immediately trigger safety pause (`isPaused = true`), stopping new task dispatches until the system cools down (temperature drops below `75°C` and RAM drops below `85%`).

3. **Telemetry & Diagnostics**:
   - Provide real-time statistics including queue length, active loads, concurrency limits, pause status, system memory usage, and GPU temperature.
   - Cache `nvidia-smi` stats for 1.5 seconds to minimize resource overhead.

---

## Code Guidelines & Tuning

- **Do NOT check VRAM percentages for safety guards**: Ollama pre-allocates and locks remaining VRAM for its KV Cache on Windows WDDM, which causes false-positive overloads. Monitor GPU temperature and system RAM usage instead.
- **Isolate future changes**: If there are performance issues, bugs in task routing, or adjustments to temperature/RAM thresholds, modify **ONLY** `src/utils/gpuOrchestrator.ts`. Do not write ad-hoc scheduling logic in `server.ts` or `App.tsx`.
- **Validation**:
  - Always run typechecking: `npx tsc --noEmit`
  - Always run production build: `npm run build`
  - Ensure the Express backend continues to run in the background. Check logs to verify task queueing and dispatch logs.
