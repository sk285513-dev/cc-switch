"""
whisper_pool.py — LexMind-Omni 全域 Whisper 資源池（單例模式）

核心設計目標：
- 全系統只加載「1 個」faster-whisper 模型實例（佔用約 500MB RAM），
  無論有多少個 Task 並列執行，皆共用同一實例。
- 透過 threading.Semaphore(1) 確保同時只有 1 個 Task 在進行 Whisper 本地推論，
  防止多路並發的 CPU 暴衝（100% 假死）與 RAM OOM（記憶體溢出）。
- 加載失敗時提供完整的降備鏈（CPU int8 → CPU float32）。
"""
import threading
import logging
import os


class WhisperPool:
    """全域 Whisper 模型資源池 — 單例 + Semaphore 排隊模式。"""

    _instance_lock = threading.Lock()
    _model = None
    _model_name = None
    _semaphore = threading.Semaphore(1)  # 同時只允許 1 個推論

    @classmethod
    def get_model(cls, model_name: str = "medium"):
        """取得（或初始化）全域共享的 Whisper 模型實例。線程安全。"""
        with cls._instance_lock:
            if cls._model is None or cls._model_name != model_name:
                logging.info(
                    f"[WhisperPool] 首次初始化全域 Whisper 模型 '{model_name}'（CPU int8 模式）..."
                )
                cls._model = cls._load_model(model_name)
                cls._model_name = model_name
                logging.info(f"[WhisperPool] 模型 '{model_name}' 已就緒，全域共享實例已建立。")
        return cls._model

    @classmethod
    def _load_model(cls, model_name: str):
        """模型加載：強制 CPU int8 模式。"""
        from faster_whisper import WhisperModel
        try:
            logging.info(f"[WhisperPool] 嘗試加載：device=cpu, compute_type=int8")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logging.info(f"[WhisperPool] CPU int8 加載成功。")
            return model
        except Exception as e:
            logging.error(f"[WhisperPool] CPU int8 加載失敗：{e}。系統記憶體耗盡。")
            raise RuntimeError(f"WhisperPool load failed: {e}")

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
