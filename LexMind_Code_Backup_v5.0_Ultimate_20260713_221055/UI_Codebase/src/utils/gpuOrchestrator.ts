import { exec } from "child_process";
import os from "os";
import path from "path";

export interface GpuStat {
  index: number;
  temp: number;
  util: number;
  vram_used: number;
  vram_total: number;
}

export interface OrchestratorStatus {
  queueLength: number;
  activeGpuLoads: { [key: number]: number };
  concurrencyLimit: number;
  isPaused: boolean;
  pausedReason: string;
  systemRamUsagePercent: number;
  maxGpuTemperature: number;
}

interface QueueItem {
  filePath: string;
  resolve: (gpuIndex: number) => void;
  reject: (err: Error) => void;
  timestamp: number;
}

class GpuOrchestrator {
  private activeGpuLoads: { [key: number]: number } = { 0: 0, 1: 0 };
  private queue: QueueItem[] = [];
  private concurrencyLimit: number = 2; // Default start limit: 1 task per GPU
  private isPaused: boolean = false;
  private pausedReason: string = "";
  
  // Bounds
  private readonly minConcurrency = 2;
  private readonly maxConcurrencyLimit = 4; // Up to 2 tasks per GPU
  
  // Telemetry caching
  private lastGpuStats: GpuStat[] | null = null;
  private lastStatsTime: number = 0;

  constructor() {
    // Start periodic background health check and queue processing every 5 seconds
    setInterval(() => {
      this.checkSystemHealthAndScale().then(() => {
        this.processQueue();
      });
    }, 5000);
  }

  public async getRealGpuStats(): Promise<GpuStat[] | null> {
    const now = Date.now();
    if (this.lastGpuStats && now - this.lastStatsTime < 1500) {
      return this.lastGpuStats;
    }

    return new Promise((resolve) => {
      exec(
        "nvidia-smi --query-gpu=index,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits",
        { timeout: 3000 },
        (err, stdout) => {
          if (err) {
            console.warn("[GPU ORCHESTRATOR] Failed to query GPU stats via nvidia-smi:", err.message);
            resolve(this.lastGpuStats); // return cached on error
            return;
          }
          try {
            const lines = stdout.trim().split("\n");
            const gpus: GpuStat[] = [];
            for (const line of lines) {
              const parts = line.split(",").map((p) => p.trim());
              if (parts.length >= 5) {
                gpus.push({
                  index: parseInt(parts[0]),
                  temp: parseInt(parts[1]),
                  util: parseInt(parts[2]),
                  vram_used: parseInt(parts[3]),
                  vram_total: parseInt(parts[4]),
                });
              }
            }
            this.lastGpuStats = gpus;
            this.lastStatsTime = Date.now();
            resolve(gpus);
          } catch (e) {
            console.warn("[GPU ORCHESTRATOR] Error parsing nvidia-smi output:", e);
            resolve(this.lastGpuStats);
          }
        }
      );
    });
  }

  /**
   * Acquire a slot for a parsing task. Resolves to the selected GPU index (0 or 1)
   * when a slot becomes available under current system limits.
   */
  public acquireSlot(filePath: string): Promise<number> {
    return new Promise<number>((resolve, reject) => {
      console.log(`[GPU ORCHESTRATOR] Queueing task for file: ${path.basename(filePath)}`);
      this.queue.push({
        filePath,
        resolve,
        reject,
        timestamp: Date.now()
      });
      // Try to process immediately
      this.processQueue();
    });
  }

  /**
   * Release a task's slot on a specific GPU, decrementing its load and scheduling next tasks.
   */
  public releaseSlot(gpuIndex: number): void {
    const prevLoad = this.activeGpuLoads[gpuIndex] || 0;
    this.activeGpuLoads[gpuIndex] = Math.max(0, prevLoad - 1);
    console.log(
      `[GPU ORCHESTRATOR] Released slot on GPU ${gpuIndex}. Remaining active loads: GPU0=${this.activeGpuLoads[0]}, GPU1=${this.activeGpuLoads[1]}`
    );
    this.processQueue();
  }

  /**
   * Returns current status and telemetry of the Orchestrator.
   */
  public async getOrchestratorStatus(): Promise<OrchestratorStatus> {
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const ramPercent = totalMem > 0 ? (totalMem - freeMem) / totalMem : 0;
    const gpus = await this.getRealGpuStats();
    const maxTemp = gpus && gpus.length > 0 ? Math.max(...gpus.map((g) => g.temp)) : 0;

    return {
      queueLength: this.queue.length,
      activeGpuLoads: { ...this.activeGpuLoads },
      concurrencyLimit: this.concurrencyLimit,
      isPaused: this.isPaused,
      pausedReason: this.pausedReason,
      systemRamUsagePercent: parseFloat((ramPercent * 100).toFixed(1)),
      maxGpuTemperature: maxTemp
    };
  }

  /**
   * Monitors system memory and GPU temperatures to dynamically scale workload capacity.
   */
  private async checkSystemHealthAndScale(): Promise<void> {
    const gpus = await this.getRealGpuStats();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();
    const ramPercent = totalMem > 0 ? (totalMem - freeMem) / totalMem : 0;

    let maxTemp = 0;
    if (gpus && gpus.length > 0) {
      maxTemp = Math.max(...gpus.map((g) => g.temp));
    }

    const ramOverloaded = ramPercent >= 0.90;
    const gpuOverheated = maxTemp >= 80;

    // Check for Emergency Pause Thresholds
    if (ramOverloaded || gpuOverheated) {
      if (!this.isPaused) {
        this.isPaused = true;
        const reasons = [];
        if (ramOverloaded) reasons.push(`系統記憶體 ${(ramPercent * 100).toFixed(1)}% (閾值 90%)`);
        if (gpuOverheated) reasons.push(`GPU 溫度 ${maxTemp}°C (閾值 80°C)`);
        this.pausedReason = reasons.join("、");
        console.error(
          `[GPU ORCHESTRATOR] 🛑 系統過載安全保護啟動！原因: ${this.pausedReason}。暫停派送新任務。`
        );
      }
      return;
    }

    // Check for Recovery to resume from pause
    if (this.isPaused) {
      const ramCooled = ramPercent < 0.85;
      const gpuCooled = maxTemp < 75;
      if (ramCooled && gpuCooled) {
        this.isPaused = false;
        this.pausedReason = "";
        console.log(
          `[GPU ORCHESTRATOR] ✅ 系統已恢復安全狀態 (RAM: ${(ramPercent * 100).toFixed(1)}%, Max Temp: ${maxTemp}°C)，重新開始排程。`
        );
      } else {
        // Still cooling down
        return;
      }
    }

    // Dynamic Scale Down
    const shouldScaleDown = maxTemp >= 78 || ramPercent >= 0.88;
    // Dynamic Scale Up
    const shouldScaleUp = maxTemp < 72 && ramPercent < 0.80;

    if (shouldScaleDown && this.concurrencyLimit > this.minConcurrency) {
      this.concurrencyLimit--;
      console.warn(
        `[GPU ORCHESTRATOR] ⚠️ 系統溫度/記憶體偏高 (RAM: ${(ramPercent * 100).toFixed(1)}%, Max Temp: ${maxTemp}°C)，調降最大併發量至 ${this.concurrencyLimit}`
      );
    } else if (shouldScaleUp && this.concurrencyLimit < this.maxConcurrencyLimit && this.queue.length > 0) {
      // Only scale up if there's actual queue pressure to avoid unnecessarily increasing limit
      this.concurrencyLimit++;
      console.log(
        `[GPU ORCHESTRATOR] 🚀 系統資源充裕且佇列積壓，調高最大併發量至 ${this.concurrencyLimit} (RAM: ${(ramPercent * 100).toFixed(1)}%, Max Temp: ${maxTemp}°C)`
      );
    }
  }

  /**
   * Main scheduling logic. Processes the queue, checks concurrency constraints,
   * performs smart GPU selection, and assigns tasks.
   */
  private async processQueue(): Promise<void> {
    if (this.queue.length === 0) return;

    if (this.isPaused) {
      console.log(`[GPU ORCHESTRATOR] Scheduler paused due to: ${this.pausedReason}. Tasks pending in queue: ${this.queue.length}`);
      return;
    }

    const currentRunning = (this.activeGpuLoads[0] || 0) + (this.activeGpuLoads[1] || 0);
    if (currentRunning >= this.concurrencyLimit) {
      // At capacity, wait for active tasks to complete or scale up during periodic ticks
      return;
    }

    // Pull next item
    const item = this.queue.shift();
    if (!item) return;

    try {
      const gpus = await this.getRealGpuStats();
      let selectedGpu = 0;

      if (gpus && gpus.length >= 2) {
        const gpu0FreeVram = gpus[0].vram_total - gpus[0].vram_used;
        const gpu1FreeVram = gpus[1].vram_total - gpus[1].vram_used;

        if (gpus[0].util > gpus[1].util + 15) {
          selectedGpu = 1;
        } else if (gpus[1].util > gpus[0].util + 15) {
          selectedGpu = 0;
        } else {
          selectedGpu = gpu0FreeVram >= gpu1FreeVram ? 0 : 1;
        }
        console.log(
          `[GPU ORCHESTRATOR] Smart Selected GPU ${selectedGpu} based on nvidia-smi: GPU0(util=${gpus[0].util}%, freeVram=${gpu0FreeVram}MB), GPU1(util=${gpus[1].util}%, freeVram=${gpu1FreeVram}MB)`
        );
      } else {
        selectedGpu = (this.activeGpuLoads[0] || 0) <= (this.activeGpuLoads[1] || 0) ? 0 : 1;
        console.log(
          `[GPU ORCHESTRATOR] Fallback Selected GPU ${selectedGpu} based on active loads counter: GPU0=${this.activeGpuLoads[0]}, GPU1=${this.activeGpuLoads[1]}`
        );
      }

      // Lock slot
      const prevLoad = this.activeGpuLoads[selectedGpu] || 0;
      this.activeGpuLoads[selectedGpu] = prevLoad + 1;
      
      console.log(
        `[GPU ORCHESTRATOR] Dispatched task on GPU ${selectedGpu} (Current running: ${currentRunning + 1}/${this.concurrencyLimit}, Queue size: ${this.queue.length})`
      );
      
      item.resolve(selectedGpu);
    } catch (e) {
      console.error("[GPU ORCHESTRATOR] Exception in queue processing, returning item to queue:", e);
      this.queue.unshift(item); // Push back
    }

    // Process recursively in case there are more slots available
    if (this.queue.length > 0) {
      process.nextTick(() => this.processQueue());
    }
  }
}

export const gpuOrchestrator = new GpuOrchestrator();
