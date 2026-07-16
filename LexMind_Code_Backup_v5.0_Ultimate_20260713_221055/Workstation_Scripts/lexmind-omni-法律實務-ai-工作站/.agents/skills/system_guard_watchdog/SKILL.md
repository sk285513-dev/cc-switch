---
name: system-guard-watchdog
description: Monitors frontend batch ingestion queues, checks resources (RAM / Temperature) every 15s to pause batch processes before CPU/GPU crash. Use this skill when modifying, debugging, or tuning resource limits and safety pause behaviors.
---

# System Guard Watchdog Agent Skill

This skill defines the responsibilities and guidelines for the dedicated System Guard Watchdog Agent. This agent operates on the client-side (frontend React UI) to prevent system crashes during batch ingestion of large legal files.

## File Locations
- **Frontend Watchdog Implementation**: [App.tsx](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/src/App.tsx) (runs resource check loops and controls queue pause/resume states)
- **Express Backend Status API**: [server.ts](file:///c:/Users/temp/antigravity/LexMind-Omni-法律實務-AI-工作站/server.ts) (exposes raw system statistics at `/api/system-status`)

---

## Agent Guidelines & Tuning

1. **Watchdog Check Loop**:
   - The loop runs every 15 seconds inside `runBatchIngestProcess` when processing the queue.
   - It queries `/api/system-status` to retrieve CPU load, host RAM usage, and GPU temperature.

2. **Safety Thresholds**:
   - **System RAM Overload**: If host memory usage $\ge 90\%$.
   - **GPU Temperature Overload**: If any GPU temperature $\ge 80^\circ\text{C}$.
   - If either condition is met, the watchdog sets the queue status to paused and displays warning alerts.

3. **Automatic Recovery**:
   - The watchdog continues checking resources every 15 seconds while paused.
   - It automatically resumes execution when RAM usage drops below $85\%$ and GPU temperature drops below $75^\circ\text{C}$.

4. **Debugging Guidelines**:
   - If you need to tune safety limits, change the resource polling interval, or modify frontend overload UI notifications, do so strictly within the `App.tsx` watchdog loop. Keep backend endpoints stateless.
