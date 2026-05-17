"""
نظام الرتب - يحدد صلاحيات كل مستخدم
الرتب من الأعلى للأدنى:
  مطور (DEV_ID) > مالك البوت (botowner) > Dev² > Myth > مالك أساسي > مالك > مدير > ادمن > مميز > عضو

✅ تحسين الأداء:
  - كل فحص رتبة يجلب جميع المفاتيح بـ mget واحد
  - نتيجة الفحص تُخزَّن مؤقتاً 2 ثانية (TTL قصير)
  - الاستدعاءات المتعددة لنفس المستخدم في نفس الرسالة تضرب الكاش بدون Redis
"""

import time
from config import r, DEV_ID

# ─────────────────────────────────────────────────────────────
# كاش قصير المدى للرتب
# المستويات:
#   0=عضو  1=pre  2=admin  3=mod  4=owner  5=gowner
#   6=Myth (rankDEV)  7=Dev² (rankDEV2)  8=botowner  9=dev (DEV_ID)
# ─────────────────────────────────────────────────────────────
_rank_cache: dict = {}
_RANK_TTL = 8  # رُفع من 2 → 8 ثواني — الرتب لا تتغير بهذه السرعة


def _get_rank_level(uid: int, cid: int) -> int:
    now = time.monotonic()
    cache_key = (uid, cid)
    entry = _rank_cache.get(cache_key)
    if entry and now - entry[1] < _RANK_TTL:
        return entry[0]

    su, sc = str(uid), str(cid)
    keys = [
        f"{DEV_ID}:owner",                    # 0 — botowner id
        f"{su}:rankDEV2:{DEV_ID}",             # 1 — Dev²
        f"{su}:rankDEV:{DEV_ID}",              # 2 — Myth
        f"{sc}:rankGOWNER:{su}:{DEV_ID}",      # 3
        f"{sc}:rankOWNER:{su}:{DEV_ID}",       # 4
        f"{sc}:rankMOD:{su}:{DEV_ID}",         # 5
        f"{sc}:rankADMIN:{su}:{DEV_ID}",       # 6
        f"{sc}:rankPRE:{su}:{DEV_ID}",         # 7
    ]
    vals = r.mget(keys)
    owner_id, rank_dev2, rank_dev, rank_go, rank_ow, rank_mo, rank_adm, rank_pre = vals

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

    _rank_cache[cache_key] = (level, now)
    return level


def rank_cache_invalidate(uid: int, cid: int):
    """امسح كاش المستخدم فوراً بعد تغيير رتبته"""
    _rank_cache.pop((uid, cid), None)


# ─────────────────────────── الاسم المعروض ──────────────────────────────

def get_rank(uid: int, cid: int) -> str:
    su, sc = str(uid), str(cid)
    level = _get_rank_level(uid, cid)

    all_keys = [
        f"{DEV_ID}:rankName:dev",         # 0
        f"{DEV_ID}:rankName:owner_g",     # 1 — botowner label
        f"{DEV_ID}:rankName:dev2",        # 2 — Dev² label
        f"{DEV_ID}:rankName:myth",        # 3 — Myth label
        f"{sc}:RankGowner:{DEV_ID}",      # 4
        f"{sc}:RankOwner:{DEV_ID}",       # 5
        f"{sc}:RankMod:{DEV_ID}",         # 6
        f"{sc}:RankAdm:{DEV_ID}",         # 7
        f"{sc}:RankPre:{DEV_ID}",         # 8
        f"{sc}:RankMem:{DEV_ID}",         # 9
        f"{su}:gban:{DEV_ID}",            # 10
        f"{su}:mute:{DEV_ID}",            # 11
    ]
    vals = r.mget(all_keys)

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
    """المطور الرئيسي فقط"""
    return _get_rank_level(uid, cid) >= 9

def is_botowner(uid: int, cid: int = 0) -> bool:
    """مالك البوت والمطور"""
    return _get_rank_level(uid, cid) >= 8

def is_dev2(uid: int, cid: int = 0) -> bool:
    """Dev² وفوق"""
    return _get_rank_level(uid, cid) >= 7

def is_myth(uid: int, cid: int = 0) -> bool:
    """Myth وفوق"""
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


# ─── aliases بأسماء الملفات القديمة (للتوافق مع set_ranks, replace, welcome) ────

def admin_pls(uid: int, cid: int) -> bool:  return is_admin(uid, cid)
def mod_pls(uid: int, cid: int) -> bool:    return is_mod(uid, cid)
def owner_pls(uid: int, cid: int) -> bool:  return is_owner(uid, cid)
def gowner_pls(uid: int, cid: int) -> bool: return is_gowner(uid, cid)
def dev_pls(uid: int, cid: int) -> bool:    return is_myth(uid, cid)
def dev2_pls(uid: int, cid: int) -> bool:   return is_dev2(uid, cid)
def devp_pls(uid: int, cid: int) -> bool:   return is_botowner(uid, cid)
def pre_pls(uid: int, cid: int) -> bool:    return is_pre(uid, cid)


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


# alias قديم
def isLockCommand(uid: int, cid: int, text: str) -> bool:
    return is_locked(uid, cid, text)


# ─────────────────────────── get_devs (للإشعارات) ──────────────────────────

def get_devs() -> list:
    """يُرجع قائمة بكل معرّفات المطورين (DEV_ID + botowner + DEV2 + DEV)"""
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
    return list(dict.fromkeys(devs))  # remove duplicates, preserve order
