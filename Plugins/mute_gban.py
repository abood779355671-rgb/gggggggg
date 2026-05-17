"""
إدارة الكتم والحظر
أوامر:
  كتم (رد) / كتم @user / كتم عام (رد) / كتم عام @user
  الغاء الكتم (رد) / الغاء الكتم @user / الغاء الكتم العام (رد)
  حظر عام (رد) / حظر عام @user
  حظر عام من الالعاب (رد) / حظر عام من الالعاب @user
  الغاء الحظر العام (رد) / الغاء الحظر العام @user
  الغاء الحظر العام من الالعاب (رد) / الغاء الحظر العام من الالعاب @user
  مسح المكتومين / مسح المكتومين عام / مسح المحظورين عام
"""
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from config import r, DEV_ID, botkey, ar
from helpers.ranks import (
    get_rank, is_admin, is_mod, is_dev, is_pre,
)
from helpers.utils import group_enabled, resolve_text, can_speak, is_gbanned


# ───────────────────────── مساعد استخراج المستخدم ─────────────────────────

async def _resolve_user(c: Client, m: Message, target: str):
    if target is None and m.reply_to_message and m.reply_to_message.from_user:
        u = m.reply_to_message.from_user
        return u.id, u.mention
    if target is None:
        return None, None
    try:
        uid = int(target)
    except ValueError:
        uid = target.lstrip("@")
    try:
        u = await c.get_users(uid)
        return u.id, u.mention
    except Exception:
        return None, None


# ───────────────────────── حذف رسائل المكتوم/المحظور ─────────────────────

@Client.on_message(filters.group, group=15)
async def enforce_mute_gban(c: Client, m: Message):
    if not m.from_user:
        return
    uid = m.from_user.id
    cid = m.chat.id

    if is_gbanned(uid):
        try:
            await m.chat.ban_member(uid)
        except Exception:
            try:
                await m.delete()
            except Exception:
                pass
        return

    if not can_speak(uid, cid):
        try:
            await m.delete()
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
        except Exception:
            pass


# ───────────────────────── معالج أوامر الكتم/الحظر ────────────────────────

@Client.on_message(filters.text & filters.group, group=14)
async def mute_handler(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not can_speak(uid, cid):
        return

    text = resolve_text(m.text, cid)
    k    = botkey()

    # ── كتم (بالردّ) ───────────────────────────────────────────────────────
    if text == "كتم" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if target_id == uid:
            return await m.reply(f"{k} ما تقدر تكتم نفسك 😅")
        if is_pre(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"{cid}:listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه ✅\n☆")

    # ── كتم @user أو كتم id ────────────────────────────────────────────────
    m_local = re.fullmatch(r"كتم\s+(@?\S+)", text)
    if m_local:
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        target_id, target_mention = await _resolve_user(c, m, m_local.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        if target_id == uid:
            return await m.reply(f"{k} ما تقدر تكتم نفسك 😅")
        if is_pre(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"{cid}:listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه ✅\n☆")

    # ── كتم عام (بالردّ) ───────────────────────────────────────────────────
    if text == "كتم عام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم عاماً مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه عاماً ✅\n☆")

    # ── كتم عام @user ──────────────────────────────────────────────────────
    m_gmute = re.fullmatch(r"كتم عام\s+(@?\S+)", text)
    if m_gmute:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_gmute.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم عاماً مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه عاماً ✅\n☆")

    # ── الغاء الكتم (بالردّ) ──────────────────────────────────────────────
    if text == "الغاء الكتم" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"{cid}:listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم ✅\n༄")

    # ── الغاء الكتم @user ─────────────────────────────────────────────────
    m_unmute = re.fullmatch(r"الغاء الكتم\s+(@?\S+)", text)
    if m_unmute:
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        target_id, target_mention = await _resolve_user(c, m, m_unmute.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"{cid}:listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم ✅\n☆")

    # ── الغاء الكتم العام (بالردّ) ────────────────────────────────────────
    if text == "الغاء الكتم العام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:mute:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم العام ✅\n☆")

    # ── الغاء الكتم العام @user ───────────────────────────────────────────
    m_ungmute = re.fullmatch(r"الغاء الكتم العام\s+(@?\S+)", text)
    if m_ungmute:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_ungmute.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:mute:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listMUTE:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم العام ✅\n☆")

    # ── حظر عام (بالردّ) ─────────────────────────────────────────────────
    if text == "حظر عام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تحظر {get_rank(target_id, cid)}")
        key = f"{target_id}:gban:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور عاماً مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listGBAN:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره عاماً 🔴\n☆")

    # ── حظر عام @user ─────────────────────────────────────────────────────
    m_gban = re.fullmatch(r"حظر عام\s+(@?\S+)", text)
    if m_gban:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_gban.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تحظر {get_rank(target_id, cid)}")
        key = f"{target_id}:gban:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور عاماً مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listGBAN:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره عاماً 🔴\n☆")

    # ── حظر عام من الالعاب (بالردّ) ─────────────────────────────────────
    if text == "حظر عام من الالعاب" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تحظر {get_rank(target_id, cid)}")
        key = f"{target_id}:gbangames:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور من الالعاب مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listGBANGAMES:{DEV_ID}", target_id)
        pipe.execute()
        pipe = r.pipeline()
        pipe.delete(f"{target_id}:Floos")
        pipe.srem("BankList", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره من الالعاب عاماً 🔴\n☆")

    # ── حظر عام من الالعاب @user ─────────────────────────────────────────
    m_gbangames = re.fullmatch(r"حظر عام من الالعاب\s+(@?\S+)", text)
    if m_gbangames:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_gbangames.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تحظر {get_rank(target_id, cid)}")
        key = f"{target_id}:gbangames:{DEV_ID}"
        if await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور من الالعاب مسبقاً")
        pipe = r.pipeline()
        pipe.set(key, 1)
        pipe.sadd(f"listGBANGAMES:{DEV_ID}", target_id)
        pipe.execute()
        pipe = r.pipeline()
        pipe.delete(f"{target_id}:Floos")
        pipe.srem("BankList", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره من الالعاب عاماً 🔴\n☆")

    # ── الغاء الحظر العام (بالردّ) ───────────────────────────────────────
    if text == "الغاء الحظر العام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:gban:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listGBAN:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الحظر العام ✅\n☆")

    # ── الغاء الحظر العام @user ───────────────────────────────────────────
    m_ungban = re.fullmatch(r"الغاء الحظر العام\s+(@?\S+)", text)
    if m_ungban:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_ungban.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:gban:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listGBAN:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الحظر العام ✅\n☆")

    # ── الغاء الحظر العام من الالعاب (بالردّ) ───────────────────────────
    if text == "الغاء الحظر العام من الالعاب" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:gbangames:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور من الالعاب عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listGBANGAMES:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع حظره من الالعاب ✅\n☆")

    # ── الغاء الحظر العام من الالعاب @user ──────────────────────────────
    m_ungbangames = re.fullmatch(r"الغاء الحظر العام من الالعاب\s+(@?\S+)", text)
    if m_ungbangames:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_ungbangames.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:gbangames:{DEV_ID}"
        if not await ar.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور من الالعاب عاماً")
        pipe = r.pipeline()
        pipe.delete(key)
        pipe.srem(f"listGBANGAMES:{DEV_ID}", target_id)
        pipe.execute()
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع حظره من الالعاب ✅\n☆")

    # ── مسح المكتومين (في المجموعة) ─────────────────────────────────────
    if text == "مسح المكتومين":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المدير وفوق فقط")
        muted = await ar.smembers(f"{cid}:listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} لا يوجد مكتومون")
        count = 0
        for mid in list(muted):
            await ar.srem(f"{cid}:listMUTE:{DEV_ID}", mid)
            await ar.delete(f"{mid}:mute:{cid}:{DEV_ID}")
            count += 1
        return await m.reply(f"{k} تم مسح ( {count} ) مكتوم\n☆")

    # ── مسح المكتومين عام ────────────────────────────────────────────────
    if text == "مسح المكتومين عام":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        muted = await ar.smembers(f"listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} لا يوجد مكتومون عاماً")
        count = 0
        for mid in list(muted):
            await ar.srem(f"listMUTE:{DEV_ID}", mid)
            await ar.delete(f"{mid}:mute:{DEV_ID}")
            count += 1
        return await m.reply(f"{k} تم مسح ( {count} ) مكتوم عام\n☆")

    # ── مسح المحظورين عام ────────────────────────────────────────────────
    if text == "مسح المحظورين عام":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        gbanned = await ar.smembers(f"listGBAN:{DEV_ID}")
        if not gbanned:
            return await m.reply(f"{k} لا يوجد محظورون عاماً")
        count = 0
        for gid in list(gbanned):
            await ar.srem(f"listGBAN:{DEV_ID}", gid)
            await ar.delete(f"{gid}:gban:{DEV_ID}")
            count += 1
        return await m.reply(f"{k} تم مسح ( {count} ) محظور عام\n☆")

    # ── قائمة المكتومين ───────────────────────────────────────────────────
    if text == "قائمة المكتومين":
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        muted = await ar.smembers(f"{cid}:listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} لا يوجد أحد مكتوم")
        lines = "\n".join(f"• `{mid}`" for mid in muted)
        return await m.reply(f"{k} المكتومون:\n{lines}")
