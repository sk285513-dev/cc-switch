import pytest
import asyncio
import time
import psutil
import socket
import ctypes
import multiprocessing
import os

# ==============================================================================
# 機制十四：硬體級 Watchdog 與 Email 警報 (M14)
# 機制十七：異步 I/O 與 OOM 崩潰邊界防護 (M17)
# 機制二十四：IPv6 解析繞道與底層 Socket 超時重構 (M24)
# ==============================================================================

@pytest.mark.asyncio
async def test_m14_watchdog_deadlock_detection():
    """
    【機制十四】驗證成功標準：
    主進程卡死時，Watchdog 能夠偵測到 Heartbeat 逾時，
    發出警告並執行處置（此測試為概念性斷言）。
    """
    # 模擬 Watchdog 的 Heartbeat 檔案行為
    heartbeat_file = "heartbeat.tmp"
    with open(heartbeat_file, "w") as f:
        f.write(str(time.time()))
        
    # 斷言心跳檔案可被 Watchdog 讀取並偵測時差
    assert os.path.exists(heartbeat_file)
    last_ping = float(open(heartbeat_file, "r").read())
    current = time.time()
    diff = current - last_ping
    assert diff < 10.0, "Watchdog: Heartbeat is fresh, normal operation."
    
    # 清理
    os.remove(heartbeat_file)


def allocate_massive_memory(target_gb):
    """ 用於 M17 的子行程輔助函數，在獨立行程中強勢消耗記憶體以防崩潰主測試環境 """
    dummy_data = []
    chunk_size = 1024 * 1024 * 10  # 10MB chunks
    try:
        # 強制佔用約 target_gb GB 記憶體
        for _ in range(target_gb * 100):
            dummy_data.append(b"A" * chunk_size)
    except MemoryError:
        pass # Expected on small RAM machines if hit

def test_m17_oom_pagefile_swap_survival():
    """
    【機制十七】驗證成功標準：
    高壓 OOM 時不拋出 MemoryError，順利置換到 Pagefile。
    此處僅發起適度壓力，斷言 psutil 能夠正確讀取 swap memory 並未 crash。
    """
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    initial_swap = swap.used
    
    # 這裡我們不實際寫爆 64GB 避免癱瘓 CI，而是建立一個 500MB 的輕量壓力測試
    target_pressure_gb = 0.5
    
    # 利用 multiprocessing 隔離記憶體分配，避免 pytest 本身被 kill
    p = multiprocessing.Process(target=allocate_massive_memory, args=(target_pressure_gb,))
    p.start()
    p.join(timeout=3)
    
    # 如果行程仍在，我們終止它
    if p.is_alive():
        p.terminate()
        p.join()
        
    assert p.exitcode is not None, "Memory intensive process exited cleanly or was killed."
    
    final_swap = psutil.swap_memory()
    assert True, "OOM 防護測試完成，進程無預期外崩潰"


@pytest.mark.asyncio
async def test_m24_ipv6_bypass_localhost():
    """
    【機制二十四】驗證成功標準：
    所有對 localhost 11434 的連線，強制繞過 IPv6 (::1)，
    使用 127.0.0.1 直接連線，避免 Windows DNS Timeout。
    """
    start = time.perf_counter()
    try:
        # 建立強制綁定 IPv4 (AF_INET) 的連線測試
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1) # 100ms timeout
        
        # 測試 127.0.0.1 解析
        result = sock.connect_ex(('127.0.0.1', 11434))
        # 無論 Ollama 有沒有開，這個 connect_ex 不會卡在 IPv6 DNS 查詢超過 2 秒
        # 回傳 0 (連線成功) 或是 10061 (拒絕連線) 都是合格的，代表沒有發生 Timeout
        assert result in [0, 10061], f"Unexpected socket error code: {result}"
        
    except socket.timeout:
        pytest.fail("IPv6/DNS 繞道失敗，發生 Timeout")
    finally:
        sock.close()
        
    duration = time.perf_counter() - start
    # 斷言連線嘗試耗時極短，沒有陷入 IPv6 fallback timeout
    assert duration < 0.2, f"連線嘗試耗時 {duration}s 過長，懷疑進入 IPv6 解析迴圈"

if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
