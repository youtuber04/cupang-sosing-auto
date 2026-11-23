"""쿠팡 파트너스 딥링크 API(간편링크 만들기) + 한도 보호 안전장치. 검색 API 는 쓰지 않는다.

키: 환경변수 또는 스킬 폴더 .env 의 COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY (본인 파트너스 키, 채팅으로 주고받지 않음)
안전장치: 쿠팡에 보내기 전에 막는다. 기록 파일 ~/.coupang_api_guard.json (이 PC 의 모든 스킬 공용)
  - 딥링크 최근 1시간 COUPANG_DEEPLINK_PER_HOUR 회(기본 40) 넘으면 보내지 않음
  - 요청 사이 최소 COUPANG_MIN_GAP_SEC 초(기본 3)
  - 쿠팡이 "시간당 사용 횟수 초과"로 답하면 알려 준 시각까지 모든 쿠팡 API 를 멈춤
"""
import hashlib, hmac, json, os, re, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

DOMAIN = "https://api-gateway.coupang.com"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
ROOT = Path(__file__).resolve().parent.parent
GUARD_FILE = Path(os.environ.get("COUPANG_GUARD_FILE") or (Path.home() / ".coupang_api_guard.json"))


class CoupangLimitError(RuntimeError):
    """안전장치가 막은 요청(쿠팡에 보내지 않았음). 재시도 루프로 다시 부르지 말 것."""


def _env(key):
    if os.environ.get(key):
        return os.environ[key]
    env = ROOT / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(key + "="):
                return line.split("=", 1)[1].split("#")[0].strip().strip('"')
    return ""


def _num(key, default):
    try:
        return float(os.environ.get(key) or default)
    except ValueError:
        return float(default)


def _load():
    try:
        return json.loads(GUARD_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(st):
    try:
        GUARD_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def _guard_before(kind="deeplink"):
    st, now = _load(), time.time()
    until = float(st.get("blocked_until") or 0)
    if now < until:
        raise CoupangLimitError("쿠팡 API 한도 보호: %s 까지 쿠팡 API 를 쓰지 않습니다. 그 시각 뒤에 다시 하세요."
                                % time.strftime("%Y-%m-%d %H:%M", time.localtime(until)))
    calls = [t for t in st.get(kind, []) if now - t < 3600]
    if len(calls) >= _num("COUPANG_DEEPLINK_PER_HOUR", 40):
        raise CoupangLimitError("쿠팡 API 한도 보호: 최근 1시간 딥링크 %d회 — 약 %d분 뒤 다시 하세요."
                                % (len(calls), int((3600 - (now - min(calls))) / 60) + 1))
    gap = _num("COUPANG_MIN_GAP_SEC", 3) - (now - float(st.get("last") or 0))
    if gap > 0:
        time.sleep(gap)
    calls.append(time.time())
    st[kind], st["last"] = calls, time.time()
    _save(st)


def _guard_after_error(code, detail):
    if code not in (403, 429) and "횟수" not in detail and "limit" not in detail.lower():
        return
    until = time.time() + 3600
    m = re.search(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})", detail)
    if m:
        try:
            until = time.mktime(time.strptime(m.group(1) + " " + m.group(2), "%Y-%m-%d %H:%M"))
        except ValueError:
            pass
    st = _load()
    st["blocked_until"] = max(until, float(st.get("blocked_until") or 0))
    st["over_count"] = int(st.get("over_count") or 0) + 1
    _save(st)


def _auth(method, path, query, access, secret):
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    sig = hmac.new(secret.encode(), (dt + method + path + query).encode(), hashlib.sha256).hexdigest()
    return "CEA algorithm=HmacSHA256, access-key=%s, signed-date=%s, signature=%s" % (access, dt, sig)


def deeplink_one(url):
    """쿠팡 상품 주소 하나 → (간편링크, 실패 이유)."""
    access, secret = _env("COUPANG_ACCESS_KEY"), _env("COUPANG_SECRET_KEY")
    if not (access and secret):
        return "", "COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY 가 없습니다(.env 에 본인 키를 넣으세요)"
    try:
        _guard_before("deeplink")
    except CoupangLimitError as e:
        return "", str(e)
    req = urllib.request.Request(DOMAIN + DEEPLINK_PATH, method="POST",
                                 data=json.dumps({"coupangUrls": [url]}).encode(),
                                 headers={"Authorization": _auth("POST", DEEPLINK_PATH, "", access, secret),
                                          "Content-Type": "application/json;charset=UTF-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:600]
        _guard_after_error(e.code, detail)
        return "", "쿠팡 API HTTP %s: %s" % (e.code, detail[:200])
    except Exception as e:  # 네트워크 등
        return "", str(e)[:200]
    for d in payload.get("data") or []:
        u = d.get("shortenUrl") or ""
        if u.startswith(("https://link.coupang.com/", "https://coupa.ng/")):
            return u, ""
    return "", "쿠팡 응답 %s %s" % (payload.get("rCode", "?"), payload.get("rMessage") or "(간편링크 없음)")
