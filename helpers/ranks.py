"""
نظام الرتب - يحدد صلاحيات كل مستخدم
الرتب من الأعلى للأدنى:
  مطور (DEV_ID) > مالك البوت (botowner) > Dev² > Myth > مالك أساسي > مالك > مدير > ادمن > مميز > عضو

✅ تحسين الأداء:
  - كل فحص رتبة يجلب جميع المفاتيح بـ mget واحد
  - نتيجة الفحص تُخزَّن مؤقتاً 8 ثواني (TTL)
  - حد أقصى 10,000 إدخال في الكاش لمنع Memory Leak
  - is_locked مع كاش 30 ثانية
"""

import time
from config import r, DEV_ID

# ─────────────────────────────────────────────────────────────────────────
# كاش الرتب
# ─────────────────────────────────────────────────────────────────────────
_rank_cache: dict = {}
_lock_cache: dict = {}
_RANK_TTL = 8
_LOCK_TTL = 30
_MAX_RANK_CACHE = 10000
_MAX_LOCK_CACHE = 2000


def _rank_cache_cleanup():
    if len(_rank_cache) < _MAX_RANK_CACHE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t) in _rank_cache.items() if now - t > _RANK_TTL]
    for k in expired:
        _rank_cache.pop(k, None)
    if len(_rank_cache) >= _MAX_RANK_CACHE:
        oldest = sorted(_rank_cache.items(), key=lambda x: x[1][1])[:2000]
        for k, _ in oldest:
            _rank_cache.pop(k, None)


def _lock_cache_cleanup():
    if len(_lock_cache) < _MAX_LOCK_CACHE:
        return
    now = time.monotonic()
    expired = [k for k, (_, t) in _lock_cache.items() if now - t > _LOCK_TTL]
    for k in expired:
        _lock_cache.pop(k, None)


def _get_rank_level(uid: int, cid: int) -> int:
    now = time.monotonic()
    cache_key = (uid, cid)
    entry = _rank_cache.get(cache_key)
    if entry and now - entry[1] < _RANK_TTL:
        return entry[0]

    su, sc = str(uid), str(cid)
    try:
        keys = [
            f"{DEV_ID}:owner",
            f"{su}:rankDEV2:{DEV_ID}",
            f"{su}:rankDEV:{DEV_ID}",
            f"{sc}:rankGOWNER:{su}:{DEV_ID}",
            f"{sc}:rankOWNER:{su}:{DEV_ID}",
            f"{sc}:rankMOD:{su}:{DEV_ID}",
            f"{sc}:rankADMIN:{su}:{DEV_ID}",
            f"{sc}:rankPRE:{su}:{DEV_ID}",
        ]
        vals = r.mget(keys)
        owner_id, rank_dev2, rank_dev, rank_go, rank_ow, rank_mo, rank_adm, rank_pre = vals
    except Exception:
        owner_id = rank_dev2 = rank_dev = rank_go = rank_ow = rank_mo = rank_adm = rank_pre = None

    if su == str(DEV_ID):
        level = 9
    elif owner_id and su == owner_id:
        level = 8
    elif rank_dev2:
        level = 7
    elif rank_dev:
        level = 6
    elif rank_go:
        level = 5
    elif rank_ow:
        level = 4
    elif rank_mo:
        level = 3
    elif rank_adm:
        level = 2
    elif rank_pre:
        level = 1
    else:
        level = 0

    _rank_cache_cleanup()
    _rank_cache[cache_key] = (level, now)
    return level


def rank_cache_invalidate(uid: int, cid: int):
    """امسح كاش المستخدم فوراً بعد تغيير رتبته"""
    _rank_cache.pop((uid, cid), None)


# ─────────────────────────── الاسم المعروض ──────────────────────────────

def get_rank(uid: int, cid: int) -> str:
    su, sc = str(uid), str(cid)
    level = _get_rank_level(uid, cid)

    try:
        all_keys = [
            f"{DEV_ID}:rankName:dev",
            f"{DEV_ID}:rankName:owner_g",
            f"{DEV_ID}:rankName:dev2",
            f"{DEV_ID}:rankName:myth",
            f"{sc}:RankGowner:{DEV_ID}",
            f"{sc}:RankOwner:{DEV_ID}",
            f"{sc}:RankMod:{DEV_ID}",
            f"{sc}:RankAdm:{DEV_ID}",
            f"{sc}:RankPre:{DEV_ID}",
            f"{sc}:RankMem:{DEV_ID}",
            f"{su}:gban:{DEV_ID}",
            f"{su}:mute:{DEV_ID}",
        ]
        vals = r.mget(all_keys)
    except Exception:
        vals = [None] * 12

    if level == 9:  return vals[0] or "مطوّر 🎖️"
    if level == 8:  return vals[1] or "مالك البوت 🎖️"
    if vals[10]: return "محظور عام 🔴"
    if vals[11]: return "مكتوم عام 🔇"
    if level == 7:  return vals[2] or "Dev²🎖"
    if level == 6:  return vals[3] or "Myth🎖️"
    if level == 5:  return vals[4] or "المالك الأساسي 👑"
    if level == 4:  return vals[5] or "المالك 💎"
    if level == 3:  return vals[6] or "المدير ⚙️"
    if level == 2:  return vals[7] or "ادمن 🛡️"
    if level == 1:  return vals[8] or "مميز ⭐"
    return vals[9] or "عضو"


# ─────────────────────────── فحص الصلاحيات ──────────────────────────────

def is_dev(uid: int, cid: int = 0) -> bool:
    return _get_rank_level(uid, cid) >= 9

def is_botowner(uid: int, cid: int = 0) -> bool:
    return _get_rank_level(uid, cid) >= 8

def is_dev2(uid: int, cid: int = 0) -> bool:
    return _get_rank_level(uid, cid) >= 7

def is_myth(uid: int, cid: int = 0) -> bool:
    return _get_rank_level(uid, cid) >= 6

def is_gowner(uid: int, cid: int) -> bool:
    return _get_rank_level(uid, cid) >= 5

def is_owner(uid: int, cid: int) -> bool:
    return _get_rank_level(uid, cid) >= 4

def is_mod(uid: int, cid: int) -> bool:
    return _get_rank_level(uid, cid) >= 3

def is_admin(uid: int, cid: int) -> bool:
    return _get_rank_level(uid, cid) >= 2

def is_pre(uid: int, cid: int) -> bool:
    return _get_rank_level(uid, cid) >= 1


# ─── aliases ────────────────────────────────────────────────────────────

def admin_pls(uid: int, cid: int) -> bool:  return is_admin(uid, cid)
def mod_pls(uid: int, cid: int) -> bool:    return is_mod(uid, cid)
def owner_pls(uid: int, cid: int) -> bool:  return is_owner(uid, cid)
def gowner_pls(uid: int, cid: int) -> bool: return is_gowner(uid, cid)
def dev_pls(uid: int, cid: int) -> bool:    return is_myth(uid, cid)
def dev2_pls(uid: int, cid: int) -> bool:   return is_dev2(uid, cid)
def devp_pls(uid: int, cid: int) -> bool:   return is_botowner(uid, cid)
def pre_pls(uid: int, cid: int) -> bool:    return is_pre(uid, cid)


# ─────────────────────────── قفل الأوامر — مع كاش ──────────────────────

LOCK_LEVELS = {0: is_gowner, 1: is_owner, 2: is_mod, 3: is_admin, 4: is_pre}


def is_locked(uid: int, cid: int, text: str) -> bool:
    """يرجع True إذا كان الأمر مقفولاً على المستخدم — مع كاش 30 ثانية"""
    now = time.monotonic()
    cache_key = f"locks:{cid}"
    entry = _lock_cache.get(cache_key)
    if entry and now - entry[1] < _LOCK_TTL:
        locks = entry[0]
    else:
        try:
            locks = r.hgetall(f"{DEV_ID}:locks:{cid}")
        except Exception:
            return False
        _lock_cache_cleanup()
        _lock_cache[cache_key] = (locks, now)

    if not locks:
        return False
    txt_lower = text.lower()
    for cmd, level in locks.items():
        if cmd.lower() in txt_lower:
            checker = LOCK_LEVELS.get(int(level), is_gowner)
            return not checker(uid, cid)
    return False


def lock_cache_invalidate(cid: int):
    """امسح كاش الأقفال لمجموعة معينة"""
    _lock_cache.pop(f"locks:{cid}", None)


# alias قديم
def isLockCommand(uid: int, cid: int, text: str) -> bool:
    return is_locked(uid, cid, text)


# ─────────────────────────── get_devs ──────────────────────────────────

_devs_cache: tuple | None = None
_devs_cache_time: float = 0
_DEVS_TTL = 60


def get_devs() -> list:
    """يُرجع قائمة بكل معرّفات المطورين — مع كاش 60 ثانية"""
    global _devs_cache, _devs_cache_time
    now = time.monotonic()
    if _devs_cache is not None and now - _devs_cache_time < _DEVS_TTL:
        return list(_devs_cache)

    try:
        devs = [int(DEV_ID)]
        owner_id = r.get(f"{DEV_ID}:owner")
        if owner_id and int(owner_id) != int(DEV_ID):
            devs.append(int(owner_id))
        for uid in r.smembers(f"{DEV_ID}:DEV2"):
            try: devs.append(int(uid))
            except: pass
        for uid in r.smembers(f"{DEV_ID}:DEV"):
            try: devs.append(int(uid))
            except: pass
        result = list(dict.fromkeys(devs))
    except Exception:
        result = [int(DEV_ID)]

    _devs_cache = tuple(result)
    _devs_cache_time = now
    return result
