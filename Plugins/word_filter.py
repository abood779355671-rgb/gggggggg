"""
فلتر الكلمات السيئة
أوامر:
  اضف كلمة [كلمة]        → إضافة كلمة محظورة
  حذف كلمة [كلمة]        → حذف كلمة من القائمة
  الكلمات المحظورة        → عرض القائمة
  تفعيل فلتر الكلمات      → تشغيل الفلتر
  تعطيل فلتر الكلمات      → إيقاف الفلتر
"""
import re
from pyrogram import Client, filters
from pyrogram.types import Message

from config import r, DEV_ID, botkey, cached_smembers
from helpers.ranks import is_mod, is_pre
from helpers.utils import group_enabled, resolve_text


@Client.on_message(filters.text & filters.group, group=13)
async def word_filter_commands(c: Client, m: Message):
    if not m.from_user:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    text = resolve_text(m.text, cid)
    k    = botkey()

    add_m = re.fullmatch(r"اضف كلمة\s+(.+)", text)
    if add_m:
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        word = add_m.group(1).strip().lower()
        r.sadd(f"{cid}:badwords:{DEV_ID}", word)
        return await m.reply(f"{k} تم إضافة الكلمة المحظورة: `{word}` ✅")

    del_m = re.fullmatch(r"حذف كلمة\s+(.+)", text)
    if del_m:
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        word = del_m.group(1).strip().lower()
        r.srem(f"{cid}:badwords:{DEV_ID}", word)
        return await m.reply(f"{k} تم حذف الكلمة: `{word}` ✅")

    if text == "الكلمات المحظورة":
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        words = cached_smembers(f"{cid}:badwords:{DEV_ID}")
        if not words:
            return await m.reply(f"{k} لا توجد كلمات محظورة")
        return await m.reply(
            f"{k} الكلمات المحظورة:\n" +
            "\n".join(f"• `{w}`" for w in sorted(words))
        )

    if text in ("تفعيل فلتر الكلمات",):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.set(f"{cid}:wordfilter:{DEV_ID}", 1)
        return await m.reply(f"{k} تم تفعيل فلتر الكلمات ✅")

    if text in ("تعطيل فلتر الكلمات",):
        if not is_mod(uid, cid):
            return await m.reply(f"{k} هذا الأمر للمدير وفوق فقط")
        r.delete(f"{cid}:wordfilter:{DEV_ID}")
        return await m.reply(f"{k} تم تعطيل فلتر الكلمات")


@Client.on_message(filters.text & filters.group, group=12)
async def apply_word_filter(c: Client, m: Message):
    """يحذف الرسائل التي تحتوي كلمات محظورة"""
    if not m.from_user or not m.text:
        return
    cid, uid = m.chat.id, m.from_user.id
    if not group_enabled(cid):
        return
    if not r.get(f"{cid}:wordfilter:{DEV_ID}"):
        return
    # الإداريون والمميزون محصّنون
    if is_pre(uid, cid):
        return

    words = cached_smembers(f"{cid}:badwords:{DEV_ID}")
    if not words:
        return

    msg_lower = m.text.lower()
    for w in words:
        if w in msg_lower:
            try:
                await m.delete()
                k = botkey()
                await m.reply(f"{k} {m.from_user.mention}، رسالتك تحتوي كلمة محظورة 🚫")
            except Exception:
                pass
            return
