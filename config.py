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
_MAX_CACHE_SIZE = 5000  # حد أقصى لمنع Memory Leak

_STR_TTL = 60
_SET_TTL = 10


def _cache_cleanup():
    """تنظيف الإدخالات المنتهية الصلاحية إذا تجاوز الكاش الحد الأقصى"""
    if len(_cache) < _MAX_CACHE_SIZE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t, ttl) in _cache.items() if now - t > ttl]
    for k in expired:
        _cache.pop(k, None)
    # إذا لم يكفِ، احذف الأقدم
    if len(_cache) >= _MAX_CACHE_SIZE:
        oldest = sorted(_cache.items(), key=lambda x: x[1][1])[:1000]
        for k, _ in oldest:
            _cache.pop(k, None)


def _cached_get(cache_key: str, redis_key: str, default: str, ttl: int = _STR_TTL) -> str:
    now = time.monotonic()
    entry = _cache.get(cache_key)
    if entry and now - entry[1] < ttl:
        return entry[0]
    try:
        value = r.get(redis_key) or default
    except Exception:
        return default
    _cache_cleanup()
    _cache[cache_key] = (value, now, ttl)
    return value


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
