import os
import time
import logging
import redis
import redis.asyncio as aioredis
from pyrogram import Client

logger = logging.getLogger("config")

API_ID    = int(os.getenv("API_ID", "0"))
API_HASH  = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEV_ID    = os.getenv("DEV_ID", "").strip()  # .strip() يُزيل مسافات البيئة الزائدة

# ── التحقق من المتغيرات الإلزامية عند الإقلاع ─────────────────────────────
_missing = [k for k, v in {"API_ID": API_ID, "API_HASH": API_HASH,
                             "BOT_TOKEN": BOT_TOKEN, "DEV_ID": DEV_ID}.items()
            if not v or str(v) == "0"]
if _missing:
    raise EnvironmentError(
        f"❌ المتغيرات البيئية التالية مفقودة أو غير مضبوطة: {', '.join(_missing)}\n"
        f"   أضفها في إعدادات Render / Heroku قبل التشغيل."
    )

# ── DEV_ID_INT — مرجع رقمي موحّد، استخدمه بدلاً من int(DEV_ID) في كل مكان ──
try:
    DEV_ID_INT: int = int(DEV_ID)
except ValueError:
    raise EnvironmentError("❌ DEV_ID يجب أن يكون رقم Telegram صحيح (أرقام فقط).")


if DEV_ID == "123456789":
    raise EnvironmentError(
        "❌ DEV_ID لا يزال على القيمة الافتراضية '123456789'.\n"
        "   هذا خطر أمني — أي شخص بهذا الـ ID سيملك صلاحيات المطور الكاملة.\n"
        "   اضبط DEV_ID بـ ID الحقيقي الخاص بك في المتغيرات البيئية."
    )

# ── Redis sync (للكاش المحلي والعمليات البسيطة) ─────────────────────────────
if REDIS_URL:
    r = redis.from_url(REDIS_URL, decode_responses=True, max_connections=20)
    _ar = aioredis.from_url(REDIS_URL, decode_responses=True, max_connections=20)
else:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True, max_connections=20)
    _ar = aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True, max_connections=20)

# ar = async Redis client — يُصدَّر للاستخدام في جميع الـ async handlers
# استورده في كل Plugin: from config import ar
ar = _ar

# تصدير صريح لمنع الغموض
__all__ = [
    "r", "ar", "DEV_ID", "DEV_ID_INT",
    "botkey", "botname", "cached_smembers",
    "cache_invalidate", "cache_invalidate_prefix",
    "safe_get", "safe_set", "safe_delete", "Client",
]

# ─────────────────────────────────────────────────────────────────────────
# Cache موحّد لجميع القيم الثابتة نسبياً
# TTL مُدرَّج:
#   - القيم النصية (botkey/botname): 60 ثانية
#   - المجموعات (smembers): 10 ثوانٍ
# ─────────────────────────────────────────────────────────────────────────
_cache: dict = {}
_cache_order: list = []          # لتتبع ترتيب الوصول (LRU)
_MAX_CACHE_SIZE = 10000          # رُفع من 5000 لاستيعاب المجموعات الكبيرة

_STR_TTL = 60
_SET_TTL = 10


def _cache_cleanup():
    """LRU eviction: يحذف الأقل استخداماً عند امتلاء الكاش"""
    if len(_cache) < _MAX_CACHE_SIZE:
        return
    now = time.monotonic()
    # أولاً: احذف المنتهية الصلاحية
    expired = [k for k, (_, t, ttl) in _cache.items() if now - t > ttl]
    for k in expired:
        _cache.pop(k, None)
        try: _cache_order.remove(k)
        except ValueError: pass
    # ثانياً: إذا لم يكفِ، احذف الأقل استخداماً (LRU — أول عنصر في القائمة)
    evict_count = max(0, len(_cache) - int(_MAX_CACHE_SIZE * 0.8))
    for k in _cache_order[:evict_count]:
        _cache.pop(k, None)
    del _cache_order[:evict_count]


def _cached_get(cache_key: str, redis_key: str, default: str, ttl: int = _STR_TTL) -> str:
    """
    يُرجع القيمة من الكاش دائماً — بدون أي blocking Redis.
    عند انتهاء الكاش يُبقي القيمة القديمة ويُشغّل تحديثاً async في الخلفية.
    """
    now = time.monotonic()
    entry = _cache.get(cache_key)
    if entry:
        value, ts, _ = entry
        if now - ts < ttl:
            return value
        # الكاش انتهى — أعد القيمة القديمة وابدأ تحديثاً في الخلفية
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_refresh_cached_get(cache_key, redis_key, default, ttl))
        except RuntimeError:
            pass  # لا يوجد event loop جارٍ — سيُحدَّث في الطلب القادم
        return value
    # أول مرة — اجلب بشكل متزامن مرة واحدة فقط (عند الإقلاع)
    try:
        value = r.get(redis_key) or default
    except Exception:
        value = default
    _cache_cleanup()
    _cache[cache_key] = (value, now, ttl)
    try: _cache_order.remove(cache_key)
    except ValueError: pass
    _cache_order.append(cache_key)
    return value


async def _refresh_cached_get(cache_key: str, redis_key: str, default: str, ttl: int):
    """يُحدِّث الكاش من Redis بشكل async — يُستدعى في الخلفية فقط"""
    try:
        value = await _ar.get(redis_key) or default
    except Exception:
        return
    _cache_cleanup()
    _cache[cache_key] = (value, time.monotonic(), ttl)


def _cached_smembers(cache_key: str, redis_key: str) -> frozenset:
    """smembers مع كاش TTL=10 ثواني"""
    now = time.monotonic()
    entry = _cache.get(cache_key)
    if entry and now - entry[1] < _SET_TTL:
        return entry[0]
    try:
        value = frozenset(r.smembers(redis_key))
    except Exception:
        return frozenset()
    _cache_cleanup()
    _cache[cache_key] = (value, now, _SET_TTL)
    try: _cache_order.remove(cache_key)
    except ValueError: pass
    _cache_order.append(cache_key)
    return value


def cache_invalidate(cache_key: str):
    """امسح قيمة من الكاش فوراً"""
    _cache.pop(cache_key, None)


def cache_invalidate_prefix(prefix: str):
    """امسح كل مفاتيح الكاش التي تبدأ بـ prefix"""
    for k in list(_cache.keys()):
        if k.startswith(prefix):
            _cache.pop(k, None)


def botkey() -> str:
    return _cached_get("botkey", f"{DEV_ID}:botkey", "⚡")


def botname() -> str:
    return _cached_get("botname", f"{DEV_ID}:BotName", "بوتي")


def cached_smembers(redis_key: str) -> frozenset:
    return _cached_smembers(f"sm:{redis_key}", redis_key)


# ── safe Redis wrappers — تُعيد قيمة افتراضية عند الانقطاع ─────────────────
def safe_get(key: str, default=None):
    try:
        return r.get(key) or default
    except Exception as e:
        logger.warning("Redis get error: %s", e)
        return default


def safe_set(key: str, value, **kwargs) -> bool:
    try:
        r.set(key, value, **kwargs)
        return True
    except Exception as e:
        logger.warning("Redis set error: %s", e)
        return False


def safe_delete(*keys) -> bool:
    try:
        r.delete(*keys)
        return True
    except Exception as e:
        logger.warning("Redis delete error: %s", e)
        return False


Client = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="Plugins"),
)
