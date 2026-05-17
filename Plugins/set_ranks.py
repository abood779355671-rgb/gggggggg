"""
نظام الرفع والتنزيل - أوامر تعيين وإزالة الرتب
أوامر الرفع:
  رفع Dev @user / رد      → رفع إلى Dev²🎖 (يحتاج botowner)
  رفع MY @user / رد       → رفع إلى Myth🎖️ (يحتاج Dev²)
  رفع مالك اساسي @user   → يحتاج gowner وفوق
  رفع مالك @user          → يحتاج gowner
  رفع مدير @user          → يحتاج owner
  رفع ادمن @user          → يحتاج mod
  رفع مميز @user          → يحتاج admin
  تعطيل الرفع / تفعيل الرفع → يحتاج owner
أوامر التنزيل:
  تنزيل Dev / تنزيل MY / تنزيل مالك اساسي / تنزيل مالك
  تنزيل مدير / تنزيل ادمن / تنزيل مميز / تنزيل الكل
"""

import re
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message

from config import r, DEV_ID, botkey
from helpers.ranks import (
    get_rank, is_dev, is_botowner, is_dev2, is_myth,
    is_gowner, is_owner, is_mod, is_admin, is_pre,
    rank_cache_invalidate, isLockCommand,
)
from helpers.utils import group_enabled, can_speak, resolve_text


def _key(cid, rkey, uid):
    """تنسيق مفاتيح Redis الموحّد"""
    return f"{cid}:{rkey}:{uid}:{DEV_ID}"

def _list_key(cid, rkey):
    return f"{cid}:{rkey}s:{DEV_ID}"


async def _resolve_target(c: Client, m: Message, text_part: str | None):
    if text_part is None:
        if m.reply_to_message and m.reply_to_message.from_user:
            u = m.reply_to_message.from_user
            return u.id, u.mention
        return None, None
    try:
        uid = int(text_part)
    except ValueError:
        uid = text_part.lstrip("@")
    try:
        u = await c.get_users(uid)
        return u.id, u.mention
    except Exception:
        return None, None


def _self_check(m, target_id):
    return target_id == m.from_user.id

def _dev_check(target_id):
    return target_id == int(DEV_ID)


@Client.on_message(filters.text & filters.group, group=7)
async def set_ranks_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    if isLockCommand(uid, cid, text):
        return

    # ── تعطيل / تفعيل الرفع ──────────────────────────────────────────────
    if text == "تعطيل الرفع":
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        if r.get(f"{cid}:disableRanks:{DEV_ID}"):
            return await m.reply(f"{k} من「 {m.from_user.mention} 」\n{k} الرفع معطل من قبل\n☆")
        r.set(f"{cid}:disableRanks:{DEV_ID}", 1)
        return await m.reply(f"{k} من「 {m.from_user.mention} 」\n{k} ابشر عطلت الرفع\n☆")

    if text == "تفعيل الرفع":
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        if not r.get(f"{cid}:disableRanks:{DEV_ID}"):
            return await m.reply(f"「 {m.from_user.mention} 」\n{k} الرفع مفعل من قبل\n☆")
        r.delete(f"{cid}:disableRanks:{DEV_ID}")
        return await m.reply(f"{k} من「 {m.from_user.mention} 」\n{k} ابشر فعلت الرفع\n☆")

    if r.get(f"{cid}:disableRanks:{DEV_ID}"):
        return

    rank = get_rank(uid, cid)

    # ─────────── دوال مساعدة لرفع / تنزيل ────────────────────────────────
    async def do_promote(rkey: str, list_rkey: str, rank_label: str, checker, extra_keys_to_clear=None):
        """checker = الدالة التي تتحقق من رتبة الشخص المُرفَّع"""
        # استخراج الهدف
        parts  = text.split()
        raw    = parts[-1] if len(parts) > 2 else None
        has_at = raw and (raw.startswith("@") or raw.lstrip("-").isdigit()) if raw else False

        if has_at:
            target_id, mention = await _resolve_target(c, m, raw)
        else:
            target_id, mention = await _resolve_target(c, m, None)

        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _self_check(m, target_id):
            return await m.reply(f"{k} هطف تبي ترفع نفسك؟")
        if _dev_check(target_id):
            return await m.reply("ركز حبيبي كيف ارفع نفسي")

        key = _key(cid, rkey, target_id)
        if r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} {rank_label} من قبل\n☆")

        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(_list_key(cid, rkey), target_id)
        pipe.execute()
        rank_cache_invalidate(target_id, cid)
        # رفع الكتم إذا موجود
        _clear_mute(target_id, cid)
        return await m.reply(f"{k} الحلو 「 {mention} 」\n{k} رفعته صار {rank_label}\n☆")

    async def do_demote(rkey: str, list_rkey: str, rank_label: str):
        parts  = text.split()
        raw    = parts[-1] if len(parts) > 2 else None
        has_at = raw and (raw.startswith("@") or raw.lstrip("-").isdigit()) if raw else False

        if has_at:
            target_id, mention = await _resolve_target(c, m, raw)
        else:
            target_id, mention = await _resolve_target(c, m, None)

        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _dev_check(target_id):
            return await m.reply("ركز حبيبي كيف انزل نفسي")
        if rank == get_rank(target_id, cid):
            return await m.reply("نفس رتبتك ترا")

        key = _key(cid, rkey, target_id)
        if not r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} مو {rank_label}\n☆")

        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(_list_key(cid, rkey), target_id)
        pipe.execute()
        rank_cache_invalidate(target_id, cid)
        return await m.reply(f"「 {mention} 」\n{k} نزلته من {rank_label}\n☆")

    def _clear_mute(tid, c_id):
        r.delete(f"{tid}:mute:{DEV_ID}")
        r.srem(f"listMUTE:{DEV_ID}", tid)
        r.delete(f"{tid}:mute:{c_id}:{DEV_ID}")
        r.srem(f"{c_id}:listMUTEs:{DEV_ID}", tid)

    # ═══════════════════════════════════════════════════════════════════════
    # ── أوامر الرفع ────────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    # رفع Dev² (يحتاج botowner)
    if re.match(r"^رفع Dev($| .+)", text):
        if not is_botowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( Dev🎖️ ) بس")
        # تحقق إضافي: لا يرفع Myth أو فوق
        parts = text.split()
        raw = parts[-1] if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()) else None
        target_id, mention = await _resolve_target(c, m, raw)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _self_check(m, target_id): return await m.reply(f"{k} هطف تبي ترفع نفسك؟")
        if _dev_check(target_id):     return await m.reply("ركز حبيبي كيف ارفع نفسي")
        key = f"{target_id}:rankDEV2:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} Dev²🎖 من قبل\n☆")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"{DEV_ID}:DEV2", target_id)
        rank_cache_invalidate(target_id, cid)
        _clear_mute(target_id, cid)
        return await m.reply(f"{k} الحلو 「 {mention} 」\n{k} رفعته صار Dev²🎖\n☆")

    # رفع Myth (يحتاج Dev²)
    if re.match(r"^رفع MY($| .+)", text):
        if not is_dev2(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس")
        parts = text.split()
        raw = parts[-1] if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()) else None
        target_id, mention = await _resolve_target(c, m, raw)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _self_check(m, target_id): return await m.reply(f"{k} هطف تبي ترفع نفسك؟")
        if _dev_check(target_id):     return await m.reply("ركز حبيبي كيف ارفع نفسي")
        if rank == get_rank(target_id, cid): return await m.reply("نفس رتبتك ترا")
        key = f"{target_id}:rankDEV:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} Myth🎖️ من قبل\n☆")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"{DEV_ID}:DEV", target_id)
        rank_cache_invalidate(target_id, cid)
        _clear_mute(target_id, cid)
        return await m.reply(f"{k} الحلو 「 {mention} 」\n{k} رفعته صار Myth🎖️\n☆")

    # رفع مالك اساسي (يحتاج gowner)
    if re.match(r"^رفع مالك اساسي($| .+)", text):
        if not is_gowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك الاساسي وفوق ) بس")
        return await do_promote("rankGOWNER", "rankGOWNERs", "المالك الاساسي", is_gowner)

    # رفع مالك (يحتاج gowner)
    if re.match(r"^رفع مالك($| .+)", text):
        if not is_gowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك الاساسي ) بس")
        return await do_promote("rankOWNER", "rankOWNERs", "المالك", is_owner)

    # رفع مدير (يحتاج owner)
    if re.match(r"^رفع مدير($| .+)", text):
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        return await do_promote("rankMOD", "rankMODs", "المدير", is_mod)

    # رفع ادمن (يحتاج mod)
    if re.match(r"^رفع ادمن($| .+)", text):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        return await do_promote("rankADMIN", "rankADMINs", "الادمن", is_admin)

    # رفع مميز (يحتاج admin)
    if re.match(r"^رفع مميز($| .+)", text):
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( الادمن وفوق ) بس")
        return await do_promote("rankPRE", "rankPREs", "المميز", is_pre)

    # ═══════════════════════════════════════════════════════════════════════
    # ── أوامر التنزيل ──────────────────────────────────────────────────────
    # ═══════════════════════════════════════════════════════════════════════

    if re.match(r"^تنزيل Dev($| .+)", text):
        if not is_botowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( Dev🎖️ ) بس")
        parts = text.split()
        raw = parts[-1] if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()) else None
        target_id, mention = await _resolve_target(c, m, raw)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _dev_check(target_id): return await m.reply("ركز حبيبي كيف انزل نفسي")
        key = f"{target_id}:rankDEV2:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} مو Dev²🎖\n☆")
        r.delete(key)
        r.srem(f"{DEV_ID}:DEV2", target_id)
        rank_cache_invalidate(target_id, cid)
        return await m.reply(f"「 {mention} 」\n{k} نزلته من Dev²🎖\n☆")

    if re.match(r"^تنزيل MY($| .+)", text):
        if not is_dev2(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( Dev²🎖️ وفوق ) بس")
        parts = text.split()
        raw = parts[-1] if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()) else None
        target_id, mention = await _resolve_target(c, m, raw)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _dev_check(target_id): return await m.reply("ركز حبيبي كيف انزل نفسي")
        if rank == get_rank(target_id, cid): return await m.reply("نفس رتبتك ترا")
        key = f"{target_id}:rankDEV:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {mention} 」\n{k} مو Myth🎖️ من قبل\n☆")
        r.delete(key)
        r.srem(f"{DEV_ID}:DEV", target_id)
        rank_cache_invalidate(target_id, cid)
        return await m.reply(f"「 {mention} 」\n{k} نزلته من Myth🎖️\n☆")

    if re.match(r"^تنزيل مالك اساسي($| .+)", text):
        if not is_gowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك الاساسي وفوق ) بس")
        return await do_demote("rankGOWNER", "rankGOWNERs", "المالك الاساسي")

    if re.match(r"^تنزيل مالك($| .+)", text):
        if not is_gowner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك الاساسي ) بس")
        return await do_demote("rankOWNER", "rankOWNERs", "المالك")

    if re.match(r"^تنزيل مدير($| .+)", text):
        if not is_owner(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المالك وفوق ) بس")
        return await do_demote("rankMOD", "rankMODs", "المدير")

    if re.match(r"^تنزيل ادمن($| .+)", text):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        return await do_demote("rankADMIN", "rankADMINs", "الادمن")

    if re.match(r"^تنزيل مميز($| .+)", text):
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( الادمن وفوق ) بس")
        return await do_demote("rankPRE", "rankPREs", "المميز")

    # تنزيل الكل
    if re.match(r"^تنزيل الكل($| .+)", text):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")

        parts = text.split()
        raw = parts[-1] if len(parts) > 1 and (parts[-1].startswith("@") or parts[-1].lstrip("-").isdigit()) else None
        target_id, mention = await _resolve_target(c, m, raw)
        if target_id is None:
            return await m.reply(f"{k} حدد المستخدم برد أو يوزر/آيدي")
        if _dev_check(target_id): return await m.reply("ركز حبيبي كيف انزل نفسي")
        if target_id == uid:       return await m.reply(f"{k} مافيك تنزل نفسك")
        if rank == get_rank(target_id, cid): return await m.reply("نفس رتبتك ترا")

        t_level   = 0
        my_level  = 0
        from helpers.ranks import _get_rank_level
        t_level  = _get_rank_level(target_id, cid)
        my_level = _get_rank_level(uid, cid)

        if t_level >= my_level:
            return await m.reply(f"{k} رتبته اعلى منك أو مساوية")

        t_rank_name = get_rank(target_id, cid)
        # حذف كل الرتب حسب المستوى
        rank_map = [
            (7, f"{target_id}:rankDEV2:{DEV_ID}",          f"{DEV_ID}:DEV2"),
            (6, f"{target_id}:rankDEV:{DEV_ID}",            f"{DEV_ID}:DEV"),
            (5, _key(cid, "rankGOWNER", target_id),         _list_key(cid, "rankGOWNER")),
            (4, _key(cid, "rankOWNER",  target_id),         _list_key(cid, "rankOWNER")),
            (3, _key(cid, "rankMOD",    target_id),         _list_key(cid, "rankMOD")),
            (2, _key(cid, "rankADMIN",  target_id),         _list_key(cid, "rankADMIN")),
            (1, _key(cid, "rankPRE",    target_id),         _list_key(cid, "rankPRE")),
        ]
        pipe = r.pipeline()
        for lvl, rkey, lkey in rank_map:
            if lvl < my_level:
                pipe.delete(rkey)
                pipe.srem(lkey, target_id)
        pipe.execute()

        rank_cache_invalidate(target_id, cid)
        return await m.reply(f"「 {mention} 」\n{k} نزلته من {t_rank_name}\n☆")
