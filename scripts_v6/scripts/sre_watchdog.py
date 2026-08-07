import os
import time
import psutil
import sys

if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from scripts.win32_kernel import KernelEvent, KernelJobObject

TIMEOUT_SEC = 1800 # 30分鐘無心跳判定為死鎖
HEARTBEAT_EVENT_NAME = "Global\\LexMind_Heartbeat_Event"
JOB_NAME = "Global\\LexMind_Job"

import asyncio
import smtplib
from email.message import EmailMessage

async def send_alert_email(subject, body):
    """
    【修復 Issue 19】將信件發送改為 asyncio 非同步執行，避免 smtplib 阻塞主迴圈與 GIL
    """
    def _send_sync():
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = subject
            msg['From'] = "watchdog@lexmind.local"
            msg['To'] = "admin@lexmind.local"
            
            # 此處為模擬 SMTP 連線，可根據實際環境配置
            # server = smtplib.SMTP('localhost', 1025)
            # server.send_message(msg)
            # server.quit()
            print(f"[Watchdog Email] 已非同步發送警報: {subject}")
        except Exception as e:
            print(f"[Watchdog Email Error] 發送失敗: {e}")
            
    await asyncio.to_thread(_send_sync)

async def monitor_workflow_async():
    print(f"[Watchdog] 啟動核心級防偽造 (Anti-Spoofing) 監控: {HEARTBEAT_EVENT_NAME}")
    try:
        event = KernelEvent(HEARTBEAT_EVENT_NAME)
    except Exception as e:
        print(f"[Watchdog Error] 無法存取核心事件: {e}")
        return

    last_io_count = 0
    
    while True:
        # 等待心跳，最多等待 30 分鐘。由於是同步 C 擴充元件，交給 to_thread 避免阻塞事件迴圈
        has_heartbeat = await asyncio.to_thread(event.wait, TIMEOUT_SEC * 1000)
        
        try:
            job = KernelJobObject(JOB_NAME, open_only=True)
            io_info = job.get_io_counters()
            current_io_count = io_info.WriteTransferCount + io_info.ReadTransferCount
            
            if not has_heartbeat:
                msg = "偵測到 30 分鐘零心跳 (Event Timeout)！發動核心級斬殺..."
                print(f"[Watchdog Alert] {msg}")
                asyncio.create_task(send_alert_email("Watchdog Timeout Alert", msg))
                job.terminate(1)
                job.close()
                break
                
            # Phase 7.9: 反制心跳偽造 (Heartbeat Spoofing)
            io_diff = current_io_count - last_io_count
            if last_io_count > 0 and io_diff < 1024 * 1024:
                msg = f"偵測到【心跳偽造】！IO吞吐僅 {io_diff} bytes。發動強制斬殺..."
                print(f"[Watchdog Alert] {msg}")
                asyncio.create_task(send_alert_email("Watchdog Spoofing Alert", msg))
                job.terminate(1)
                job.close()
                break
                
            # 【修復 Issue 10】RAM 監控防護，避免 SSD 虛擬記憶體導致 I/O 阻塞
            mem = psutil.virtual_memory()
            if mem.percent >= 92.0:
                msg = f"偵測到 RAM 負載過高 ({mem.percent}%)！為避免觸發 SSD Swap 導致全機癱瘓，發動預防性斬殺..."
                print(f"[Watchdog Alert] {msg}")
                asyncio.create_task(send_alert_email("Watchdog OOM Alert", msg))
                job.terminate(1)
                job.close()
                break
                
            last_io_count = current_io_count
            job.close()
        except Exception as e:
            # 如果找不到 Job，代表工作流沒在跑，繼續等待
            pass

    event.close()

if __name__ == "__main__":
    asyncio.run(monitor_workflow_async())

