"""
whisper_pool.py — LexMind-Omni 全域 Whisper 資源池（單例模式）

核心設計目標：
- 全系統只加載「1 個」faster-whisper 模型實例。
- 透過 threading.Semaphore(N_GPU) 允許雙 GPU 同步並列推論。
- 加載失敗時提供完整的降備鏈（CUDA float16 → CUDA float32 → CPU int8）。
"""
import threading
import logging
import os


class WhisperPool:
    """全域 Whisper 模型資源池 — 單例 + Semaphore 排隊模式（支援雙 GPU）。"""

    _instance_lock = threading.Lock()
    _model = None
    _model_name = None
    _device = None
    # Semaphore 數量依 GPU 數決定：有 GPU 就允許 2 個並列（雙顯卡），否則 1 個
    _semaphore = None  # 延遲初始化，待 GPU 偵測後設定

    @classmethod
    def _init_semaphore(cls):
        """依偵測到的 GPU 數量初始化 Semaphore。"""
        if cls._semaphore is not None:
            return
        try:
            import ctranslate2
            gpu_count = ctranslate2.get_cuda_device_count()
        except Exception:
            gpu_count = 0
        # 雙 GPU：Semaphore=2；單 GPU：Semaphore=1；純 CPU：Semaphore=1
        parallel = max(1, min(gpu_count, 2))
        cls._semaphore = threading.Semaphore(parallel)
        cls._device = "cuda" if gpu_count > 0 else "cpu"
        logging.info(f"[WhisperPool] 偵測到 {gpu_count} 個 GPU，Semaphore={parallel}，device={cls._device}")

    @classmethod
    def get_model(cls, model_name: str = "medium"):
        """取得（或初始化）全域共享的 Whisper 模型實例。線程安全。"""
        cls._init_semaphore()
        with cls._instance_lock:
            if cls._model is None or cls._model_name != model_name:
                logging.info(
                    f"[WhisperPool] 首次初始化全域 Whisper 模型 '{model_name}'（device={cls._device}）..."
                )
                cls._model = cls._load_model(model_name)
                cls._model_name = model_name
                logging.info(f"[WhisperPool] 模型 '{model_name}' 已就緒，device={cls._device}。")
        return cls._model

    @classmethod
    def _load_model(cls, model_name: str):
        """帶降備鏈的模型加載：CUDA float16 → CUDA float32 → CPU int8 → CPU float32。"""
        from faster_whisper import WhisperModel
        device = cls._device or "cpu"

        if device == "cuda":
            try:
                logging.info(f"[WhisperPool] 嘗試 CUDA float16...")
                model = WhisperModel(model_name, device="cuda", compute_type="float16")
                logging.info(f"[WhisperPool] CUDA float16 加載成功 ✅")
                return model
            except Exception as e:
                logging.warning(f"[WhisperPool] CUDA float16 失敗：{e}，嘗試 CUDA float32...")
            try:
                model = WhisperModel(model_name, device="cuda", compute_type="float32")
                logging.info(f"[WhisperPool] CUDA float32 加載成功 ✅")
                return model
            except Exception as e2:
                logging.warning(f"[WhisperPool] CUDA float32 失敗：{e2}，降備 CPU...")

        # CPU 降備
        try:
            logging.info(f"[WhisperPool] 嘗試 CPU int8...")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logging.info(f"[WhisperPool] CPU int8 加載成功。")
            return model
        except Exception as e:
            logging.warning(f"[WhisperPool] CPU int8 失敗：{e}，嘗試 CPU float32...")
            model = WhisperModel(model_name, device="cpu", compute_type="float32")
            logging.info(f"[WhisperPool] CPU float32 加載成功（最終降備）。")
            return model

    @classmethod
    def transcribe(cls, chunk_path: str, model_name: str = "medium") -> str:
        """
        取得 Semaphore 後執行本地 Whisper 推論（線程安全，自動排隊）。

        當多個並列 Task 同時呼叫此方法時，Semaphore 確保它們依序執行推論，
        不會同時佔滿 CPU，防止系統假死。

        Args:
            chunk_path: 待轉錄的 WAV 音訊切片路徑。
            model_name: 使用的 Whisper 模型名稱，預設為 'medium'。

        Returns:
            帶時間戳的繁體中文轉錄文字。
        """
        model = cls.get_model(model_name)
        logging.info(f"[WhisperPool] 等候 Semaphore，準備推論：{os.path.basename(chunk_path)}")
        with cls._semaphore:
            logging.info(f"[WhisperPool] 取得 Semaphore，開始推論：{os.path.basename(chunk_path)}")
            segments, info = model.transcribe(chunk_path, beam_size=5, language="zh")
            text_parts = []
            for segment in segments:
                m, s = divmod(int(segment.start), 60)
                h, m2 = divmod(m, 60)
                time_str = (
                    f"[{h:02d}:{m2:02d}:{s:02d}]" if h > 0 else f"[{m:02d}:{s:02d}]"
                )
                text_parts.append(f"{time_str} {segment.text}")
            result = "\n".join(text_parts)
            logging.info(
                f"[WhisperPool] 推論完成：{os.path.basename(chunk_path)}，"
                f"音訊時長 {info.duration:.1f}s，輸出 {len(result)} 字元。"
            )
        return result

    @classmethod
    def is_initialized(cls) -> bool:
        """回傳模型是否已初始化（供健康檢查使用）。"""
        return cls._model is not None

    @classmethod
    def pool_status(cls) -> dict:
        """回傳資源池狀態摘要（供監控使用）。"""
        semaphore_value = cls._semaphore._value  # 0 = 正在推論中，1 = 閒置
        return {
            "model_loaded": cls._model is not None,
            "model_name": cls._model_name,
            "semaphore_available": semaphore_value == 1,
            "inference_in_progress": semaphore_value == 0,
        }
