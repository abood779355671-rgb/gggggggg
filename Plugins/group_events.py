"""
أحداث المجموعة - تتبع الأحداث وإعلام المطور
"""
from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated

from config import r, DEV_ID, botkey
from helpers.ranks import is_dev, get_rank
from helpers.utils import group_enabled


@Client.on_message(filters.left_chat_member, group=6)
async def on_left_member(c: Client, m: Message):
    """عند مغادرة عضو"""
    cid = m.chat.id
    if not group_enabled(cid):
        return
    if not r.get(f"{cid}:trackLeave:{DEV_ID}"):
        return
    k = botkey()
    try:
        await m.reply(
            f"{k} غادر المجموعة: {m.left_chat_member.mention}",
            disable_web_page_preview=True,
        )
    except Exception:
        pass


@Client.on_message(filters.text & filters.group, group=8)
async def group_settings(c: Client, m: Message):
    """إعدادات متعلقة بأحداث المجموعة"""
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return

    text = m.text.strip() if m.text else ""
    k    = botkey()

    if text == "تفعيل مغادرة":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        r.set(f"{cid}:trackLeave:{DEV_ID}", 1)
        return await m.reply(f"{k} سيتم الإعلان عن مغادرة الأعضاء ✅")

    if text == "تعطيل مغادرة":
        if not is_dev(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمطور فقط")
        r.delete(f"{cid}:trackLeave:{DEV_ID}")
        return await m.reply(f"{k} تم تعطيل إعلان المغادرة")

    if text == "معلومات":
        rank = get_rank(uid, cid)
        me   = await c.get_me()
        members_count = await c.get_chat_members_count(cid)
        return await m.reply(
            f"{k} **معلومات المجموعة**\n\n"
            f"الاسم: **{m.chat.title}**\n"
            f"الأيدي: `{cid}`\n"
            f"عدد الأعضاء: **{members_count}**\n\n"
            f"{k} **معلوماتك**\n"
            f"الاسم: {m.from_user.mention}\n"
            f"الأيدي: `{uid}`\n"
            f"رتبتك: **{rank}**"
        )
