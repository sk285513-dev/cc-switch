# ==============================================================================
# [CRITICAL DEPENDENCY WARNING] Group 2: 核心加工管線 (Core Pipeline)
# ------------------------------------------------------------------------------
# ⚠️ 此檔案屬於高度解耦架構的【Group 2】。
# 修改此檔案時，必須確保多執行緒併發 (Concurrency) 及跨進程 JSON 狀態寫入的安全。
# 任何資料輸出格式的變動，都會直接導致 Group 5 (UI) 與 Group 8 (KPI) 癱瘓！
# 修改前請務必參閱：PIPELINE_DEPENDENCIES.md
# ==============================================================================
# -*- coding: utf-8 -*-
"""
Phase 7.8 Windows Kernel API 封裝 (OOP)
負責提供跨進程 Named Mutex、Named Event 以及 Job Object 管理。
"""
import ctypes
from ctypes import wintypes
import time
import sys

kernel32 = ctypes.windll.kernel32

# Win32 Constants
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_ABANDONED = 0x00000080
INFINITE = 0xFFFFFFFF

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.POINTER(wintypes.ULONG)),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]
    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]

class KernelMutex:
    """跨進程具名互斥鎖 (Named Mutex)"""
    def __init__(self, name: str):
        self.name = name
        # CreateMutexW 會建立或開啟已存在的 Mutex
        self.handle = kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise ctypes.WinError()

    def acquire(self, timeout_ms: int = INFINITE) -> bool:
        """請求 Mutex。由 OS 排程器控制，期間 CPU 負載為 0%"""
        result = kernel32.WaitForSingleObject(self.handle, timeout_ms)
        if result == WAIT_OBJECT_0 or result == WAIT_ABANDONED:
            return True
        return False

    def release(self):
        kernel32.ReleaseMutex(self.handle)

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self):
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class KernelEvent:
    """跨進程具名事件 (Named Event) 用於心跳"""
    def __init__(self, name: str):
        self.name = name
        # CreateEventW (bManualReset=False, bInitialState=False)
        self.handle = kernel32.CreateEventW(None, False, False, self.name)
        if not self.handle:
            raise ctypes.WinError()

    def signal(self):
        """發送事件信號 (Heartbeat)"""
        kernel32.SetEvent(self.handle)

    def wait(self, timeout_ms: int) -> bool:
        """等待事件。由 OS 負責計時與喚醒，無視 NTFS 延遲"""
        result = kernel32.WaitForSingleObject(self.handle, timeout_ms)
        return result == WAIT_OBJECT_0

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

class KernelJobObject:
    """工作物件 (Job Object) 用於自動管理進程樹"""
    def __init__(self, name: str = None, open_only: bool = False):
        if open_only:
            # 存取權限: JOB_OBJECT_TERMINATE = 0x0008
            self.handle = kernel32.OpenJobObjectW(0x0008, False, name)
        else:
            self.handle = kernel32.CreateJobObjectW(None, name)
            if self.handle:
                self._set_kill_on_close()
                
        if not self.handle:
            raise ctypes.WinError()

    def _set_kill_on_close(self):
        """設定 Job Object 在 Handle 關閉時自動斬殺所有關聯進程"""
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        
        # SetInformationJobObject (JobObjectExtendedLimitInformation = 9)
        result = kernel32.SetInformationJobObject(
            self.handle,
            9, 
            ctypes.byref(info),
            ctypes.sizeof(info)
        )
        if not result:
            raise ctypes.WinError()

    def assign_current_process(self):
        """將當前進程加入 Job。其衍生的子進程會自動繼承"""
        current_process = kernel32.GetCurrentProcess()
        result = kernel32.AssignProcessToJobObject(self.handle, current_process)
        if not result:
            raise ctypes.WinError()

    def get_io_counters(self):
        """取得 Job Object 的 IO_COUNTERS 數據，用於防禦心跳偽造"""
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        ret_len = wintypes.DWORD()
        result = kernel32.QueryInformationJobObject(
            self.handle,
            9, # JobObjectExtendedLimitInformation
            ctypes.byref(info),
            ctypes.sizeof(info),
            ctypes.byref(ret_len)
        )
        if not result:
            raise ctypes.WinError()
        return info.IoInfo

    def terminate(self, exit_code: int = 1):
        """瞬間無情斬殺整個進程樹"""
        result = kernel32.TerminateJobObject(self.handle, exit_code)
        if not result:
            raise ctypes.WinError()

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

