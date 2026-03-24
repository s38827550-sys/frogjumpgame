# core/network.py
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CORE_DIR = Path(__file__).resolve().parent
BASE_DIR = CORE_DIR.parent
PENDING_FILE = BASE_DIR / "pending_scores.json"
CONFIG_FILE = BASE_DIR / "config.json"

# 웹 로그인 토큰 파일 경로 (로컬스토리지 대신 파일로 저장)
TOKEN_FILE = Path.home() / ".frogjump_token.json"

def load_web_token() -> Optional[Dict]:
    """웹페이지에서 로그인한 토큰 읽기"""
    try:
        if TOKEN_FILE.exists():
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            return data
    except Exception as e:
        print(f"[Network] Token load error: {e}")
    return None

def _load_api_base() -> str:
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(cfg, dict) and cfg.get("api_base"):
                return str(cfg["api_base"]).rstrip("/")
    except Exception as e:
        print(f"[Network] Config load error: {e}")
    return "https://frogjump-leaderboard.onrender.com"

def _load_supabase_config() -> Dict:
    try:
        if CONFIG_FILE.exists():
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return {
                "url": cfg.get("supabase_url", ""),
                "anon_key": cfg.get("supabase_anon_key", ""),
            }
    except Exception as e:
        print(f"[Network] Supabase config load error: {e}")
    return {}

API_BASE = _load_api_base()
SUPABASE_CONFIG = _load_supabase_config()
TIMEOUT = 5.0

def _http_json(method: str, url: str, payload: Optional[dict] = None, headers_extra: Optional[dict] = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload else None
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "FrogJumpGame/2.0"
    }
    if headers_extra:
        headers.update(headers_extra)
    
    # 헤더값을 ascii로 인코딩 가능하도록 변환
    safe_headers = {}
    for k, v in headers.items():
        try:
            v.encode('latin-1')
            safe_headers[k] = v
        except (UnicodeEncodeError, AttributeError):
            safe_headers[k] = v.encode('utf-8').decode('latin-1', errors='ignore')
    
    req = Request(url=url, data=body, method=method.upper(), headers=safe_headers)
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(f"[Network] HTTP Error {e.code}: {e.read().decode('utf-8', 'ignore')}")
        raise
    except URLError as e:
        print(f"[Network] URL Error: {e.reason}")
        raise
    except Exception as e:
        print(f"[Network] Unexpected Error: {e}")
        raise

def refresh_access_token() -> Optional[str]:
    """refresh_token으로 access_token 갱신"""
    try:
        token = load_web_token()
        if not token or not token.get("refresh_token"):
            return None
        
        supabase_url = SUPABASE_CONFIG.get("url")
        anon_key = SUPABASE_CONFIG.get("anon_key")
        
        url = f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
        headers_extra = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
        }
        result = _http_json("POST", url, 
            {"refresh_token": token["refresh_token"]}, 
            headers_extra)
        
        if result.get("access_token"):
            # 새 토큰 저장
            token["access_token"] = result["access_token"]
            token["refresh_token"] = result.get("refresh_token", token["refresh_token"])
            TOKEN_FILE.write_text(json.dumps(token, ensure_ascii=False), encoding="utf-8")
            print("[Network] Token refreshed!")
            return result["access_token"]
    except Exception as e:
        print(f"[Network] Token refresh error: {e}")
    return None

def upload_score_supabase(user_id: str, score: int, access_token: str) -> bool:
    """Supabase scores 테이블에 직접 저장"""
    try:
        supabase_url = SUPABASE_CONFIG.get("url")
        anon_key = SUPABASE_CONFIG.get("anon_key")
        if not supabase_url or not anon_key:
            print("[Network] Supabase config missing")
            return False

        url = f"{supabase_url}/rest/v1/scores"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "FrogJumpGame/2.0",
            "apikey": anon_key,
            "Authorization": f"Bearer {access_token}",
            "Prefer": "return=minimal",
        }
        payload = {
            "user_id": user_id,
            "score": max(0, int(score)),
        }
        body = json.dumps(payload).encode("utf-8")
        req = Request(url=url, data=body, method="POST", headers=headers)
        with urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.status
            print(f"[Network] Score saved to Supabase. Status: {status}, Score: {score}")
            return status in (200, 201, 204)
    except Exception as e:
        print(f"[Network] Supabase upload failed: {e}")
        return False

def upload_score(nickname: str, score: int) -> bool:
    token = load_web_token()
    if token and token.get("access_token") and token.get("user_id"):
        # 토큰 만료 체크
        import json, base64, time
        try:
            payload = token["access_token"].split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload).decode("utf-8"))
            exp = decoded.get("exp", 0)
            
            if exp <= time.time():
                # 토큰 만료 → refresh
                print("[Network] Token expired, refreshing...")
                new_token = refresh_access_token()
                if new_token:
                    token["access_token"] = new_token
                else:
                    print("[Network] Token refresh failed, using legacy")
                    # fallback
                    url = f"{API_BASE}/scores"
                    payload = {"nickname": nickname.strip()[:16], "score": max(0, int(score))}
                    try:
                        result = _http_json("POST", url, payload)
                        if result.get("ok"): return True
                        return False
                    except Exception as e:
                        _enqueue(nickname, score)
                        return False
        except Exception as e:
            print(f"[Network] Token check error: {e}")

        success = upload_score_supabase(token["user_id"], score, token["access_token"])
        if success: return True

    # 토큰 없으면 기존 방식
    url = f"{API_BASE}/scores"
    payload_data = {"nickname": nickname.strip()[:16], "score": max(0, int(score))}
    try:
        result = _http_json("POST", url, payload_data)
        if result.get("ok"):
            return True
        return False
    except Exception as e:
        _enqueue(nickname, score)
        return False

def _enqueue(nickname: str, score: int):
    items = _read_pending()
    items.append({"nickname": nickname, "score": score, "ts": int(time.time())})
    if len(items) > 50: items = items[-50:]
    _write_pending(items)

def _read_pending() -> List[Dict]:
    if not PENDING_FILE.exists(): return []
    try:
        data = PENDING_FILE.read_text(encoding="utf-8")
        return json.loads(data) if data.strip() else []
    except Exception:
        return []

def _write_pending(items: List):
    try:
        PENDING_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Network] Pending write error: {e}")

def flush_pending(force: bool = False):
    items = _read_pending()
    if not items: return
    print(f"[Network] Attempting to flush {len(items)} pending scores...")
    still_pending = []
    for it in items:
        time.sleep(0.5)
        if not upload_score(it["nickname"], it["score"]):
            still_pending.append(it)
    _write_pending(still_pending)

def login_with_supabase(username: str, password: str) -> Optional[Dict]:
    try:
        from urllib.parse import quote
        supabase_url = SUPABASE_CONFIG.get("url")
        anon_key = SUPABASE_CONFIG.get("anon_key")
        if not supabase_url or not anon_key:
            print("[Network] Supabase config missing")
            return None

        # 아이디로 이메일 찾기 (URL 인코딩 추가)
        encoded_username = quote(username, safe='')
        url = f"{supabase_url}/rest/v1/users?select=email&username=eq.{encoded_username}"
        headers_extra = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
        }
        result = _http_json("GET", url, headers_extra=headers_extra)
        if not result or len(result) == 0:
            print("[Network] Username not found")
            return None
        
        email = result[0]["email"]

        # 이메일 + 비밀번호로 로그인
        auth_url = f"{supabase_url}/auth/v1/token?grant_type=password"
        auth_headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
        }
        auth_result = _http_json("POST", auth_url,
            {"email": email, "password": password},
            auth_headers)

        if not auth_result.get("access_token"):
            print("[Network] Login failed")
            return None

        # 닉네임 가져오기
        user_url = f"{supabase_url}/rest/v1/users?select=nickname,status,deleted_at&username=eq.{encoded_username}"
        user_result = _http_json("GET", user_url, headers_extra=headers_extra)

        if user_result and user_result[0].get("status") == "deleted":
            print("[Network] Account deleted")
            return {"error": "deleted"}

        nickname = user_result[0]["nickname"] if user_result else username

        token_data = {
            "access_token": auth_result["access_token"],
            "refresh_token": auth_result["refresh_token"],
            "user_id": auth_result["user"]["id"],
            "nickname": nickname,
        }
        TOKEN_FILE.write_text(json.dumps(token_data, ensure_ascii=False), encoding="utf-8")
        print(f"[Network] Login success! Welcome {nickname}")
        return token_data

    except Exception as e:
        print(f"[Network] Login error: {e}")
        return None

def logout() -> None:
    """로그아웃 - 토큰 파일 삭제"""
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("[Network] Logged out")
    except Exception as e:
        print(f"[Network] Logout error: {e}")