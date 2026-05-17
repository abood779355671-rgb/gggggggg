"""
وظائف مساعدة مشتركة - التحقق من الشروط الأساسية قبل معالجة الأوامر
"""
import time
from config import r, DEV_ID, botname, cached_smembers
from helpers.ranks import is_admin

# ─────────────────────────────────────────────────────────────────────────
# كاش خفيف لتقليل طلبات Redis المتكررة من داخل handlers
# TTL مُدرَّج:
#   _UTILS_TTL = 3 ثوانٍ — للـ bool flags (enable, mute, gban …)
#   _RTXT_TTL  = 30 ثانية — لـ custom text aliases (تتغير نادراً)
# ─────────────────────────────────────────────────────────────────────────
_utils_cache: dict = {}
_UTILS_TTL  = 30  # رُفع من 3 → 30 ثانية — group_enabled لا يتغير كثيراً
_RTXT_TTL   = 5


def _bool_cached(key: str) -> bool:
    now = time.monotonic()
    entry = _utils_cache.get(key)
    if entry and now - entry[1] < _UTILS_TTL:
        return entry[0]
    val = bool(r.get(key))
    _utils_cache[key] = (val, now)
    return val


def _str_cached(cache_key: str, redis_key: str) -> str | None:
    now = time.monotonic()
    entry = _utils_cache.get(cache_key)
    if entry and now - entry[1] < _RTXT_TTL:
        return entry[0]
    val = r.get(redis_key)
    _utils_cache[cache_key] = (val, now)
    return val


def utils_cache_invalidate(key: str):
    """امسح مفتاح من الكاش فوراً بعد أي تعديل على Redis"""
    _utils_cache.pop(key, None)


def group_enabled(cid: int) -> bool:
    """هل البوت مفعّل في هذه المجموعة؟"""
    return _bool_cached(f"{cid}:enable:{DEV_ID}")


def is_muted_user(uid: int, cid: int) -> bool:
    """هل المستخدم مكتوم (محلي أو عام)؟"""
    return (
        _bool_cached(f"{uid}:mute:{cid}:{DEV_ID}") or
        _bool_cached(f"{uid}:mute:{DEV_ID}")
    )


def is_gbanned(uid: int) -> bool:
    return _bool_cached(f"{uid}:gban:{DEV_ID}")


def group_muted(cid: int) -> bool:
    """هل المجموعة في وضع الصمت العام؟"""
    return _bool_cached(f"{cid}:mute:{DEV_ID}")


def can_speak(uid: int, cid: int) -> bool:
    """هل يحق لهذا المستخدم الكلام في هذه المجموعة؟"""
    if group_muted(cid) and not is_admin(uid, cid):
        return False
    if is_muted_user(uid, cid):
        return False
    return True


def resolve_text(text: str, cid: int) -> str:
    """
    يحلّ أسماء البوت وأوامر مخصصة.
    - إذا بدأت الرسالة باسم البوت → يحذفه.
    - إذا كان هناك استبدال مخصص → يطبّقه.
    النتيجة مخزّنة 30 ثانية — الأوامر المخصصة تتغير نادراً.
    """
    name = botname()
    if text.startswith(f"{name} "):
        text = text[len(name) + 1:]

    # استبدال محلي (للمجموعة) — مُخزَّن
    local = _str_cached(f"rtxt:l:{cid}:{text}", f"{cid}:Custom:{cid}:{DEV_ID}&text={text}")
    if local:
        return local

    # استبدال عام (لكل المجموعات) — مُخزَّن
    global_ = _str_cached(f"rtxt:g:{text}", f"Custom:{DEV_ID}&text={text}")
    if global_:
        return global_

    return text
