import threading
import time
from dataclasses import dataclass
from typing import Optional

_IN_FLIGHT = {}
_IN_FLIGHT_LOCK = threading.Lock()


@dataclass
class InFlightToken:
    key: str
    owner: str
    started_at: float
    meta: Optional[dict] = None


def build_inflight_key(scope: str, stage: str, task_id: str, chunk_id: str) -> str:
    return f"{scope}:{stage}:{task_id}:{chunk_id}"


def acquire_inflight(key: str, owner: str, meta: Optional[dict] = None) -> bool:
    with _IN_FLIGHT_LOCK:
        if key in _IN_FLIGHT:
            return False
        _IN_FLIGHT[key] = InFlightToken(
            key=key,
            owner=owner,
            started_at=time.time(),
            meta=meta or {},
        )
        return True


def release_inflight(key: str) -> None:
    with _IN_FLIGHT_LOCK:
        _IN_FLIGHT.pop(key, None)


def get_inflight_token(key: str) -> Optional[InFlightToken]:
    with _IN_FLIGHT_LOCK:
        return _IN_FLIGHT.get(key)


def list_inflight_tokens() -> list[InFlightToken]:
    with _IN_FLIGHT_LOCK:
        return list(_IN_FLIGHT.values())


def find_stale_tokens(max_age_sec: float) -> list[InFlightToken]:
    now = time.time()
    with _IN_FLIGHT_LOCK:
        return [token for token in _IN_FLIGHT.values() if now - token.started_at >= max_age_sec]
