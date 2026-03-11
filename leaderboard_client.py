# leaderboard_client.py
from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------
# Config (선택 A: API_BASE 유지)
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PENDING_FILE = BASE_DIR / "pending_scores.json"

def _runtime_dir() -> Path:
    """
    실행 기준 폴더:
    - EXE(PyInstaller) 실행 시: exe가 있는 폴더
    - 파이썬 스크립트 실행 시: 이 파일이 있는 폴더
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return BASE_DIR

CONFIG_FILE = _runtime_dir() / "config.json"

def _load_api_base() -> str:
    # 1) config.json 우선
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(cfg, dict) and cfg.get("api_base"):
                return str(cfg["api_base"]).rstrip("/")
    except Exception:
        pass

    # 2) 환경변수
    env = os.getenv("API_BASE")
    if env:
        return env.rstrip("/")

    # 3) 기본값(로컬 개발용)
    return "http://127.0.0.1:8000"

API_BASE = _load_api_base()

def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    try:
        return int(v) if v is not None and str(v).strip() != "" else default
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    v = os.getenv(key)
    try:
        return float(v) if v is not None and str(v).strip() != "" else default
    except Exception:
        return default

TIMEOUT_SECONDS = _env_float("API_TIMEOUT_SECONDS", 3.0)

# 재전송(Flush) 정책
FLUSH_MAX_ITEMS = _env_int("FLUSH_MAX_ITEMS", 50)            # 한 번에 최대 전송 개수
FLUSH_MIN_INTERVAL = _env_float("FLUSH_MIN_INTERVAL", 5.0)   # 연속 호출 시 최소 간격(초)
_last_flush_ts: float = 0.0


# ---------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------
def _now() -> float:
    return time.time()


def _sanitize_nickname(nickname: str) -> str:
    nickname = (nickname or "").strip()
    if not nickname:
        return "PLAYER"
    # 서버에서 min/max 길이 검증하므로, 여기서는 과도한 길이만 컷
    return nickname[:16]


def _coerce_score(score: Any) -> int:
    try:
        s = int(score)
    except Exception:
        s = 0
    return max(0, min(s, 999_999))


def _read_pending() -> List[Dict[str, Any]]:
    if not PENDING_FILE.exists():
        return []
    try:
        data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            # 최소 형태만 유지
            out: List[Dict[str, Any]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                if "nickname" in item and "score" in item:
                    out.append(item)
            return out
        return []
    except Exception:
        # 파일이 깨졌다면 안전하게 비우지 말고, 백업 후 새로 시작하는 게 좋지만
        # 여기서는 단순히 빈 목록으로 처리(게임 크래시 방지)
        return []


def _atomic_write_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_pending(items: List[Dict[str, Any]]) -> None:
    # 너무 커지는 것 방지(정상 상황이면 그렇게 커지지 않음)
    if len(items) > 5000:
        items = items[-5000:]
    _atomic_write_json(PENDING_FILE, items)


def _http_json(method: str, url: str, payload: Optional[dict] = None, timeout: float = 3.0) -> Any:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, data=body, method=method.upper(), headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        if not raw:
            return None
        return json.loads(raw)


def _enqueue(nickname: str, score: int) -> None:
    items = _read_pending()
    items.append({"nickname": nickname, "score": score, "ts": int(_now())})
    _write_pending(items)


# ---------------------------------------------------------
# 공개 API
# ---------------------------------------------------------
def upload_score(nickname: str, score: Any) -> bool:
    """
    점수 업로드를 시도합니다.
    - 성공하면 True 반환
    - 실패하면 pending 파일에 저장 후 False 반환
    """
    nn = _sanitize_nickname(nickname)
    sc = _coerce_score(score)

    url = f"{API_BASE}/scores"
    payload = {"nickname": nn, "score": sc}

    try:
        _http_json("POST", url, payload=payload, timeout=TIMEOUT_SECONDS)
        return True
    except (URLError, HTTPError, TimeoutError, ValueError):
        _enqueue(nn, sc)
        return False
    except Exception:
        _enqueue(nn, sc)
        return False


def flush_pending(force: bool = False) -> Dict[str, Any]:
    """
    pending_scores.json에 쌓인 점수를 서버로 재전송합니다.
    - force=False면, FLUSH_MIN_INTERVAL 이내 연속 호출은 무시
    - 성공한 항목만 제거
    """
    global _last_flush_ts

    now = _now()
    if (not force) and (now - _last_flush_ts) < FLUSH_MIN_INTERVAL:
        return {"ok": True, "skipped": True, "sent": 0, "remaining": len(_read_pending())}

    _last_flush_ts = now

    items = _read_pending()
    if not items:
        return {"ok": True, "skipped": False, "sent": 0, "remaining": 0}

    to_send = items[:FLUSH_MAX_ITEMS]
    remain = items[FLUSH_MAX_ITEMS:]

    sent = 0
    failed_batch = False

    url = f"{API_BASE}/scores"

    for it in to_send:
        nn = _sanitize_nickname(str(it.get("nickname", "")))
        sc = _coerce_score(it.get("score", 0))
        payload = {"nickname": nn, "score": sc}

        try:
            _http_json("POST", url, payload=payload, timeout=TIMEOUT_SECONDS)
            sent += 1
        except (URLError, HTTPError, TimeoutError, ValueError):
            failed_batch = True
            # 실패한 건 다시 큐로
            remain.insert(0, it)
        except Exception:
            failed_batch = True
            remain.insert(0, it)

    # 실패가 있었든 없었든, 남은 것 포함해서 다시 저장
    _write_pending(remain)

    return {
        "ok": True,
        "skipped": False,
        "sent": sent,
        "remaining": len(remain),
        "had_failures": failed_batch,
    }


def fetch_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """
    서버 리더보드 조회 (게임 화면에 표시 안 하더라도 디버그/검증용)
    """
    try:
        limit = int(limit)
    except Exception:
        limit = 10
    limit = max(1, min(limit, 200))

    url = f"{API_BASE}/leaderboard?limit={limit}"
    try:
        data = _http_json("GET", url, payload=None, timeout=TIMEOUT_SECONDS)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []
