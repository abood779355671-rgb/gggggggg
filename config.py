import os
import time
import redis
from pyrogram import Client

API_ID    = int(os.getenv("API_ID", "0"))
API_HASH  = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DEV_ID    = os.getenv("DEV_ID", "123456789")   # ضع ID المطور هنا

# Redis
if REDIS_URL:
    r = redis.from_url(REDIS_URL, decode_responses=True)
else:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# ─────────────────────────────────────────────────────────────────
# Cache موحّد لجميع القيم الثابتة نسبياً (botkey, botname, smembers)
# TTL مُدرَّج:
#   - القيم النصية (botkey/botname): 60 ثانية
#   - المجموعات (smembers): 10 ثوانٍ — تتغير أحياناً بأوامر المدير
# استدعِ cache_invalidate() فور تعديل أي قيمة في Redis
# ─────────────────────────────────────────────────────────────────
_cache: dict = {}

_STR_TTL = 60   # ثانية — botkey / botname لا تتغير كثيراً
_SET_TTL = 10   # ثواني — smembers (فلاتر، كلمات محظورة …)


def _cached_get(cache_key: str, redis_key: str, default: str, ttl: int = _STR_TTL) -> str:
    now = time.monotonic()
    entry = _cache.get(cache_key)
    if entry and now - entry[1] < ttl:
        return entry[0]
    value = r.get(redis_key) or default
    _cache[cache_key] = (value, now)
    return value


def _cached_smembers(cache_key: str, redis_key: str) -> frozenset:
    """smembers مع كاش TTL=10 ثواني — يُعيد frozenset دائماً."""
    now = time.monotonic()
    entry = _cache.get(cache_key)
    if entry and now - entry[1] < _SET_TTL:
        return entry[0]
    value = frozenset(r.smembers(redis_key))
    _cache[cache_key] = (value, now)
    return value


def cache_invalidate(cache_key: str):
    """امسح قيمة من الكاش فوراً (استدعها بعد أي تعديل على Redis)."""
    _cache.pop(cache_key, None)


def cache_invalidate_prefix(prefix: str):
    """امسح كل مفاتيح الكاش التي تبدأ بـ prefix."""
    for k in list(_cache.keys()):
        if k.startswith(prefix):
            _cache.pop(k, None)


# مفتاح البوت الافتراضي في الردود
def botkey() -> str:
    return _cached_get("botkey", f"{DEV_ID}:botkey", "⚡")


# اسم البوت الافتراضي
def botname() -> str:
    return _cached_get("botname", f"{DEV_ID}:BotName", "بوتي")


# smembers مع كاش — للاستخدام في hot-path handlers
def cached_smembers(redis_key: str) -> frozenset:
    return _cached_smembers(f"sm:{redis_key}", redis_key)


Client = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="Plugins"),
)
