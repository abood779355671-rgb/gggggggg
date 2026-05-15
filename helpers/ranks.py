"""
نظام الرتب - يحدد صلاحيات كل مستخدم
الرتب من الأعلى للأدنى:
  مطور (DEV_ID) > مالك أساسي (gowner) > مالك (owner) > مدير (mod) > ادمن (admin) > مميز (pre) > عضو

✅ تحسين الأداء:
  - كل فحص رتبة يجلب جميع المفاتيح بـ mget واحد
  - نتيجة الفحص تُخزَّن مؤقتاً 2 ثانية (TTL قصير)
  - الاستدعاءات المتعددة لنفس المستخدم في نفس الرسالة تضرب الكاش بدون Redis
"""

import time
from config import r, DEV_ID

# ─────────────────────────────────────────────────────────────
# كاش قصير المدى للرتب
# المفتاح: (uid, cid) — القيمة: (مستوى الرتبة رقم، وقت الحفظ)
# المستويات: 0=عضو 1=pre 2=admin 3=mod 4=owner 5=gowner 6=dev
# ─────────────────────────────────────────────────────────────
_rank_cache: dict = {}
_RANK_TTL = 2  # ثانيتان تكفي لتغطية رسالة واحدة كاملة


def _get_rank_level(uid: int, cid: int) -> int:
    """
    يجلب مستوى رتبة المستخدم كرقم (0-6).
    يستخدم الكاش إذا الإدخال أحدث من _RANK_TTL ثانية.
    وإلا يجلب كل المفاتيح بـ mget واحد ويحفظ النتيجة.
    """
    now = time.monotonic()
    cache_key = (uid, cid)
    entry = _rank_cache.get(cache_key)
    if entry and now - entry[1] < _RANK_TTL:
        return entry[0]

    su, sc = str(uid), str(cid)
    keys = [
        f"{DEV_ID}:owner",                  # 0
        f"{su}:rankDEV:{DEV_ID}",           # 1
        f"{sc}:rankGOWNER:{su}:{DEV_ID}",   # 2
        f"{sc}:rankOWNER:{su}:{DEV_ID}",    # 3
        f"{sc}:rankMOD:{su}:{DEV_ID}",      # 4
        f"{sc}:rankADMIN:{su}:{DEV_ID}",    # 5
        f"{sc}:rankPRE:{su}:{DEV_ID}",      # 6
    ]
    vals = r.mget(keys)
    owner_id, rank_dev, rank_go, rank_ow, rank_mo, rank_adm, rank_pre = vals

    if su == DEV_ID or (owner_id and su == owner_id) or rank_dev:
        level = 6  # dev
    elif rank_go:
        level = 5  # gowner
    elif rank_ow:
        level = 4  # owner
    elif rank_mo:
        level = 3  # mod
    elif rank_adm:
        level = 2  # admin
    elif rank_pre:
        level = 1  # pre
    else:
        level = 0  # عضو عادي

    _rank_cache[cache_key] = (level, now)
    return level


def rank_cache_invalidate(uid: int, cid: int):
    """امسح كاش المستخدم فوراً بعد تغيير رتبته"""
    _rank_cache.pop((uid, cid), None)


# ─────────────────────────── الاسم المعروض ──────────────────────────────

def get_rank(uid: int, cid: int) -> str:
    su, sc = str(uid), str(cid)
    level = _get_rank_level(uid, cid)

    # دمج كل المفاتيح في mget واحد بدل 3 استدعاءات منفصلة
    all_keys = [
        f"{DEV_ID}:rankName:dev",        # 0
        f"{DEV_ID}:rankName:owner_g",    # 1
        f"{DEV_ID}:rankName:dev2",       # 2
        f"{sc}:RankGowner:{DEV_ID}",     # 3
        f"{sc}:RankOwner:{DEV_ID}",      # 4
        f"{sc}:RankMod:{DEV_ID}",        # 5
        f"{sc}:RankAdm:{DEV_ID}",        # 6
        f"{sc}:RankPre:{DEV_ID}",        # 7
        f"{sc}:RankMem:{DEV_ID}",        # 8
        f"{su}:gban:{DEV_ID}",           # 9
        f"{su}:mute:{DEV_ID}",           # 10
        f"{DEV_ID}:owner",               # 11
        f"{su}:rankDEV:{DEV_ID}",        # 12
    ]
    vals = r.mget(all_keys)
    names  = vals[:9]
    gban   = vals[9]
    mute   = vals[10]
    owner_id  = vals[11]
    rank_dev  = vals[12]

    if level == 6:
        if owner_id and su == owner_id:
            return names[1] or "مالك البوت 🎖️"
        if rank_dev:
            return names[2] or "مطوّر مساعد 🎖️"
        return names[0] or "مطوّر 🎖️"
    if gban:  return "محظور عام 🔴"
    if mute:  return "مكتوم عام 🔇"
    if level == 5: return names[3] or "المالك الأساسي 👑"
    if level == 4: return names[4] or "المالك 💎"
    if level == 3: return names[5] or "المدير ⚙️"
    if level == 2: return names[6] or "ادمن 🛡️"
    if level == 1: return names[7] or "مميز ⭐"
    return names[8] or "عضو"


# ─────────────────────────── فحص الصلاحيات ──────────────────────────────
# كل دالة تضرب _get_rank_level → الكاش يمنع أي طلب Redis إضافي
# في نفس الرسالة (TTL = 2 ثانية)

def is_dev(uid: int, cid: int = 0) -> bool:
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


# ─────────────────────────── قفل الأوامر ────────────────────────────────

LOCK_LEVELS = {0: is_gowner, 1: is_owner, 2: is_mod, 3: is_admin, 4: is_pre}

def is_locked(uid: int, cid: int, text: str) -> bool:
    """يرجع True إذا كان الأمر مقفولاً على المستخدم"""
    locks = r.hgetall(f"{DEV_ID}:locks:{cid}")
    if not locks:
        return False
    for cmd, level in locks.items():
        if cmd.lower() in text.lower():
            checker = LOCK_LEVELS.get(int(level), is_gowner)
            return not checker(uid, cid)
    return False
