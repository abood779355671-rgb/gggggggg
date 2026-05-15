"""
إدارة الكتم والحظر
أوامر:
  كتم (رد) / كتم @user / كتم عام (رد) / كتم عام @user
  الغاء الكتم (رد) / الغاء الكتم @user / الغاء الكتم العام (رد)
  حظر عام (رد) / حظر عام @user
  الغاء الحظر العام (رد) / الغاء الحظر العام @user
"""
import asyncio
import re
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import Message

from config import r, DEV_ID, botkey
from helpers.ranks import (
    get_rank, is_admin, is_mod, is_dev, is_pre,
)
from helpers.utils import group_enabled, resolve_text, can_speak, is_gbanned


# ───────────────────────── مساعد استخراج المستخدم ─────────────────────────

async def _resolve_user(c: Client, m: Message, target: str):
    """
    يُرجع (id, mention) من ردّ أو نص (@user أو id).
    يُرجع None إذا لم يُجد المستخدم.
    """
    # من الردّ
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
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المدير وفوق فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if target_id == uid:
            return await m.reply(f"{k} ما تقدر تكتم نفسك 😅")
        if is_pre(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم مسبقاً")
        r.set(key, 1)
        r.sadd(f"{cid}:listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه ✅")

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
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم مسبقاً")
        r.set(key, 1)
        r.sadd(f"{cid}:listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه ✅")

    # ── كتم عام (بالردّ) ───────────────────────────────────────────────────
    if text == "كتم عام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تكتم {get_rank(target_id, cid)}")
        key = f"{target_id}:mute:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم عاماً مسبقاً")
        r.set(key, 1)
        r.sadd(f"listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه عاماً ✅")

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
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} مكتوم عاماً مسبقاً")
        r.set(key, 1)
        r.sadd(f"listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم كتمه عاماً ✅")

    # ── الغاء الكتم (بالردّ) ──────────────────────────────────────────────
    if text == "الغاء الكتم" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم")
        r.delete(key)
        r.srem(f"{cid}:listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم ✅")

    # ── الغاء الكتم @user ─────────────────────────────────────────────────
    m_unmute = re.fullmatch(r"الغاء الكتم\s+(@?\S+)", text)
    if m_unmute:
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المدير وفوق فقط")
        target_id, target_mention = await _resolve_user(c, m, m_unmute.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:mute:{cid}:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم")
        r.delete(key)
        r.srem(f"{cid}:listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم ✅")

    # ── الغاء الكتم العام (بالردّ) ────────────────────────────────────────
    if text == "الغاء الكتم العام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:mute:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير مكتوم عاماً")
        r.delete(key)
        r.srem(f"listMUTE:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الكتم العام ✅")

    # ── حظر عام (بالردّ) ─────────────────────────────────────────────────
    if text == "حظر عام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        if is_dev(target_id, cid):
            return await m.reply(f"{k} ما تقدر تحظر {get_rank(target_id, cid)}")
        key = f"{target_id}:gban:{DEV_ID}"
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور عاماً مسبقاً")
        r.set(key, 1)
        r.sadd(f"listGBAN:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره عاماً 🔴")

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
        if r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} محظور عاماً مسبقاً")
        r.set(key, 1)
        r.sadd(f"listGBAN:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم حظره عاماً 🔴")

    # ── الغاء الحظر العام (بالردّ) ───────────────────────────────────────
    if text == "الغاء الحظر العام" and m.reply_to_message and m.reply_to_message.from_user:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id   = m.reply_to_message.from_user.id
        target_mention = m.reply_to_message.from_user.mention
        key = f"{target_id}:gban:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور عاماً")
        r.delete(key)
        r.srem(f"listGBAN:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الحظر العام ✅")

    # ── الغاء الحظر العام @user ───────────────────────────────────────────
    m_ungban = re.fullmatch(r"الغاء الحظر العام\s+(@?\S+)", text)
    if m_ungban:
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص المطور فقط")
        target_id, target_mention = await _resolve_user(c, m, m_ungban.group(1))
        if target_id is None:
            return await m.reply(f"{k} ما لقيت هذا المستخدم")
        key = f"{target_id}:gban:{DEV_ID}"
        if not r.get(key):
            return await m.reply(f"「 {target_mention} 」\n{k} غير محظور عاماً")
        r.delete(key)
        r.srem(f"listGBAN:{DEV_ID}", target_id)
        return await m.reply(f"「 {target_mention} 」\n{k} تم رفع الحظر العام ✅")

    # ── قائمة المكتومين ───────────────────────────────────────────────────
    if text == "قائمة المكتومين":
        if not is_admin(uid, cid):
            return await m.reply(f"{k} هذا الأمر يخص الادمن وفوق فقط")
        muted = r.smembers(f"{cid}:listMUTE:{DEV_ID}")
        if not muted:
            return await m.reply(f"{k} لا يوجد أحد مكتوم")
        lines = "\n".join(f"• `{mid}`" for mid in muted)
        return await m.reply(f"{k} المكتومون:\n{lines}")
