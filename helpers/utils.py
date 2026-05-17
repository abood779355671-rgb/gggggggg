"""
وظائف مساعدة مشتركة
"""
import time
from config import r, DEV_ID, botname, cached_smembers
from helpers.ranks import is_admin

_utils_cache: dict = {}
_MAX_UTILS_CACHE = 5000
_ENABLE_TTL = 30
_MUTE_TTL   = 3
_RTXT_TTL   = 5


def _utils_cache_cleanup():
    if len(_utils_cache) < _MAX_UTILS_CACHE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t, ttl) in _utils_cache.items() if now - t > ttl]
    for k in expired:
        _utils_cache.pop(k, None)
    if len(_utils_cache) >= _MAX_UTILS_CACHE:
        oldest = sorted(_utils_cache.items(), key=lambda x: x[1][1])[:1000]
        for k, _ in oldest:
            _utils_cache.pop(k, None)


def _bool_cached(key: str, ttl: float = _ENABLE_TTL) -> bool:
    now = time.monotonic()
    entry = _utils_cache.get(key)
    if entry and now - entry[1] < ttl:
        return entry[0]
    try:
        val = bool(r.get(key))
    except Exception:
        return False
    _utils_cache_cleanup()
    _utils_cache[key] = (val, now, ttl)
    return val


def _str_cached(cache_key: str, redis_key: str) -> str | None:
    now = time.monotonic()
    entry = _utils_cache.get(cache_key)
    if entry and now - entry[1] < _RTXT_TTL:
        return entry[0]
    try:
        val = r.get(redis_key)
    except Exception:
        val = None
    _utils_cache_cleanup()
    _utils_cache[cache_key] = (val, now, _RTXT_TTL)
    return val


def utils_cache_invalidate(key: str):
    _utils_cache.pop(key, None)


def group_enabled(cid: int) -> bool:
    return _bool_cached(f"{cid}:enable:{DEV_ID}")


def is_muted_user(uid: int, cid: int) -> bool:
    return (
        _bool_cached(f"{uid}:mute:{cid}:{DEV_ID}", ttl=_MUTE_TTL) or
        _bool_cached(f"{uid}:mute:{DEV_ID}", ttl=_MUTE_TTL)
    )


def is_gbanned(uid: int) -> bool:
    return _bool_cached(f"{uid}:gban:{DEV_ID}", ttl=_MUTE_TTL)


def group_muted(cid: int) -> bool:
    return _bool_cached(f"{cid}:mute:{DEV_ID}")


def can_speak(uid: int, cid: int) -> bool:
    if group_muted(cid) and not is_admin(uid, cid):
        return False
    if is_muted_user(uid, cid):
        return False
    return True


def resolve_text(text: str, cid: int) -> str:
    name = botname()
    if text.startswith(f"{name} "):
        text = text[len(name) + 1:]

    local = _str_cached(f"rtxt:l:{cid}:{text}", f"{cid}:Custom:{cid}:{DEV_ID}&text={text}")
    if local:
        return local

    global_ = _str_cached(f"rtxt:g:{text}", f"Custom:{DEV_ID}&text={text}")
    if global_:
        return global_

    return text
